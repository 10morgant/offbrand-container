from datetime import datetime
import json
from pathlib import Path
from typing import Annotated, Any, Dict, Generator, List, Optional

from urllib.parse import parse_qs, unquote, urlparse

import httpx
import typer
from sqlmodel import SQLModel, Session, create_engine, insert, select
import yaml

from models.models import Image, Namespace, ImageTags, set_last_updated
from classes import Registry

app = typer.Typer(add_completion=False)


def split_namespace(full_name: str) -> tuple[str | None, str]:
    """'library/python' -> ('library', 'python'); 'python' -> (None, 'python')"""
    if "/" in full_name:
        namespace, name = full_name.split("/", 1)
        return namespace, name
    return None, full_name


def get_repo_list(repositories: Dict[str, List[str]]) -> List[str]:
    return repositories.get("repositories", [])


def paginated_fetch(url: str, page_size: int, client: httpx.Client) -> Generator[List[str], None, None]:
    last = ""

    while last is not None:
        params = {"n": page_size, "last": last}
        resp = client.get(f"{url}", params=params)
        resp.raise_for_status()

        res = resp.json()
        repos = get_repo_list(res)
        yield repos

        if "link" in resp.headers:
            last = resp.headers["link"]
            last = last.split(">")[0].lstrip("<")
            last = parse_qs(urlparse(last).query)["last"][0]
            last = unquote(last)
        else:
            last = None


def _format_platform(platform: dict[str, Any] | None) -> str | None:
    if not platform:
        return None
    os_name = platform.get("os")
    architecture = platform.get("architecture")
    variant = platform.get("variant")
    parts = [p for p in [os_name, architecture, variant] if p]
    return "/".join(parts) if parts else None


def _parse_created(created: Any) -> datetime | None:
    if not isinstance(created, str) or not created:
        return None
    return datetime.fromisoformat(created.replace("Z", "+00:00"))


def fetch_tag_details(repo: str, registry: str, client: httpx.Client) -> list[dict[str, Any]]:
    resp = client.get(f"{registry}/v2/{repo}/tags/list")
    resp.raise_for_status()

    tags = resp.json().get("tags") or []
    details: list[dict[str, Any]] = []

    for tag_name in tags:
        manifest_resp = client.get(
            f"{registry}/v2/{repo}/manifests/{tag_name}",
            headers={
                "Accept": (
                    "application/vnd.docker.distribution.manifest.v2+json, "
                    "application/vnd.oci.image.manifest.v1+json, "
                    "application/vnd.docker.distribution.manifest.list.v2+json"
                )
            },
        )
        manifest_resp.raise_for_status()

        manifest = manifest_resp.json()
        media_type = manifest_resp.headers.get(
            "Content-Type") or manifest.get("mediaType")
        digest = manifest_resp.headers.get("Docker-Content-Digest")

        size = 0
        created_at = None
        platforms: list[str] = []

        if manifest.get("manifests"):
            for item in manifest["manifests"]:
                if isinstance(item.get("size"), int):
                    size += item["size"]
                platform_name = _format_platform(item.get("platform"))
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
                config_resp = client.get(
                    f"{registry}/v2/{repo}/blobs/{config_digest}")
                config_resp.raise_for_status()
                # print(config_resp.request.url)
                config_blob = config_resp.json()
                created_at = _parse_created(config_blob.get("created"))
                platform_name = _format_platform(
                    {
                        "os": config_blob.get("os"),
                        "architecture": config_blob.get("architecture"),
                        "variant": config_blob.get("variant"),
                    }
                )
                if platform_name:
                    platforms.append(platform_name)

        details.append(
            {
                "name": tag_name,
                "digest": digest,
                "size": size or None,
                "media_type": media_type,
                "created_at": created_at,
                "platforms": json.dumps(sorted(set(platforms))) if platforms else None,
            }
        )

    return details


