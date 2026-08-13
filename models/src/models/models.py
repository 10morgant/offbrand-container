from datetime import datetime, timezone
import json
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship, Session

class LastUpdated(SQLModel, table=True):
    id: int = Field(default=1, primary_key=True)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Namespace(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=255, index=True)
    src_registry: str

    images: List["Image"] = Relationship(back_populates="namespace")


class Image(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    # MySQL/MariaDB requires a length for indexed/text columns
    name: str | None = Field(default=None, max_length=255)
    self_hosted: bool = False
    src_registry: str = "?"
    namespace_name: str = "?"
    qualified_name: str = "?"

    namespace_id: Optional[int] = Field(
        default=None, foreign_key="namespace.id")
    namespace: Optional[Namespace] = Relationship(back_populates="images")

    tags: List["ImageTags"] = Relationship(back_populates="image")


class ImageTags(SQLModel, table=True):
    __tablename__ = "tags"

    id: int | None = Field(default=None, primary_key=True)
    image_id: int = Field(foreign_key="image.id", index=True)
    name: str = Field(index=True)
    digest: str | None = Field(default=None, index=True)
    size: int | None = None
    media_type: str | None = None
    created_at: datetime | None = Field(default=None, index=True)
    platforms: str | None = None
    version: str | None = Field(default=None, index=True)
    variants: str | None = None
    src_registry: str = Field(index=True)

    image: Image = Relationship(back_populates="tags")



# ---- Read view models ----

class NamespaceRead(SQLModel):
    id: int
    name: str
    num_images: int
    regsitry: str
    images: List["ImageRead"] = []


class ImageTagsRead(SQLModel):
    id: int
    image_id: Optional[int] = None
    tag: str
    digest: str
    size: int
    created_at: datetime | None = None
    platforms: List[str] = []
    version: str | None = None
    variants: List[str] = []



class ImageRead(SQLModel):
    id: int
    name: str
    self_hosted: bool
    namespace: Optional[NamespaceRead] = None
    tags: List[ImageTagsRead] = []
    regsitry: str
    namespace_name: str


class NamespacePage(SQLModel):
    total: int
    limit: int
    offset: int
    items: List[NamespaceRead]


class ImagePage(SQLModel):
    total: int
    limit: int
    offset: int
    items: List[ImageRead]


class Stats(SQLModel):
    namespaces: int
    images: int
    tags: int

def set_last_updated(session: Session) -> LastUpdated:
    row = session.get(LastUpdated, 1)
    now = datetime.now(timezone.utc)
    if row is None:
        row = LastUpdated(id=1, timestamp=now)
    else:
        row.timestamp = now
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def TagDBOtoRead(dbo:ImageTags):
    return ImageTagsRead(
        id=dbo.id,
        tag=dbo.name,
        image_id=dbo.image_id,
        digest=dbo.digest,
        size=dbo.size,
        created_at=dbo.created_at,
        platforms=[] if not dbo.platforms else json.loads(dbo.platforms),
        version=dbo.version,
        variants=[] if not dbo.variants else json.loads(dbo.variants),
    )



def ImageDBOtoRead(dbo:Image, tags:bool = False) -> ImageRead:
    return ImageRead(
        id=dbo.id,
        name=dbo.name,
        self_hosted=dbo.self_hosted,
        regsitry=dbo.src_registry,
        namespace_name=dbo.namespace_name,
        tags=[TagDBOtoRead(tag) for tag in dbo.tags] if tags else []
    )