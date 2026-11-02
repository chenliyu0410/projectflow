"""Single-process polling that keeps the formal document index current; one API process only."""
from contextlib import contextmanager
from datetime import datetime, timezone
import logging
import os
import threading

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai import formal_index
from app.auth import CurrentUser
from app.models import Organization, User

INTERVAL_SECONDS = 10
_states = {}
_guard = threading.Lock()
logger = logging.getLogger(__name__)


def enabled():
    return formal_index.enabled() and os.environ.get("PF_AI_INDEX_AUTO_UPDATE") == "true"


def status(path):
    with _guard:
        return dict(enabled=enabled(), interval_seconds=INTERVAL_SECONDS,
                    **_states.get(str(path), dict(last_checked_at=None, last_error=None)))


def tick(engine):
    if not enabled():
        return
    with Session(engine) as db:
        administrators = db.execute(select(User, Organization).join(Organization, User.organization_id == Organization.id)
                                    .where(User.role == "admin").order_by(User.id)).all()
        seen = set()
        for user, organization in administrators:
            if organization.id in seen:
                continue
            seen.add(organization.id)
            current = CurrentUser(user, organization, "")
            path = formal_index.index_path(db, current)
            error = None
            try:
                formal_index.refresh(db, current, only_if_changed=True)
            except HTTPException as exc:
                error = ("文件索引更新中，下一輪再檢查" if exc.status_code == 409 else
                         "來源版本超過隔離版上限，請管理者處理" if exc.status_code == 422 else
                         "自動更新失敗，原索引保留；下一輪重試")
            except Exception:
                error = "自動更新失敗，原索引保留；下一輪重試"
            with _guard:
                _states[str(path)] = dict(last_checked_at=datetime.now(timezone.utc).isoformat(), last_error=error)
            db.rollback()


@contextmanager
def running(engine=None):
    owned_engine = False
    if not enabled():
        yield None
        return
    if engine is None:
        from app.database import get_engine
        engine = get_engine()
        owned_engine = True
    stop = threading.Event()

    def loop():
        while not stop.is_set():
            try:
                tick(engine)
            except Exception:
                # No DB URLs, file paths or source content in worker logs.
                logger.warning("Formal index check failed; retrying on next interval")
            stop.wait(INTERVAL_SECONDS)

    worker = threading.Thread(target=loop, name="formal-file-index", daemon=True)
    worker.start()
    try:
        yield worker
    finally:
        stop.set()
        worker.join()  # Finish atomic builds before releasing the file runtime lock.
        if owned_engine:
            engine.dispose()
