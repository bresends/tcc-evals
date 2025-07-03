"""Renomear coluna precisao para fundamentacao_tecnica

Revision ID: 81ffe35fb693
Revises: a9f8eca9864b
Create Date: 2025-07-02 11:30:18.279987

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '81ffe35fb693'
down_revision: Union[str, Sequence[str], None] = 'a9f8eca9864b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Renomear coluna preservando dados existentes
    op.alter_column('respostas', 'precisao', new_column_name='fundamentacao_tecnica')


def downgrade() -> None:
    """Downgrade schema."""
    # Reverter renomeação da coluna
    op.alter_column('respostas', 'fundamentacao_tecnica', new_column_name='precisao')
