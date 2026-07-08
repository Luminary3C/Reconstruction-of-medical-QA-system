"""enforce NOT NULL on knowledge tables

Revision ID: 002_notnull
Revises: 001_init
Create Date: 2026-07-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '002_notnull'
down_revision: Union[str, Sequence[str], None] = '001_init'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('knowledge_chunks', 'document_id',
               existing_type=sa.BigInteger(),
               nullable=False)
    op.alter_column('knowledge_documents', 'source_type',
               existing_type=sa.String(50),
               nullable=False,
               existing_server_default=sa.text("'text'::character varying"))
    op.alter_column('knowledge_documents', 'chunk_count',
               existing_type=sa.Integer(),
               nullable=False,
               existing_server_default=sa.text('0'))


def downgrade() -> None:
    op.alter_column('knowledge_documents', 'chunk_count',
               existing_type=sa.Integer(),
               nullable=True,
               existing_server_default=sa.text('0'))
    op.alter_column('knowledge_documents', 'source_type',
               existing_type=sa.String(50),
               nullable=True,
               existing_server_default=sa.text("'text'::character varying"))
    op.alter_column('knowledge_chunks', 'document_id',
               existing_type=sa.BigInteger(),
               nullable=True)
