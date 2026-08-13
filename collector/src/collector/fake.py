#!/usr/bin/env python3
"""
Mirror all (or a filtered subset of) tags for a Docker Hub image into a
local/private registry.

Example:
    python mirror_image_tags.py --image library/python --registry 0.0.0.0:5000

Requires:
    - Docker installed and running, with the current user able to run
      `docker` commands (or run this script with sufficient privileges).
    - Network access to Docker Hub for pulling and to the target registry
      for pushing.
    - `httpx` (pip install httpx)
"""

import argparse
import subprocess
import sys
import time

import httpx
from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

HUB_API = "https://hub.docker.com/v2/repositories/{image}/tags"

console = Console()


def get_all_tags(image: str, page_size: int = 100, tag_filter: str | None = None):
    """Yield every tag name for `image` (e.g. 'library/python') from Docker Hub."""
    url = HUB_API.format(image=image) + f"?page_size={page_size}"
    while url:
        resp = httpx.get(url, timeout=30)
        try:
            resp.raise_for_status()
        except httpx.HTTPError as e:
            print(f"Error fetching tags from {url}: {e}")
            break
        data = resp.json()
        for result in data.get("results", []):
            name = result["name"]
            if tag_filter is None or tag_filter in name:
                yield name
        url = data.get("next")


def run(cmd: list[str]) -> bool:
    """Run a subprocess command. Output is only shown on failure to keep the bar clean."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        console.log(f"[red]$ {' '.join(cmd)}[/red]")
        if result.stderr:
            console.log(result.stderr.strip())
    return result.returncode == 0


def mirror_tag(image: str, tag: str, registry: str, retries: int = 2) -> bool:
    # src = f"{image}:{tag}"
    src = f"{image}:latest"
    # src = f"library/maven:latest"
    dst = f"{registry}/{image}:{tag}"

    for attempt in range(1, retries + 2):  # initial try + retries
        # if not run(["docker", "pull", src]):
        #     console.log(f"[{tag}] pull failed")
        #     time.sleep(2)
        #     continue

        if not run(["docker", "tag", src, dst]):
            console.log(f"[yellow]{tag}[/yellow] tag failed (attempt {attempt})")
            continue

        if not run(["docker", "push", dst]):
            console.log(f"[yellow]{tag}[/yellow] push failed (attempt {attempt})")
            time.sleep(2)
            continue

        return True

    return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--image",
        default="library/python",
        help="Docker Hub image, e.g. 'library/python' (default: %(default)s)",
    )
    parser.add_argument(
        "--registry",
        default="0.0.0.0:5000",
        help="Target registry host:port (default: %(default)s)",
    )
    parser.add_argument(
        "--filter",
        default=None,
        help="Only mirror tags containing this substring, e.g. '3.12' or 'slim'",
    )
    parser.add_argument(
        "--tags",
        nargs="*",
        default=None,
        help="Explicit list of tags to mirror instead of fetching from Docker Hub",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List the tags that would be mirrored without pulling/pushing anything",
    )
    parser.add_argument(
        "--keep-local",
        action="store_true",
        help="Don't remove local images after pushing (default: removes to save disk)",
    )
    args = parser.parse_args()

    if args.tags:
        tags = args.tags
    else:
        print(f"Fetching tag list for {args.image} from Docker Hub...")
        tags = list(get_all_tags(args.image, tag_filter=args.filter))

    if not tags:
        console.print("[red]No tags found (check the image name / filter).[/red]")
        sys.exit(1)

    console.print(f"Found [bold cyan]{len(tags)}[/bold cyan] tag(s) to mirror")

    if args.dry_run:
        for t in tags:
            console.print(f"  - {t}")
        console.print("\nDry run only, nothing pulled or pushed.")
        return

    failures = []
    succeeded = 0
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]Mirroring tags"),
        BarColumn(),
        MofNCompleteColumn(),
        TextColumn("[progress.percentage]{task.percentage:>5.1f}%"),
        TextColumn("ok=[green]{task.fields[ok]}[/green] fail=[red]{task.fields[fail]}[/red]"),
        TextColumn("[dim]{task.fields[tag]}[/dim]"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
    )

    with progress:
        task_id = progress.add_task("mirror", total=len(tags), ok=0, fail=0, tag="-")

        if not run(["docker", "pull", f"{args.image}:latest"]):
            console.log(f"{args.image}:latest pull failed")
            time.sleep(2)

        for tag in tags:
            progress.update(task_id, tag=tag)
            ok = mirror_tag(args.image, tag, args.registry)
            if not ok:
                failures.append(tag)
            else:
                succeeded += 1
                if not args.keep_local:
                    dst = f"{args.registry}/{args.image}:{tag}"
                    run(["docker", "rmi", dst])

            progress.update(task_id, advance=1, ok=succeeded, fail=len(failures))

    console.print("\n[bold]Summary[/bold]")
    console.print(f"Succeeded: [green]{succeeded}[/green]/{len(tags)}")
    if failures:
        console.print("[red]Failed tags:[/red]")
        for t in failures:
            console.print(f"  - {t}")
        sys.exit(1)


if __name__ == "__main__":
    main()