import asyncio
from concurrent.futures import ProcessPoolExecutor
from contextlib import asynccontextmanager
from dataclasses import dataclass
import os
from pathlib import Path

from fastapi import APIRouter, FastAPI, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import yaml
from models import Image, ImageDBOtoRead, ImagePage, ImageRead, ImageTags, LastUpdated, Namespace, NamespacePage, NamespaceRead, Stats
from typing import List, Optional
from sqlmodel import SQLModel, select, func
from sqlmodel.ext.asyncio.session import AsyncSession

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.orm import selectinload

from collect import collect
from classes import Registry


DEFAULT_DB_URL = "postgresql+psycopg2://appuser:StrongPassword123@localhost:5432/docker"
db: str = os.environ.get("DB_URL", DEFAULT_DB_URL)


def get_async_db_url() -> str:
    if db.startswith("postgresql+psycopg2://"):
        return db.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
    return db



executor = ProcessPoolExecutor(max_workers=1)


def collect_data(reg: Registry, index: int):
    # , drop=(index == 0))
    collect(reg.url, db=db, self_hosted=reg.self_hosted)


async def periodic_task():
    loop = asyncio.get_running_loop()

    while True:
        read_registries()
        for i, reg in enumerate(REGISTRIES):
            print(f"Loading {reg.display_name}")
            await loop.run_in_executor(
                executor,
                collect_data,
                reg,
                i
            )

        await asyncio.sleep(300)  # 5 minutes


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(periodic_task())
    yield
    task.cancel()  # cleanup on shutdown


app = FastAPI(lifespan=lifespan, root_path="/")

router = APIRouter(prefix="/api")
app.include_router(router)
REGISTRIES = []


