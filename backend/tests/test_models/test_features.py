"""
Tests pour quantum_core.models.features.

8 tests couvrant FeatureMetadata, TeamFeatures et MatchFeatures.
"""

import pytest
from datetime import datetime, timedelta
from quantum_core.models.features import (
    FeatureType,
    FeatureSource,
    FeatureMetadata,
    TeamFeatures,
    MatchFeatures,
)


class TestFeatureMetadata:
    """Tests pour le modèle FeatureMetadata."""

    def test_feature_metadata_creation(self):
        """Test création d'une FeatureMetadata basique."""
        meta = FeatureMetadata(
            feature_name="xg_per_90",
            feature_type=FeatureType.CONTINUOUS,
            source=FeatureSource.UNDERSTAT,
            version="2.1.0",
            computed_at=datetime.utcnow(),
            quality_score=0.98,
            confidence=0.95,
        )

        assert meta.feature_name == "xg_per_90"
        assert meta.feature_type == "continuous"
        assert meta.source == "understat"
        assert meta.version == "2.1.0"
        assert meta.quality_score == 0.98
        assert not meta.is_imputed

    def test_feature_metadata_with_imputation(self):
        """Test FeatureMetadata avec imputation."""
        meta = FeatureMetadata(
            feature_name="possession_pct",
            feature_type=FeatureType.CONTINUOUS,
            source=FeatureSource.CALCULATED,
            version="1.0.0",
            is_imputed=True,
            imputation_method="mean",
            original_value=None,
            quality_score=0.75,
            confidence=0.70,
        )

        assert meta.is_imputed is True
        assert meta.imputation_method == "mean"
        assert meta.quality_score == 0.75


class TestTeamFeatures:
    """Tests pour le modèle TeamFeatures."""

    def test_team_features_creation(self):
        """Test création de TeamFeatures complètes."""
        now = datetime.utcnow()
        team = TeamFeatures(
            team_name="Liverpool",
            team_id="liverpool_fc",
            is_home=True,
            xg_per_90=2.14,
            xga_per_90=0.87,
            possession_pct=63.2,
            ppda=8.3,
            recent_form="WWDWW",
            elo_rating=1987,
            completeness_score=0.95,
            data_quality="excellent",
            computed_at=now,
        )

        assert team.team_name == "Liverpool"
        assert team.is_home is True
        assert team.xg_per_90 == 2.14
        assert team.xga_per_90 == 0.87
        assert team.possession_pct == 63.2
        assert team.recent_form == "WWDWW"
        assert team.elo_rating == 1987
        assert team.completeness_score == 0.95

    def test_team_features_minimal(self):
        """Test TeamFeatures avec données minimales."""
        team = TeamFeatures(
            team_name="Test FC",
            team_id="test_fc",
            is_home=False,
        )

        assert team.team_name == "Test FC"
        assert team.is_home is False
        assert team.xg_per_90 is None
        assert team.completeness_score == 1.0  # Default
        assert team.data_quality == "excellent"  # Default

    def test_team_features_form_validation(self):
        """Test validation du champ recent_form (pattern W/D/L)."""
        # Forme valide
        team = TeamFeatures(
            team_name="Team A",
            team_id="team_a",
            is_home=True,
            recent_form="WWLDW",
        )
        assert team.recent_form == "WWLDW"

        # Forme invalide (caractères interdits)
        with pytest.raises(Exception):
            TeamFeatures(
                team_name="Team B",
                team_id="team_b",
                is_home=True,
                recent_form="WWXDL",  # X invalide
            )

    def test_team_features_with_metadata(self):
        """Test TeamFeatures avec feature_metadata."""
        meta_xg = FeatureMetadata(
            feature_name="xg_per_90",
            feature_type=FeatureType.CONTINUOUS,
            source=FeatureSource.UNDERSTAT,
            version="2.1.0",
            quality_score=0.98,
        )

        meta_elo = FeatureMetadata(
            feature_name="elo_rating",
            feature_type=FeatureType.CONTINUOUS,
            source=FeatureSource.CALCULATED,
            version="1.0.0",
            quality_score=1.0,
        )

        team = TeamFeatures(
            team_name="Manchester City",
            team_id="mancity",
            is_home=False,
            xg_per_90=2.05,
            elo_rating=2012,
            feature_metadata=[meta_xg, meta_elo],
            completeness_score=0.92,
        )

        assert len(team.feature_metadata) == 2
        assert team.feature_metadata[0].feature_name == "xg_per_90"
        assert team.feature_metadata[1].feature_name == "elo_rating"


