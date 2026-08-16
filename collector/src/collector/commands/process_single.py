from __future__ import annotations

import asyncio
from pathlib import Path

import httpx
from rich.console import Console
from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn
from rich.panel import Panel
from rich.table import Table
from sqlmodel import SQLModel, Session, col, create_engine, select
from typer import BadParameter, Typer

from shared.models import Image, ImageTags, set_last_updated

from collector.utils.registry import fetch_tags_for_image
from collector.utils.shared import DEFAULT_DB_URL, DEFAULT_REPOS_FILE, ImagePayload, REQUEST_TIMEOUT_SECONDS, count_names, iter_name_file, split_namespace
from collector.utils.storage import persist_image_payload_batch

console = Console()

app = Typer()

def load_existing_tags(session: Session, registry: str, self_hosted: bool) -> dict[tuple[str, str], frozenset[str]]:
    stmt = (
        select(Image.namespace_name, Image.name, ImageTags.name)
        .join(ImageTags, ImageTags.image_id == Image.id)  # type: ignore[arg-type]
        .where(Image.src_registry == registry, Image.self_hosted == self_hosted)
    )
    rows = session.exec(stmt).all()
    accumulated: dict[tuple[str, str], set[str]] = {}
    for namespace, image_name, tag_name in rows:
        if image_name is not None and tag_name is not None:
            accumulated.setdefault((namespace, image_name), set()).add(tag_name)
    return {key: frozenset(values) for key, values in accumulated.items()}


@app.command()
def process_single(
    registry: str,
    url: str = "v2/",
    names_file: Path = DEFAULT_REPOS_FILE,
    db: str = DEFAULT_DB_URL,
    self_hosted: bool = False,
    downloaders: int = 30,
    db_batch_size: int = 200,
    skip_existing: bool = False,
) -> None:
    if not names_file.exists():
        raise BadParameter(f"Names file does not exist: {names_file}")
    asyncio.run(process_async(registry, url, names_file, db, self_hosted, downloaders, db_batch_size, skip_existing))


