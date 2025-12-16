"""Create new ORM tables only (safe)

Revision ID: bad0a064eeda
Revises: abbc4f65c12b
Create Date: 2025-12-16 16:42:01.912276

Creates only the new Quantum ADN 2.0 tables in quantum schema.
Does NOT touch existing tables.

Tables created:
- quantum.team_quantum_dna
- quantum.goalscorer_profiles
- quantum.chess_classifications
- quantum.quantum_friction_matrix
- quantum.quantum_strategies
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'bad0a064eeda'
down_revision = 'abbc4f65c12b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create new Quantum ADN 2.0 tables."""

    # 1. team_quantum_dna
    op.create_table(
        'team_quantum_dna',
        sa.Column('team_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('team_name', sa.String(length=100), nullable=False),
        sa.Column('league', sa.String(length=50), nullable=False),
        sa.Column('tier', sa.String(length=20), nullable=True),
        sa.Column('best_strategy', sa.String(length=50), nullable=True),
        sa.Column('market_dna', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('context_dna', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('risk_dna', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('temporal_dna', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('nemesis_dna', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('psyche_dna', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('roster_dna', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('physical_dna', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('luck_dna', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('total_pnl', sa.Float(), nullable=True),
        sa.Column('win_rate', sa.Float(), nullable=True),
        sa.Column('avg_clv', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('team_id', name='pk_team_quantum_dna'),
        schema='quantum'
    )
    op.create_index('ix_quantum_team_quantum_dna_league', 'team_quantum_dna', ['league'], unique=False, schema='quantum')
    op.create_index('ix_quantum_team_quantum_dna_team_name', 'team_quantum_dna', ['team_name'], unique=True, schema='quantum')

    # 2. goalscorer_profiles
    op.create_table(
        'goalscorer_profiles',
        sa.Column('player_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('player_name', sa.String(length=100), nullable=False),
        sa.Column('team_name', sa.String(length=100), nullable=False),
        sa.Column('league', sa.String(length=50), nullable=False),
        sa.Column('position', sa.String(length=30), nullable=True),
        sa.Column('goals_total', sa.Integer(), nullable=False),
        sa.Column('goals_home', sa.Integer(), nullable=False),
        sa.Column('goals_away', sa.Integer(), nullable=False),
        sa.Column('appearances', sa.Integer(), nullable=False),
        sa.Column('anytime_prob', sa.Float(), nullable=True),
        sa.Column('first_goal_prob', sa.Float(), nullable=True),
        sa.Column('last_goal_prob', sa.Float(), nullable=True),
        sa.Column('timing_dna', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('season', sa.String(length=10), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('player_id', name='pk_goalscorer_profiles'),
        schema='quantum'
    )
    op.create_index('ix_quantum_goalscorer_profiles_player_name', 'goalscorer_profiles', ['player_name'], unique=False, schema='quantum')
    op.create_index('ix_quantum_goalscorer_profiles_team_name', 'goalscorer_profiles', ['team_name'], unique=False, schema='quantum')

    # 3. chess_classifications
    op.create_table(
        'chess_classifications',
        sa.Column('classification_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('piece_type', sa.String(length=20), nullable=False),
        sa.Column('piece_subtype', sa.String(length=30), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('characteristics', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('match_patterns', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('season', sa.String(length=10), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('classification_id', name='pk_chess_classifications'),
        sa.ForeignKeyConstraint(['team_id'], ['quantum.team_quantum_dna.team_id'], name='fk_chess_classifications_team_id'),
        schema='quantum'
    )
    op.create_index('ix_quantum_chess_classifications_team_id', 'chess_classifications', ['team_id'], unique=False, schema='quantum')

    # 4. quantum_friction_matrix
    op.create_table(
        'quantum_friction_matrix',
        sa.Column('friction_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('team_home_id', sa.Integer(), nullable=False),
        sa.Column('team_away_id', sa.Integer(), nullable=False),
        sa.Column('friction_score', sa.Float(), nullable=False),
        sa.Column('style_clash', sa.Float(), nullable=True),
        sa.Column('tactical_friction', sa.Float(), nullable=True),
        sa.Column('tempo_friction', sa.Float(), nullable=True),
        sa.Column('risk_friction', sa.Float(), nullable=True),
        sa.Column('psychological_edge', sa.Float(), nullable=True),
        sa.Column('historical_friction', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('matches_analyzed', sa.Integer(), nullable=False),
        sa.Column('season', sa.String(length=10), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('friction_id', name='pk_quantum_friction_matrix'),
        sa.ForeignKeyConstraint(['team_home_id'], ['quantum.team_quantum_dna.team_id'], name='fk_quantum_friction_matrix_team_home_id'),
        sa.ForeignKeyConstraint(['team_away_id'], ['quantum.team_quantum_dna.team_id'], name='fk_quantum_friction_matrix_team_away_id'),
        schema='quantum'
    )
    op.create_index('ix_friction_teams', 'quantum_friction_matrix', ['team_home_id', 'team_away_id'], unique=False, schema='quantum')

    # 5. quantum_strategies
    op.create_table(
        'quantum_strategies',
        sa.Column('strategy_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('strategy_name', sa.String(length=100), nullable=False),
        sa.Column('strategy_type', sa.String(length=50), nullable=False),
        sa.Column('market_family', sa.String(length=50), nullable=True),
        sa.Column('win_rate', sa.Float(), nullable=True),
        sa.Column('total_pnl', sa.Float(), nullable=True),
        sa.Column('avg_clv', sa.Float(), nullable=True),
        sa.Column('total_bets', sa.Integer(), nullable=False),
        sa.Column('context_filters', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('performance_by_context', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('priority', sa.Integer(), nullable=True),
        sa.Column('season', sa.String(length=10), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('strategy_id', name='pk_quantum_strategies'),
        sa.ForeignKeyConstraint(['team_id'], ['quantum.team_quantum_dna.team_id'], name='fk_quantum_strategies_team_id'),
        schema='quantum'
    )


def downgrade() -> None:
    """Drop Quantum ADN 2.0 tables (reverse migration)."""
    op.drop_table('quantum_strategies', schema='quantum')
    op.drop_table('quantum_friction_matrix', schema='quantum')
    op.drop_table('chess_classifications', schema='quantum')
    op.drop_table('goalscorer_profiles', schema='quantum')
    op.drop_table('team_quantum_dna', schema='quantum')
