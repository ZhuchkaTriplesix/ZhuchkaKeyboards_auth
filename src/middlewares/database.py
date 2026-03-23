"""Database session middleware for managing database connections per request."""

from contextvars import ContextVar
from typing import Final
from uuid import uuid1

from sqlalchemy.ext.asyncio.session import AsyncSession
from starlette.requests import Request

from src.database.core import async_session_maker
from src.database.logging import SessionTracker

REQUEST_ID_CTX_KEY: Final[str] = "request_id"
_request_id_ctx_var: ContextVar[str | None] = ContextVar(REQUEST_ID_CTX_KEY, default=None)


def get_request_id() -> str | None:
    """Get the current request ID from context."""
    return _request_id_ctx_var.get()


async def db_session_middleware(request: Request, call_next):
    """
    Middleware for managing database sessions per request.

    Creates a new database session for each request, handles commits/rollbacks,
    and ensures proper cleanup of resources.

    Args:
        request: The incoming request
        call_next: The next middleware/endpoint in the chain

    Returns:
        Response from the next handler
    """
    request_id = str(uuid1())
    ctx_token = _request_id_ctx_var.set(request_id)

    session: AsyncSession | None = None

    try:
        session = async_session_maker()
        request.state.db = session

        session._chime_service_session_id = SessionTracker.track_session(
            session, context="api_request_chime_service"
        )

        response = await call_next(request)

        if session.is_active:
            await session.commit()

        return response

    except Exception as e:
        if session and session.is_active:
            await session.rollback()
        raise e
    finally:
        if session:
            if hasattr(session, "service_session_id"):
                SessionTracker.untrack_session(session.service_session_id)

            await session.close()

        _request_id_ctx_var.reset(ctx_token)
