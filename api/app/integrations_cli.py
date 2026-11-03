"""Demo helper for N8N: give accounts without an email `<username>@demo.local` (existing databases predate the seed change)."""
import argparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_engine
from app.models import Organization, User


def demo_emails(db, organization_key=None):
    query = select(User).join(Organization, Organization.id == User.organization_id).where(User.email.is_(None))
    if organization_key:
        query = query.where(Organization.key == organization_key)
    users = list(db.scalars(query))
    for user in users:
        user.email = f'{user.username}@demo.local'
    return len(users)


def main():
    parser = argparse.ArgumentParser(description='N8N demo helpers')
    sub = parser.add_subparsers(dest='command', required=True)
    emails = sub.add_parser('demo-emails', help='fill <username>@demo.local for accounts without an email')
    emails.add_argument('--org', help='organization key; all organizations when omitted')
    args = parser.parse_args()
    with Session(get_engine()) as db:
        count = demo_emails(db, args.org)
        db.commit()
    print(f'filled {count} email(s)')


if __name__ == '__main__':
    main()
