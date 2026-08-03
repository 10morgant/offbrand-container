from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import re
import time
from typing import Any, Iterable, Iterator
from urllib.parse import parse_qs, unquote, urlparse

import httpx
import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.table import Table
from rich.traceback import install as install_rich_traceback
from sqlmodel import SQLModel, Session, col, create_engine, select

from models import Image, ImageTags, Namespace, set_last_updated

install_rich_traceback(show_locals=False)
console = Console()

app = typer.Typer(add_completion=False, rich_markup_mode="rich")

DEFAULT_DB_URL = "postgresql+psycopg2://appuser:StrongPassword123@localhost:5432/docker"
DEFAULT_REPOS_FOLDER = Path("data/")
DEFAULT_REPOS_FOLDER.mkdir(parents=True, exist_ok=True)
DEFAULT_REPOS_FILE = DEFAULT_REPOS_FOLDER/Path("repositories.txt")
REQUEST_TIMEOUT_SECONDS = 180.0
RETRY_STATUS_CODES = {408, 409, 425, 429, 500, 502, 503, 504}
MAX_RETRIES = 6
RETRY_BASE_DELAY = 1.0

# Synthetic namespace used for images without a real namespace (e.g. `nginx` on
# a self-hosted registry). Kept as a valid single character so it can be used in
# URL paths like /namespaces/_/images/nginx without special-casing.
ROOT_NAMESPACE = "library"

# Tag names that are treated as versions even though they aren't numeric.
KEYWORD_VERSIONS = {
    "latest", "stable", "edge", "main", "master", "current",
    "lts", "nightly", "next", "canary", "dev", "rolling",
}

# Matches segments like 1, 1.2, 1.2.3, v1.2.3
_VERSION_RE = re.compile(r"^v?\d+(?:\.\d+)*$", re.IGNORECASE)


def parse_tag(tag: str) -> tuple[str | None, list[str]]:
    """Split a tag like `3.14-slim-bookworm` into (version, [variants])."""
    if not tag:
        return None, []

    parts = tag.split("-")
    version: str | None = None
    variants: list[str] = []

    for part in parts:
        if version is None and (_VERSION_RE.match(part) or part.lower() in KEYWORD_VERSIONS):
            version = part
        else:
            variants.append(part)

    return version, variants


@dataclass
class TagPayload:
    name: str
    digest: str | None
    size: int | None
    media_type: str | None
    created_at: datetime | None
    platforms: str | None
    version: str | None
    variants: str | None


@dataclass
class ImagePayload:
    full_name: str
    namespace_name: str
    image_name: str
    tags: list[TagPayload]


def split_namespace(full_name: str) -> tuple[str, str]:
    if "/" in full_name:
        namespace, image_name = full_name.split("/", 1)
        return namespace, image_name
    return ROOT_NAMESPACE, full_name


def parse_next_last(link_header: str | None) -> str | None:
    if not link_header:
        return None

    link_url = link_header.split(">", 1)[0].lstrip("<")
    query = parse_qs(urlparse(link_url).query)
    last_values = query.get("last")
    if not last_values:
        return None
    return unquote(last_values[0])


def request_with_retries(
    client: httpx.Client,
    method: str,
    url: str,
    debug: bool = True,
    **kwargs: Any,
) -> httpx.Response:
    delay = RETRY_BASE_DELAY

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.request(method, url, **kwargs)
            if debug:
                console.print(f"{response.request.url}")
            if response.status_code in RETRY_STATUS_CODES:
                if attempt == MAX_RETRIES:
                    response.raise_for_status()
                else:
                    console.log(
                        f"[yellow]Retry[/yellow] {method} {url} status={response.status_code} attempt={attempt}/{MAX_RETRIES}"
                    )
                    time.sleep(delay)
                    delay *= 2
                    continue

            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status not in RETRY_STATUS_CODES or attempt == MAX_RETRIES:
                raise
            console.log(
                f"[yellow]Retry[/yellow] {method} {url} status={status} attempt={attempt}/{MAX_RETRIES}"
            )
            time.sleep(delay)
            delay *= 2
        except (httpx.TimeoutException, httpx.TransportError):
            if attempt == MAX_RETRIES:
                raise
            console.log(
                f"[yellow]Retry[/yellow] {method} {url} attempt={attempt}/{MAX_RETRIES}")
            time.sleep(delay)
            delay *= 2

    raise RuntimeError("request_with_retries exhausted all retries")


