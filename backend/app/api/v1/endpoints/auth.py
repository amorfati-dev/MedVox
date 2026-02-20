"""
Authentication endpoints: login and current user
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_password, create_access_token
from app.models.user import User
from app.schemas.auth import LoginRequest, Token, UserResponse
from app.api.dependencies import get_current_user

logger = structlog.get_logger()

router = APIRouter()


@router.post("/login", response_model=Token)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate with email and password, return a JWT access token."""
    user = db.query(User).filter(
        User.email == request.email,
        User.is_active == True
    ).first()

    if not user or not verify_password(request.password, user.hashed_password):
        logger.warning("Failed login attempt", email=request.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(subject=str(user.id))

    logger.info("User logged in", user_id=user.id, email=user.email, role=user.role.value)

    return Token(access_token=token)


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    """Return the current authenticated user's profile."""
    return current_user
