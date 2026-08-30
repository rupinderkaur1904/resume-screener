"""
FastAPI application entry point: creates the app, wires up startup/shutdown,
registers middleware + exception handlers, and includes the routers.
Business logic lives in app/services/* and app/ml/*, not here.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.database import init_db
from app.api.routes import auth, resumes, jobs, matches

settings = get_settings()

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs once when the container starts, and once when it shuts down."""
    logger.info("Startup: ensuring pgvector extension...")
    await init_db()
    logger.info("Database extensions ready. Run 'alembic upgrade head' for schema migrations.")

    logger.info("Startup: loading sentence-transformers model into memory...")
    from app.ml.model_loader import get_embedding_model
    get_embedding_model()  # warms the @lru_cache so the first real request is fast

    logger.info("Startup complete - %s is ready.", settings.APP_NAME)
    yield
    logger.info("Shutting down %s.", settings.APP_NAME)


from app.core.limiter import limiter

app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan,
    state={"limiter": limiter},
)
app.state.limiter = limiter
if hasattr(limiter, 'reset'):  # real Limiter, not noop
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """
    Catch-all so an unexpected bug never leaks a Python traceback to the client.
    The real traceback still goes to the server logs via logger.exception().
    """
    logger.exception("Unhandled error on %s %s", request.method, request.url)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again later."},
    )


@app.get("/health", tags=["meta"])
async def health_check():
    """Liveness probe used by the Docker HEALTHCHECK and, later, any load balancer."""
    return {"status": "ok", "environment": settings.ENVIRONMENT}


app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(resumes.router, prefix="/resumes", tags=["resumes"])
app.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
app.include_router(matches.router, prefix="/matches", tags=["matches"])