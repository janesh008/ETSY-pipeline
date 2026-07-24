"""Generic single-database configuration."""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0001_initial'
down_revision: str | None = None
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    # ── users ─────────────────────────────────────────────────────────────
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=False, server_default=''),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # ── etsy_shops ────────────────────────────────────────────────────────
    op.create_table(
        'etsy_shops',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('shop_id', sa.String(64), nullable=False),
        sa.Column('shop_name', sa.String(255), nullable=False, server_default=''),
        sa.Column('encrypted_access_token', sa.Text, nullable=False),
        sa.Column('encrypted_refresh_token', sa.Text, nullable=False),
        sa.Column('token_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_etsy_shops_user_id', 'etsy_shops', ['user_id'])

    # ── gcp_configs ───────────────────────────────────────────────────────
    op.create_table(
        'gcp_configs',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(255), nullable=False),
        sa.Column('zone', sa.String(64), nullable=False),
        sa.Column('instance_name', sa.String(255), nullable=False),
        sa.Column('encrypted_service_account_json', sa.Text, nullable=False),
        sa.Column('comfy_ui_port', sa.Integer, nullable=False, server_default='8188'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_gcp_configs_user_id', 'gcp_configs', ['user_id'])

    # ── api_keys ──────────────────────────────────────────────────────────
    op.create_table(
        'api_keys',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('service', sa.String(64), nullable=False),
        sa.Column('encrypted_api_key', sa.Text, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_api_keys_user_id', 'api_keys', ['user_id'])


def downgrade() -> None:
    op.drop_table('api_keys')
    op.drop_table('gcp_configs')
    op.drop_table('etsy_shops')
    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')
