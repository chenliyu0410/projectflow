from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_engine
from app.models import Department, Node, Organization, Project, User
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


def ensure_project(session: Session, organization: Organization, title: str, owner: User) -> Project:
    project = session.execute(
        select(Project).where(Project.organization_id == organization.id, Project.title == title)
    ).scalar_one_or_none()
    if project is None:
        project = Project(organization_id=organization.id, title=title, owner_user_id=owner.id)
        session.add(project)
        session.flush()
    return project


def ensure_node(
    session: Session,
    organization: Organization,
    project: Project,
    title: str,
    kind: str,
    sort_order: int,
    owner: User | None = None,
    department: Department | None = None,
    parent: Node | None = None,
) -> Node:
    node = session.execute(
        select(Node).where(Node.organization_id == organization.id, Node.project_id == project.id, Node.title == title)
    ).scalar_one_or_none()
    if node is None:
        node = Node(
            organization_id=organization.id,
            project_id=project.id,
            parent_id=parent.id if parent else None,
            kind=kind,
            title=title,
            owner_user_id=owner.id if owner else None,
            department_id=department.id if department else None,
            sort_order=sort_order,
        )
        session.add(node)
    return node


def seed_demo_data(session: Session) -> None:
    food = ensure_org(session, "food", "毛研食品")
    electronics = ensure_org(session, "electronics", "峰曜科技")
    session.flush()

    yu = ensure_user(session, food, "yu", "游專案", "admin", "demo-yu")
    chen = ensure_user(session, food, "chen", "陳主管", "reviewer", "demo-chen")
    ming = ensure_user(session, food, "ming", "明成員", "member", "demo-ming")
    ensure_user(session, food, "lin", "林唯讀", "readonly", "demo-lin")
    elaine = ensure_user(session, electronics, "elaine", "Elaine", "admin", "demo-elaine")
    kai = ensure_user(session, electronics, "kai", "Kai", "member", "demo-kai")
    session.flush()

    food_rd = ensure_department(session, food, "研發", yu)
    food_qa = ensure_department(session, food, "品保", chen)
    ensure_department(session, food, "採購")
    electronics_rd = ensure_department(session, electronics, "研發", elaine)
    ensure_department(session, electronics, "製造")
    session.flush()

    food_project = ensure_project(session, food, "成貓主食罐正式版", yu)
    food_phase = ensure_node(session, food, food_project, "市場與配方", "phase", 10, yu, food_rd)
    ensure_node(session, food, food_project, "殺菌條件驗證", "task", 5, ming, food_qa, food_phase)
    electronics_project = ensure_project(session, electronics, "連接器新產品正式版", elaine)
    ensure_node(session, electronics, electronics_project, "端子耐久測試", "task", 10, kai, electronics_rd)


if __name__ == "__main__":
    from sqlalchemy.orm import Session as DbSession

    with DbSession(get_engine()) as db:
        seed_demo_data(db)
        db.commit()
