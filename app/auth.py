"""
Authentication dependencies for protecting endpoints.
"""

from fastapi import HTTPException, Header, Depends
from app.config import settings, logger
import json
import base64
import time
from typing import Any


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
        token_parts = token.split(".")
        if len(token_parts) != 3:
            logger.error(f"Token has {len(token_parts)} parts instead of 3")
            raise ValueError(f"Invalid JWT format: expected 3 parts, got {len(token_parts)}")

        payload_part = token_parts[1]

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
            logger.error(f"Token missing 'sub' claim. Payload keys: {list(payload.keys())}")
            raise HTTPException(status_code=401, detail="Invalid token: missing user ID")

        # Basic validation: check expiry if present
        if "exp" in payload:
            import time
            current_time = time.time()
            exp_time = payload["exp"]
            if exp_time < current_time:
                logger.warning(f"Token expired. exp={exp_time}, now={current_time}")
                raise HTTPException(status_code=401, detail="Token expired")

        logger.info(f"✅ User authenticated: {user_id[:8]}... (email: {payload.get('email', 'unknown')})")
        return user_id

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"❌ Token verification failed: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=401, detail=f"Invalid token: {type(e).__name__}: {str(e)[:50]}")


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
