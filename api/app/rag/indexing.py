"""Small durable worker: every attempt has a fresh session and current editor ACL."""
from contextlib import contextmanager
from datetime import timedelta
import os
import threading
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.auth import CurrentUser
from app.models import Organization, User
from app.rag.models import RagIndex, now


def enqueue(row, user_id):
    row.requested_by_user_id = user_id
    row.requested_at = now()
    row.attempts = 0
    row.next_attempt_at = now()


def finish_request(row, transient=False):
    row.next_attempt_at = now() + timedelta(seconds=30 if row.attempts == 1 else 120) if transient and row.attempts < 3 else None
    if row.next_attempt_at is None:
        row.requested_at = None


def run_once(engine):
    from app.rag import service
    with Session(engine) as db:
        db.execute(update(RagIndex).where(RagIndex.state == 'processing', RagIndex.attempts >= 3, RagIndex.updated_at < now()-timedelta(minutes=5)).values(state='failed',claim=None,requested_at=None,next_attempt_at=None,error_code='retry_exhausted'))
        db.commit()
        row = db.scalar(select(RagIndex).where(
            RagIndex.enabled.is_(True), RagIndex.requested_at.is_not(None), RagIndex.attempts < 3,
            (RagIndex.next_attempt_at.is_(None)) | (RagIndex.next_attempt_at <= now()),
            (RagIndex.state != 'processing') | (RagIndex.updated_at < now() - timedelta(minutes=5))
        ).order_by(RagIndex.requested_at).limit(1))
        if row is None:
            return False
        user = db.get(User, row.requested_by_user_id) if row.requested_by_user_id else None
        org = db.get(Organization, row.organization_id)
        if user is None or user.organization_id != row.organization_id or org is None:
            row.state, row.error_code, row.requested_at = 'failed', 'access_changed', None
            db.commit()
            return True
        document_id, version, requested_at = row.document_id, row.version, row.requested_at
        current = CurrentUser(user=user, organization=org, token='')
        try:
            service.index_document(db, current, row.document_id, automatic=True)
        except HTTPException as error:
            db.rollback()
            if error.status_code in (401,403,404):
                db.execute(update(RagIndex).where(RagIndex.document_id == document_id, RagIndex.version == version, RagIndex.requested_at == requested_at, RagIndex.claim.is_(None)).values(state='failed', error_code='access_changed', requested_at=None))
                db.commit()
        return True


@contextmanager
def worker_lifecycle():
    stop = threading.Event()
    thread = None
    if os.environ.get('PF_RAG_AUTO_INDEX') == 'true':
        from app.database import get_engine
        engine = get_engine()
        def work():
            while not stop.is_set():
                try:
                    run_once(engine)
                except Exception:
                    # No document or provider exception text is logged.
                    pass
                stop.wait(5)
        thread = threading.Thread(target=work, name='rag-index-worker', daemon=True)
        thread.start()
    try:
        yield
    finally:
        stop.set()
        if thread:
            thread.join(timeout=1)
