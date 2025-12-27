"""
FORTRESS V38 - SECURITY
=======================

Sécurité, coûts, checkpoints et retry policies.

Modules:
- system_guardian: Gardien du système (budget Claude)
- cost_tracker: Suivi des coûts API (Singleton Thread-Safe)
- checkpoint_manager: Gestion de l'idempotence
- retry_policy: Exponential backoff pour API calls

Version: 1.0.0
"""

# ═══════════════════════════════════════════════════════════════
# SYSTEM GUARDIAN
# ═══════════════════════════════════════════════════════════════

from .system_guardian import (
    SystemGuardian,
    get_guardian,
)

# ═══════════════════════════════════════════════════════════════
# COST TRACKER
# ═══════════════════════════════════════════════════════════════

from .cost_tracker import CostTracker

# ═══════════════════════════════════════════════════════════════
# CHECKPOINT MANAGER
# ═══════════════════════════════════════════════════════════════

from .checkpoint_manager import CheckpointManager

# ═══════════════════════════════════════════════════════════════
# RETRY POLICY
# ═══════════════════════════════════════════════════════════════

from .retry_policy import (
    RetryConfig,
    call_with_retry,
    get_retry_info,
)

# ═══════════════════════════════════════════════════════════════
# EXPORTS PUBLICS
# ═══════════════════════════════════════════════════════════════

__all__ = [
    # System Guardian
    "SystemGuardian",
    "get_guardian",
    # Cost Tracker
    "CostTracker",
    # Checkpoint Manager
    "CheckpointManager",
    # Retry Policy
    "RetryConfig",
    "call_with_retry",
    "get_retry_info",
]

__version__ = "1.0.0"
