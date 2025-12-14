"""Custom exceptions for Mon_PS API.

Hedge Fund Grade: Exception hierarchy bien définie.
"""

from fastapi import status


class MonPSException(Exception):
    """Base exception for all Mon_PS errors."""

    def __init__(
        self, detail: str, status_code: int = 500, error_code: str = "MONPS_ERROR"
    ):
        self.detail = detail
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(self.detail)


class LowConfidenceError(MonPSException):
    """Raised when prediction confidence is below threshold."""

    def __init__(self, detail: str = "Prediction confidence below threshold"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="LOW_CONFIDENCE",
        )


class UnifiedBrainError(MonPSException):
    """Raised when UnifiedBrain fails."""

    def __init__(self, detail: str = "UnifiedBrain processing failed"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="BRAIN_ERROR",
        )


class MatchNotFoundError(MonPSException):
    """Raised when match is not found."""

    def __init__(self, match_id: str):
        super().__init__(
            detail=f"Match not found: {match_id}",
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="MATCH_NOT_FOUND",
        )


class InvalidDateError(MonPSException):
    """Raised when date is invalid (past, too far future, etc.)."""

    def __init__(self, detail: str = "Invalid date"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="INVALID_DATE",
        )
