from fastapi import Depends, Header, HTTPException
from uuid import UUID
from typing import Optional
from pydantic import BaseModel


class UserInfo(BaseModel):
    user_id: UUID
    username: str
    roles: list[str] = []


async def get_current_user(
        x_user_id: str = Header(..., alias="X-User-Id"),
        x_username: str = Header(..., alias="X-Username"),
        x_user_roles: Optional[str] = Header(None, alias="X-User-Roles")
):
    try:
        return UserInfo(
            user_id=UUID(x_user_id),
            username=x_username,
            roles=x_user_roles.split(",") if x_user_roles else []
        )
    except ValueError:
        raise HTTPException(
            status_code=400, detail="Invalid user information in headers")
