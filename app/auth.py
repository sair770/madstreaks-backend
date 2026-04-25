"""
Authentication dependencies for protecting endpoints.
"""

from fastapi import HTTPException, Header, Depends
from app.config import settings, logger


async def verify_user_token(authorization: str = Header(None)) -> str:
    """
    Verify user authentication token.
    Returns user_id if valid.

    For MVP: Accept any valid user_id format (UUID).
    TODO: Integrate with JWT/session tokens from frontend auth.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    # Extract token from "Bearer <user-id>"
    parts = authorization.split()
    if len(parts) != 2 or parts[0] != "Bearer":
        raise HTTPException(
            status_code=401,
            detail="Invalid Authorization format. Use: Bearer <user-id>"
        )

    user_id = parts[1]

    # Basic validation: should be UUID format (36 chars with hyphens)
    if len(user_id) != 36 or user_id.count("-") != 4:
        logger.warning(f"Invalid user_id format attempted: {user_id[:20]}...")
        raise HTTPException(status_code=401, detail="Invalid user token format")

    logger.debug(f"User authenticated: {user_id[:8]}...")
    return user_id


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