async def async_request_with_retries(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    **kwargs: Any,
) -> httpx.Response:
    delay = RETRY_BASE_DELAY

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = await client.request(method, url, **kwargs)
            if response.status_code in RETRY_STATUS_CODES:
                if attempt == MAX_RETRIES:
                    response.raise_for_status()
                else:
                    console.log(
                        f"[yellow]Retry[/yellow] {method} {url} status={response.status_code} attempt={attempt}/{MAX_RETRIES}"
                    )
                    await asyncio.sleep(delay)
                    delay *= 2
                    continue

            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status not in RETRY_STATUS_CODES or attempt == MAX_RETRIES:
                raise
            console.log(
                f"[yellow]Retry[/yellow] {method} {url} status={status} attempt={attempt}/{MAX_RETRIES}"
            )
            await asyncio.sleep(delay)
            delay *= 2
        except (httpx.TimeoutException, httpx.TransportError):
            if attempt == MAX_RETRIES:
                raise
            console.log(
                f"[yellow]Retry[/yellow] {method} {url} attempt={attempt}/{MAX_RETRIES}")
            await asyncio.sleep(delay)
            delay *= 2

    raise RuntimeError("async_request_with_retries exhausted all retries")


def iter_name_file(path: Path) -> Iterator[str]:
    with path.open("r", encoding="utf-8") as f:
        for raw in f:
            name = raw.strip()
            if name:
                yield name


def count_names(path: Path) -> int:
    total = 0
    with path.open("r", encoding="utf-8") as f:
        for raw in f:
            if raw.strip():
                total += 1
    return total


def chunked(items: Iterable[str], chunk_size: int) -> Iterator[list[str]]:
    batch: list[str] = []
    for item in items:
        batch.append(item)
        if len(batch) >= chunk_size:
            yield batch
            batch = []
    if batch:
        yield batch


def ensure_namespaces(
    session: Session,
    registry: str,
    namespace_names: set[str],
) -> dict[str, Namespace]:
    if not namespace_names:
        return {}

    existing = session.exec(
        select(Namespace).where(
            Namespace.src_registry == registry,
            col(Namespace.name).in_(namespace_names),
        )
    ).all()

    namespace_by_name = {ns.name: ns for ns in existing}
    missing = namespace_names - set(namespace_by_name)

    if missing:
        session.add_all([Namespace(name=name, src_registry=registry)
                        for name in sorted(missing)])
        session.flush()
        created = session.exec(
            select(Namespace).where(
                Namespace.src_registry == registry,
                col(Namespace.name).in_(missing),
            )
        ).all()
        for ns in created:
            namespace_by_name[ns.name] = ns

    return namespace_by_name


def ensure_images(
    session: Session,
    registry: str,
    self_hosted: bool,
    records: list[tuple[str, str]],
    namespace_by_name: dict[str, Namespace],
) -> dict[tuple[str, str], Image]:
    if not records:
        return {}

    names = {name for _, name in records}

    existing = session.exec(
        select(Image).where(
            Image.src_registry == registry,
            Image.self_hosted == self_hosted,
            col(Image.name).in_(names),
        )
    ).all()

    image_by_key: dict[tuple[str, str], Image] = {}
    for img in existing:
        if img.name is None:
            continue
        image_by_key[(img.namespace_name, img.name)] = img

    missing: list[Image] = []
    for namespace_name, image_name in records:
        key = (namespace_name, image_name)
        if key in image_by_key:
            continue

        namespace = namespace_by_name.get(namespace_name)
        namespace_id = namespace.id if namespace else None

        missing.append(
            Image(
                name=image_name,
                self_hosted=self_hosted,
                src_registry=registry,
                namespace_name=namespace_name,
                namespace_id=namespace_id,
            )
        )

    if missing:
        session.add_all(missing)
        session.flush()
        for image in missing:
            if image.name is not None:
                image_by_key[(image.namespace_name, image.name)] = image

    return image_by_key


