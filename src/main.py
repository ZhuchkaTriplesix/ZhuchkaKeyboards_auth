import logging
import secrets

import uvicorn

from fastapi import Depends, HTTPException
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.security import HTTPBasicCredentials, HTTPBasic
from starlette import status
from starlette.responses import HTMLResponse

from src.config import uvicorn_cfg
from src.configuration.app import App
from src.middlewares import db_session_middleware

logging.basicConfig(level=logging.INFO)

app = App().app

# Register middleware
app.middleware("http")(db_session_middleware)


async def get_current_username(credentials: HTTPBasicCredentials = Depends(HTTPBasic())) -> str:
    correct_username = secrets.compare_digest(credentials.username, "USERNAME")
    correct_password = secrets.compare_digest(credentials.password, "PASSWORD")

    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )

    return credentials.username


@app.get("/api/docs", response_class=HTMLResponse)
async def get_docs(username: str = Depends(get_current_username)) -> HTMLResponse:
    return get_swagger_ui_html(
        openapi_url="/api/openapi.json",
        title="docs"
    )


if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=uvicorn_cfg.host,
        port=uvicorn_cfg.port,
        workers=uvicorn_cfg.workers,
        loop=uvicorn_cfg.loop,
        http=uvicorn_cfg.http
    )
