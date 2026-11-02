from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_engine
from app.models import Department, Node, Organization, Project, User, Workflow, WorkflowNode
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
            email=f'{username}@demo.local',
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


def ensure_workflow(session: Session, organization: Organization, name: str) -> Workflow:
    workflow = session.execute(
        select(Workflow).where(Workflow.organization_id == organization.id, Workflow.name == name)
    ).scalar_one_or_none()
    if workflow is None:
        workflow = Workflow(organization_id=organization.id, name=name, content={})
        session.add(workflow)
        session.flush()
    return workflow


def ensure_workflow_node(
    session: Session,
    organization: Organization,
    workflow: Workflow,
    title: str,
    kind: str,
    sort_order: int,
    parent_template: WorkflowNode | None = None,
    gate_after: bool = False,
) -> WorkflowNode:
    node = session.execute(
        select(WorkflowNode).where(
            WorkflowNode.organization_id == organization.id,
            WorkflowNode.workflow_id == workflow.id,
            WorkflowNode.title == title,
        )
    ).scalar_one_or_none()
    if node is None:
        node = WorkflowNode(
            organization_id=organization.id,
            workflow_id=workflow.id,
            parent_template_id=parent_template.id if parent_template else None,
            title=title,
            kind=kind,
            sort_order=sort_order,
            gate_after=gate_after,
        )
        session.add(node)
    return node


def seed_demo_data(session: Session) -> None:
    food = ensure_org(session, "food", "毛研食品")
    electronics = ensure_org(session, "electronics", "峰曜科技")
    session.flush()

    yu = ensure_user(session, food, "yu", "游專案", "admin", "demo-yu")
    ensure_user(session, food, "owner", "專案負責", "project_owner", "demo-owner")
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

    food_workflow = ensure_workflow(session, food, "食品新品開發")
    food_phase_1 = ensure_workflow_node(session, food, food_workflow, "市場與配方", "phase", 10, gate_after=True)
    food_phase_2 = ensure_workflow_node(session, food, food_workflow, "小量試作", "phase", 20)
    ensure_workflow_node(session, food, food_workflow, "配方設計", "task", 30, food_phase_1)
    ensure_workflow_node(session, food, food_workflow, "試作工單", "task", 40, food_phase_2)

    electronics_workflow = ensure_workflow(session, electronics, "電子新品開發")
    electronics_phase_1 = ensure_workflow_node(session, electronics, electronics_workflow, "規格確認", "phase", 10, gate_after=True)
    electronics_phase_2 = ensure_workflow_node(session, electronics, electronics_workflow, "試產驗證", "phase", 20)
    ensure_workflow_node(session, electronics, electronics_workflow, "端子規格審查", "task", 30, electronics_phase_1)
    ensure_workflow_node(session, electronics, electronics_workflow, "小量試產", "task", 40, electronics_phase_2)


if __name__ == "__main__":
    from sqlalchemy.orm import Session as DbSession

    with DbSession(get_engine()) as db:
        seed_demo_data(db)
        db.commit()
