import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from sqlalchemy import text
from starlette.middleware.cors import CORSMiddleware

from src.auth.bootstrap import run_bootstrap
from src.database.core import async_session_maker
from src.database.dependencies import DbSession
from src.routers import Router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    try:
        async with async_session_maker() as session:
            await run_bootstrap(session)
    except Exception as exc:
        logger.warning("Bootstrap skipped or failed (DB unavailable?): %s", exc)
    yield


class App:
    def __init__(self) -> None:
        self._app: FastAPI = FastAPI(
            title="Zhuchka Auth",
            description="OAuth2/OIDC authorization server (ZhuchkaKeyboards)",
            version="1.0.0",
            docs_url=None,
            redoc_url=None,
            openapi_url="/api/openapi.json",
            default_response_class=ORJSONResponse,
            lifespan=_lifespan,
        )
        self._app.add_middleware(
            middleware_class=CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["GET", "POST", "DELETE", "PATCH", "PUT"],
            allow_headers=["*"],
        )

        @self._app.get("/health/live", tags=["health"])
        async def health_live() -> dict:
            return {"status": "ok"}

        @self._app.get("/health/ready", tags=["health"])
        async def health_ready(session: DbSession) -> dict:
            await session.execute(text("SELECT 1"))
            return {"status": "ready"}

        self._register_routers()

    def _register_routers(self) -> None:
        for router, prefix, tags in Router.routers:
            self._app.include_router(router=router, prefix=prefix, tags=tags)

    @property
    def app(self) -> FastAPI:
        return self._app
