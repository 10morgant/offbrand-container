from __future__ import annotations

from pathlib import Path
from typing import Annotated

from rich.console import Console
from shared.utils import read_registries
import typer


from collector.commands.process_single import process_single
from collector.utils.shared import DEFAULT_DB_URL, DEFAULT_REPOS_FOLDER

console = Console()

app = typer.Typer()



@app.command()
def process(
    registry_file: Annotated[str, typer.Option(help="Path to the registry file")] = "registries.yaml",
    output_folder: Path = DEFAULT_REPOS_FOLDER,
    db: str = DEFAULT_DB_URL,
    self_hosted: bool = False,
    downloaders: int = 30,
    db_batch_size: int = 200,
    skip_existing: bool = False,
) -> None:
    registries = read_registries(registry_file)
    
    if not registries:
        console.print("[bold red]No registries found in the file.[/bold red]")
        raise typer.Exit(code=1)

    for registry in registries:
        reg_file = registry.url.removeprefix("https://")\
                .removeprefix("http://")\
                .replace("/", "")
        
        process_single(
            registry=registry.url,
            url="v2/",
            names_file=output_folder / f"{reg_file}.txt",
            db=db,
            self_hosted=self_hosted,
            downloaders=downloaders,
            db_batch_size=db_batch_size,
            skip_existing=skip_existing,
        )