"""
Database engine + session management using SQLModel (built on SQLAlchemy 2.0 async).

Pattern used here:
- One global `engine` for the whole app (connection pooling handled by SQLAlchemy).
- `get_session()` is a FastAPI dependency: it opens a session, yields it to the
  route function, and guarantees it's closed afterwards -- even if the route raises.
- `init_db()` is a DEV-ONLY convenience that creates tables directly from the
  SQLModel metadata. A real deployment should replace this with
  `alembic upgrade head`, since create_all() can't handle schema changes
  safely once there's real data.
"""
from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from app.config import get_settings

settings = get_settings()

engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,   # logs every SQL statement when DEBUG=true - great for learning
    pool_pre_ping=True,    # avoids "stale connection" errors after DB restarts
)

AsyncSessionLocal = sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)


async def init_db() -> None:
    """Create the pgvector extension and all tables. Dev-only, see docstring above."""
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        # Importing the models module here (not at top of file) ensures every
        # SQLModel table class has been registered on SQLModel.metadata before
        # we call create_all.
        from app import models  # noqa: F401
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: `session: AsyncSession = Depends(get_session)`."""
    async with AsyncSessionLocal() as session:
        yield session