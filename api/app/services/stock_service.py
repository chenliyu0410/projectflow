"""Net quantities from the stock ledger. A reversal counts as the kind of the entry it cancels."""
from sqlalchemy import case, func, select
from sqlalchemy.orm import aliased

from app.models import InventoryMovement, OperationsRecord

ORIGINAL = aliased(InventoryMovement, name='original')
KIND = func.coalesce(ORIGINAL.kind, InventoryMovement.kind)
REVERSED = (ORIGINAL.organization_id == InventoryMovement.organization_id) & (ORIGINAL.id == InventoryMovement.reversal_of)


def net(db, organization_id, kinds, *filters):
    """Sum of deltas posted as the given kinds, minus their reversals."""
    return db.scalar(select(func.coalesce(func.sum(InventoryMovement.delta_milli), 0)).select_from(InventoryMovement)
        .outerjoin(ORIGINAL, REVERSED).where(InventoryMovement.organization_id == organization_id, KIND.in_(kinds), *filters))


def free_received(db, organization_id, order_id, resource_id):
    """Net receipts of an order outside its lines: orders without lines, or receipts before lines existed."""
    return net(db, organization_id, ['receipt', 'return'], InventoryMovement.order_id == order_id,
        InventoryMovement.resource_id == resource_id, InventoryMovement.line_id.is_(None))


def net_issued(db, organization_id, work_id, resource_id):
    return -net(db, organization_id, ['issue', 'issue_return'], InventoryMovement.work_id == work_id,
        InventoryMovement.resource_id == resource_id)


def returned_by_line(db, organization_id, order_id):
    return dict(db.execute(select(InventoryMovement.line_id, func.sum(-InventoryMovement.delta_milli)).select_from(InventoryMovement)
        .outerjoin(ORIGINAL, REVERSED).where(InventoryMovement.organization_id == organization_id, InventoryMovement.order_id == order_id,
            InventoryMovement.line_id.is_not(None), KIND == 'return').group_by(InventoryMovement.line_id)).all())


def issued_by_resource(db, organization_id, work_id):
    """Per material of one work order: net issued (total) and net returned, both after reversals."""
    return db.execute(select(InventoryMovement.resource_id, InventoryMovement.unit, OperationsRecord.code, OperationsRecord.title,
            func.sum(-InventoryMovement.delta_milli).label('total'),
            func.sum(case((KIND == 'issue_return', InventoryMovement.delta_milli), else_=0)).label('returned'))
        .select_from(InventoryMovement).outerjoin(ORIGINAL, REVERSED)
        .join(OperationsRecord, (OperationsRecord.organization_id == InventoryMovement.organization_id) & (OperationsRecord.id == InventoryMovement.resource_id))
        .where(InventoryMovement.organization_id == organization_id, InventoryMovement.work_id == work_id, KIND.in_(['issue', 'issue_return']))
        .group_by(InventoryMovement.resource_id, InventoryMovement.unit, OperationsRecord.code, OperationsRecord.title)
        .order_by(OperationsRecord.code)).all()
