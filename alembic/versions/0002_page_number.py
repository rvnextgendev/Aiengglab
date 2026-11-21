"""Preserve source PDF page number for each chunk."""
from alembic import op
import sqlalchemy as sa

revision = "0002_page_number"
down_revision = "0001_initial_rag"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("rag_chunks", sa.Column("page_number", sa.Integer(), nullable=True))

def downgrade():
    op.drop_column("rag_chunks", "page_number")