async def process_async(
    registry: str,
    url: str,
    names_file: Path,
    db: str,
    self_hosted: bool,
    downloaders: int,
    db_batch_size: int,
    skip_existing: bool = False,
) -> None:
    engine = create_engine(db, echo=False)
    SQLModel.metadata.create_all(engine)
    with console.status("[cyan]Counting names...", spinner="dots"):
        total_expected = count_names(names_file)

    existing_tags: dict[tuple[str, str], frozenset[str]] = {}
    if skip_existing:
        with console.status("[cyan]Loading existing tags from DB...", spinner="dots"), Session(engine) as session:
            existing_tags = load_existing_tags(session, registry, self_hosted)
        console.log(f"[cyan]skip-existing[/cyan] loaded {sum(len(values) for values in existing_tags.values())} tags across {len(existing_tags)} images")

    console.print(Panel.fit(
        f"[bold cyan]Registry[/bold cyan]      {registry}\n"
        f"[bold cyan]Url[/bold cyan]           {url}\n"
        f"[bold cyan]Names file[/bold cyan]    {names_file}\n"
        f"[bold cyan]Total names[/bold cyan]   {total_expected}\n"
        f"[bold cyan]Downloaders[/bold cyan]   {downloaders}\n"
        f"[bold cyan]DB batch size[/bold cyan] {db_batch_size}\n"
        f"[bold cyan]Self hosted[/bold cyan]   {self_hosted}\n"
        f"[bold cyan]Skip existing[/bold cyan] {skip_existing}",
        title="[bold]process[/bold]", border_style="cyan",
    ))

    name_queue: asyncio.Queue[str | None] = asyncio.Queue(maxsize=downloaders * 4)
    db_queue: asyncio.Queue[ImagePayload | None] = asyncio.Queue(maxsize=downloaders * 8)
    stats = {"queued": 0, "downloaded": 0, "failed": 0, "processed_tags": 0, "db_batches": 0, "db_records": 0, "skipped_tags": 0}
    batch_tags = {"discovered": 0, "processed": 0}
    progress = Progress(
        SpinnerColumn(), TextColumn("[bold blue]{task.description}"), BarColumn(),
        MofNCompleteColumn(), TextColumn("[progress.percentage]{task.percentage:>5.1f}%"),
        TextColumn("{task.fields[info]}"), TimeElapsedColumn(), TimeRemainingColumn(), console=console,
    )
    image_task = progress.add_task("Images", total=total_expected, info="")
    tag_task = progress.add_task("New tags (batch)", total=0, info="")

    def refresh_task() -> None:
        progress.update(image_task, info=f"ok=[green]{stats['downloaded']}[/green] fail=[red]{stats['failed']}[/red] batches=[cyan]{stats['db_batches']}[/cyan]")
        progress.update(tag_task, info=f"total=[magenta]{stats['processed_tags']}[/magenta] skipped=[yellow]{stats['skipped_tags']}[/yellow]")

    def reset_tag_bar() -> None:
        in_flight = max(batch_tags["discovered"] - batch_tags["processed"], 0)
        batch_tags["discovered"], batch_tags["processed"] = in_flight, 0
        progress.reset(tag_task, total=in_flight, completed=0, info="")
        refresh_task()

    def on_tags_discovered(count: int) -> None:
        batch_tags["discovered"] += count
        progress.update(tag_task, total=batch_tags["discovered"])

    def on_tag_processed() -> None:
        batch_tags["processed"] += 1
        stats["processed_tags"] += 1
        progress.advance(tag_task, 1)
        refresh_task()

    async def producer() -> None:
        for name in iter_name_file(names_file):
            await name_queue.put(name)
            stats["queued"] += 1
        for _ in range(downloaders):
            await name_queue.put(None)

    async def downloader(worker_id: int, client: httpx.AsyncClient) -> None:
        while True:
            item = await name_queue.get()
            if item is None:
                name_queue.task_done()
                break
            namespace_name, image_name = split_namespace(item)
            try:
                tags, skipped = await fetch_tags_for_image(client, registry, url, item, existing_tags.get((namespace_name, image_name), frozenset()), on_tags_discovered, on_tag_processed)
                stats["skipped_tags"] += skipped
                await db_queue.put(ImagePayload(item, namespace_name, image_name, tags))
                stats["downloaded"] += 1
            except Exception as exc:
                stats["failed"] += 1
                console.log(f"[red]worker={worker_id} failed[/red] repo={item} err={exc}")
            finally:
                progress.update(image_task, advance=1)
                refresh_task()
                name_queue.task_done()

    def flush_payloads(session: Session, payloads: list[ImagePayload]) -> int:
        if not payloads:
            return 0
        return persist_image_payload_batch(session, registry, self_hosted, payloads)[2]

    async def db_worker() -> None:
        batch: list[ImagePayload] = []
        with Session(engine) as session:
            while True:
                try:
                    item = await asyncio.wait_for(db_queue.get(), timeout=2.0)
                except TimeoutError:
                    if batch:
                        stats["db_records"] += flush_payloads(session, batch)
                        stats["db_batches"] += 1
                        reset_tag_bar()
                        batch = []
                    continue
                if item is None:
                    db_queue.task_done()
                    if batch:
                        stats["db_records"] += flush_payloads(session, batch)
                        stats["db_batches"] += 1
                        reset_tag_bar()
                    set_last_updated(session)
                    break
                batch.append(item)
                db_queue.task_done()
                if len(batch) >= db_batch_size:
                    stats["db_records"] += flush_payloads(session, batch)
                    stats["db_batches"] += 1
                    reset_tag_bar()
                    batch = []

    with progress:
        async with httpx.AsyncClient(verify=False, timeout=REQUEST_TIMEOUT_SECONDS) as client:
            producer_task = asyncio.create_task(producer())
            db_task = asyncio.create_task(db_worker())
            downloader_tasks = [asyncio.create_task(downloader(index + 1, client)) for index in range(downloaders)]
            await producer_task
            await name_queue.join()
            await asyncio.gather(*downloader_tasks)
            await db_queue.put(None)
            await db_queue.join()
            await db_task

    summary = Table(title="process summary", show_header=False, border_style="green")
    summary.add_column(style="bold cyan")
    summary.add_column()
    summary.add_row("Queued", str(stats["queued"]))
    summary.add_row("Downloaded", f"[green]{stats['downloaded']}[/green]")
    summary.add_row("Failed", f"[red]{stats['failed']}[/red]")
    summary.add_row("DB batches", str(stats["db_batches"]))
    summary.add_row("Tags changed", str(stats["db_records"]))
    summary.add_row("Tags skipped (existing)", f"[yellow]{stats['skipped_tags']}[/yellow]")
    console.print(summary)

