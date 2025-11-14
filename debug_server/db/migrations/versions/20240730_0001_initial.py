"""Initial metadata schema."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

worktree_status = sa.Enum("idle", "reserved", "busy", name="worktree_status")
session_status = sa.Enum(
    "pending", "running", "completed", "failed", "cancelled", name="session_status"
)
command_status = sa.Enum(
    "pending", "running", "succeeded", "failed", "cancelled", name="command_status"
)
artifact_kind = sa.Enum("log", "coverage", "junit", "core-dump", "custom", name="artifact_kind")

# revision identifiers, used by Alembic.
revision = "20240730_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "repositories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False, unique=True),
        sa.Column("remote_url", sa.String(length=1024), nullable=False),
        sa.Column("default_branch", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=1024)),
        sa.Column("settings", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "worktrees",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("repository_id", sa.Integer(), sa.ForeignKey("repositories.id"), nullable=False),
        sa.Column("path", sa.String(length=1024), nullable=False, unique=True),
        sa.Column("commit_sha", sa.String(length=40)),
        sa.Column("environment_hash", sa.String(length=64)),
        sa.Column("status", worktree_status, nullable=False),
        sa.Column("lease_owner", sa.String(length=255)),
        sa.Column("lease_token", sa.String(length=64), unique=True),
        sa.Column("leased_at", sa.DateTime()),
        sa.Column("lease_expires_at", sa.DateTime()),
        sa.Column("last_heartbeat_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )

    op.create_table(
        "auth_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False, unique=True),
        sa.Column("token_hash", sa.String(length=128), nullable=False, unique=True),
        sa.Column("scopes", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("last_used_at", sa.DateTime()),
        sa.Column("expires_at", sa.DateTime()),
        sa.Column("revoked_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "sessions",
        sa.Column("id", sa.String(length=255), primary_key=True),
        sa.Column("repository_id", sa.Integer(), sa.ForeignKey("repositories.id"), nullable=False),
        sa.Column("worktree_id", sa.Integer(), sa.ForeignKey("worktrees.id")),
        sa.Column("token_id", sa.Integer(), sa.ForeignKey("auth_tokens.id")),
        sa.Column("requested_by", sa.String(length=255)),
        sa.Column("commit_sha", sa.String(length=40), nullable=False),
        sa.Column("patch_hash", sa.String(length=64)),
        sa.Column("status", session_status, nullable=False),
        sa.Column("expires_at", sa.DateTime()),
        sa.Column("started_at", sa.DateTime()),
        sa.Column("completed_at", sa.DateTime()),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "commands",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "session_id",
            sa.String(length=255),
            sa.ForeignKey("sessions.id"),
            nullable=False,
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("command", sa.String(length=1024), nullable=False),
        sa.Column("cwd", sa.String(length=512)),
        sa.Column("env", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("status", command_status, nullable=False),
        sa.Column("exit_code", sa.Integer()),
        sa.Column("started_at", sa.DateTime()),
        sa.Column("completed_at", sa.DateTime()),
        sa.Column("log_path", sa.String(length=1024)),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "artifacts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "session_id",
            sa.String(length=255),
            sa.ForeignKey("sessions.id"),
            nullable=False,
        ),
        sa.Column("command_id", sa.Integer(), sa.ForeignKey("commands.id")),
        sa.Column("kind", artifact_kind, nullable=False),
        sa.Column("path", sa.String(length=1024), nullable=False),
        sa.Column("content_type", sa.String(length=255)),
        sa.Column("description", sa.String(length=1024)),
        sa.Column("size_bytes", sa.Integer()),
        sa.Column("checksum_sha256", sa.String(length=64)),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "debugger_state",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "session_id",
            sa.String(length=255),
            sa.ForeignKey("sessions.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("last_event", sa.String(length=255)),
        sa.Column("breakpoints", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("debugger_state")
    op.drop_table("artifacts")
    op.drop_table("commands")
    op.drop_table("sessions")
    op.drop_table("auth_tokens")
    op.drop_table("worktrees")
    op.drop_table("repositories")
    worktree_status.drop(op.get_bind(), checkfirst=False)
    session_status.drop(op.get_bind(), checkfirst=False)
    command_status.drop(op.get_bind(), checkfirst=False)
    artifact_kind.drop(op.get_bind(), checkfirst=False)
