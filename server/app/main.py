import asyncio
import logging
import os
import random
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","message":"%(message)s"}',
)
logger = logging.getLogger(__name__)

# --- In-memory store ---

ITEMS: dict[uuid.UUID, dict] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up")
    yield
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
    return sorted(ITEMS.values(), key=lambda x: x["created_at"], reverse=True)


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
    ITEMS[item["id"]] = item
    return item


@app.get("/v1/items/{item_id}", response_model=ItemResponse)
async def get_item(item_id: uuid.UUID):
    item = ITEMS.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@app.patch("/v1/items/{item_id}", response_model=ItemResponse)
async def update_item(item_id: uuid.UUID, body: ItemUpdate):
    item = ITEMS.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        item[key] = value
    item["updated_at"] = datetime.now(timezone.utc)
    return item


@app.delete("/v1/items/{item_id}", status_code=204)
async def delete_item(item_id: uuid.UUID):
    if item_id not in ITEMS:
        raise HTTPException(status_code=404, detail="Item not found")
    del ITEMS[item_id]
