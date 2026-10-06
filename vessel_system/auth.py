"""
Authentication and security boundary for remote MCP server requests.
Enforces Bearer token verification, protects endpoints, and prevents leakage.
"""

import os
import hmac
import logging
from typing import Optional
from dotenv import load_dotenv
from fastapi import Request, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

load_dotenv()

logger = logging.getLogger("vessel_system.auth")

security_bearer = HTTPBearer(auto_error=False)


def get_configured_auth_token() -> Optional[str]:
    """Retrieve the configured auth token from environment variables."""
    token = os.environ.get("VESSEL_MCP_AUTH_TOKEN")
    if token:
        token = token.strip()
    return token or None


def is_auth_enabled() -> bool:
    """Returns True if VESSEL_MCP_AUTH_TOKEN is defined."""
    return get_configured_auth_token() is not None


def verify_bearer_token(credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer)) -> bool:
    """
    Verifies Bearer token against VESSEL_MCP_AUTH_TOKEN using constant-time comparison.
    Raises HTTPException(401) on failure.
    """
    configured_token = get_configured_auth_token()

    # If no token is configured in environment, allow local development with warning
    if not configured_token:
        logger.debug("VESSEL_MCP_AUTH_TOKEN not configured. Bypassing token check in dev mode.")
        return True

    if not credentials or not credentials.credentials:
        logger.warning("Unauthorized access attempt: Missing Bearer token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization Bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Constant time comparison to prevent timing attacks
    if not hmac.compare_digest(credentials.credentials.strip(), configured_token):
        logger.warning("Unauthorized access attempt: Invalid Bearer token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return True


def check_auth_header(auth_header: Optional[str]) -> bool:
    """
    Direct string check useful for MCP transport intercepts.
    """
    configured_token = get_configured_auth_token()
    if not configured_token:
        return True
    if not auth_header:
        return False
    parts = auth_header.strip().split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return hmac.compare_digest(parts[1], configured_token)
    elif len(parts) == 1:
        return hmac.compare_digest(parts[0], configured_token)
    return False
