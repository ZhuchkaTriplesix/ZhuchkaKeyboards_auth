import logging
import secrets

from fastapi import Depends, HTTPException
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette import status
from starlette.responses import HTMLResponse

from src.config import run_granian_app
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
async def get_docs(_username: str = Depends(get_current_username)) -> HTMLResponse:
    return get_swagger_ui_html(openapi_url="/api/openapi.json", title="docs")


if __name__ == "__main__":
    run_granian_app("src.main:app")
