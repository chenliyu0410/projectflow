import os
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session


class Base(DeclarativeBase):
    pass


def database_url() -> str:
    value = os.environ.get("DATABASE_URL")
    if not value:
        raise RuntimeError("DATABASE_URL is required")
    return value


def sqlalchemy_url(value: str) -> str:
    if value.startswith("postgresql://"):
        return "postgresql+psycopg://" + value.removeprefix("postgresql://")
    return value


def get_engine():
    return create_engine(sqlalchemy_url(database_url()), pool_pre_ping=True, future=True)


def get_session() -> Iterator[Session]:
    with Session(get_engine()) as session:
        yield session
