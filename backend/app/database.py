"""
Database engine + session management using SQLModel (built on SQLAlchemy 2.0 async).

Pattern used here:
- One global `engine` for the whole app (connection pooling handled by SQLAlchemy).
- `get_session()` is a FastAPI dependency: it opens a session, yields it to the
  route function, and guarantees it's closed afterwards -- even if the route raises.
- `init_db()` ensures the pgvector extension exists. Schema creation is handled
  by Alembic (`alembic upgrade head`), not by create_all(). The app should
  be started after running migrations, not instead of them.
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
    """Ensure the pgvector extension exists. Schema is managed by Alembic."""
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: `session: AsyncSession = Depends(get_session)`."""
    async with AsyncSessionLocal() as session:
        yield session