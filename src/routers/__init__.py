from dataclasses import dataclass

from src.routers.admin.router import router as admin_router
from src.routers.oauth.router import router as oauth_router
from src.routers.root.router import router as root_request_router


@dataclass(frozen=True)
class Router:
    routers = [
        (oauth_router, "", ["oauth", "oidc"]),
        (admin_router, "/api/v1", ["admin"]),
        (root_request_router, "/api/root", ["root"]),
    ]
