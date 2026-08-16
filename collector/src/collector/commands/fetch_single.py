from __future__ import annotations

from pathlib import Path

import httpx
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.table import Table
from typer import Typer
import typer

from collector.utils.http_client import request_with_retries
from collector.utils.shared import DEFAULT_DB_URL, DEFAULT_REPOS_FILE, DEFAULT_REPOS_FOLDER, REQUEST_TIMEOUT_SECONDS, parse_next_last

console = Console()


app = typer.Typer()


@app.command()
def fetch_single(
    registry: str,
    route: str = "/v2/_catalog",
    page_size: int = 100,
    output_folder: Path = DEFAULT_REPOS_FOLDER,
    last: str | None = None,
) -> None:
    """Fetch a list of repositories from a Docker registry and write to a file."""
    output_folder.mkdir(parents=True, exist_ok=True)

    registry_file = registry.removeprefix("https://")\
        .removeprefix("http://")\
        .replace("/", "")

    output = output_folder / f"{registry_file}.txt"

    console.print(Panel.fit(
        f"[bold cyan]Registry[/bold cyan]  {registry}\n"
        f"[bold cyan]Route[/bold cyan]     {route}\n"
        f"[bold cyan]Page size[/bold cyan] {page_size}\n"
        f"[bold cyan]Output[/bold cyan]    {output}\n"
        f"[bold cyan]Start last[/bold cyan] {last or '(none)'}",
        title="[bold]fetch[/bold]", border_style="cyan",
    ))

    total = pages = 0
    current_last = last
    progress = Progress(
        SpinnerColumn(), TextColumn("[bold blue]Fetching catalog"),
        TextColumn("pages [green]{task.fields[pages]}[/green]"),
        TextColumn("last=[dim]{task.fields[last]}[/dim]"),
        TimeElapsedColumn(), console=console, transient=False,
    )
    with progress, httpx.Client(verify=False, timeout=REQUEST_TIMEOUT_SECONDS) as client, output.open("w", encoding="utf-8") as file:
        task_id = progress.add_task("fetch", pages=0, last=current_last or "-")
        while True:
            params: dict[str, int | str] = {"n": page_size}
            if current_last:
                params["last"] = current_last
            response = request_with_retries(
                client, "GET", f"{registry}{route}", params=params)
            console.log(f"[green]Fetched[/green] {response.url} status={response.status_code}")
            repositories = response.json().get("repositories", [])
            if not repositories:
                break
            file.writelines(f"{name}\n" for name in repositories)
            total += len(repositories)
            pages += 1
            progress.update(task_id, pages=pages, total=total,
                            last=(current_last or "-")[:40])
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