def upsert_tags_for_payloads(
    session: Session,
    registry: str,
    image_by_key: dict[tuple[str, str], Image],
    payloads: list[ImagePayload],
) -> tuple[int, int]:
    image_ids = {img.id for img in image_by_key.values() if img.id is not None}
    tag_names = {tag.name for payload in payloads for tag in payload.tags}

    existing_by_key: dict[tuple[int, str], ImageTags] = {}
    if image_ids and tag_names:
        existing_tags = session.exec(
            select(ImageTags).where(
                col(ImageTags.image_id).in_(image_ids),
                col(ImageTags.name).in_(tag_names),
            )
        ).all()
        existing_by_key = {(tag.image_id, tag.name)                           : tag for tag in existing_tags}

    inserted = 0
    updated = 0

    for payload in payloads:
        image = image_by_key[(payload.namespace_name, payload.image_name)]
        image_id = image.id
        if image_id is None:
            continue

        for tag in payload.tags:
            key = (image_id, tag.name)
            row = existing_by_key.get(key)
            if row is None:
                session.add(
                    ImageTags(
                        image_id=image_id,
                        name=tag.name,
                        digest=tag.digest,
                        size=tag.size,
                        media_type=tag.media_type,
                        created_at=tag.created_at,
                        platforms=tag.platforms,
                        version=tag.version,
                        variants=tag.variants,
                        src_registry=registry,
                    )
                )
                inserted += 1
                continue

            row.digest = tag.digest
            row.size = tag.size
            row.media_type = tag.media_type
            row.created_at = tag.created_at
            row.platforms = tag.platforms
            row.version = tag.version
            row.variants = tag.variants
            row.src_registry = registry
            updated += 1

    return inserted, updated


def persist_name_chunk(
    session: Session,
    registry: str,
    self_hosted: bool,
    names: list[str],
) -> tuple[int, int]:
    split_records = [split_namespace(name) for name in names]
    namespace_names = {ns for ns, _ in split_records}
    image_records = list(split_records)

    namespace_by_name = ensure_namespaces(session, registry, namespace_names)
    image_by_key = ensure_images(
        session, registry, self_hosted, image_records, namespace_by_name)

    session.commit()
    return len(namespace_by_name), len(image_by_key)


def persist_image_payload_batch(
    session: Session,
    registry: str,
    self_hosted: bool,
    payloads: list[ImagePayload],
) -> tuple[int, int, int]:
    split_records = [(payload.namespace_name, payload.image_name)
                     for payload in payloads]
    namespace_names = {payload.namespace_name for payload in payloads}

    namespace_by_name = ensure_namespaces(session, registry, namespace_names)
    image_by_key = ensure_images(
        session, registry, self_hosted, split_records, namespace_by_name)
    inserted_tags, updated_tags = upsert_tags_for_payloads(
        session, registry, image_by_key, payloads)

    session.commit()
    return len(namespace_by_name), len(image_by_key), inserted_tags + updated_tags