class TestMatchFeatures:
    """Tests pour le modèle MatchFeatures."""

    def test_match_features_creation(self):
        """Test création de MatchFeatures complètes."""
        home = TeamFeatures(
            team_name="Liverpool",
            team_id="liverpool",
            is_home=True,
            xg_per_90=2.14,
            elo_rating=1987,
            squad_value_millions=950.0,
        )

        away = TeamFeatures(
            team_name="Manchester City",
            team_id="mancity",
            is_home=False,
            xg_per_90=2.05,
            elo_rating=2010,
            squad_value_millions=1100.0,
        )

        match = MatchFeatures(
            match_id="liverpool_vs_mancity_20251215",
            competition="Premier League",
            season="2025-26",
            match_date=datetime(2025, 12, 15, 15, 0),
            home_team=home,
            away_team=away,
            h2h_home_wins=12,
            h2h_draws=8,
            h2h_away_wins=15,
            overall_completeness=0.92,
            overall_quality="excellent",
        )

        assert match.match_id == "liverpool_vs_mancity_20251215"
        assert match.competition == "Premier League"
        assert match.season == "2025-26"
        assert match.home_team.team_name == "Liverpool"
        assert match.away_team.team_name == "Manchester City"
        assert match.h2h_home_wins == 12

    def test_match_features_auto_xg_differential(self):
        """Test calcul automatique de xg_differential."""
        home = TeamFeatures(
            team_name="Team A",
            team_id="team_a",
            is_home=True,
            xg_per_90=1.8,
        )

        away = TeamFeatures(
            team_name="Team B",
            team_id="team_b",
            is_home=False,
            xg_per_90=1.2,
        )

        match = MatchFeatures(
            match_id="test_match",
            competition="Test League",
            season="2025-26",
            match_date=datetime.utcnow(),
            home_team=home,
            away_team=away,
        )

        # xg_differential = 1.8 - 1.2 = 0.6
        assert match.xg_differential == pytest.approx(0.6, rel=1e-6)

    def test_match_features_auto_elo_differential(self):
        """Test calcul automatique de elo_differential."""
        home = TeamFeatures(
            team_name="Team A",
            team_id="team_a",
            is_home=True,
            elo_rating=2000,
        )

        away = TeamFeatures(
            team_name="Team B",
            team_id="team_b",
            is_home=False,
            elo_rating=1950,
        )

        match = MatchFeatures(
            match_id="test_match",
            competition="Test League",
            season="2025-26",
            match_date=datetime.utcnow(),
            home_team=home,
            away_team=away,
        )

        # elo_differential = 2000 - 1950 = 50
        assert match.elo_differential == 50

    def test_match_features_auto_value_differential(self):
        """Test calcul automatique de value_differential."""
        home = TeamFeatures(
            team_name="Team A",
            team_id="team_a",
            is_home=True,
            squad_value_millions=800.0,
        )

        away = TeamFeatures(
            team_name="Team B",
            team_id="team_b",
            is_home=False,
            squad_value_millions=600.0,
        )

        match = MatchFeatures(
            match_id="test_match",
            competition="Test League",
            season="2025-26",
            match_date=datetime.utcnow(),
            home_team=home,
            away_team=away,
        )

        # value_differential = 800.0 - 600.0 = 200.0
        assert match.value_differential == pytest.approx(200.0, rel=1e-6)


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS ADR COMPLIANCE
# ═══════════════════════════════════════════════════════════════════════════════


