"""Preserve existing templates and seed immutable version one snapshots."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
import uuid
revision='20261010_0009'
down_revision='20261010_0008'
branch_labels=None
depends_on=None


def upgrade():
    with op.batch_alter_table('workflows') as batch:
        batch.add_column(sa.Column('kind',sa.String(16),nullable=False,server_default='workflow'))
        batch.add_column(sa.Column('version',sa.Integer(),nullable=False,server_default='1'))
        batch.add_column(sa.Column('deleted_at',sa.DateTime(timezone=True)))
    versions=op.create_table('workflow_versions',
        sa.Column('id',sa.String(36),primary_key=True),sa.Column('organization_id',sa.String(36),nullable=False),
        sa.Column('workflow_id',sa.String(36),nullable=False),sa.Column('version',sa.Integer(),nullable=False),
        sa.Column('snapshot',sa.JSON().with_variant(JSONB(),'postgresql'),nullable=False),
        sa.Column('created_by',sa.String(36)),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint('organization_id','workflow_id','version'),
        sa.ForeignKeyConstraint(['organization_id','workflow_id'],['workflows.organization_id','workflows.id']),
        sa.ForeignKeyConstraint(['organization_id','created_by'],['users.organization_id','users.id']),
        sa.CheckConstraint('version >= 1',name='ck_workflow_version_positive'))
    bind=op.get_bind();meta=sa.MetaData()
    workflows=sa.Table('workflows',meta,autoload_with=bind);nodes=sa.Table('workflow_nodes',meta,autoload_with=bind)
    for w in bind.execute(sa.select(workflows)).mappings():
        content=w['content'] or {};relative=content.get('offsets',{}) if content.get('p2c_version')==1 else {}
        snapshot={'name':w['name'],'kind':'workflow','nodes':[], 'dependencies':content.get('dependencies',[]) if content.get('p2c_version')==1 else [],'conditions':[]}
        for n in bind.execute(sa.select(nodes).where(nodes.c.organization_id==w['organization_id'],nodes.c.workflow_id==w['id']).order_by(nodes.c.sort_order,nodes.c.id)).mappings():
            offsets=relative.get(n['id'],{})
            snapshot['nodes'].append(dict(id=n['id'],parent_id=n['parent_template_id'],kind=n['kind'],title=n['title'],sort_order=n['sort_order'],gate_after=n['gate_after'],
                start_offset=offsets.get('start_offset'),due_offset=offsets.get('due_offset')))
        bind.execute(versions.insert().values(id=str(uuid.uuid4()),organization_id=w['organization_id'],workflow_id=w['id'],version=1,snapshot=snapshot,created_at=w['created_at']))


def downgrade():
    bind=op.get_bind()
    if bind.execute(sa.text("SELECT 1 FROM workflows WHERE version > 1 OR kind != 'workflow' OR deleted_at IS NOT NULL LIMIT 1")).first():
        raise RuntimeError('template history exists; refusing lossy downgrade')
    meta=sa.MetaData();workflows=sa.Table('workflows',meta,autoload_with=bind)
    if any((c or {}).get('tpe_version') for c in bind.execute(sa.select(workflows.c.content)).scalars()):
        raise RuntimeError('advanced template content exists; refusing lossy downgrade')
    op.drop_table('workflow_versions')
    with op.batch_alter_table('workflows') as batch:
        for key in ('deleted_at','version','kind'):batch.drop_column(key)