def parse_created(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def format_platform(platform: dict[str, Any] | None) -> str | None:
    if not platform:
        return None
    os_name = platform.get("os")
    architecture = platform.get("architecture")
    variant = platform.get("variant")
    parts = [part for part in [os_name, architecture, variant] if part]
    return "/".join(parts) if parts else None


async def fetch_tags_for_image(
    client: httpx.AsyncClient,
    registry: str,
    repo_name: str,
    skip_tags: frozenset[str] = frozenset(),
) -> tuple[list[TagPayload], int]:
    try:
        tags_resp = await async_request_with_retries(client, "GET", f"{registry}/v2/{repo_name}/tags/list")
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            console.log(f"[yellow]skip[/yellow] no tags/list for {repo_name}")
            return [], 0
        raise
    tags = tags_resp.json().get("tags") or []

    result: list[TagPayload] = []
    skipped = 0

    for tag_name in tags:
        if not isinstance(tag_name, str) or not tag_name:
            continue

        if tag_name in skip_tags:
            skipped += 1
            continue

        try:
            manifest_resp = await async_request_with_retries(
                client,
                "GET",
                f"{registry}/v2/{repo_name}/manifests/{tag_name}",
                headers={
                    "Accept": (
                        "application/vnd.docker.distribution.manifest.v2+json, "
                        "application/vnd.oci.image.manifest.v1+json, "
                        "application/vnd.docker.distribution.manifest.list.v2+json, "
                        "application/vnd.oci.image.index.v1+json"
                    )
                },
            )
        except httpx.HTTPStatusError as exc:
            # Dangling tag: listed by tags/list but the manifest is gone
            # (common on docker/distribution after manual delete or GC).
            if exc.response.status_code == 404:
                console.log(
                    f"[yellow]skip[/yellow] missing manifest {repo_name}:{tag_name}"
                )
                continue
            raise

        manifest = manifest_resp.json()
        media_type = manifest_resp.headers.get(
            "Content-Type") or manifest.get("mediaType")
        digest = manifest_resp.headers.get("Docker-Content-Digest")

        size = 0
        created_at = None
        platforms: list[str] = []

        if manifest.get("manifests"):
            for entry in manifest["manifests"]:
                if isinstance(entry.get("size"), int):
                    size += entry["size"]
                platform_name = format_platform(entry.get("platform"))
                if platform_name:
                    platforms.append(platform_name)
        else:
            config = manifest.get("config") or {}
            layers = manifest.get("layers") or []

            if isinstance(config.get("size"), int):
                size += config["size"]
            for layer in layers:
                if isinstance(layer.get("size"), int):
                    size += layer["size"]

            config_digest = config.get("digest")
            if isinstance(config_digest, str) and config_digest:
                try:
                    config_resp = await async_request_with_retries(
                        client,
                        "GET",
                        f"{registry}/v2/{repo_name}/blobs/{config_digest}",
                    )
                except httpx.HTTPStatusError as exc:
                    if exc.response.status_code == 404:
                        console.log(
                            f"[yellow]skip[/yellow] missing config blob {repo_name}:{tag_name} {config_digest}"
                        )
                        config_resp = None
                    else:
                        raise

                if config_resp is not None:
                    blob = config_resp.json()
                    created_at = parse_created(blob.get("created"))
                    platform_name = format_platform(
                        {
                            "os": blob.get("os"),
                            "architecture": blob.get("architecture"),
                            "variant": blob.get("variant"),
                        }
                    )
                    if platform_name:
                        platforms.append(platform_name)

        version, variants = parse_tag(tag_name)

        result.append(
            TagPayload(
                name=tag_name,
                digest=digest,
                size=size or None,
                media_type=media_type,
                created_at=created_at,
                platforms=json.dumps(sorted(set(platforms))
                                     ) if platforms else None,
                version=version,
                variants=json.dumps(variants) if variants else None,
            )
        )

    return result, skipped


@app.command()
def fetch(
    registry: str,
    route: str = "/v2/_catalog",
    page_size: int = 100,
    db: str | None = DEFAULT_DB_URL,
    output: Path = DEFAULT_REPOS_FILE,
    last: str | None = None,
) -> None:
    del db

    output.parent.mkdir(parents=True, exist_ok=True)

    console.print(
        Panel.fit(
            f"[bold cyan]Registry[/bold cyan]  {registry}\n"
            f"[bold cyan]Route[/bold cyan]     {route}\n"
            f"[bold cyan]Page size[/bold cyan] {page_size}\n"
            f"[bold cyan]Output[/bold cyan]    {output}\n"
            f"[bold cyan]Start last[/bold cyan] {last or '(none)'}",
            title="[bold]fetch[/bold]",
            border_style="cyan",
        )
    )

    total = 0
    pages = 0
    current_last = last

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]Fetching catalog"),
        TextColumn("pages [green]{task.fields[pages]}[/green]"),
        TextColumn("last=[dim]{task.fields[last]}[/dim]"),
        TimeElapsedColumn(),
        console=console,
        transient=False,
    )

    with progress, httpx.Client(verify=False, timeout=REQUEST_TIMEOUT_SECONDS) as client, output.open(
        "w", encoding="utf-8"
    ) as f:
        task_id = progress.add_task("fetch", pages=0, last=current_last or "-")
        # Explicitly render task before first response for immediate feedback
        progress.update(task_id, pages=0)

        while True:
            params: dict[str, int | str] = {"n": page_size}
            if current_last:
                params["last"] = current_last

            response = request_with_retries(
                client, "GET", f"{registry}{route}", params=params)
            repositories = response.json().get("repositories", [])

            if not repositories:
                break

            for name in repositories:
                f.write(f"{name}\n")

            total += len(repositories)
            pages += 1
            progress.update(
                task_id,
                pages=pages,
                total=total,
                last=(current_last or "-")[:40],
            )

            next_last = parse_next_last(response.headers.get("link"))
            if not next_last or next_last == current_last:
                break
            current_last = next_last

    summary = Table(title="fetch summary",
                    show_header=False, border_style="green")
    summary.add_column(style="bold cyan")
    summary.add_column()
    summary.add_row("Pages", str(pages))
    summary.add_row("Names written", str(total))
    summary.add_row("Output", str(output))
    console.print(summary)