@app.command()
def collect(
    registry: str,
    route: str = "/v2/_catalog",
    page_size: int = 50,
    db: str | None = "postgresql+psycopg2://appuser:StrongPassword123@localhost:5432/docker",
    output: Path | None = None,
    self_hosted: bool = False,
    drop: bool = False,
):

    client = httpx.Client()

    repos = paginated_fetch(f"{registry}{route}", page_size, client)

    if db:
        engine = create_engine(db, echo=False)
        if drop:
            SQLModel.metadata.drop_all(engine)

        SQLModel.metadata.create_all(engine)

        with Session(engine) as session:
            total = 0
            print(f"batch|count|images")
            for i, batch in enumerate(repos):
                total += len(batch)
                print(f"{i:5}|{len(batch):5}|{total:6}")

                namespace_id_cache: dict[Optional[str], Optional[int]] = {}

                for full_name in batch:
                    namespace_name, name = split_namespace(full_name)

                    if namespace_name not in namespace_id_cache:
                        namespace = None
                        if namespace_name is not None:
                            namespace = session.exec(
                                select(Namespace)
                                .where(Namespace.name == namespace_name)
                                .where(Namespace.src_registry == registry)
                            ).first()

                            if namespace is None:
                                namespace = Namespace(
                                    name=namespace_name, src_registry=registry)
                                session.add(namespace)
                                session.flush()

                        namespace_id_cache[namespace_name] = namespace.id if namespace else None

                    image = session.exec(
                        select(Image).where(
                            Image.name == name,
                            Image.namespace_name == namespace_name,
                            Image.src_registry == registry,
                            Image.self_hosted == self_hosted,
                        )
                    ).first()

                    if image is None:
                        image = Image(
                            name=name,
                            self_hosted=self_hosted,
                            namespace_id=namespace_id_cache[namespace_name],
                            src_registry=registry,
                            namespace_name=namespace_name,
                        )
                        session.add(image)
                        session.flush()

                    for tag_info in fetch_tag_details(full_name, registry, client):
                        existing_tag = session.exec(
                            select(ImageTags).where(
                                ImageTags.image_id == image.id,
                                ImageTags.name == tag_info["name"],
                            )
                        ).first()

                        if existing_tag is None:
                            session.add(
                                ImageTags(
                                    image_id=image.id,
                                    name=tag_info["name"],
                                    digest=tag_info["digest"],
                                    size=tag_info["size"],
                                    media_type=tag_info["media_type"],
                                    created_at=tag_info["created_at"],
                                    platforms=tag_info["platforms"],
                                    src_registry=registry,
                                )
                            )
                        else:
                            existing_tag.digest = tag_info["digest"]
                            existing_tag.size = tag_info["size"]
                            existing_tag.media_type = tag_info["media_type"]
                            existing_tag.created_at = tag_info["created_at"]
                            existing_tag.platforms = tag_info["platforms"]
                            existing_tag.src_registry = registry

                session.commit()
            set_last_updated(session)

    elif output:
        with open(output, "w") as f:
            total = 0
            print(f"batch|count|images")
            for i, batch in enumerate(repos):
                total += len(batch)
                print(f"{i:5}|{len(batch):5}|{total:6}")
                for name in batch:
                    f.write(f"{name}, {self_hosted}\n")
    else:
        for i, batch in enumerate(repos):
            for name in batch:
                print(name)

    if db or output:
        print("Done!")


@app.command()
def all(
    registry_file: Annotated[Path, typer.Argument(exists=True, dir_okay=False)],
    route: str = "/v2/_catalog",
    page_size: int = 50,
    db: str | None = "postgresql+psycopg2://appuser:StrongPassword123@localhost:5432/docker",
    output: Path | None = None,
    drop: bool = False,
):

    print("Reading registries")
    with open(registry_file, "r") as f:
        try:
            data = yaml.safe_load(f)
            regs = [
                Registry(**fields)
                for _, fields in data["registries"].items()
            ]
            print(f"{len(regs)} registries to process")
            for reg in regs:
                print(reg)
                collect(
                    registry=reg.url,
                    route=route,
                    page_size=page_size,
                    db=db,
                    output=output,
                    self_hosted=reg.self_hosted,
                    drop=drop,
                )
        except Exception as e:
            print(e)
            pass


if __name__ == "__main__":
    app()
