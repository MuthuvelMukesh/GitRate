"""Initial database schema migration."""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create initial database schema."""
    
    # Create repositories table
    op.create_table(
        'repositories',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('owner', sa.String(255), nullable=False),
        sa.Column('repo', sa.String(255), nullable=False),
        sa.Column('url', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('language', sa.String(50), nullable=True),
        sa.Column('license', sa.String(100), nullable=True),
        sa.Column('stars', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('forks', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('open_issues', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('last_fetched_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('owner', 'repo', name='idx_owner_repo'),
    )
    op.create_index('idx_last_fetched', 'repositories', ['last_fetched_at'])
    
    # Create audits table
    op.create_table(
        'audits',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('audit_id', sa.String(8), nullable=False, unique=True),
        sa.Column('repository_id', sa.String(36), nullable=False),
        sa.Column('overall_score', sa.Float(), nullable=False),
        sa.Column('ip_legal_score', sa.Float(), nullable=False),
        sa.Column('team_score', sa.Float(), nullable=False),
        sa.Column('code_quality_score', sa.Float(), nullable=False),
        sa.Column('security_score', sa.Float(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='COMPLETED'),
        sa.Column('go_no_go', sa.String(20), nullable=False, server_default='CAUTION'),
        sa.Column('technical_debt_cost', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('compliance_risk_cost', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('security_risk_cost', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('team_risk_cost', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('total_risk_usd', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('valuation_discount_percent', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('executive_summary', sa.Text(), nullable=True),
        sa.Column('red_flags', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('critical_findings_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('audit_date', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_repository_id', 'audits', ['repository_id'])
    op.create_index('idx_audit_date', 'audits', ['audit_date'])
    op.create_index('idx_status', 'audits', ['status'])
    
    # Create audit_findings table
    op.create_table(
        'audit_findings',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('audit_id', sa.String(36), nullable=False),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('recommendation', sa.Text(), nullable=False),
        sa.Column('affected_items', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('estimation_hours', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('evidence', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['audit_id'], ['audits.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_audit_id', 'audit_findings', ['audit_id'])
    op.create_index('idx_severity', 'audit_findings', ['severity'])
    op.create_index('idx_category', 'audit_findings', ['category'])
    
    # Create audit_cache table
    op.create_table(
        'audit_cache',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('repository_id', sa.String(36), nullable=False),
        sa.Column('cache_key', sa.String(255), nullable=False, unique=True),
        sa.Column('cache_data', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('ttl_seconds', sa.Integer(), nullable=False, server_default='86400'),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_repository_id', 'audit_cache', ['repository_id'])
    op.create_index('idx_expires_at', 'audit_cache', ['expires_at'])
    
    # Create github_metrics table
    op.create_table(
        'github_metrics',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('repository_id', sa.String(36), nullable=False),
        sa.Column('metric_date', sa.DateTime(), nullable=False),
        sa.Column('stars', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('forks', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('open_issues', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('commits_total', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('contributors_total', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('commit_frequency', sa.String(50), nullable=True),
        sa.Column('test_coverage', sa.Float(), nullable=True),
        sa.Column('documentation_quality', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_repository_id', 'github_metrics', ['repository_id'])
    op.create_index('idx_metric_date', 'github_metrics', ['metric_date'])
    
    # Create vulnerability_cache table
    op.create_table(
        'vulnerability_cache',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('cve_id', sa.String(50), nullable=False, unique=True),
        sa.Column('package_name', sa.String(255), nullable=False),
        sa.Column('package_version', sa.String(100), nullable=True),
        sa.Column('severity', sa.String(20), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('cvss_score', sa.Float(), nullable=True),
        sa.Column('published_date', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('cve_id', name='idx_cve_id'),
    )
    op.create_index('idx_package_name', 'vulnerability_cache', ['package_name'])
    op.create_index('idx_expires_at', 'vulnerability_cache', ['expires_at'])


def downgrade() -> None:
    """Revert initial database schema."""
    
    op.drop_table('vulnerability_cache')
    op.drop_table('github_metrics')
    op.drop_table('audit_cache')
    op.drop_table('audit_findings')
    op.drop_table('audits')
    op.drop_table('repositories')