@app.command()
def names(
    registry: str,
    names_file: Path = DEFAULT_REPOS_FILE,
    db: str = DEFAULT_DB_URL,
    self_hosted: bool = False,
    chunk_size: int = 2000,
) -> None:
    if not names_file.exists():
        raise typer.BadParameter(f"Names file does not exist: {names_file}")

    engine = create_engine(db, echo=False)
    SQLModel.metadata.create_all(engine)

    with console.status("[cyan]Counting names...", spinner="dots"):
        total_expected = count_names(names_file)

    console.print(
        Panel.fit(
            f"[bold cyan]Registry[/bold cyan]    {registry}\n"
            f"[bold cyan]Names file[/bold cyan]  {names_file}\n"
            f"[bold cyan]Total names[/bold cyan] {total_expected}\n"
            f"[bold cyan]Chunk size[/bold cyan]  {chunk_size}\n"
            f"[bold cyan]Self hosted[/bold cyan] {self_hosted}",
            title="[bold]names[/bold]",
            border_style="cyan",
        )
    )

    total_names = 0
    total_chunks = 0

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TextColumn("[progress.percentage]{task.percentage:>5.1f}%"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
    )

    with progress, Session(engine) as session:
        task_id = progress.add_task("Persisting names", total=total_expected)

        for chunk in chunked(iter_name_file(names_file), chunk_size):
            persist_name_chunk(session, registry, self_hosted, chunk)
            total_names += len(chunk)
            total_chunks += 1
            progress.update(task_id, advance=len(chunk))

        set_last_updated(session)

    summary = Table(title="names summary",
                    show_header=False, border_style="green")
    summary.add_column(style="bold cyan")
    summary.add_column()
    summary.add_row("Names processed", str(total_names))
    summary.add_row("Chunks", str(total_chunks))
    console.print(summary)


def load_existing_tags(
    session: Session,
    registry: str,
    self_hosted: bool,
) -> dict[tuple[str, str], frozenset[str]]:
    stmt = (
        select(Image.namespace_name, Image.name, ImageTags.name)
        .join(ImageTags, ImageTags.image_id == Image.id)  # type: ignore[arg-type]
        .where(Image.src_registry == registry, Image.self_hosted == self_hosted)
    )
    rows = session.exec(stmt).all()
    acc: dict[tuple[str, str], set[str]] = {}
    for ns, img_name, tag_name in rows:
        if img_name is None or tag_name is None:
            continue
        acc.setdefault((ns, img_name), set()).add(tag_name)
    return {key: frozenset(values) for key, values in acc.items()}


@app.command()
def process(
    registry: str,
    names_file: Path = DEFAULT_REPOS_FILE,
    db: str = DEFAULT_DB_URL,
    self_hosted: bool = False,
    downloaders: int = 30,
    db_batch_size: int = 200,
    skip_existing: bool = False,
) -> None:
    if not names_file.exists():
        raise typer.BadParameter(f"Names file does not exist: {names_file}")

    asyncio.run(
        process_async(
            registry=registry,
            names_file=names_file,
            db=db,
            self_hosted=self_hosted,
            downloaders=downloaders,
            db_batch_size=db_batch_size,
            skip_existing=skip_existing,
        )
    )


