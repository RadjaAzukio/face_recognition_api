"""Add nim column to users table

Revision ID: cfb89fb709b2
Revises: 
Create Date: 2025-05-08 14:45:37.113030

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cfb89fb709b2'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column('users', sa.Column('nim', sa.String(20), nullable=True))

def downgrade():
    op.drop_column('users', 'nim')
