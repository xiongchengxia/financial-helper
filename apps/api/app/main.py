from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings, reload_settings
from app.routers import documents, export, health, media, tasks, vouchers

@asynccontextmanager
async def lifespan(_app: FastAPI):
    reload_settings()
    yield


app = FastAPI(
    title="Financial Helper API",
    version="1.0.0",
    description="财税票据自动处理 API",
    lifespan=lifespan,
)

settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(tasks.router)
app.include_router(documents.router)
app.include_router(vouchers.router)
app.include_router(export.router)
app.include_router(media.router)
