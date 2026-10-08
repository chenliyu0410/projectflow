"""Recover one pending attachment only after this stack's API has stopped."""
import argparse
import os
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.database import sqlalchemy_url
from app.models import Attachment
from app.services.attachment_store import runtime_lock, storage_root, reconcile_upload


def recover(bind, organization_id, attachment_id, root, *, api_stopped=False):
    if not api_stopped:
        raise ValueError('Stop the API and explicitly confirm --api-stopped first')
    with runtime_lock(root, exclusive=True):
        with Session(bind) as db:
            row = db.scalar(select(Attachment).where(Attachment.organization_id == organization_id, Attachment.id == attachment_id))
            if row is None or row.state not in {'pending', 'failed'} or row.report_id or row.note_id or row.deleted_at:
                raise ValueError('Only an unbound pending attachment can be recovered')
        # API lifetime lock prevents a live uploader from racing offline cleanup.
        reconcile_upload(bind, organization_id, attachment_id, root)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--organization-id', required=True)
    parser.add_argument('--attachment-id', required=True)
    parser.add_argument('--api-stopped', action='store_true', required=True)
    args = parser.parse_args()
    engine = None
    try:
        engine = create_engine(sqlalchemy_url(os.environ['DATABASE_URL']))
        recover(engine, args.organization_id, args.attachment_id, storage_root(), api_stopped=args.api_stopped)
    except Exception:
        print('Recovery refused or incomplete; keep files and quota, stop this API and verify the pending attachment.')
        return 1
    finally:
        if engine is not None:
            engine.dispose()
    print('Pending attachment recovery complete; files and quota are consistent.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
