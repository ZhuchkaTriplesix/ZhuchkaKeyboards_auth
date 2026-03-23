from sqlalchemy import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from starlette.requests import Request

from src.config import PostgresCfg
from src.database.logging import SessionTracker


def create_db_engine(connection_string: str) -> AsyncEngine:
    """Create a database engine with proper timeout settings.

    Args:
        connection_string: Database connection string
    """
    url = make_url(connection_string)

    # Use existing configuration values with fallbacks
    timeout_kwargs = {
        # Connection timeout - how long to wait for a connection from the pool
        "pool_timeout": PostgresCfg().database_engine_pool_timeout,
        # Recycle connections after this many seconds
        "pool_recycle": PostgresCfg().database_engine_pool_recycle,
        # Maximum number of connections to keep in the pool
        "pool_size": PostgresCfg().database_engine_pool_size,
        # Maximum overflow connections allowed beyond pool_size
        "max_overflow": PostgresCfg().database_engine_max_overflow,
        # Connection pre-ping to verify connection is still alive
        "pool_pre_ping": PostgresCfg().database_engine_pool_ping,
        # Enables/Disables engine logging.
        "echo": PostgresCfg().database_echo,
    }
    return create_async_engine(url=url, **timeout_kwargs)


# Create the default engine with standard timeout
engine = create_db_engine(
    PostgresCfg().url,
)


def get_db(request: Request) -> AsyncSession:
    """Get database session from request state."""
    session = request.state.db
    if not hasattr(session, "service_session_id"):
        session._dispatch_session_id = SessionTracker.track_session(
            session, context="api_request_service"
        )
    return session


async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
