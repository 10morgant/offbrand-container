from __future__ import annotations

from pathlib import Path
from typing_extensions import Annotated

import httpx
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.table import Table
from shared.utils import read_registries
from typer import Typer
import typer

from collector.commands.fetch_single import fetch_single
from collector.utils.http_client import request_with_retries
from collector.utils.shared import DEFAULT_DB_URL, DEFAULT_REPOS_FILE, DEFAULT_REPOS_FOLDER, REQUEST_TIMEOUT_SECONDS, parse_next_last

console = Console()


app = typer.Typer()


@app.command()
def fetch(
    registry_file: Annotated[str, typer.Option(help="Path to the registry file")] = "registries.yaml",
    route: str = "/v2/_catalog",
    page_size: int = 100,
    output_folder: Path = DEFAULT_REPOS_FOLDER,
    last: str | None = None,
) -> None:
    """Read a list of registries from a file and fetch from a Docker registry and write to a file."""
    output_folder.mkdir(parents=True, exist_ok=True)
    registries = read_registries(registry_file)

    if not registries:
        console.print("[bold red]No registries found in the file.[/bold red]")
        raise typer.Exit(code=1)

    for registry in registries:
        fetch_single(
            registry=registry.url,
            route=route,
            page_size=page_size,
            output_folder=output_folder,
            last=last,
        )
