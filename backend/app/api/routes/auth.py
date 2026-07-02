"""
Authentication routes: register and login.

POST /auth/register  - create a new account, return the user profile.
POST /auth/login     - verify credentials, return a JWT access token.

Login returns HTTP 200, not 201, since no new resource is created - a token
is minted, not stored. Passwords are never echoed back in any response.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.security import create_access_token, hash_password, verify_password
from app.database import get_session
from app.models.user import User
from app.schemas.user import LoginRequest, RegisterRequest, TokenResponse, UserResponse

router = APIRouter()


async def get_user_by_email(email: str, session: AsyncSession) -> User | None:
    """Return the User row for *email*, or None if not found. Also used by deps.py."""
    result = await session.execute(select(User).where(User.email == email))
    return result.scalars().first()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new account",
)
async def register(
    body: RegisterRequest,
    session: AsyncSession = Depends(get_session),
) -> User:
    """
    Register a new user.

    Rejects duplicate emails with 409, hashes the password with bcrypt before
    storing it, and returns the created profile - no password, no token. The
    client redirects to /auth/login after a successful registration.
    """
    existing = await get_user_by_email(body.email, session)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Log in and receive a JWT access token",
)
async def login(
    body: LoginRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    """
    Authenticate with email + password, receive a Bearer token.

    "Email not found" and "wrong password" return the identical 401 message -
    distinguishing them would tell an attacker which emails are registered.
    """
    auth_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect email or password.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    user = await get_user_by_email(body.email, session)
    if user is None:
        raise auth_error

    if not verify_password(body.password, user.hashed_password):
        raise auth_error

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated.",
        )

    token = create_access_token(subject=user.id)
    return TokenResponse(access_token=token)
