import base64
import json as _json
from fastapi import Header, HTTPException, Request
from uuid import UUID
from typing import Optional
from pydantic import BaseModel
from loguru import logger


class UserInfo(BaseModel):
    user_id: UUID
    username: str
    roles: list[str] = []


def _decode_jwt_payload(token: str) -> dict:
    try:
        payload_b64 = token.split('.')[1]
        payload_b64 += '=' * (4 - len(payload_b64) % 4)
        return _json.loads(base64.urlsafe_b64decode(payload_b64))
    except Exception:
        return {}


async def get_current_user(
        request: Request,
        x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
        x_username: Optional[str] = Header(None, alias="X-Username"),
        x_user_roles: Optional[str] = Header(None, alias="X-User-Roles")
):
    if not x_user_id or not x_username:
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            payload = _decode_jwt_payload(auth[7:])
            x_user_id = x_user_id or payload.get("sub")
            x_username = x_username or payload.get("preferred_username")
            if not x_user_roles:
                roles = payload.get("realm_access", {}).get("roles", [])
                x_user_roles = ",".join(roles) if roles else None

    if not x_user_id or not x_username:
        raise HTTPException(
            status_code=401,
            detail="Missing user identity headers"
        )

    try:
        return UserInfo(
            user_id=UUID(x_user_id),
            username=x_username,
            roles=x_user_roles.split(",") if x_user_roles else []
        )
    except ValueError as e:
        logger.error(f"UUID conversion failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid UUID format in X-User-Id")
