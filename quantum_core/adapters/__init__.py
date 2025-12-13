"""
Adapters - Connecteurs entre systemes
Pattern: Adapter
Principe: Exposer une interface connue avec une nouvelle implementation.
"""

from .data_hub_adapter import DataHubAdapter, get_data_hub_adapter

__all__ = ["DataHubAdapter", "get_data_hub_adapter"]
