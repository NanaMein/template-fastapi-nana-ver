import os
from datetime import datetime, timedelta
from json import JSONDecodeError
from json import dumps as json_dumps
from json import loads as json_loads
from secrets import token_urlsafe
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, Request, Response, status
from redis import RedisError
from redis.asyncio import Redis

load_dotenv()

REDIS_URL: str = os.getenv("REDIS_URL", "redis://127.0.0.1:6379")
PH_ZONE = ZoneInfo("Asia/Manila")
TOKEN_TYPES= Literal["access", "refresh"]
ACCESS_TOKEN_EXPIRY = timedelta(minutes=5)
REFRESH_TOKEN_EXPIRY = timedelta(days=7)
ACCESS_TOKEN_MAX_AGE = int(ACCESS_TOKEN_EXPIRY.total_seconds())
REFRESH_TOKEN_MAX_AGE = int(REFRESH_TOKEN_EXPIRY.total_seconds())
IS_TESTING_MODE = os.getenv("IS_TESTING_MODE", "yes").lower() == "yes"
SECURE = not IS_TESTING_MODE


class AuthRedisClientService:
    _redis_client: Redis | None = None

    @classmethod
    def redis_init(cls) -> None:
        if cls._redis_client is None:
            cls._redis_client = Redis.from_url(REDIS_URL, decode_responses=True)

    @classmethod
    async def redis_close(cls) -> None:
        if cls._redis_client is not None:
            await cls._redis_client.aclose()
            cls._redis_client = None

    def get_redis_client(self) -> Redis:
        if self._redis_client is None:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Redis client is not initialized")
        return self._redis_client

    async def set(
        self,
        key: str,
        value: dict[str, str],
        expiry: timedelta | None,
    ) -> bool:
        try:
            new_value = json_dumps(value)
            r = self.get_redis_client()
            await r.set(
                name=key,
                value=new_value,
                ex=expiry
            )
            return True
        except (TypeError, RedisError):
            return False

    async def get(self, key: str) -> dict[str, str] | None:
        try:
            r = self.get_redis_client()
            value = await r.get(key)
            if value is not None:
                return json_loads(value)
            return None
        except (JSONDecodeError, TypeError, RedisError):
            return None

    async def delete(self, key: str) -> bool:
        try:
            r = self.get_redis_client()
            await r.delete(key)
            return True
        except RedisError:
            return False



class TokenService:
    def __init__(self, auth_redis_service: AuthRedisClientService):
        self.auth_redis_service = auth_redis_service

    @staticmethod
    def get_token() -> str:
        return token_urlsafe(32)

    async def get_payload(self, token: str) -> dict[str, str] | None:
        return await self.auth_redis_service.get(token)



    async def set_token(self, user_id: str, token_type: TOKEN_TYPES) -> str:
        new_token = self.get_token()
        if token_type == "access":
            expiry = ACCESS_TOKEN_EXPIRY
        else:
            expiry = REFRESH_TOKEN_EXPIRY

        value = {
            "token_type": f"{token_type}_token",
            "user_id": user_id,
            "iat": datetime.now(PH_ZONE).isoformat(),
        }

        if await self.auth_redis_service.set(
            key=new_token,
            value=value,
            expiry=expiry
        ):
            return new_token

        raise RedisError("Failed to set token in Redis")

    async def delete_token(self, token: str):
        return self.auth_redis_service.delete(token)

class HttpsCookieService:
    def __init__(
        self,
        token_service: TokenService,
        request: Request,
        response: Response,
    ):
        self.token_service = token_service
        self.request = request
        self.response = response

    async def set_cookie(self, user_id: str, token_type: TOKEN_TYPES) -> None:
        new_token = await self.token_service.set_token(
            user_id=user_id,
            token_type=token_type,
        )
        if token_type == "access":
            max_age = ACCESS_TOKEN_MAX_AGE
            samesite = "lax"
        else:
            max_age = REFRESH_TOKEN_MAX_AGE
            samesite = "strict"

        self.response.set_cookie(
            key=token_type,
            value=new_token,
            max_age=max_age,
            httponly=True,
            samesite=samesite,
            secure=SECURE,
            path="/",
        )


    def get_access_token_from_cookie(self) -> str | None:
        return self.request.cookies.get("access", None)

    def get_refresh_token_from_cookie(self) -> str | None:
        return self.request.cookies.get("refresh", None)

    async def get_payload_from_access_token(self) -> dict[str, str] | None:
        access_token = self.get_access_token_from_cookie()
        if not access_token:
            return None

        return await self.token_service.get_payload(token=access_token)

    async def get_payload_from_refresh_token(self) -> dict[str, str] | None:
        refresh_token = self.get_refresh_token_from_cookie()
        if not refresh_token:
            return None

        return await self.token_service.get_payload(token=refresh_token)

    async def verified_user_id_from_access_token(self) -> str | None:
        payload = await self.get_payload_from_access_token()
        if not payload or payload.get("token_type") != "access_token":
            return None

        return payload.get("user_id")

    async def verified_user_id_from_refresh_token(self) -> str | None:
        payload = await self.get_payload_from_refresh_token()
        if not payload or payload.get("token_type") != "refresh_token":
            return None

        return payload.get("user_id")


    async def get_user_id(self) -> str:

        is_verified_access_user_id = await self.verified_user_id_from_access_token()
        if is_verified_access_user_id:
            return is_verified_access_user_id


        is_verified_refresh_user_id = await self.verified_user_id_from_refresh_token()
        if is_verified_refresh_user_id:
            await self.set_cookie(user_id=is_verified_refresh_user_id, token_type="access")
            await self.set_cookie(user_id=is_verified_refresh_user_id, token_type="refresh")

            old_refresh_token = self.get_refresh_token_from_cookie()
            if old_refresh_token:
                await self.token_service.delete_token(old_refresh_token)

            return is_verified_refresh_user_id

        raise ValueError("User ID not verified")




def _get_auth_redis_service() -> AuthRedisClientService:
    return AuthRedisClientService()

AuthServiceDep = Annotated[AuthRedisClientService, Depends(_get_auth_redis_service)]

def _get_token_service(
    auth_redis_service: AuthServiceDep
) -> TokenService:
    return TokenService(auth_redis_service)

TokenServiceDep = Annotated[TokenService, Depends(_get_token_service)]


def _get_http_cookie_service(
    token_service: TokenServiceDep,
    request: Request,
    response: Response,
) -> HttpsCookieService:
    return HttpsCookieService(request=request, response=response, token_service=token_service)

HttpCookieServiceDep = Annotated[HttpsCookieService, Depends(_get_http_cookie_service)]

async def get_user_id(http_cookies_service: HttpCookieServiceDep) -> str:
    return await http_cookies_service.get_user_id()
