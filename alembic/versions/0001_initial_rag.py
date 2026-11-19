"""Initial pgvector document schema for fresh databases."""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import VECTOR

revision = "0001_initial_rag"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table("rag_documents",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("tenant_id", sa.String(80), nullable=False),
        sa.Column("filename", sa.String(100), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False))
    op.create_index("ix_rag_documents_tenant_id", "rag_documents", ["tenant_id"])
    op.create_index("ix_rag_document_unique", "rag_documents", ["tenant_id", "filename"], unique=True)
    op.create_table("rag_chunks",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("document_id", sa.BigInteger(), sa.ForeignKey("rag_documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", VECTOR(384), nullable=False))
    op.create_index("ix_rag_chunks_embedding_hnsw", "rag_chunks", ["embedding"],
                    postgresql_using="hnsw", postgresql_ops={"embedding": "vector_cosine_ops"})

def downgrade():
    op.drop_index("ix_rag_chunks_embedding_hnsw", table_name="rag_chunks")
    op.drop_table("rag_chunks")
    op.drop_index("ix_rag_document_unique", table_name="rag_documents")
    op.drop_index("ix_rag_documents_tenant_id", table_name="rag_documents")
    op.drop_table("rag_documents")
