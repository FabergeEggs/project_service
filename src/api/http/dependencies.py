from fastapi import Depends, Header, HTTPException
from uuid import UUID
from typing import Optional
from pydantic import BaseModel
import jwt
import requests
import json
import os
from jwt import PyJWKClient
from loguru import logger


class UserInfo(BaseModel):
    user_id: UUID
    username: str
    roles: list[str] = []


# Get configuration from environment
SKIP_AUTH = os.getenv("SKIP_AUTH", "false").lower() == "true"
JWKS_URL = os.getenv("JWKS_URL", "http://keycloak:8080/realms/myrealm/protocol/openid-connect/certs")

# Cache the JWK client
_jwk_client = None

def get_jwk_client():
    global _jwk_client
    if _jwk_client is None:
        logger.info(f"Initializing JWK client with JWKS_URL: {JWKS_URL}")
        try:
            _jwk_client = PyJWKClient(JWKS_URL)
        except Exception as e:
            logger.error(f"Failed to initialize JWK client: {e}")
            raise
    return _jwk_client


async def get_current_user(
    authorization: str = Header(..., alias="Authorization")
):
    # Skip auth in development if configured
    if SKIP_AUTH:
        logger.info("Auth skipped (SKIP_AUTH=true)")
        return UserInfo(
            user_id=UUID("f16b9f8f-e006-45d3-a184-83bfa004f714"),
            username="dev-user",
            roles=["user"]
        )

    logger.debug(f"Authorization header received: {authorization[:50] if len(authorization) > 50 else authorization}...")
    
    if not authorization.startswith("Bearer "):
        logger.warning("Authorization header does not start with 'Bearer '")
        raise HTTPException(status_code=401, detail="Invalid authorization header format")

    token = authorization[7:]  # Remove "Bearer "
    logger.debug(f"Token extracted, length: {len(token)}")
    logger.debug(f"Token format: {token[:20]}...{token[-20:]}")

    try:
        # First, try to decode the token WITHOUT verification to see its structure
        try:
            unverified = jwt.decode(token, options={"verify_signature": False})
            logger.debug(f"Token structure (unverified): sub={unverified.get('sub')}, exp={unverified.get('exp')}, username={unverified.get('preferred_username')}")
        except Exception as decode_err:
            logger.error(f"Could not decode token structure: {decode_err}")
        
        logger.debug(f"Fetching JWK client from: {JWKS_URL}")
        jwk_client = get_jwk_client()
        
        logger.debug("Attempting to fetch signing key from JWKS endpoint...")
        try:
            signing_key = jwk_client.get_signing_key_from_jwt(token)
            logger.debug(f"Signing key obtained successfully")
        except Exception as key_err:
            logger.error(f"Failed to get signing key: {type(key_err).__name__}: {key_err}", exc_info=True)
            raise HTTPException(status_code=401, detail=f"Failed to validate token signature: {str(key_err)}")

        logger.debug("Decoding JWT with RS256 verification...")
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={"verify_exp": True, "verify_aud": False}
        )
        logger.debug(f"Token decoded successfully. Subject (user_id): {payload.get('sub')}")

        user_id = UUID(payload["sub"])
        username = payload.get("preferred_username", "")
        roles = payload.get("realm_access", {}).get("roles", [])

        logger.info(f"User authenticated: {user_id} ({username}) with roles: {roles}")
        return UserInfo(
            user_id=user_id,
            username=username,
            roles=roles
        )
    except jwt.ExpiredSignatureError as e:
        logger.warning(f"Token has expired: {e}")
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token validation failed: {type(e).__name__}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=401, detail=f"Token validation failed: {str(e)}")
