from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re
from typing import Iterable, Iterator
from urllib.parse import parse_qs, unquote, urlparse

from packaging.version import InvalidVersion, parse

DEFAULT_DB_URL = "postgresql+psycopg2://appuser:StrongPassword123@localhost:5432/docker"
DEFAULT_REPOS_FOLDER = Path("data/")
DEFAULT_REPOS_FOLDER.mkdir(parents=True, exist_ok=True)
DEFAULT_REPOS_FILE = DEFAULT_REPOS_FOLDER / "repositories.txt"
REQUEST_TIMEOUT_SECONDS = 180.0
RETRY_STATUS_CODES = {408, 409, 425, 429, 500, 502, 503, 504}
MAX_RETRIES = 6
RETRY_BASE_DELAY = 1.0
ROOT_NAMESPACE = "library"
KEYWORD_VERSIONS = {
    "latest", "stable", "edge", "main", "master", "current",
    "lts", "nightly", "next", "canary", "dev", "rolling",
}
_VERSION_RE = re.compile(r"^v?\d+(?:\.\d+)*$", re.IGNORECASE)


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


def parse_tag(tag: str) -> tuple[str | None, list[str]]:
    """Split a tag like `3.14-slim-bookworm` into (version, [variants])."""
    if not tag:
        return None, []

    parts = tag.split("-")
    version: str | None = None
    variants: list[str] = []

    ver_part = parts[0]
    try:
        version = str(parse(ver_part))
    except InvalidVersion:
        if ver_part.lower() in KEYWORD_VERSIONS:
            version = ver_part
        else:
            variants.append(ver_part)

    variants.extend(parts[1:])
    return version, variants


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


def iter_name_file(path: Path) -> Iterator[str]:
    with path.open("r", encoding="utf-8") as file:
        for raw in file:
            name = raw.strip()
            if name:
                yield name


def count_names(path: Path) -> int:
    return sum(1 for name in iter_name_file(path) if name)


def chunked(items: Iterable[str], chunk_size: int) -> Iterator[list[str]]:
    batch: list[str] = []
    for item in items:
        batch.append(item)
        if len(batch) >= chunk_size:
            yield batch
            batch = []
    if batch:
        yield batch
