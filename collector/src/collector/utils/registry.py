from __future__ import annotations

from datetime import datetime
import json
from typing import Any, Callable

import httpx
from rich.console import Console

from .http_client import async_request_with_retries
from .shared import TagPayload, parse_tag

console = Console()


def parse_created(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def format_platform(platform: dict[str, Any] | None) -> str | None:
    if not platform:
        return None
    parts = [platform.get(key) for key in ("os", "architecture", "variant")]
    parts = [part for part in parts if part]
    return "/".join(parts) if parts else None


async def fetch_tags_for_image(client: httpx.AsyncClient, registry: str, url: str, repo_name: str, skip_tags: frozenset[str] = frozenset(), on_tags_discovered: Callable[[int], None] | None = None, on_tag_processed: Callable[[], None] | None = None) -> tuple[list[TagPayload], int]:
    try:
        tags_response = await async_request_with_retries(client, "GET", f"{registry}/v2/{repo_name}/tags/list")
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            console.log(f"[yellow]skip[/yellow] no tags/list for {repo_name}")
            return [], 0
        raise
    tags = tags_response.json().get("tags") or []
    pending = [tag for tag in tags if isinstance(tag, str) and tag and tag not in skip_tags]
    skipped = sum(1 for tag in tags if isinstance(tag, str) and tag in skip_tags)
    if on_tags_discovered:
        on_tags_discovered(len(pending))
    result: list[TagPayload] = []
    for tag_name in pending:
        if on_tag_processed:
            on_tag_processed()
        try:
            manifest_response = await async_request_with_retries(client, "GET", f"{registry}/v2/{repo_name}/manifests/{tag_name}", headers={"Accept": "application/vnd.docker.distribution.manifest.v2+json, application/vnd.oci.image.manifest.v1+json, application/vnd.docker.distribution.manifest.list.v2+json, application/vnd.oci.image.index.v1+json"})
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                console.log(f"[yellow]skip[/yellow] missing manifest {repo_name}:{tag_name}")
                continue
            raise
        manifest = manifest_response.json()
        size = 0
        platforms: list[str] = []
        created_at = None
        if manifest.get("manifests"):
            for entry in manifest["manifests"]:
                if isinstance(entry.get("size"), int):
                    size += entry["size"]
                platform = format_platform(entry.get("platform"))
                if platform:
                    platforms.append(platform)
        else:
            config = manifest.get("config") or {}
            size += config.get("size", 0) if isinstance(config.get("size"), int) else 0
            size += sum(layer.get("size", 0) for layer in manifest.get("layers", []) if isinstance(layer.get("size"), int))
            digest = config.get("digest")
            if isinstance(digest, str) and digest:
                try:
                    config_response = await async_request_with_retries(client, "GET", f"{registry}/v2/{repo_name}/blobs/{digest}")
                except httpx.HTTPStatusError as exc:
                    if exc.response.status_code == 404:
                        console.log(f"[yellow]skip[/yellow] missing config blob {repo_name}:{tag_name} {digest}")
                        config_response = None
                    else:
                        raise
                if config_response is not None:
                    blob = config_response.json()
                    created_at = parse_created(blob.get("created"))
                    platform = format_platform({key: blob.get(key) for key in ("os", "architecture", "variant")})
                    if platform:
                        platforms.append(platform)
        version, variants = parse_tag(tag_name)
        result.append(TagPayload(name=tag_name, digest=manifest_response.headers.get("Docker-Content-Digest"), size=size or None, media_type=manifest_response.headers.get("Content-Type") or manifest.get("mediaType"), created_at=created_at, platforms=json.dumps(sorted(set(platforms))) if platforms else None, version=version, variants=json.dumps(variants) if variants else None))
    return result, skipped
