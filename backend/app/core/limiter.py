"""
Shared slowapi Limiter instance.

Defined here so both app/main.py (which wires it to app.state) and
app/api/routes/auth.py (which uses @limiter.limit) reference the
exact same object. Two separate Limiter() instances means the rate
limits configured in auth.py are never enforced by the middleware.

Set DISABLE_RATE_LIMITING=true in the environment to disable all rate
limits (useful for integration tests hitting the live server).
"""
import os
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.requests import Request
from starlette.responses import JSONResponse

def _disabled_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """No-op handler when rate limiting is disabled."""
    return JSONResponse(status_code=200, content={"detail": "rate limit disabled"})

_is_disabled = os.environ.get("DISABLE_RATE_LIMITING", "false").lower() == "true"

if _is_disabled:
    # Return a no-op limiter that never blocks
    class _NoopLimiter:
        def reset(self): pass
        def limit(self, *args, **kwargs):
            def deco(fn): return fn
            return deco
    limiter = _NoopLimiter()
else:
    limiter = Limiter(key_func=get_remote_address)
