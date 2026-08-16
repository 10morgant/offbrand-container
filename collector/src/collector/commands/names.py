from __future__ import annotations

from pathlib import Path
from typing import Annotated

from rich.console import Console

from shared.utils import read_registries
import typer

from collector.commands.names_single import names_single
from collector.utils.shared import DEFAULT_DB_URL, DEFAULT_REPOS_FOLDER

console = Console()

app = typer.Typer()


@app.command()
def names(
    registry_file: Annotated[str, typer.Option(
        help="Path to the registry file", exists=True, dir_okay=False)] = "registries.yaml",
    output_folder: Path = DEFAULT_REPOS_FOLDER,
    db: str = DEFAULT_DB_URL,
    self_hosted: bool = False,
    chunk_size: int = 2000,
) -> None:

    registries = read_registries(registry_file)

    if not registries:
        console.print("[bold red]No registries found in the file.[/bold red]")
        raise typer.Exit(code=1)

    for registry in registries:
        registry_file = registry.url.removeprefix("https://")\
                .removeprefix("http://")\
                .replace("/", "")

        names_single(
            registry=registry.url,
            names_file=output_folder / f"{registry_file}.txt",
            db=db,
            self_hosted=self_hosted,
            chunk_size=chunk_size,
        )
