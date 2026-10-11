"""Explicit, idempotent import of existing fictional operations previews."""
from sqlalchemy import select
from app.auth import CurrentUser
from app.models import Organization, User, OperationsRecord
from app.routes.operations import CATALOG, RecordWrite, save


def import_records(db):
    counts = {'created': 0, 'skipped': 0}
    for org in db.scalars(select(Organization).order_by(Organization.key)).all():
        actor = db.scalar(select(User).where(User.organization_id == org.id, User.role == 'admin').order_by(User.id))
        if actor is None:
            continue
        current = CurrentUser(actor, org, '')
        for group in CATALOG.get(org.key, []):
            for record in group['records']:
                if db.scalar(select(OperationsRecord.id).where(OperationsRecord.organization_id == org.id,
                    OperationsRecord.category == group['key'], OperationsRecord.code == record['code'].upper())):
                    counts['skipped'] += 1
                    continue
                save(db, current, RecordWrite(category=group['key'], **record), source='showcase')
                counts['created'] += 1
    return counts


if __name__ == '__main__':
    import json, os
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app.database import sqlalchemy_url
    engine = create_engine(sqlalchemy_url(os.environ['DATABASE_URL']))
    with Session(engine) as db:
        print(json.dumps(import_records(db)))
