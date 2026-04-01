"""add store_transactions append-only ledger

Revision ID: d2a8f3c91b7e
Revises: b934e3018163
Create Date: 2026-04-01 15:05:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd2a8f3c91b7e'
down_revision = 'b934e3018163'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'store_transactions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('item_id', sa.UUID(), nullable=False),
        sa.Column('recorded_by', sa.UUID(), nullable=True),
        sa.Column('action', sa.String(length=20), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['item_id'], ['inventory_items.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['recorded_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )

    with op.batch_alter_table('store_transactions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_store_transactions_item_id'), ['item_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_store_transactions_recorded_by'), ['recorded_by'], unique=False)
        batch_op.create_index(batch_op.f('ix_store_transactions_action'), ['action'], unique=False)
        batch_op.create_index(batch_op.f('ix_store_transactions_created_at'), ['created_at'], unique=False)


def downgrade():
    with op.batch_alter_table('store_transactions', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_store_transactions_created_at'))
        batch_op.drop_index(batch_op.f('ix_store_transactions_action'))
        batch_op.drop_index(batch_op.f('ix_store_transactions_recorded_by'))
        batch_op.drop_index(batch_op.f('ix_store_transactions_item_id'))

    op.drop_table('store_transactions')
