"""
Authentication routes: register and login.

POST /auth/register  - create a new account, return the user profile.
POST /auth/login     - verify credentials, return a JWT access token (also
                       set as an httpOnly cookie for the web frontend).
POST /auth/logout    - clear the access_token cookie.

Login returns HTTP 200, not 201, since no new resource is created - a token
is minted, not stored. Passwords are never echoed back in any response.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import get_settings
from app.core.security import create_access_token, hash_password, verify_password
from app.database import get_session
from app.models.user import User
from app.api.deps import get_current_user
from app.schemas.user import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.core.limiter import limiter

router = APIRouter()
settings = get_settings()

_COOKIE_NAME = "access_token"


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
@limiter.limit("3/minute")
async def register(
    request: Request,
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
    summary="Log in and receive a JWT access token",
)
@limiter.limit("5/minute")
async def login(
    request: Request,
    body: LoginRequest,
    session: AsyncSession = Depends(get_session),
) -> Response:
    """
    Authenticate with email + password, receive a Bearer token.

    The token is also set as an httpOnly, Secure, SameSite=Strict cookie so
    the web frontend can use it without JavaScript access to the raw value.

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

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated.",
        )

    if not verify_password(body.password, user.hashed_password):
        raise auth_error

    token = create_access_token(subject=user.id)

    response = Response(
        content=TokenResponse(access_token=token).model_dump_json(),
        media_type="application/json",
        status_code=status.HTTP_200_OK,
    )
    response.set_cookie(
        key=_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    return response


@router.get("/me", response_model=UserResponse, summary="Get current user profile")
async def get_me(current_user: User = Depends(get_current_user)) -> User:
    """Return the current user's profile from the httpOnly cookie session."""
    return current_user


@router.post("/logout", summary="Clear the access token cookie")
async def logout() -> Response:
    """Clear the httpOnly access_token cookie so the session is ended."""
    response = JSONResponse(
        content={"detail": "Logged out."},
        status_code=status.HTTP_200_OK,
    )
    response.delete_cookie(key=_COOKIE_NAME, path="/")
    return response
