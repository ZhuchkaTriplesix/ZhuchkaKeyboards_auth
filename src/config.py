import configparser
import os
from abc import ABC
from dataclasses import asdict, dataclass

config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__), '..', 'config.ini'))


class CfgBase(ABC):
    dict: callable = asdict


class PostgresCfg(CfgBase):
    def __init__(self):
        self.database: str = config["POSTGRES"]["DATABASE"]
        self.driver: str = config["POSTGRES"]["DRIVER"]
        self.database_name: str = config["POSTGRES"]["DATABASE_NAME"]
        self.username: str = config["POSTGRES"]["USERNAME"]
        self.password: str = config["POSTGRES"]["PASSWORD"]
        self.ip: str = config["POSTGRES"]["IP"]
        self.port: int = config.getint("POSTGRES", "PORT")

        self.database_engine_pool_timeout: int = config.getint("POSTGRES", "DATABASE_ENGINE_POOL_TIMEOUT")
        self.database_engine_pool_recycle: int = config.getint("POSTGRES", "DATABASE_ENGINE_POOL_RECYCLE")
        self.database_engine_pool_size: int = config.getint("POSTGRES", "DATABASE_ENGINE_POOL_SIZE")
        self.database_engine_max_overflow: int = config.getint("POSTGRES", "DATABASE_ENGINE_MAX_OVERFLOW")
        self.database_engine_pool_ping: bool = config.getboolean("POSTGRES", "DATABASE_ENGINE_POOL_PING")
        self.database_echo: bool = config.getboolean("POSTGRES", "DATABASE_ECHO")

    @property
    def url(self) -> str:
        return f"{self.database}+{self.driver}://{self.username}:{self.password}@{self.ip}:{self.port}/{self.database_name}"


@dataclass
class UvicornCfg(CfgBase):
    """Bind/workers/loop/http: used by Granian in run_granian_app (UVICORN section name is legacy)."""

    host: str = config["UVICORN"]["HOST"]
    port: int = config.getint("UVICORN", "PORT")
    workers: int = config.getint("UVICORN", "WORKERS")
    loop: str = config.get("UVICORN", "LOOP", fallback="auto")
    http: str = config.get("UVICORN", "HTTP", fallback="auto")


@dataclass
class RedisCfg(CfgBase):
    host: str = config["REDIS"]["HOST"]
    port: int = config.getint("REDIS", "PORT")
    db: int = config.getint("REDIS", "DB")
    password: str = config["REDIS"]["PASSWORD"]


class AuthCfg(CfgBase):
    """OAuth/JWT settings ([AUTH] in config.ini; optional — defaults apply)."""

    def __init__(self) -> None:
        self.issuer: str = self._get("ISSUER", "http://127.0.0.1:8000")
        self.audience: str = self._get("AUDIENCE", "zhuchka-api")
        self.access_token_minutes: int = self._get_int("ACCESS_TOKEN_MINUTES", 15)
        self.refresh_token_days: int = self._get_int("REFRESH_TOKEN_DAYS", 30)
        self.jwt_private_key_path: str = self._get("JWT_PRIVATE_KEY_PATH", "var/jwt_private.pem")
        self.bootstrap_admin_email: str = self._get("BOOTSTRAP_ADMIN_EMAIL", "").strip()
        self.bootstrap_admin_password: str = self._get("BOOTSTRAP_ADMIN_PASSWORD", "").strip()
        self.bootstrap_client_id: str = self._get("BOOTSTRAP_CLIENT_ID", "zhuchka-dev")
        self.bootstrap_client_secret: str = self._get("BOOTSTRAP_CLIENT_SECRET", "change-me-dev-only")
        self.password_grant_enabled: bool = self._get_bool("PASSWORD_GRANT_ENABLED", True)

    def _get(self, key: str, fallback: str) -> str:
        if not config.has_section("AUTH"):
            return fallback
        return config.get("AUTH", key, fallback=fallback)

    def _get_int(self, key: str, fallback: int) -> int:
        if not config.has_section("AUTH"):
            return fallback
        return config.getint("AUTH", key, fallback=fallback)

    def _get_bool(self, key: str, fallback: bool) -> bool:
        if not config.has_section("AUTH"):
            return fallback
        return config.getboolean("AUTH", key, fallback=fallback)


uvicorn_cfg = UvicornCfg()
redis_cfg = RedisCfg()
auth_cfg = AuthCfg()

def granian_loop_mode(loop_name: str):
    from granian.constants import Loops

    name = (loop_name or "auto").strip().lower()
    for m in Loops:
        if m.value == name or m.name.lower() == name:
            return m
    return Loops.auto


def granian_http_mode(http_name: str):
    from granian.constants import HTTPModes

    name = (http_name or "auto").strip().lower()
    if name == "auto":
        return HTTPModes.auto
    if name in ("1", "http1", "h1"):
        return HTTPModes.http1
    if name in ("2", "http2", "h2"):
        return HTTPModes.http2
    return HTTPModes.auto


def run_granian_app(target: str) -> None:
    # ASGI via Granian; HTTP access lines use the granian.access logger (log_access=True).
    from granian import Granian
    from granian.constants import Interfaces

    Granian(
        target=target,
        address=uvicorn_cfg.host,
        port=uvicorn_cfg.port,
        interface=Interfaces.ASGI,
        workers=uvicorn_cfg.workers,
        loop=granian_loop_mode(uvicorn_cfg.loop),
        http=granian_http_mode(uvicorn_cfg.http),
        log_access=True,
    ).serve()