async def get_session():
    engine = create_async_engine(get_async_db_url(), echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    async with AsyncSession(engine) as session:
        yield session


def read_registries():
    print("Reading registries")
    with open("registries.yaml", "r") as f:
        data = yaml.safe_load(f)
        global REGISTRIES
        print(f"OLD {REGISTRIES}")
        REGISTRIES = [
            Registry(**fields)
            for _, fields in data["registries"].items()
        ]
        print(f"NEW {REGISTRIES}")


@router.get("/registries")
def get_registries():
    return REGISTRIES


@router.get("/last-updated")
async def get_last_updated(session: AsyncSession = Depends(get_session)) -> dict:
    row = await session.get(LastUpdated, 1)
    if row is None:
        return {"timestamp": None}
    return {"timestamp": row.timestamp.isoformat()}


@router.get("/stats")
async def stats(url: str = Query(), session: AsyncSession = Depends(get_session)) -> Stats:
    ns_result = await session.exec(
        select(func.count()).select_from(Namespace).where(
            Namespace.src_registry == url)
    )
    ns = ns_result.one()

    ims_result = await session.exec(
        select(func.count()).select_from(
            Image).where(Image.src_registry == url)
    )
    ims = ims_result.one()

    tgs_result = await session.exec(
        select(func.count()).select_from(ImageTags).where(
            ImageTags.src_registry == url)
    )
    tgs = tgs_result.one()

    return Stats(namespaces=ns, images=ims, tags=tgs)


@router.get("/namespaces", response_model=NamespacePage, tags=["namespaces"])
async def list_namespaces(
    url: str = Query(),
    limit: int = Query(50, ge=0, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    print("namespace: ", url, limit, offset)
    total_result = await session.exec(
        select(func.count()).select_from(Namespace).where(
            Namespace.src_registry == url)
    )
    total = total_result.one()

    stmt = (
        select(Namespace)
        .options(selectinload(Namespace.images))
        .where(Namespace.src_registry == url)
    )
    if limit > 0:
        stmt = stmt.offset(offset).limit(limit)

    result = await session.exec(stmt)
    items = [
        NamespaceRead(
            id=ns.id,
            name=ns.name,
            num_images=len(ns.images),
            regsitry=ns.src_registry
        )
        for ns in result.all()
    ]

    return NamespacePage(total=total, limit=limit, offset=offset, items=items)


@router.get("/namespaces/{namespace:str}", response_model=NamespaceRead, tags=["namespaces"])
async def get_namespace(
    namespace: str,
    url: str = Query(),
    session: AsyncSession = Depends(get_session),
):
    print(namespace, url)
    stmt = (
        select(Namespace)
        .options(selectinload(Namespace.images))
        .where(Namespace.src_registry == url)
        .where(Namespace.name == namespace)
    )

    result = await session.exec(stmt)
    dbo = result.first()
    if dbo:
        return NamespaceRead(
            id=dbo.id,
            name=dbo.name,
            num_images=len(dbo.images),
            regsitry=dbo.src_registry,
            images=[ImageDBOtoRead(im) for im in dbo.images]
        )
    raise HTTPException(404, f"{namespace} not found")


@router.get("/images", response_model=ImagePage)
async def list_images(
    url: str = Query(),
    limit: int = Query(50, ge=0, le=500),
    offset: int = Query(0, ge=0),
    namespace_id: Optional[int] = None,
    session: AsyncSession = Depends(get_session),
):
    print("images: ", url, limit, offset, namespace_id)
    count_stmt = select(func.count()) \
        .select_from(Image).where(Image.src_registry == url)

    items_stmt = select(Image).where(Image.src_registry == url)
    if limit > 0:
        items_stmt = items_stmt.offset(offset).limit(limit)

    if namespace_id is not None:
        count_stmt = count_stmt.where(Image.namespace_id == namespace_id)
        items_stmt = items_stmt.where(Image.namespace_id == namespace_id)

    count_result = await session.exec(count_stmt)
    total = count_result.one()

    result = await session.exec(items_stmt)
    items = [ImageDBOtoRead(im) for im in result.all()]

    return ImagePage(total=total, limit=limit, offset=offset, items=items)


@router.get("/namespaces/{namespace:str}/images/{image:str}", response_model=ImageRead)
async def fetch_image(
    namespace: str,
    image: str,
    url: str = Query(),
    limit: int = Query(50, ge=0, le=500),
    offset: int = Query(0, ge=0),
    namespace_id: Optional[int] = None,
    session: AsyncSession = Depends(get_session),
):
    print("images: ", image, url, limit, offset, namespace_id)

    stmt = (
        select(Image)
        .options(selectinload(Image.tags))
        .where(Image.src_registry == url)
        .where(Image.namespace_name == namespace)
        .where(Image.name == image)
    )

    result = await session.exec(stmt)
    dbo = result.first()
    if dbo:
        return ImageDBOtoRead(dbo, True)


async def search_table(session: AsyncSession, model, url: str, q: str, limit: int = 25):
    stmt = select(model).where(model.src_registry == url).where(
        model.name.ilike(f"{q}%")).limit(limit)
    result = await session.exec(stmt)
    return result.all()


@router.get("/search")
async def search(
    url: str = Query(),
    q: str = Query(..., min_length=1, max_length=100),
    session: AsyncSession = Depends(get_session)
):
    namespaces, images = await asyncio.gather(
        search_table(session, Namespace, url, q),
        search_table(session, Image, url, q),
    )
    return {
        "namespaces": [r.dict() for r in namespaces],
        "images": [r.dict() for r in images],
    }


# app.mount("/", StaticFiles(directory="static", html=True), name="static")


# @app.get("/{full_path:path}")
# async def spa_fallback(full_path: str, request: Request):
#     # If it's a real file in dist (favicon.ico, manifest.json, etc), serve it
#     DIST_DIR = Path("static")
#     candidate = DIST_DIR / full_path
#     if full_path and candidate.is_file():
#         return FileResponse(candidate)
#     # Otherwise hand control to the client-side router
#     return FileResponse(DIST_DIR / "index.html")
@app.get("/{path:path}")
async def spa(path: str):
    STATIC = Path("static")
    file = STATIC / path

    if path and file.exists() and file.is_file():
        return FileResponse(file)

    return FileResponse(STATIC / "index.html")