class TestADR002ModelValidatorFeatures:
    """Tests validant ADR #002 pour features.py.

    ADR #002: model_validator pour cross-field logic.
    - Garantit accès aux defaults
    - Plus rapide que field_validator × N
    - Type-safe avec Self return
    """

    def test_model_validator_accesses_defaults(self):
        """ADR #002: model_validator accède aux defaults et calcule."""
        home = TeamFeatures(
            team_name="Liverpool",
            team_id="liverpool",
            is_home=True,
            xg_per_90=2.14,
            elo_rating=1987,
            squad_value_millions=950.0,
        )

        away = TeamFeatures(
            team_name="Manchester City",
            team_id="mancity",
            is_home=False,
            xg_per_90=2.05,
            elo_rating=2010,
            squad_value_millions=1100.0,
        )

        # Tous les differentials omis → defaults None → calculés
        match = MatchFeatures(
            match_id="test_adr002_1",
            competition="Premier League",
            season="2025-26",
            match_date=datetime.utcnow(),
            home_team=home,
            away_team=away,
            # xg_differential omis → None → calculé
            # elo_differential omis → None → calculé
            # value_differential omis → None → calculé
        )

        # ADR #002: model_validator a calculé tous les differentials
        assert match.xg_differential == pytest.approx(0.09, rel=1e-6)  # 2.14 - 2.05
        assert match.elo_differential == -23  # 1987 - 2010
        assert match.value_differential == pytest.approx(-150.0, rel=1e-6)  # 950 - 1100

    def test_model_validator_cross_field_logic(self):
        """ADR #002: model_validator combine données de plusieurs champs."""
        home = TeamFeatures(
            team_name="Team A",
            team_id="team_a",
            is_home=True,
            xg_per_90=1.5,
            elo_rating=1800,
            # squad_value_millions omis
        )

        away = TeamFeatures(
            team_name="Team B",
            team_id="team_b",
            is_home=False,
            xg_per_90=1.2,
            # elo_rating omis
            squad_value_millions=600.0,
        )

        match = MatchFeatures(
            match_id="test_adr002_2",
            competition="Test League",
            season="2025-26",
            match_date=datetime.utcnow(),
            home_team=home,
            away_team=away,
        )

        # Logique cross-field avec données partielles
        assert match.xg_differential == pytest.approx(0.3, rel=1e-6)  # 1.5 - 1.2
        assert match.elo_differential is None  # away_elo manquant
        assert match.value_differential is None  # home_value manquant


class TestADR003FieldSerializerFeatures:
    """Tests validant ADR #003 pour features.py.

    ADR #003: field_serializer explicite.
    - when_used='json' pour .model_dump_json()
    - Préserve datetime dans .model_dump()
    - Type-safe et testable
    """

    def test_datetime_serializes_to_iso8601_json_metadata(self):
        """ADR #003: .model_dump_json() serialise datetime en ISO 8601 (FeatureMetadata)."""
        meta = FeatureMetadata(
            feature_name="xg_per_90",
            feature_type=FeatureType.CONTINUOUS,
            source=FeatureSource.UNDERSTAT,
            version="2.1.0",
            computed_at=datetime(2025, 12, 13, 21, 0, 0),
            data_timestamp=datetime(2025, 12, 13, 20, 0, 0),
            quality_score=0.98,
        )

        json_str = meta.model_dump_json()

        # Vérifier serialisation ISO 8601
        assert '"computed_at":"2025-12-13T21:00:00"' in json_str
        assert '"data_timestamp":"2025-12-13T20:00:00"' in json_str

    def test_datetime_preserved_in_model_dump_team(self):
        """ADR #003: .model_dump() préserve datetime object (TeamFeatures)."""
        computed = datetime(2025, 12, 13, 21, 30, 0)

        team = TeamFeatures(
            team_name="Test Team",
            team_id="test_team",
            is_home=True,
            computed_at=computed,
        )

        data = team.model_dump()

        # Datetime préservé (pas de serialisation)
        assert isinstance(data["computed_at"], datetime)
        assert data["computed_at"] == computed

    def test_match_datetime_serialization(self):
        """ADR #003: MatchFeatures serialise computed_at et expires_at."""
        home = TeamFeatures(team_name="A", team_id="a", is_home=True)
        away = TeamFeatures(team_name="B", team_id="b", is_home=False)

        computed = datetime(2025, 12, 13, 22, 0, 0)
        expires = datetime(2025, 12, 14, 10, 0, 0)

        match = MatchFeatures(
            match_id="test_adr003_match",
            competition="Test League",
            season="2025-26",
            match_date=datetime(2025, 12, 15, 15, 0),
            home_team=home,
            away_team=away,
            computed_at=computed,
            expires_at=expires,
        )

        json_str = match.model_dump_json()

        # Serialisation ISO 8601
        assert '"computed_at":"2025-12-13T22:00:00"' in json_str
        assert '"expires_at":"2025-12-14T10:00:00"' in json_str

        # .model_dump() préserve
        data = match.model_dump()
        assert isinstance(data["computed_at"], datetime)
        assert isinstance(data["expires_at"], datetime)


