"""
auth.py – JWT token creation and verification for the Admin Panel.

Credentials are loaded from environment variables:
  ADMIN_USERNAME  (default: "admin")
  ADMIN_PASSWORD  (default: "changeme")
  JWT_SECRET      (default: dev-only secret — override in production!)

Tokens are HS256-signed, expire after JWT_EXPIRE_HOURS (8h).
"""

from __future__ import annotations

import datetime
import os
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "changeme")
JWT_SECRET: str = os.getenv("JWT_SECRET", "dev-secret-do-not-use-in-prod")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 8

# Points to POST /api/auth/login for the Swagger UI "Authorize" button
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=True)


def create_access_token(username: str) -> str:
    """Create a signed JWT that expires in JWT_EXPIRE_HOURS hours."""
    expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
        hours=JWT_EXPIRE_HOURS
    )
    payload = {"sub": username, "exp": expire}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str = Depends(oauth2_scheme)) -> str:
    """
    FastAPI dependency: extracts and verifies the Bearer JWT.
    Returns the username (`sub` claim) or raises HTTP 401.
    """
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload: dict = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        username: Optional[str] = payload.get("sub")
        if username is None:
            raise exc
        return username
    except jwt.PyJWTError:
        raise exc
