from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_engine
from app.models import Department, Organization, User
from app.security import hash_password


def ensure_org(session: Session, key: str, name: str) -> Organization:
    org = session.execute(select(Organization).where(Organization.key == key)).scalar_one_or_none()
    if org is None:
        org = Organization(key=key, name=name)
        session.add(org)
        session.flush()
    return org


def ensure_user(session: Session, organization: Organization, username: str, display_name: str, role: str, password: str) -> User:
    user = session.execute(
        select(User).where(User.organization_id == organization.id, User.username == username)
    ).scalar_one_or_none()
    if user is None:
        user = User(
            organization_id=organization.id,
            username=username,
            display_name=display_name,
            role=role,
            password_hash=hash_password(password),
        )
        session.add(user)
    return user


def ensure_department(session: Session, organization: Organization, name: str, head: User | None = None) -> Department:
    dept = session.execute(
        select(Department).where(Department.organization_id == organization.id, Department.name == name)
    ).scalar_one_or_none()
    if dept is None:
        dept = Department(organization_id=organization.id, name=name, head_user_id=head.id if head else None)
        session.add(dept)
    elif head is not None:
        dept.head_user_id = head.id
    return dept


def seed_demo_data(session: Session) -> None:
    food = ensure_org(session, "food", "毛研食品")
    electronics = ensure_org(session, "electronics", "峰曜科技")
    session.flush()

    yu = ensure_user(session, food, "yu", "游專案", "admin", "demo-yu")
    chen = ensure_user(session, food, "chen", "陳主管", "reviewer", "demo-chen")
    ensure_user(session, food, "ming", "明成員", "member", "demo-ming")
    ensure_user(session, food, "lin", "林唯讀", "readonly", "demo-lin")
    elaine = ensure_user(session, electronics, "elaine", "Elaine", "admin", "demo-elaine")
    ensure_user(session, electronics, "kai", "Kai", "member", "demo-kai")
    session.flush()

    ensure_department(session, food, "研發", yu)
    ensure_department(session, food, "品保", chen)
    ensure_department(session, food, "採購")
    ensure_department(session, electronics, "研發", elaine)
    ensure_department(session, electronics, "製造")


if __name__ == "__main__":
    from sqlalchemy.orm import Session as DbSession

    with DbSession(get_engine()) as db:
        seed_demo_data(db)
        db.commit()
