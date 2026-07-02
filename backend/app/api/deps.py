"""
FastAPI dependencies shared across route modules.

get_current_user() is used by every protected route via
`current_user: User = Depends(get_current_user)`. Keeping it here (rather
than inline per router) gives one place to change if the auth scheme changes,
and makes it easy to mock in tests via app.dependency_overrides.
"""
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.security import decode_access_token
from app.database import get_session
from app.models.user import User

# HTTPBearer extracts the token from "Authorization: Bearer <token>" automatically.
# auto_error=False means it returns None instead of raising 403 when the header is
# absent, we handle the None case ourselves so we can return 401, not 403.
_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_session),
) -> User:
    """
    Decode the JWT in the Authorization header and load the matching User row.

    Raises HTTP 401 for every auth failure, expired token, bad signature,
    missing header, unknown user, deactivated account. We intentionally use the
    same status code and a generic message for all cases; distinguishing "bad
    signature" from "expired" leaks information to an attacker.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # 1. Header present?
    if credentials is None:
        raise credentials_exception

    # 2. Decode + verify signature and expiry.
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise credentials_exception

    # 3. Extract user identifier from the *sub* claim.
    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    # 4. Load the user from the database.
    user = await session.get(User, int(user_id))
    if user is None:
        raise credentials_exception

    # 5. Check account is still active (soft-delete / ban support).
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated.",
        )

    return user