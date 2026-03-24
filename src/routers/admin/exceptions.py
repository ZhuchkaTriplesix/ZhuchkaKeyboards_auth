"""Исключения домена admin API (без HTTP)."""


class AdminNotFoundError(Exception):
    def __init__(self, resource: str, key: str | None = None) -> None:
        self.resource = resource
        self.key = key


class EmailExistsError(Exception):
    pass


class ClientIdExistsError(Exception):
    pass


class UnknownRoleError(Exception):
    def __init__(self, role_name: str) -> None:
        self.role_name = role_name
