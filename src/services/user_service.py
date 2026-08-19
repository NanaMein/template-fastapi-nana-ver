from datetime import datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status

from src.repositories.user_repository import User, UserRepository
from src.services.password_hasher_service import PasswordHasherService

PH_ZONE = ZoneInfo("Asia/Manila")


class UserService:
    def __init__(self, repository: UserRepository, hasher: PasswordHasherService):
        self.repository = repository
        self.hasher = hasher

    async def create_user(self, username: str, password: str) -> User:
        existing = await self.repository.find_by_username(username)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered",
            )

        hash_password = self.hasher.hash(password)
        external_id = str(uuid4())
        date_created = datetime.now(PH_ZONE)

        user = User(
            username=username,
            hash_password=hash_password,
            date_created=date_created,
            external_id=external_id,
        )

        await self.repository.create(user)
        return user

    async def get_by_username(self, username: str) -> User | None:
        return await self.repository.find_by_username(username)

    async def get_by_external_id(self, external_id: str) -> User | None:
        return await self.repository.find_by_external_id(external_id)
