from pathlib import Path
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
import app.database


def test_rag_upgrade_preserves_existing_rows_and_refuses_loss(tmp_path, monkeypatch):
    url = f'sqlite:///{tmp_path / "rag-migration.db"}'
    monkeypatch.setenv('DATABASE_URL', url)
    config = Config(str(Path(app.database.__file__).resolve().parents[1] / 'alembic.ini'))
    command.upgrade(config, '20261012_0019')
    engine = create_engine(url)
    with engine.begin() as db:
        db.execute(text("INSERT INTO organizations (id,key,name) VALUES ('keep','keep','Preserved')"))
    command.upgrade(config, 'head')
    assert {'rag_indexes', 'rag_chunks', 'rag_queries', 'rag_settings'} <= set(inspect(engine).get_table_names())
    with engine.begin() as db:
        assert db.scalar(text('SELECT name FROM organizations')) == 'Preserved'
        db.execute(text("INSERT INTO rag_settings VALUES ('keep',0,'','','',1)"))
    with pytest.raises(RuntimeError, match='拒絕有損降級'):
        command.downgrade(config, '20261012_0019')
    with engine.connect() as db:
        assert db.scalar(text('SELECT name FROM organizations')) == 'Preserved'
        assert db.scalar(text('SELECT count(*) FROM rag_settings')) == 1
    engine.dispose()
