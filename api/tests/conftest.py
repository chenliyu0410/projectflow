import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_session
from app.main import create_app
from app.seed import seed_demo_data


@pytest.fixture()
def engine(tmp_path, monkeypatch):
    db_path = tmp_path / f"projectflow-{uuid.uuid4().hex}.db"
    url = f"sqlite+pysqlite:///{db_path}"
    monkeypatch.setenv("DATABASE_URL", url)
    engine = create_engine(url, future=True)
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture()
def client(engine):
    SessionLocal = sessionmaker(bind=engine, future=True)

    def override_session():
        with SessionLocal() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_session] = override_session
    with SessionLocal() as session:
        seed_demo_data(session)
        session.commit()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
