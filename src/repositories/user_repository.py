from datetime import datetime
from zoneinfo import ZoneInfo

from pymongo import AsyncMongoClient
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.asynchronous.database import AsyncDatabase

PH_ZONE = ZoneInfo("Asia/Manila")
USER_DATABASE_NAME = "test_database"
USER_COLLECTION_NAME = "users"


class User:
    def __init__(
        self,
        username: str,
        hash_password: str,
        date_created: datetime,
        external_id: str,
    ):
        self.username = username
        self.hash_password = hash_password
        self.date_created = date_created
        self.external_id = external_id


class UserRepository:
    _client: AsyncMongoClient | None = None

    @classmethod
    def mongodb_init(cls, client: AsyncMongoClient) -> None:
        if cls._client is None:
            cls._client = client

    @classmethod
    async def find_by_username(cls, username: str) -> User | None:
        if cls._client is None:
            return None
        db: AsyncDatabase = cls._client.get_database(USER_DATABASE_NAME)
        collection: AsyncCollection = db.get_collection(USER_COLLECTION_NAME)
        doc = await collection.find_one({"username": username})
        if doc is None:
            return None
        return User(
            username=doc["username"],
            hash_password=doc["hash_password"],
            date_created=doc["date_created"],
            external_id=doc["external_id"],
        )

    @classmethod
    async def find_by_external_id(cls, external_id: str) -> User | None:
        if cls._client is None:
            return None
        db = cls._client.get_database(USER_DATABASE_NAME)
        collection = db.get_collection(USER_COLLECTION_NAME)
        doc = await collection.find_one({"external_id": external_id})
        if doc is None:
            return None
        return User(
            username=doc["username"],
            hash_password=doc["hash_password"],
            date_created=doc["date_created"],
            external_id=doc["external_id"],
        )

    @classmethod
    async def create(cls, user: User) -> User:
        if cls._client is None:
            raise ValueError("MongoDB client not initialized. Call mongodb_init first.")
        db: AsyncDatabase = cls._client.get_database(USER_DATABASE_NAME)
        collection: AsyncCollection = db.get_collection(USER_COLLECTION_NAME)
        await collection.insert_one(
            {
                "username": user.username,
                "hash_password": user.hash_password,
                "date_created": user.date_created,
                "external_id": user.external_id,
            }
        )
        return user
