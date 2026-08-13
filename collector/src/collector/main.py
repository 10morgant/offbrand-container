from __future__ import annotations

from rich.console import Console
from rich.traceback import install as install_rich_traceback
import typer
from collector.commands.fetch import app as fetch_app
from collector.commands.names import app as names_app
from collector.commands.process import app as process_app

install_rich_traceback(show_locals=False)
console = Console()

app = typer.Typer(add_completion=False, rich_markup_mode="rich")

app.add_typer(fetch_app)
app.add_typer(names_app)
app.add_typer(process_app)


if __name__ == "__main__":
    app()
