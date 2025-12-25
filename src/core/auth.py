"""
Authentication utilities for the application.

This module provides JWT-based authentication and user management.
"""

import logging
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from src.core.config import settings

logger = logging.getLogger(__name__)

# Security scheme for JWT tokens
security = HTTPBearer(auto_error=False)


class TokenData(BaseModel):
    """Token data model."""
    username: str | None = None
    user_id: str | None = None


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: Data to encode in the token
        expires_delta: Token expiration time

    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=settings.jwt_expiration_hours)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return encoded_jwt


def verify_token(token: str) -> TokenData | None:
    """
    Verify and decode a JWT token.

    Args:
        token: JWT token to verify

    Returns:
        TokenData if valid, None if invalid
    """
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        username: str = payload.get("sub")
        user_id: str = payload.get("user_id")

        if username is None:
            return None

        token_data = TokenData(username=username, user_id=user_id)
        return token_data
    except JWTError as e:
        logger.error(f"Token verification failed: {e}")
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security)
) -> str:
    """
    Get current user from JWT token.

    Args:
        credentials: HTTP authorization credentials

    Returns:
        User ID if authenticated, raises HTTPException if not

    Raises:
        HTTPException: If authentication fails
    """
    if not credentials:
        # For development, allow a default user
        if settings.debug:
            return "dev_user_123"
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_data = verify_token(credentials.credentials)

    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return token_data.user_id


# Dependency for optional authentication (doesn't raise error if not authenticated)
async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(security)
) -> str | None:
    """Get current user if authenticated, None if not."""
    if not credentials:
        return None

    token_data = verify_token(credentials.credentials)
    return token_data.user_id if token_data else None


# Type alias for authenticated user
CurrentUser = Annotated[str, Depends(get_current_user)]
CurrentUserOptional = Annotated[str | None, Depends(get_current_user_optional)]
