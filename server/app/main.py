import asyncio
import json
import logging
import os
import random
import ssl
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import redis.asyncio as redis
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","message":"%(message)s"}',
)
logger = logging.getLogger(__name__)

# --- Redis connection ---

REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", None)
REDIS_TLS = os.environ.get("REDIS_TLS", "").lower() in ("1", "true", "yes")
REDIS_CA_CERT = os.environ.get("REDIS_CA_CERT", None)

ITEMS_KEY = "items"

_redis: redis.Redis | None = None


def _build_redis_client() -> redis.Redis:
    kwargs: dict = {
        "host": REDIS_HOST,
        "port": REDIS_PORT,
        "password": REDIS_PASSWORD,
        "decode_responses": True,
    }
    if REDIS_TLS:
        kwargs["ssl"] = True
        if REDIS_CA_CERT:
            kwargs["ssl_context"] = ssl.create_default_context(cafile=REDIS_CA_CERT)
        else:
            kwargs["ssl_context"] = ssl.create_default_context()
    return redis.Redis(**kwargs)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _redis
    _redis = _build_redis_client()
    logger.info("Connected to Redis at %s:%s", REDIS_HOST, REDIS_PORT)
    yield
    if _redis:
        await _redis.aclose()
    logger.info("Shut down")


app = FastAPI(title="Toy Server", lifespan=lifespan)

from fastapi.middleware.cors import CORSMiddleware

_cors_origins = os.environ.get("CORS_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Schemas ---


class ItemCreate(BaseModel):
    name: str
    description: str | None = None


class ItemUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class ItemResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime


# --- Helpers ---


def _serialize_item(item: dict) -> str:
    d = dict(item)
    d["id"] = str(d["id"])
    d["created_at"] = d["created_at"].isoformat()
    d["updated_at"] = d["updated_at"].isoformat()
    return json.dumps(d)


def _deserialize_item(raw: str) -> dict:
    d = json.loads(raw)
    d["id"] = uuid.UUID(d["id"])
    d["created_at"] = datetime.fromisoformat(d["created_at"])
    d["updated_at"] = datetime.fromisoformat(d["updated_at"])
    return d


# --- Routes ---


@app.get("/health")
@app.get("/_health/")
async def health():
    return {"status": "ok"}


@app.get("/ping")
async def ping():
    return {"ping": "pong"}


@app.get("/echo")
async def echo(message: str = Query(default="hello")):
    return {"message": message}


@app.get("/time")
async def time_now():
    return {"time": datetime.now(timezone.utc).isoformat()}


@app.get("/sleepy")
async def sleepy(min_ms: int = Query(default=200), max_ms: int = Query(default=2000)):
    delay_ms = random.randint(min(min_ms, max_ms), max(min_ms, max_ms))
    await asyncio.sleep(delay_ms / 1000.0)
    return {"slept_ms": delay_ms}


@app.get("/v1/items", response_model=list[ItemResponse])
async def list_items():
    raw_items = await _redis.hvals(ITEMS_KEY)
    items = [_deserialize_item(r) for r in raw_items]
    return sorted(items, key=lambda x: x["created_at"], reverse=True)


@app.post("/v1/items", response_model=ItemResponse, status_code=201)
async def create_item(body: ItemCreate):
    now = datetime.now(timezone.utc)
    item = {
        "id": uuid.uuid4(),
        "name": body.name,
        "description": body.description,
        "created_at": now,
        "updated_at": now,
    }
    await _redis.hset(ITEMS_KEY, str(item["id"]), _serialize_item(item))
    return item


@app.get("/v1/items/{item_id}", response_model=ItemResponse)
async def get_item(item_id: uuid.UUID):
    raw = await _redis.hget(ITEMS_KEY, str(item_id))
    if not raw:
        raise HTTPException(status_code=404, detail="Item not found")
    return _deserialize_item(raw)


@app.patch("/v1/items/{item_id}", response_model=ItemResponse)
async def update_item(item_id: uuid.UUID, body: ItemUpdate):
    raw = await _redis.hget(ITEMS_KEY, str(item_id))
    if not raw:
        raise HTTPException(status_code=404, detail="Item not found")
    item = _deserialize_item(raw)
    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        item[key] = value
    item["updated_at"] = datetime.now(timezone.utc)
    await _redis.hset(ITEMS_KEY, str(item["id"]), _serialize_item(item))
    return item


@app.delete("/v1/items/{item_id}", status_code=204)
async def delete_item(item_id: uuid.UUID):
    deleted = await _redis.hdel(ITEMS_KEY, str(item_id))
    if not deleted:
        raise HTTPException(status_code=404, detail="Item not found")
