import os
import threading
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


_engines = {}
_engines_lock = threading.Lock()


def get_engine():
    # engine 自帶連線池，每個請求重建等於每次重開連線；以 URL 為鍵，測試改 DATABASE_URL 時才會拿到對應的資料庫。
    url = sqlalchemy_url(database_url())
    with _engines_lock:
        engine = _engines.get(url)
        if engine is None:
            engine = _engines[url] = create_engine(url, pool_pre_ping=True, future=True)
        return engine


def get_session() -> Iterator[Session]:
    with Session(get_engine()) as session:
        yield session