class TestADR004AutoCalculatedFeatures:
    """Tests validant ADR #004 pour features.py.

    ADR #004: Pattern Hybrid pour auto-calculs.
    - Default sentinelle (None)
    - Auto-calcul si sentinelle détectée
    - Permet override si valeur fournie
    """

    def test_xg_differential_auto_calculated(self):
        """ADR #004: xg_differential auto-calculé depuis team features."""
        home = TeamFeatures(
            team_name="Team A",
            team_id="team_a",
            is_home=True,
            xg_per_90=1.8,
        )

        away = TeamFeatures(
            team_name="Team B",
            team_id="team_b",
            is_home=False,
            xg_per_90=1.3,
        )

        match = MatchFeatures(
            match_id="test_adr004_1",
            competition="Test League",
            season="2025-26",
            match_date=datetime.utcnow(),
            home_team=home,
            away_team=away,
            # xg_differential omis → None → auto-calculé
        )

        # Auto-calculé: 1.8 - 1.3 = 0.5
        assert match.xg_differential == pytest.approx(0.5, rel=1e-6)

    def test_xg_differential_can_be_overridden(self):
        """ADR #004: xg_differential peut être overridden si nécessaire."""
        home = TeamFeatures(
            team_name="Team A",
            team_id="team_a",
            is_home=True,
            xg_per_90=1.8,
        )

        away = TeamFeatures(
            team_name="Team B",
            team_id="team_b",
            is_home=False,
            xg_per_90=1.3,
        )

        match = MatchFeatures(
            match_id="test_adr004_2",
            competition="Test League",
            season="2025-26",
            match_date=datetime.utcnow(),
            home_team=home,
            away_team=away,
            xg_differential=0.42,  # Override explicite
        )

        # Valeur override préservée (pas de calcul)
        assert match.xg_differential == pytest.approx(0.42, rel=1e-6)

    def test_elo_differential_auto_calculated(self):
        """ADR #004: elo_differential auto-calculé depuis team features."""
        home = TeamFeatures(
            team_name="Team A",
            team_id="team_a",
            is_home=True,
            elo_rating=2000,
        )

        away = TeamFeatures(
            team_name="Team B",
            team_id="team_b",
            is_home=False,
            elo_rating=1950,
        )

        match = MatchFeatures(
            match_id="test_adr004_3",
            competition="Test League",
            season="2025-26",
            match_date=datetime.utcnow(),
            home_team=home,
            away_team=away,
            # elo_differential omis → None → auto-calculé
        )

        # Auto-calculé: 2000 - 1950 = 50
        assert match.elo_differential == 50

    def test_elo_differential_can_be_overridden(self):
        """ADR #004: elo_differential peut être overridden si nécessaire."""
        home = TeamFeatures(
            team_name="Team A",
            team_id="team_a",
            is_home=True,
            elo_rating=2000,
        )

        away = TeamFeatures(
            team_name="Team B",
            team_id="team_b",
            is_home=False,
            elo_rating=1950,
        )

        match = MatchFeatures(
            match_id="test_adr004_4",
            competition="Test League",
            season="2025-26",
            match_date=datetime.utcnow(),
            home_team=home,
            away_team=away,
            elo_differential=30,  # Override explicite
        )

        # Valeur override préservée (pas de calcul)
        assert match.elo_differential == 30

    def test_value_differential_auto_calculated(self):
        """ADR #004: value_differential auto-calculé depuis team features."""
        home = TeamFeatures(
            team_name="Team A",
            team_id="team_a",
            is_home=True,
            squad_value_millions=800.0,
        )

        away = TeamFeatures(
            team_name="Team B",
            team_id="team_b",
            is_home=False,
            squad_value_millions=600.0,
        )

        match = MatchFeatures(
            match_id="test_adr004_5",
            competition="Test League",
            season="2025-26",
            match_date=datetime.utcnow(),
            home_team=home,
            away_team=away,
            # value_differential omis → None → auto-calculé
        )

        # Auto-calculé: 800.0 - 600.0 = 200.0
        assert match.value_differential == pytest.approx(200.0, rel=1e-6)

    def test_value_differential_can_be_overridden(self):
        """ADR #004: value_differential peut être overridden si nécessaire."""
        home = TeamFeatures(
            team_name="Team A",
            team_id="team_a",
            is_home=True,
            squad_value_millions=800.0,
        )

        away = TeamFeatures(
            team_name="Team B",
            team_id="team_b",
            is_home=False,
            squad_value_millions=600.0,
        )

        match = MatchFeatures(
            match_id="test_adr004_6",
            competition="Test League",
            season="2025-26",
            match_date=datetime.utcnow(),
            home_team=home,
            away_team=away,
            value_differential=150.0,  # Override explicite
        )

        # Valeur override préservée (pas de calcul)
        assert match.value_differential == pytest.approx(150.0, rel=1e-6)
