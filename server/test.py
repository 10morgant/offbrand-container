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
    - `requests` (pip install requests)
"""

import argparse
import subprocess
import sys
import time

import requests

HUB_API = "https://hub.docker.com/v2/repositories/{image}/tags"


def get_all_tags(image: str, page_size: int = 100, tag_filter: str | None = None):
    """Yield every tag name for `image` (e.g. 'library/python') from Docker Hub."""
    url = HUB_API.format(image=image) + f"?page_size={page_size}"
    while url:
        resp = requests.get(url, timeout=30)
        try:
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"Error fetching tags from {url}: {e}")
            break
        data = resp.json()
        for result in data.get("results", []):
            name = result["name"]
            if tag_filter is None or tag_filter in name:
                yield name
        url = data.get("next")


def run(cmd: list[str]) -> bool:
    """Run a subprocess command, streaming output. Return True on success."""
    print(f"  $ {' '.join(cmd)}")
    result = subprocess.run(cmd)
    return result.returncode == 0


def mirror_tag(image: str, tag: str, registry: str, retries: int = 2) -> bool:
    # src = f"{image}:{tag}"
    src = f"library/node:lts-alpine"
    dst = f"{registry}/{image}:{tag}"

    for attempt in range(1, retries + 2):  # initial try + retries
        print(f"[{tag}] pulling {src} (attempt {attempt})")
        # if not run(["docker", "pull", src]):
        #     print(f"[{tag}] pull failed")
        #     time.sleep(2)
        #     continue

        print(f"[{tag}] tagging as {dst}")
        if not run(["docker", "tag", src, dst]):
            print(f"[{tag}] tag failed")
            continue

        print(f"[{tag}] pushing {dst}")
        if not run(["docker", "push", dst]):
            print(f"[{tag}] push failed")
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
        print("No tags found (check the image name / filter).")
        sys.exit(1)

    print(f"Found {len(tags)} tag(s) to mirror:")
    for t in tags:
        print(f"  - {t}")

    if args.dry_run:
        print("\nDry run only, nothing pulled or pushed.")
        return

    failures = []
    for i, tag in enumerate(tags, start=1):
        print(f"\n=== [{i}/{len(tags)}] {args.image}:{tag} ===")
        ok = mirror_tag(args.image, tag, args.registry)
        if not ok:
            failures.append(tag)
        elif not args.keep_local:
            src = f"{args.image}:{tag}"
            dst = f"{args.registry}/{args.image}:{tag}"
            run(["docker", "rmi", dst])

    print("\n=== Summary ===")
    print(f"Succeeded: {len(tags) - len(failures)}/{len(tags)}")
    if failures:
        print("Failed tags:")
        for t in failures:
            print(f"  - {t}")
        sys.exit(1)


if __name__ == "__main__":
    main()