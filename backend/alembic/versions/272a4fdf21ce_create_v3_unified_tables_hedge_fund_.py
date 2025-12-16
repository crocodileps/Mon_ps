"""Create V3 unified tables - Hedge Fund Architecture

Revision ID: 272a4fdf21ce
Revises: bad0a064eeda
Create Date: 2025-12-16

ARCHITECTURE V3 - HEDGE FUND GRADE
===================================
Fusion du meilleur de V1 (données réelles) + V2 (structure moderne):

Tables créées:
1. quantum.team_quantum_dna_v3 (45 colonnes)
   - Identité (7) + Style (5) + Métriques (12) + ADN 9 vecteurs (9)
   - Guidance stratégique (5) + Narrative (3) + Timestamps (4)

2. quantum.quantum_friction_matrix_v3 (32 colonnes)
   - Identité (5) + Styles (2) + Friction scores (7) + Prédictions (5)
   - H2H historique (5) + Méta (4) + Tracking (4)

3. quantum.quantum_strategies_v3 (26 colonnes)
   - Identité (4) + Classification (4) + Métriques (10)
   - Context (4) + Opérationnel (5) + Timestamps (2)

NE TOUCHE PAS aux tables existantes V1 ou V2.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '272a4fdf21ce'
down_revision = 'bad0a064eeda'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create V3 unified Hedge Fund Architecture tables."""

    # ═══════════════════════════════════════════════════════════════════
    # TABLE 1: team_quantum_dna_v3 (45 colonnes)
    # ═══════════════════════════════════════════════════════════════════
    op.create_table(
        'team_quantum_dna_v3',

        # === IDENTITÉ (7 colonnes) ===
        sa.Column('team_id', sa.Integer(), autoincrement=True, nullable=False,
                  comment='Primary key - unique team identifier'),
        sa.Column('team_name', sa.String(100), nullable=False,
                  comment='Official team name'),
        sa.Column('team_name_normalized', sa.String(100), nullable=True,
                  comment='Normalized name for matching (V1)'),
        sa.Column('league', sa.String(50), nullable=False,
                  comment='League identifier (V2)'),
        sa.Column('tier', sa.String(20), nullable=True,
                  comment='Team tier classification'),
        sa.Column('tier_rank', sa.Integer(), nullable=True,
                  comment='Numeric rank within tier (V1)'),
        sa.Column('team_intelligence_id', sa.Integer(), nullable=True,
                  comment='Legacy link to team_intelligence (V1)'),

        # === STYLE & ARCHETYPE (5 colonnes) ===
        sa.Column('current_style', sa.String(50), nullable=True,
                  comment='Current playing style (V1)'),
        sa.Column('style_confidence', sa.Integer(), nullable=True,
                  comment='Confidence in style classification 0-100 (V1)'),
        sa.Column('team_archetype', sa.String(50), nullable=True,
                  comment='Behavioral archetype (V1)'),
        sa.Column('betting_identity', postgresql.JSONB(astext_type=sa.Text()), nullable=True,
                  comment='Complex betting identity profile (V1)'),
        sa.Column('best_strategy', sa.String(50), nullable=True,
                  comment='Best performing strategy name (V2)'),

        # === MÉTRIQUES BETTING COMPLÈTES (12 colonnes) ===
        sa.Column('total_matches', sa.Integer(), nullable=True, default=0,
                  comment='Total matches analyzed (V1)'),
        sa.Column('total_bets', sa.Integer(), nullable=True, default=0,
                  comment='Total bets placed on this team (V1)'),
        sa.Column('total_wins', sa.Integer(), nullable=True, default=0,
                  comment='Total winning bets (V1)'),
        sa.Column('total_losses', sa.Integer(), nullable=True, default=0,
                  comment='Total losing bets (V1)'),
        sa.Column('win_rate', sa.Float(), nullable=True,
                  comment='Win rate percentage (V1+V2)'),
        sa.Column('total_pnl', sa.Float(), nullable=True, default=0.0,
                  comment='Total profit/loss in units (V1+V2)'),
        sa.Column('roi', sa.Float(), nullable=True,
                  comment='Return on investment percentage (V1)'),
        sa.Column('avg_clv', sa.Float(), nullable=True,
                  comment='Average Closing Line Value - CRITICAL (V2)'),
        sa.Column('unlucky_losses', sa.Integer(), nullable=True, default=0,
                  comment='Losses due to bad luck not analysis (V1)'),
        sa.Column('bad_analysis_losses', sa.Integer(), nullable=True, default=0,
                  comment='Losses due to bad analysis (V1)'),
        sa.Column('unlucky_pct', sa.Float(), nullable=True,
                  comment='Percentage of unlucky losses (V1)'),

        # === ADN STRUCTURÉ - 9 VECTEURS JSONB (V2 révolutionnaire) ===
        sa.Column('market_dna', postgresql.JSONB(astext_type=sa.Text()), nullable=True,
                  comment='Market performance DNA vector'),
        sa.Column('context_dna', postgresql.JSONB(astext_type=sa.Text()), nullable=True,
                  comment='Contextual performance DNA vector'),
        sa.Column('risk_dna', postgresql.JSONB(astext_type=sa.Text()), nullable=True,
                  comment='Risk profile DNA vector'),
        sa.Column('temporal_dna', postgresql.JSONB(astext_type=sa.Text()), nullable=True,
                  comment='Temporal patterns DNA vector'),
        sa.Column('nemesis_dna', postgresql.JSONB(astext_type=sa.Text()), nullable=True,
                  comment='Opponent matchup DNA vector'),
        sa.Column('psyche_dna', postgresql.JSONB(astext_type=sa.Text()), nullable=True,
                  comment='Psychological profile DNA vector'),
        sa.Column('roster_dna', postgresql.JSONB(astext_type=sa.Text()), nullable=True,
                  comment='Squad composition DNA vector'),
        sa.Column('physical_dna', postgresql.JSONB(astext_type=sa.Text()), nullable=True,
                  comment='Physical performance DNA vector'),
        sa.Column('luck_dna', postgresql.JSONB(astext_type=sa.Text()), nullable=True,
                  comment='Luck/variance DNA vector'),

        # === GUIDANCE STRATÉGIQUE (5 colonnes JSONB - V1) ===
        sa.Column('exploit_markets', postgresql.JSONB(astext_type=sa.Text()), nullable=True,
                  comment='Markets to exploit for this team (V1)'),
        sa.Column('avoid_markets', postgresql.JSONB(astext_type=sa.Text()), nullable=True,
                  comment='Markets to avoid for this team (V1)'),
        sa.Column('optimal_scenarios', postgresql.JSONB(astext_type=sa.Text()), nullable=True,
                  comment='Optimal betting scenarios (V1)'),
        sa.Column('optimal_strategies', postgresql.JSONB(astext_type=sa.Text()), nullable=True,
                  comment='Best strategies for this team (V1)'),
        sa.Column('quantum_dna_legacy', postgresql.JSONB(astext_type=sa.Text()), nullable=True,
                  comment='Legacy monolithic DNA backup (V1)'),

        # === NARRATIVE & FINGERPRINT (3 colonnes - V1) ===
        sa.Column('narrative_profile', sa.Text(), nullable=True,
                  comment='Human-readable team description (V1)'),
        sa.Column('dna_fingerprint', sa.String(64), nullable=True,
                  comment='Unique DNA hash for change detection (V1)'),
        sa.Column('season', sa.String(10), nullable=True,
                  comment='Season identifier e.g. 2024-25 (V2)'),

        # === TIMESTAMPS (4 colonnes) ===
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('last_audit_at', sa.DateTime(), nullable=True,
                  comment='Last audit timestamp (V1)'),

        # === CONSTRAINTS ===
        sa.PrimaryKeyConstraint('team_id', name='pk_team_quantum_dna_v3'),
        sa.UniqueConstraint('team_name', 'league', name='uq_team_quantum_dna_v3_team_league'),
        schema='quantum'
    )

    # Indexes for team_quantum_dna_v3
    op.create_index('ix_tqd_v3_team_name', 'team_quantum_dna_v3', ['team_name'],
                    unique=False, schema='quantum')
    op.create_index('ix_tqd_v3_league', 'team_quantum_dna_v3', ['league'],
                    unique=False, schema='quantum')
    op.create_index('ix_tqd_v3_tier', 'team_quantum_dna_v3', ['tier'],
                    unique=False, schema='quantum')
    op.create_index('ix_tqd_v3_best_strategy', 'team_quantum_dna_v3', ['best_strategy'],
                    unique=False, schema='quantum')
    op.create_index('ix_tqd_v3_season', 'team_quantum_dna_v3', ['season'],
                    unique=False, schema='quantum')


    # ═══════════════════════════════════════════════════════════════════
    # TABLE 2: quantum_friction_matrix_v3 (32 colonnes)
    # ═══════════════════════════════════════════════════════════════════
    op.create_table(
        'quantum_friction_matrix_v3',

        # === IDENTITÉ (5 colonnes) ===
        sa.Column('friction_id', sa.Integer(), autoincrement=True, nullable=False,
                  comment='Primary key'),
        sa.Column('team_home_id', sa.Integer(), nullable=False,
                  comment='FK to team_quantum_dna_v3'),
        sa.Column('team_away_id', sa.Integer(), nullable=False,
                  comment='FK to team_quantum_dna_v3'),
        sa.Column('team_home_name', sa.String(100), nullable=False,
                  comment='Home team name (denormalized for perf)'),
        sa.Column('team_away_name', sa.String(100), nullable=False,
                  comment='Away team name (denormalized for perf)'),

        # === STYLES (2 colonnes - V1) ===
        sa.Column('style_home', sa.String(50), nullable=True,
                  comment='Home team style at time of analysis'),
        sa.Column('style_away', sa.String(50), nullable=True,
                  comment='Away team style at time of analysis'),

        # === FRICTION SCORES (7 colonnes - V1 + V2 FUSIONNÉS) ===
        sa.Column('friction_score', sa.Float(), nullable=False,
                  comment='Overall friction score 0-100'),
        sa.Column('style_clash', sa.Float(), nullable=True,
                  comment='Style clash component (V1 style_clash_score)'),
        sa.Column('tempo_friction', sa.Float(), nullable=True,
                  comment='Tempo clash component (V1 tempo_clash_score)'),
        sa.Column('mental_clash', sa.Float(), nullable=True,
                  comment='Mental clash component (V1)'),
        sa.Column('tactical_friction', sa.Float(), nullable=True,
                  comment='Tactical friction component (V2)'),
        sa.Column('risk_friction', sa.Float(), nullable=True,
                  comment='Risk friction component (V2)'),
        sa.Column('psychological_edge', sa.Float(), nullable=True,
                  comment='Psychological edge home vs away (V2)'),

        # === PRÉDICTIONS (5 colonnes - V1 CRITIQUE) ===
        sa.Column('predicted_goals', sa.Float(), nullable=True,
                  comment='Predicted total goals'),
        sa.Column('predicted_btts_prob', sa.Float(), nullable=True,
                  comment='Predicted BTTS probability'),
        sa.Column('predicted_over25_prob', sa.Float(), nullable=True,
                  comment='Predicted Over 2.5 probability'),
        sa.Column('predicted_winner', sa.String(50), nullable=True,
                  comment='Predicted match winner'),
        sa.Column('chaos_potential', sa.Float(), nullable=True,
                  comment='Chaos/upset potential score'),

        # === H2H HISTORIQUE (5 colonnes - V1 CRITIQUE) ===
        sa.Column('h2h_matches', sa.Integer(), nullable=True, default=0,
                  comment='Total H2H matches analyzed'),
        sa.Column('h2h_home_wins', sa.Integer(), nullable=True, default=0,
                  comment='H2H wins for home team'),
        sa.Column('h2h_away_wins', sa.Integer(), nullable=True, default=0,
                  comment='H2H wins for away team'),
        sa.Column('h2h_draws', sa.Integer(), nullable=True, default=0,
                  comment='H2H draws'),
        sa.Column('h2h_avg_goals', sa.Float(), nullable=True,
                  comment='Average goals in H2H matches'),

        # === MÉTA (4 colonnes - V1 + V2) ===
        sa.Column('friction_vector', postgresql.JSONB(astext_type=sa.Text()), nullable=True,
                  comment='Detailed friction breakdown vector (V1)'),
        sa.Column('historical_friction', postgresql.JSONB(astext_type=sa.Text()), nullable=True,
                  comment='Historical friction data (V2)'),
        sa.Column('matches_analyzed', sa.Integer(), nullable=False, default=0,
                  comment='Number of matches analyzed (V1 sample_size)'),
        sa.Column('confidence_level', sa.String(20), nullable=True,
                  comment='Confidence: LOW/MEDIUM/HIGH/VERY_HIGH'),

        # === TRACKING (4 colonnes) ===
        sa.Column('season', sa.String(10), nullable=True,
                  comment='Season identifier'),
        sa.Column('last_match_date', sa.DateTime(), nullable=True,
                  comment='Date of last H2H match analyzed'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),

        # === CONSTRAINTS ===
        sa.PrimaryKeyConstraint('friction_id', name='pk_quantum_friction_matrix_v3'),
        sa.ForeignKeyConstraint(['team_home_id'], ['quantum.team_quantum_dna_v3.team_id'],
                                name='fk_qfm_v3_team_home'),
        sa.ForeignKeyConstraint(['team_away_id'], ['quantum.team_quantum_dna_v3.team_id'],
                                name='fk_qfm_v3_team_away'),
        sa.UniqueConstraint('team_home_id', 'team_away_id', 'season',
                           name='uq_qfm_v3_matchup_season'),
        schema='quantum'
    )

    # Indexes for quantum_friction_matrix_v3
    op.create_index('ix_qfm_v3_teams', 'quantum_friction_matrix_v3',
                    ['team_home_id', 'team_away_id'], unique=False, schema='quantum')
    op.create_index('ix_qfm_v3_friction_score', 'quantum_friction_matrix_v3',
                    ['friction_score'], unique=False, schema='quantum')
    op.create_index('ix_qfm_v3_season', 'quantum_friction_matrix_v3',
                    ['season'], unique=False, schema='quantum')
    op.create_index('ix_qfm_v3_chaos', 'quantum_friction_matrix_v3',
                    ['chaos_potential'], unique=False, schema='quantum')


    # ═══════════════════════════════════════════════════════════════════
    # TABLE 3: quantum_strategies_v3 (26 colonnes)
    # ═══════════════════════════════════════════════════════════════════
    op.create_table(
        'quantum_strategies_v3',

        # === IDENTITÉ (4 colonnes) ===
        sa.Column('strategy_id', sa.Integer(), autoincrement=True, nullable=False,
                  comment='Primary key'),
        sa.Column('team_id', sa.Integer(), nullable=False,
                  comment='FK to team_quantum_dna_v3'),
        sa.Column('team_name', sa.String(100), nullable=False,
                  comment='Team name (denormalized for perf)'),
        sa.Column('strategy_name', sa.String(100), nullable=False,
                  comment='Strategy identifier'),

        # === CLASSIFICATION (4 colonnes - V1 + V2) ===
        sa.Column('strategy_type', sa.String(50), nullable=True,
                  comment='Type: MARKET/CONTEXT/COMPOUND (V2)'),
        sa.Column('market_family', sa.String(50), nullable=True,
                  comment='Market family: OVER/BTTS/1X2/AH (V2)'),
        sa.Column('is_best_strategy', sa.Boolean(), nullable=True, default=False,
                  comment='Is this the best strategy for team (V1)'),
        sa.Column('strategy_rank', sa.Integer(), nullable=True,
                  comment='Rank among team strategies (V1)'),

        # === MÉTRIQUES PERFORMANCE (10 colonnes - V1 + V2) ===
        sa.Column('total_bets', sa.Integer(), nullable=False, default=0,
                  comment='Total bets using this strategy'),
        sa.Column('wins', sa.Integer(), nullable=True, default=0,
                  comment='Winning bets'),
        sa.Column('losses', sa.Integer(), nullable=True, default=0,
                  comment='Losing bets'),
        sa.Column('win_rate', sa.Float(), nullable=True,
                  comment='Win rate percentage'),
        sa.Column('profit', sa.Float(), nullable=True, default=0.0,
                  comment='Absolute profit in units (V1)'),
        sa.Column('total_pnl', sa.Float(), nullable=True, default=0.0,
                  comment='Total P&L alias (V2)'),
        sa.Column('roi', sa.Float(), nullable=True,
                  comment='Return on investment (V1)'),
        sa.Column('avg_clv', sa.Float(), nullable=True,
                  comment='Average CLV - CRITICAL (V2)'),
        sa.Column('unlucky_count', sa.Integer(), nullable=True, default=0,
                  comment='Unlucky losses count (V1)'),
        sa.Column('bad_analysis_count', sa.Integer(), nullable=True, default=0,
                  comment='Bad analysis losses count (V1)'),

        # === CONTEXT & PARAMETERS (4 colonnes - V1 + V2) ===
        sa.Column('context_filters', postgresql.JSONB(astext_type=sa.Text()), nullable=True,
                  comment='Context filters for strategy (V2)'),
        sa.Column('performance_by_context', postgresql.JSONB(astext_type=sa.Text()), nullable=True,
                  comment='Performance breakdown by context (V2)'),
        sa.Column('parameters', postgresql.JSONB(astext_type=sa.Text()), nullable=True,
                  comment='Strategy parameters (V1)'),
        sa.Column('parameters_hash', sa.String(64), nullable=True,
                  comment='Hash for version tracking (V1)'),

        # === OPÉRATIONNEL (5 colonnes) ===
        sa.Column('is_active', sa.Boolean(), nullable=False,
                  server_default=sa.text('true'),
                  comment='Is strategy currently active (V2)'),
        sa.Column('priority', sa.Integer(), nullable=True,
                  comment='Execution priority (V2)'),
        sa.Column('source', sa.String(50), nullable=True,
                  comment='Strategy source/origin (V1)'),
        sa.Column('strategy_version', sa.String(20), nullable=True,
                  comment='Version string (V1)'),
        sa.Column('season', sa.String(10), nullable=True,
                  comment='Season identifier (V2)'),

        # === TIMESTAMPS (2 colonnes) ===
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),

        # === CONSTRAINTS ===
        sa.PrimaryKeyConstraint('strategy_id', name='pk_quantum_strategies_v3'),
        sa.ForeignKeyConstraint(['team_id'], ['quantum.team_quantum_dna_v3.team_id'],
                                name='fk_qs_v3_team'),
        sa.UniqueConstraint('team_id', 'strategy_name', 'season',
                           name='uq_qs_v3_team_strategy_season'),
        schema='quantum'
    )

    # Indexes for quantum_strategies_v3
    op.create_index('ix_qs_v3_team_id', 'quantum_strategies_v3',
                    ['team_id'], unique=False, schema='quantum')
    op.create_index('ix_qs_v3_market_family', 'quantum_strategies_v3',
                    ['market_family'], unique=False, schema='quantum')
    op.create_index('ix_qs_v3_is_best', 'quantum_strategies_v3',
                    ['is_best_strategy'], unique=False, schema='quantum')
    op.create_index('ix_qs_v3_is_active', 'quantum_strategies_v3',
                    ['is_active'], unique=False, schema='quantum')
    op.create_index('ix_qs_v3_season', 'quantum_strategies_v3',
                    ['season'], unique=False, schema='quantum')
    op.create_index('ix_qs_v3_avg_clv', 'quantum_strategies_v3',
                    ['avg_clv'], unique=False, schema='quantum')


    print("✅ V3 HEDGE FUND ARCHITECTURE TABLES CREATED")
    print("   - team_quantum_dna_v3: 45 columns")
    print("   - quantum_friction_matrix_v3: 32 columns")
    print("   - quantum_strategies_v3: 26 columns")
    print("   - Total: 103 columns unified")


def downgrade() -> None:
    """Drop V3 tables (reverse order for FK constraints)."""
    op.drop_table('quantum_strategies_v3', schema='quantum')
    op.drop_table('quantum_friction_matrix_v3', schema='quantum')
    op.drop_table('team_quantum_dna_v3', schema='quantum')
    print("⚠️ V3 tables dropped")
