from __future__ import annotations

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from fetch import (
    Image,
    Namespace,
    chunked,
    parse_next_last,
    parse_tag,
    persist_name_chunk,
    split_namespace,
)


@pytest.mark.parametrize(
    ("tag", "expected_version", "expected_variants"),
    [
        ("3.14-slim-bookworm", "3.14", ["slim", "bookworm"]),
        ("latest-alpine", "latest", ["alpine"]),
        ("v2.0.2-bookworm", "2.0.2", ["bookworm"]),
        ("3.14.0a4-windowsservercore-1809", "3.14.0a4", ["windowsservercore", "1809"]),
        ("windowsservercore-1809", None, ["windowsservercore", "1809"]),
        ("alpine3.22", None, ["alpine3.22"]),
        ("3.14.0b4-slim-bullseye", "3.14.0b4", ["slim", "bullseye"]),
        ("slim", None, ["slim"]),
    ],
)
def test_parse_tag(tag: str, expected_version: str, expected_variants: list[str]) -> None:
    version, variants = parse_tag(tag)

    assert version == expected_version
    assert variants == expected_variants


@pytest.mark.parametrize(
    ("full_name", "expected"),
    [
        ("nginx", ("library", "nginx")),
        ("docker/nginx", ("docker", "nginx")),
    ],
)
def test_split_namespace_defaults_to_library(full_name: str, expected: tuple[str, str]) -> None:
    assert split_namespace(full_name) == expected


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        (
            '<https://example.com/v2/_catalog?n=100&last=library%2Fnginx>; rel="next"',
            "library/nginx",
        ),
    ],
)
def test_parse_next_last_decodes_link_header_value(header: str, expected: str) -> None:
    assert parse_next_last(header) == expected


@pytest.mark.parametrize(
    ("items", "chunk_size", "expected"),
    [
        (["a", "b", "c", "d"], 2, [["a", "b"], ["c", "d"]]),
    ],
)
def test_chunked_splits_items_into_fixed_sized_groups(
    items: list[str], chunk_size: int, expected: list[list[str]]
) -> None:
    assert list(chunked(items, chunk_size)) == expected


def test_persist_name_chunk_creates_namespaces_and_images() -> None:
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        namespaces, images = persist_name_chunk(
            session,
            "docker.io",
            False,
            ["library/nginx", "redis", "library/ubuntu"],
        )

        assert namespaces == 1
        assert images == 3

        namespace_rows = session.exec(select(Namespace)).all()
        image_rows = session.exec(select(Image)).all()

        assert {row.name for row in namespace_rows} == {"library"}
        assert {row.name for row in image_rows if row.name is not None} == {"nginx", "ubuntu", "redis"}

        assert {image.namespace_name for image in image_rows} == {"library", "library", "library"}
