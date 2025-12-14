"""
Brain API Package

Expose UnifiedBrain V2.8.0 via REST API
Endpoints: /api/v1/brain/*
"""

from .routes import router

__all__ = ["router"]
