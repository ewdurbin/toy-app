import asyncio
import json
import logging
import os
import random
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import redis.asyncio as redis
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import (
    SESSION_COOKIE_NAME,
    SESSION_COOKIE_SECURE,
    SESSION_TTL_SECONDS,
    hash_password,
    hash_session_token,
    is_valid_email,
    new_session_token,
    normalize_email,
    verify_password,
)
from app.database import engine, get_db, is_database_configured
from app.models import User, UserSession

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
AUTH_DISABLED_DETAIL = "Postgres auth is unavailable because DATABASE_URL is not configured"


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
            kwargs["ssl_ca_certs"] = REDIS_CA_CERT
    return redis.Redis(**kwargs)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _redis
    _redis = _build_redis_client()
    logger.info("Connected to Redis at %s:%s", REDIS_HOST, REDIS_PORT)
    yield
    if _redis:
        await _redis.aclose()
    if engine is not None:
        await engine.dispose()
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


class AuthPayload(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=128)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    created_at: datetime


class AuthSessionResponse(BaseModel):
    user: UserResponse
    expires_at: datetime


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


def _cookie_max_age(expires_at: datetime) -> int:
    remaining = int((expires_at - datetime.now(timezone.utc)).total_seconds())
    return max(remaining, 0)


def _set_session_cookie(response: Response, token: str, expires_at: datetime) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=SESSION_COOKIE_SECURE,
        max_age=_cookie_max_age(expires_at),
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        httponly=True,
        samesite="lax",
        secure=SESSION_COOKIE_SECURE,
    )


def _auth_response(user: User, auth_session: UserSession) -> AuthSessionResponse:
    return AuthSessionResponse(
        user=UserResponse.model_validate(user),
        expires_at=auth_session.expires_at,
    )


async def _get_auth_session(
    db: AsyncSession, token: str | None
) -> UserSession | None:
    if not token:
        return None

    result = await db.execute(
        select(UserSession)
        .options(selectinload(UserSession.user))
        .where(UserSession.token_hash == hash_session_token(token))
    )
    auth_session = result.scalar_one_or_none()
    if auth_session is None:
        return None
    if auth_session.expires_at <= datetime.now(timezone.utc):
        await db.delete(auth_session)
        await db.commit()
        return None
    return auth_session


async def _create_auth_session(
    db: AsyncSession, user: User
) -> tuple[str, UserSession]:
    token = new_session_token()
    auth_session = UserSession(
        user=user,
        token_hash=hash_session_token(token),
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=SESSION_TTL_SECONDS),
    )
    db.add(auth_session)
    await db.commit()
    await db.refresh(auth_session)
    return token, auth_session


async def get_auth_db() -> AsyncGenerator[AsyncSession]:
    if not is_database_configured():
        raise HTTPException(status_code=503, detail=AUTH_DISABLED_DETAIL)
    async for session in get_db():
        yield session


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


@app.get("/v1/auth/status")
async def auth_status():
    return {"enabled": is_database_configured()}


@app.post("/v1/auth/signup", response_model=AuthSessionResponse, status_code=201)
async def signup(
    body: AuthPayload,
    response: Response,
    db: AsyncSession = Depends(get_auth_db),
):
    email = normalize_email(body.email)
    if not is_valid_email(email):
        raise HTTPException(status_code=422, detail="Invalid email address")

    existing_user = await db.scalar(select(User).where(User.email == email))
    if existing_user is not None:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(email=email, password_hash=hash_password(body.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token, auth_session = await _create_auth_session(db, user)
    _set_session_cookie(response, token, auth_session.expires_at)
    return _auth_response(user, auth_session)


@app.post("/v1/auth/login", response_model=AuthSessionResponse)
async def login(
    body: AuthPayload,
    response: Response,
    db: AsyncSession = Depends(get_auth_db),
):
    email = normalize_email(body.email)
    user = await db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token, auth_session = await _create_auth_session(db, user)
    _set_session_cookie(response, token, auth_session.expires_at)
    return _auth_response(user, auth_session)


@app.post("/v1/auth/logout", status_code=204)
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_auth_db),
):
    token = request.cookies.get(SESSION_COOKIE_NAME)
    auth_session = await _get_auth_session(db, token)
    if auth_session is not None:
        await db.delete(auth_session)
        await db.commit()
    _clear_session_cookie(response)


@app.get("/v1/auth/me", response_model=AuthSessionResponse)
async def me(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_auth_db),
):
    auth_session = await _get_auth_session(
        db, request.cookies.get(SESSION_COOKIE_NAME)
    )
    if auth_session is None:
        _clear_session_cookie(response)
        raise HTTPException(status_code=401, detail="Not authenticated")
    return _auth_response(auth_session.user, auth_session)


@app.get("/v1/items/count")
async def count_items():
    count = await _redis.hlen(ITEMS_KEY)
    return {"count": count}


@app.get("/v1/items/search", response_model=list[ItemResponse])
async def search_items(q: str = Query(default="")):
    raw_items = await _redis.hvals(ITEMS_KEY)
    items = [_deserialize_item(r) for r in raw_items]
    if q:
        q_lower = q.lower()
        items = [
            i for i in items
            if q_lower in i["name"].lower()
            or (i.get("description") and q_lower in i["description"].lower())
        ]
    return sorted(items, key=lambda x: x["created_at"], reverse=True)


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
