"""Knowledge sources, document identity/hash and chunk bookkeeping (Phase 2).

Upgrades the Phase 1 schema in place so existing rows are preserved: legacy per-document
source columns become knowledge_sources rows, and legacy display-name categories are mapped to
the ESOCategory enum values.
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

LEGACY_CATEGORIES = {
    "Items": "ITEM",
    "Gear Sets": "GEAR_SET",
    "Skills": "SKILL",
    "Builds": "BUILD",
    "Champion Points": "CHAMPION_POINTS",
    "Crafting": "CRAFTING",
    "Recipes": "RECIPE",
    "Provisioning": "PROVISIONING",
    "Fishing": "FISHING",
    "Dungeons": "DUNGEON",
    "Trials": "TRIAL",
    "Bosses": "BOSS",
    "Zones": "ZONE",
    "Locations": "LOCATION",
    "Quests": "QUEST",
    "Achievements": "ACHIEVEMENT",
    "PvP": "PVP",
    "Cyrodiil": "CYRODIIL",
    "Trading": "TRADING",
    "Addons": "ADDON",
    "Game Help": "GAME_HELP",
}


def _timestamps():
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def upgrade():
    op.create_table(
        "knowledge_sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(500), nullable=False, unique=True),
        sa.Column("base_url", sa.Text()),
        sa.Column("source_type", sa.String(50), nullable=False, server_default="manual"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        *_timestamps(),
    )
    op.execute(
        "INSERT INTO knowledge_sources (name, base_url, source_type) "
        "SELECT source_name, min(source_url), 'manual' FROM knowledge_documents "
        "GROUP BY source_name"
    )

    op.add_column("knowledge_documents", sa.Column("source_id", sa.Integer()))
    op.add_column("knowledge_documents", sa.Column("external_id", sa.String(500)))
    op.add_column("knowledge_documents", sa.Column("canonical_url", sa.Text()))
    op.add_column("knowledge_documents", sa.Column("content_hash", sa.String(64)))
    op.add_column(
        "knowledge_documents",
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
    )
    op.add_column("knowledge_documents", sa.Column("indexed_at", sa.DateTime(timezone=True)))
    op.execute(
        "UPDATE knowledge_documents d SET source_id = s.id, external_id = d.slug, "
        "canonical_url = d.source_url, "
        "content_hash = encode(sha256(convert_to(d.content, 'UTF8')), 'hex') "
        "FROM knowledge_sources s WHERE s.name = d.source_name"
    )
    for legacy, current in LEGACY_CATEGORIES.items():
        op.execute(
            sa.text(
                "UPDATE knowledge_documents SET category = :new WHERE category = :old"
            ).bindparams(new=current, old=legacy)
        )
    op.alter_column("knowledge_documents", "source_id", nullable=False)
    op.alter_column("knowledge_documents", "external_id", nullable=False)
    op.alter_column("knowledge_documents", "content_hash", nullable=False)
    op.create_foreign_key(
        "fk_knowledge_documents_source_id",
        "knowledge_documents",
        "knowledge_sources",
        ["source_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint("knowledge_documents_slug_key", "knowledge_documents", type_="unique")
    op.create_index("ix_knowledge_documents_slug", "knowledge_documents", ["slug"])
    op.create_index("ix_knowledge_documents_source_id", "knowledge_documents", ["source_id"])
    op.create_index("ix_knowledge_documents_content_hash", "knowledge_documents", ["content_hash"])
    op.create_unique_constraint(
        "uq_knowledge_documents_source_external",
        "knowledge_documents",
        ["source_id", "external_id"],
    )
    op.drop_column("knowledge_documents", "source_name")
    op.drop_column("knowledge_documents", "source_url")

    op.alter_column("knowledge_chunks", "chunk_number", new_column_name="chunk_index")
    op.add_column(
        "knowledge_chunks",
        sa.Column("token_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "knowledge_chunks",
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.add_column(
        "knowledge_chunks",
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.alter_column("knowledge_chunks", "metadata", server_default="{}")
    op.create_index("ix_knowledge_chunks_document_id", "knowledge_chunks", ["document_id"])
    op.create_unique_constraint(
        "uq_knowledge_chunks_document_index", "knowledge_chunks", ["document_id", "chunk_index"]
    )
    # No ANN (HNSW/IVFFlat) index yet: exact scans are fast and exact for small corpora. Add one
    # in a later migration (e.g. USING hnsw (embedding vector_cosine_ops)) once the corpus grows.


def downgrade():
    op.drop_constraint("uq_knowledge_chunks_document_index", "knowledge_chunks", type_="unique")
    op.drop_index("ix_knowledge_chunks_document_id", table_name="knowledge_chunks")
    op.drop_column("knowledge_chunks", "updated_at")
    op.drop_column("knowledge_chunks", "created_at")
    op.drop_column("knowledge_chunks", "token_count")
    op.alter_column("knowledge_chunks", "chunk_index", new_column_name="chunk_number")

    op.add_column("knowledge_documents", sa.Column("source_name", sa.String(500)))
    op.add_column("knowledge_documents", sa.Column("source_url", sa.Text()))
    op.execute(
        "UPDATE knowledge_documents d SET source_name = s.name, "
        "source_url = coalesce(d.canonical_url, s.base_url, '') "
        "FROM knowledge_sources s WHERE s.id = d.source_id"
    )
    for legacy, current in LEGACY_CATEGORIES.items():
        op.execute(
            sa.text(
                "UPDATE knowledge_documents SET category = :old WHERE category = :new"
            ).bindparams(new=current, old=legacy)
        )
    op.alter_column("knowledge_documents", "source_name", nullable=False)
    op.alter_column("knowledge_documents", "source_url", nullable=False)
    op.drop_constraint(
        "uq_knowledge_documents_source_external", "knowledge_documents", type_="unique"
    )
    op.drop_index("ix_knowledge_documents_content_hash", table_name="knowledge_documents")
    op.drop_index("ix_knowledge_documents_source_id", table_name="knowledge_documents")
    op.drop_index("ix_knowledge_documents_slug", table_name="knowledge_documents")
    op.drop_constraint(
        "fk_knowledge_documents_source_id", "knowledge_documents", type_="foreignkey"
    )
    for column in (
        "indexed_at",
        "metadata",
        "content_hash",
        "canonical_url",
        "external_id",
        "source_id",
    ):
        op.drop_column("knowledge_documents", column)
    op.create_unique_constraint("knowledge_documents_slug_key", "knowledge_documents", ["slug"])
    op.drop_table("knowledge_sources")
