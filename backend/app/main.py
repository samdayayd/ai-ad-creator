from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ORIGINS
from app.db import init_db
from app.routers import ads, auth, billing, contact, ugc_ads, video_ads
from app.seed import seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed()
    yield


app = FastAPI(title="ZeTruth Studio", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(ads.router)
app.include_router(video_ads.router)
app.include_router(ugc_ads.router)
app.include_router(billing.router)
app.include_router(contact.router)


@app.get("/health")
def health():
    return {"status": "ok"}
