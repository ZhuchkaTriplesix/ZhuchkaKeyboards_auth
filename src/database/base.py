import re
from sqlalchemy import inspect
from sqlalchemy.orm import declarative_base, declared_attr


def resolve_table_name(name):
    names = re.split("(?=[A-Z])", name)
    return "_".join([x.lower() for x in names if x])


class CustomBase:
    __repr_attrs__ = []
    __repr_max_length__ = 15

    @declared_attr
    def __tablename__(cls):
        return resolve_table_name(cls.__name__)

    def dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    @property
    def _id_str(self):
        ids = inspect(self).identity
        return "-".join([str(x) for x in ids]) if ids and len(ids) > 1 else str(ids[0]) if ids else "None"

    @property
    def _repr_attrs_str(self):
        max_length = self.__repr_max_length__

        values = []
        single = len(self.__repr_attrs__) == 1
        for key in self.__repr_attrs__:
            if not hasattr(self, key):
                raise KeyError(f"{self.__class__} has incorrect attribute '{key}' in __repr__attrs__")
            value = getattr(self, key)
            wrap_in_quote = isinstance(value, str)

            value = str(value)
            if len(value) > max_length:
                value = value[:max_length] + "..."

            if wrap_in_quote:
                value = f"'{value}'"
            values.append(value if single else f"{key}:{value}")

        return " ".join(values)

    def __repr__(self):
        id_str = f"#{self._id_str}" if self._id_str else ""
        return f"<{self.__class__.__name__} {id_str} {self._repr_attrs_str if self._repr_attrs_str else ''}>"


Base = declarative_base(cls=CustomBase)
