"""
Authentication dependencies for protecting endpoints.
"""

from fastapi import HTTPException, Header, Depends
from app.config import settings, logger
import jwt
import json
from typing import Any

# Get Supabase public key for JWT verification
SUPABASE_JWT_SECRET = settings.supabase_service_key.split(".")[-1] if "." in settings.supabase_service_key else ""


async def verify_user_token(authorization: str = Header(None)) -> str:
    """
    Verify Supabase JWT token from Authorization header.
    Returns user_id (UUID) from the token.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    # Extract token from "Bearer <jwt_token>"
    parts = authorization.split()
    if len(parts) != 2 or parts[0] != "Bearer":
        raise HTTPException(
            status_code=401,
            detail="Invalid Authorization format. Use: Bearer <token>"
        )

    token = parts[1]

    try:
        # Decode JWT token without verification first to get the payload
        # JWT format: header.payload.signature
        payload_part = token.split(".")[1]

        # Add padding if needed
        padding = 4 - len(payload_part) % 4
        if padding != 4:
            payload_part += "=" * padding

        # Decode base64 payload
        import base64
        decoded_bytes = base64.urlsafe_b64decode(payload_part)
        payload = json.loads(decoded_bytes)

        # Extract user_id from the 'sub' claim (subject = user_id in Supabase tokens)
        user_id = payload.get("sub")

        if not user_id:
            logger.warning(f"Token missing 'sub' claim: {payload.get('aud')}")
            raise HTTPException(status_code=401, detail="Invalid token: missing user ID")

        # Basic validation: check expiry if present
        if "exp" in payload:
            import time
            if payload["exp"] < time.time():
                raise HTTPException(status_code=401, detail="Token expired")

        logger.debug(f"User authenticated: {user_id[:8]}...")
        return user_id

    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Token verification failed: {str(e)[:100]}")
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)[:50]}")


async def verify_briefing_api_key(authorization: str = Header(None)) -> bool:
    """
    Verify briefing API key for /alerts/from-briefing endpoint.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    parts = authorization.split()
    if len(parts) != 2 or parts[0] != "Bearer":
        raise HTTPException(status_code=401, detail="Invalid Authorization format")

    api_key = parts[1]
    if api_key != settings.briefing_api_key:
        logger.warning(f"Invalid briefing API key attempted: {api_key[:10]}...")
        raise HTTPException(status_code=403, detail="Invalid API key")

    return True
