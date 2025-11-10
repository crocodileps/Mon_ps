"""add clv odds_close market_type to bets

Revision ID: abbc4f65c12b
Revises: None
Create Date: 2025-11-10 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "abbc4f65c12b"  # Garder l'ID généré automatiquement
down_revision = None  # Garder la révision précédente
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Ajoute les colonnes clv, odds_close, market_type à la table bets"""

    # Ajout de la colonne clv (Closing Line Value)
    op.add_column(
        "bets",
        sa.Column(
            "clv",
            sa.Float(),
            nullable=True,
            comment="Closing Line Value - Indicateur de qualité du pari",
        ),
    )

    # Ajout de la colonne odds_close (Cote de clôture)
    op.add_column(
        "bets",
        sa.Column(
            "odds_close",
            sa.Float(),
            nullable=True,
            comment="Cote de clôture du marché",
        ),
    )

    # Ajout de la colonne market_type (Type de marché)
    op.add_column(
        "bets",
        sa.Column(
            "market_type",
            sa.String(50),
            nullable=True,
            comment="Type de marché: h2h, totals, btts, etc.",
        ),
    )

    # Créer un index sur market_type pour améliorer les performances des requêtes analytics
    op.create_index(
        "ix_bets_market_type",
        "bets",
        ["market_type"],
        unique=False,
    )

    print("Migration upgrade completed: Added clv, odds_close, market_type to bets table")


def downgrade() -> None:
    """Supprime les colonnes ajoutées (rollback)"""

    # Supprimer l'index
    op.drop_index("ix_bets_market_type", table_name="bets")

    # Supprimer les colonnes dans l'ordre inverse
    op.drop_column("bets", "market_type")
    op.drop_column("bets", "odds_close")
    op.drop_column("bets", "clv")

    print("Migration downgrade completed: Removed clv, odds_close, market_type from bets table")

