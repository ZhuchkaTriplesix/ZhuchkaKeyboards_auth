from dataclasses import dataclass
from src.routers.root.router import router as root_request_router

@dataclass(frozen=True)
class Router:
    routers = [
        (root_request_router, "/api/root", ["root"]),
    ]
