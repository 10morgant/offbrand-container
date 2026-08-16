from __future__ import annotations

from sqlmodel import Session, col, select

from shared.models import Image, ImageTags, Namespace

from .shared import ImagePayload, split_namespace


def ensure_namespaces(session: Session, registry: str, namespace_names: set[str]) -> dict[str, Namespace]:
    if not namespace_names:
        return {}
    existing = session.exec(select(Namespace).where(Namespace.src_registry == registry, col(Namespace.name).in_(namespace_names))).all()
    namespace_by_name = {namespace.name: namespace for namespace in existing}
    missing = namespace_names - set(namespace_by_name)
    if missing:
        session.add_all([Namespace(name=name, src_registry=registry) for name in sorted(missing)])
        session.flush()
        for namespace in session.exec(select(Namespace).where(Namespace.src_registry == registry, col(Namespace.name).in_(missing))).all():
            namespace_by_name[namespace.name] = namespace
    return namespace_by_name


def ensure_images(session: Session, registry: str, self_hosted: bool, records: list[tuple[str, str]], namespace_by_name: dict[str, Namespace]) -> dict[tuple[str, str], Image]:
    if not records:
        return {}
    names = {name for _, name in records}
    existing = session.exec(select(Image).where(Image.src_registry == registry, Image.self_hosted == self_hosted, col(Image.name).in_(names))).all()
    image_by_key = {(image.namespace_name, image.name): image for image in existing if image.name is not None}
    missing: list[Image] = []
    for namespace_name, image_name in records:
        key = (namespace_name, image_name)
        if key in image_by_key:
            continue
        namespace = namespace_by_name.get(namespace_name)
        missing.append(Image(name=image_name, self_hosted=self_hosted, src_registry=registry, namespace_name=namespace_name, namespace_id=namespace.id if namespace else None, qualified_name=f"{namespace_name}/{image_name}"))
    if missing:
        session.add_all(missing)
        session.flush()
        for image in missing:
            if image.name is not None:
                image_by_key[(image.namespace_name, image.name)] = image
    return image_by_key


def upsert_tags_for_payloads(session: Session, registry: str, image_by_key: dict[tuple[str, str], Image], payloads: list[ImagePayload]) -> tuple[int, int]:
    image_ids = {image.id for image in image_by_key.values() if image.id is not None}
    tag_names = {tag.name for payload in payloads for tag in payload.tags}
    existing_by_key: dict[tuple[int, str], ImageTags] = {}
    if image_ids and tag_names:
        existing_by_key = {(tag.image_id, tag.name): tag for tag in session.exec(select(ImageTags).where(col(ImageTags.image_id).in_(image_ids), col(ImageTags.name).in_(tag_names))).all()}
    inserted = updated = 0
    for payload in payloads:
        image_id = image_by_key[(payload.namespace_name, payload.image_name)].id
        if image_id is None:
            continue
        for tag in payload.tags:
            row = existing_by_key.get((image_id, tag.name))
            if row is None:
                session.add(ImageTags(image_id=image_id, name=tag.name, digest=tag.digest, size=tag.size, media_type=tag.media_type, created_at=tag.created_at, platforms=tag.platforms, version=tag.version, variants=tag.variants, src_registry=registry))
                inserted += 1
            else:
                row.digest, row.size, row.media_type = tag.digest, tag.size, tag.media_type
                row.created_at, row.platforms = tag.created_at, tag.platforms
                row.version, row.variants, row.src_registry = tag.version, tag.variants, registry
                updated += 1
    return inserted, updated


def persist_name_chunk(session: Session, registry: str, self_hosted: bool, names: list[str]) -> tuple[int, int]:
    records = [split_namespace(name) for name in names]
    namespaces = ensure_namespaces(session, registry, {namespace for namespace, _ in records})
    images = ensure_images(session, registry, self_hosted, records, namespaces)
    session.commit()
    return len(namespaces), len(images)


def persist_image_payload_batch(session: Session, registry: str, self_hosted: bool, payloads: list[ImagePayload]) -> tuple[int, int, int]:
    records = [(payload.namespace_name, payload.image_name) for payload in payloads]
    namespaces = ensure_namespaces(session, registry, {payload.namespace_name for payload in payloads})
    images = ensure_images(session, registry, self_hosted, records, namespaces)
    inserted, updated = upsert_tags_for_payloads(session, registry, images, payloads)
    session.commit()
    return len(namespaces), len(images), inserted + updated
