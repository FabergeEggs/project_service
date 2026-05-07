from fastapi import Header, HTTPException, Request
from uuid import UUID
from typing import Optional
from pydantic import BaseModel
from loguru import logger


class UserInfo(BaseModel):
    user_id: UUID
    username: str
    roles: list[str] = []


async def get_current_user(
        request: Request,
        x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
        x_username: Optional[str] = Header(None, alias="X-Username"),
        x_user_roles: Optional[str] = Header(None, alias="X-User-Roles")
):
    headers_dict = dict(request.headers)
    print(f"\n--- DEBUG BACKEND START ---")
    print(f"All headers received: {headers_dict}")
    print(f"X-User-Id: {x_user_id}")
    print(f"X-Username: {x_username}")
    print(f"--- DEBUG BACKEND END ---\n")

    if not x_user_id or not x_username:
        raise HTTPException(
            status_code=401,
            detail={
                "msg": "Headers missing from Gateway",
                "received_headers": list(headers_dict.keys())
            }
        )

    try:
        return UserInfo(
            user_id=UUID(x_user_id),
            username=x_username,
            roles=x_user_roles.split(",") if x_user_roles else []
        )
    except ValueError as e:
        logger.error(f"UUID conversion failed: {e}")
        raise HTTPException(
            status_code=400, detail="Invalid UUID format in X-User-Id")
