"""init: create pgvector extension and all tables

Revision ID: 001_init
Revises:
Create Date: 2026-07-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = '001_init'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    # ── chat_messages ──────────────────────────────────
    op.create_table(
        'chat_messages',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.String(100), nullable=False),
        sa.Column('session_id', sa.String(100), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('answer', sa.Text(), nullable=False),
        sa.Column('embedding', Vector(2048), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_chat_messages_session', 'chat_messages', ['session_id'])
    op.create_index('idx_chat_messages_user', 'chat_messages', ['user_id'])
    op.create_index(
        'idx_chat_messages_embedding', 'chat_messages', ['embedding'],
        postgresql_using='hnsw',
        postgresql_with={},
        postgresql_ops={'embedding': 'vector_cosine_ops'},
    )

    # ── knowledge_documents ────────────────────────────
    op.create_table(
        'knowledge_documents',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('source_type', sa.String(50), server_default='text', nullable=False),
        sa.Column('source_path', sa.String(1000), nullable=True),
        sa.Column('chunk_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )

    # ── knowledge_chunks ───────────────────────────────
    op.create_table(
        'knowledge_chunks',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('document_id', sa.BigInteger(), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('embedding', Vector(2048), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ['document_id'], ['knowledge_documents.id'], ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_chunks_document', 'knowledge_chunks', ['document_id'])
    op.create_index(
        'idx_chunks_embedding', 'knowledge_chunks', ['embedding'],
        postgresql_using='hnsw',
        postgresql_with={},
        postgresql_ops={'embedding': 'vector_cosine_ops'},
    )


def downgrade() -> None:
    op.drop_index('idx_chunks_embedding', table_name='knowledge_chunks')
    op.drop_index('idx_chunks_document', table_name='knowledge_chunks')
    op.drop_table('knowledge_chunks')

    op.drop_table('knowledge_documents')

    op.drop_index('idx_chat_messages_embedding', table_name='chat_messages')
    op.drop_index('idx_chat_messages_user', table_name='chat_messages')
    op.drop_index('idx_chat_messages_session', table_name='chat_messages')
    op.drop_table('chat_messages')

    op.execute('DROP EXTENSION IF EXISTS vector')
