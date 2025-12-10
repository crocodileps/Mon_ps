"""
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║  QUANTUM LOADERS - JSON → Dataclasses                                                ║
║  Version: 2.0                                                                        ║
║  Architecture Mon_PS - Chess Engine V2.0                                             ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝

Installation: /home/Mon_ps/quantum/loaders/__init__.py

Usage:
    from quantum.loaders import load_team, load_all_teams, get_team
    
    # Charger une équipe complète
    liverpool = load_team("Liverpool")
    
    # Accès aux données
    print(liverpool.overall_strength_score)
    print(liverpool.context.attack_profile)
    print(liverpool.defense.exploitable_weaknesses)
    print(liverpool.variance.betting_signal)
    
    # Charger toutes les équipes
    all_teams = load_all_teams()
    premier_league = load_all_teams(league="Premier League")
"""

# ═══════════════════════════════════════════════════════════════════════════════════════
# BASE UTILITIES
# ═══════════════════════════════════════════════════════════════════════════════════════

from .base_loader import (
    # File operations
    load_json,
    save_json,
    
    # Name normalization
    normalize_team_name,
    get_team_key,
    TEAM_ALIASES,
    
    # Value conversion
    safe_float,
    safe_int,
    safe_bool,
    clamp,
    parse_datetime,
    
    # Data quality
    validate_required_fields,
    calculate_data_quality,
    
    # Cache & Index
    DataIndex,
    get_global_index,
    
    # Paths
    DATA_ROOT,
    QUANTUM_DATA,
    DEFENSE_DATA,
    GOALKEEPER_DATA,
    COACH_DATA,
    VARIANCE_DATA,
)

# ═══════════════════════════════════════════════════════════════════════════════════════
# INDIVIDUAL LOADERS
# ═══════════════════════════════════════════════════════════════════════════════════════

from .context_loader import (
    load_context_dna,
    load_all_context_dna,
    find_team_context_data,
)

from .defense_loader import (
    load_defense_dna,
    load_all_defense_dna,
    find_team_defense_data,
)

from .goalkeeper_loader import (
    load_goalkeeper_dna,
    load_all_goalkeeper_dna,
    find_team_goalkeeper_data,
)

from .variance_loader import (
    load_variance_dna,
    load_all_variance_dna,
    find_team_variance_data,
)

from .coach_loader import (
    load_coach_dna,
    load_all_coach_dna,
    find_team_coach_data,
)

# ═══════════════════════════════════════════════════════════════════════════════════════
# MAIN TEAM LOADER
# ═══════════════════════════════════════════════════════════════════════════════════════

from .team_loader import (
    # Main functions
    load_team,
    get_team,
    load_all_teams,
    load_teams_by_league,
    
    # Helpers
    load_team_identity,
    build_exploit_profile,
    
    # Batch operations
    preload_league,
    list_available_teams,
    clear_cache,
)

# ═══════════════════════════════════════════════════════════════════════════════════════
# ALL EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Main API
    "load_team",
    "get_team",
    "load_all_teams",
    "load_teams_by_league",
    
    # Individual loaders
    "load_context_dna",
    "load_defense_dna",
    "load_goalkeeper_dna",
    "load_variance_dna",
    "load_coach_dna",
    
    # Batch loaders
    "load_all_context_dna",
    "load_all_defense_dna",
    "load_all_goalkeeper_dna",
    "load_all_variance_dna",
    "load_all_coach_dna",
    
    # Finders
    "find_team_context_data",
    "find_team_defense_data",
    "find_team_goalkeeper_data",
    "find_team_variance_data",
    "find_team_coach_data",
    
    # Helpers
    "load_team_identity",
    "build_exploit_profile",
    
    # Utilities
    "normalize_team_name",
    "get_team_key",
    "load_json",
    "save_json",
    "safe_float",
    "safe_int",
    "clamp",
    
    # Cache
    "preload_league",
    "list_available_teams",
    "clear_cache",
    "get_global_index",
    
    # Paths
    "DATA_ROOT",
    "QUANTUM_DATA",
]

# Version info
__version__ = "2.0"