async def process_async(
    registry: str,
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
        existing_tag_count = sum(len(v) for v in existing_tags.values())
        console.log(
            f"[cyan]skip-existing[/cyan] loaded {existing_tag_count} tags "
            f"across {len(existing_tags)} images"
        )

    console.print(
        Panel.fit(
            f"[bold cyan]Registry[/bold cyan]      {registry}\n"
            f"[bold cyan]Names file[/bold cyan]    {names_file}\n"
            f"[bold cyan]Total names[/bold cyan]   {total_expected}\n"
            f"[bold cyan]Downloaders[/bold cyan]   {downloaders}\n"
            f"[bold cyan]DB batch size[/bold cyan] {db_batch_size}\n"
            f"[bold cyan]Self hosted[/bold cyan]   {self_hosted}\n"
            f"[bold cyan]Skip existing[/bold cyan] {skip_existing}",
            title="[bold]process[/bold]",
            border_style="cyan",
        )
    )

    name_queue: asyncio.Queue[str | None] = asyncio.Queue(
        maxsize=downloaders * 4)
    db_queue: asyncio.Queue[ImagePayload |
                            None] = asyncio.Queue(maxsize=downloaders * 8)

    stats = {
        "queued": 0,
        "downloaded": 0,
        "failed": 0,
        "db_batches": 0,
        "db_records": 0,
        "skipped_tags": 0,
    }

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TextColumn("[progress.percentage]{task.percentage:>5.1f}%"),
        TextColumn(
            "ok=[green]{task.fields[ok]}[/green] fail=[red]{task.fields[fail]}[/red] "
            "batches=[cyan]{task.fields[batches]}[/cyan] tags=[magenta]{task.fields[tags]}[/magenta] "
            "skipped=[yellow]{task.fields[skipped]}[/yellow]"
        ),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
    )

    download_task = progress.add_task(
        "Downloading tags",
        total=total_expected,
        ok=0,
        fail=0,
        batches=0,
        tags=0,
        skipped=0,
    )

    def refresh_task() -> None:
        progress.update(
            download_task,
            ok=stats["downloaded"],
            fail=stats["failed"],
            batches=stats["db_batches"],
            tags=stats["db_records"],
            skipped=stats["skipped_tags"],
        )

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
            skip_set = existing_tags.get(
                (namespace_name, image_name), frozenset())

            try:
                tags, skipped = await fetch_tags_for_image(
                    client, registry, item, skip_tags=skip_set)
                stats["skipped_tags"] += skipped
                await db_queue.put(
                    ImagePayload(
                        full_name=item,
                        namespace_name=namespace_name,
                        image_name=image_name,
                        tags=tags,
                    )
                )
                stats["downloaded"] += 1
            except Exception as exc:
                stats["failed"] += 1
                console.log(
                    f"[red]worker={worker_id} failed[/red] repo={item} err={exc}")
            finally:
                progress.update(download_task, advance=1)
                refresh_task()
                name_queue.task_done()

    def flush_payloads(session: Session, payloads: list[ImagePayload]) -> int:
        if not payloads:
            return 0
        _, _, changed_tags = persist_image_payload_batch(
            session, registry, self_hosted, payloads)
        return changed_tags

    async def db_worker() -> None:
        batch: list[ImagePayload] = []
        with Session(engine) as session:
            while True:
                try:
                    item = await asyncio.wait_for(db_queue.get(), timeout=2.0)
                except TimeoutError:
                    if batch:
                        changed = flush_payloads(session, batch)
                        stats["db_batches"] += 1
                        stats["db_records"] += changed
                        refresh_task()
                        batch = []
                    continue

                if item is None:
                    db_queue.task_done()
                    if batch:
                        changed = flush_payloads(session, batch)
                        stats["db_batches"] += 1
                        stats["db_records"] += changed
                        refresh_task()
                    set_last_updated(session)
                    break

                batch.append(item)
                db_queue.task_done()

                if len(batch) >= db_batch_size:
                    changed = flush_payloads(session, batch)
                    stats["db_batches"] += 1
                    stats["db_records"] += changed
                    refresh_task()
                    batch = []

    with progress:
        async with httpx.AsyncClient(verify=False, timeout=REQUEST_TIMEOUT_SECONDS) as client:
            producer_task = asyncio.create_task(producer())
            db_task = asyncio.create_task(db_worker())
            downloader_tasks = [
                asyncio.create_task(downloader(i + 1, client)) for i in range(downloaders)
            ]

            await producer_task
            await name_queue.join()
            await asyncio.gather(*downloader_tasks)

            await db_queue.put(None)
            await db_queue.join()
            await db_task

    summary = Table(title="process summary",
                    show_header=False, border_style="green")
    summary.add_column(style="bold cyan")
    summary.add_column()
    summary.add_row("Queued", str(stats["queued"]))
    summary.add_row("Downloaded", f"[green]{stats['downloaded']}[/green]")
    summary.add_row("Failed", f"[red]{stats['failed']}[/red]")
    summary.add_row("DB batches", str(stats["db_batches"]))
    summary.add_row("Tags changed", str(stats["db_records"]))
    summary.add_row(
        "Tags skipped (existing)", f"[yellow]{stats['skipped_tags']}[/yellow]")
    console.print(summary)


if __name__ == "__main__":
    app()
