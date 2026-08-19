from contextlib import asynccontextmanager

from anyio.to_thread import run_sync
from fastapi import FastAPI
from pymongo import AsyncMongoClient

from src.repositories.user_repository import UserRepository
from src.services.opaque_token_service import AuthRedisClientService


@asynccontextmanager
async def lifespan(app: FastAPI):
    await run_sync(AuthRedisClientService.redis_init)
    await run_sync(UserRepository.mongodb_init, AsyncMongoClient())
    yield
    await AuthRedisClientService.redis_close()
