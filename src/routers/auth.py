from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from src.repositories.user_repository import UserRepository
from src.services.opaque_token_service import HttpCookieServiceDep
from src.services.password_hasher_service import PasswordHasherService
from src.services.user_service import UserService

auth_router = APIRouter()


class RegisterUserRequest(BaseModel):
    username: str
    password: str


class LoginUserRequest(BaseModel):
    username: str
    password: str


def _get_user_repository() -> UserRepository:
    return UserRepository()


def _get_password_hasher_service() -> PasswordHasherService:
    return PasswordHasherService()


UserRepositoryDep = Annotated[UserRepository, Depends(_get_user_repository)]
PasswordHasherServiceDep = Annotated[
    PasswordHasherService,
    Depends(_get_password_hasher_service),
]


def _get_user_service(
    repository: UserRepositoryDep,
    hasher: PasswordHasherServiceDep,
) -> UserService:
    return UserService(repository=repository, hasher=hasher)


UserServiceDep = Annotated[UserService, Depends(_get_user_service)]


@auth_router.post("/register-user")
async def register_user(
    body: RegisterUserRequest,
    user_service: UserServiceDep,
) -> dict:
    user = await user_service.create_user(
        username=body.username,
        password=body.password,
    )
    return {
        "username": user.username,
        "external_id": user.external_id,
        "date_created": user.date_created.isoformat(),
    }


@auth_router.post("/login-user")
async def login_user(
    body: LoginUserRequest,
    user_service: UserServiceDep,
    hasher: PasswordHasherServiceDep,
    http_cookies_service: HttpCookieServiceDep,
) -> dict:
    user = await user_service.get_by_username(body.username)
    if user is None or not hasher.verify(body.password, user.hash_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    await http_cookies_service.set_cookie(
        user_id=user.external_id,
        token_type="access",
    )
    await http_cookies_service.set_cookie(
        user_id=user.external_id,
        token_type="refresh",
    )
    return {"ok": True}


@auth_router.get("/health-check-me")
async def health_check_me(
    http_cookies_service: HttpCookieServiceDep,
) -> dict:
    try:
        await http_cookies_service.get_user_id()
        return {"has_user": True}
    except ValueError:
        return {"has_user": False}