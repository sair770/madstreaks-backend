"""
Authentication dependencies for protecting endpoints.
"""

from fastapi import HTTPException, Header, Depends
from app.config import settings, logger


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
        # Verify and decode the JWT token using Supabase client
        # The token was issued by Supabase, so we use their verified endpoint
        response = db.client.auth.get_user(token)

        if not response or not response.user:
            raise HTTPException(status_code=401, detail="Invalid token")

        user_id = response.user.id
        logger.debug(f"User authenticated: {user_id[:8]}...")
        return user_id

    except Exception as e:
        logger.warning(f"Token verification failed: {str(e)[:50]}")
        raise HTTPException(status_code=401, detail="Invalid or expired token")


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
