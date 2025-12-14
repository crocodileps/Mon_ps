"""Tests for FastAPI Lifespan Events - Application Lifecycle.

Validates:
- Startup events (logging, initialization)
- Shutdown events (cleanup, graceful termination)
- State management during lifecycle
- Error handling in startup/shutdown

Critical for production: Ensures application starts/stops cleanly.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi import FastAPI

from quantum_core.api.lifespan import lifespan


# ─────────────────────────────────────────────────────────────────────────
# TESTS - Startup Events
# ─────────────────────────────────────────────────────────────────────────


class TestLifespanStartup:
    """Tests for application startup events."""

    @pytest.mark.anyio
    async def test_startup_executes_successfully(self):
        """Test that startup completes without errors."""
        app = FastAPI()

        # Mock dependencies to avoid real initialization
        with patch("quantum_core.api.lifespan.get_settings"), patch(
            "quantum_core.api.lifespan.setup_logging"
        ), patch("quantum_core.api.lifespan.get_prediction_service"):

            # Execute lifespan startup
            async with lifespan(app):
                # If we reach here, startup succeeded
                assert True

    @pytest.mark.anyio
    async def test_startup_logs_are_emitted(self):
        """Test that startup emits log messages.

        Critical for monitoring: Startup logs indicate healthy boot.
        """
        app = FastAPI()

        with patch("quantum_core.api.lifespan.logger") as mock_logger, patch(
            "quantum_core.api.lifespan.get_settings"
        ), patch("quantum_core.api.lifespan.setup_logging"), patch(
            "quantum_core.api.lifespan.get_prediction_service"
        ):

            async with lifespan(app):
                # Verify startup log was emitted
                mock_logger.info.assert_any_call(
                    "🚀 Starting Mon_PS API - Hedge Fund Grade 2.0"
                )

    @pytest.mark.anyio
    async def test_startup_initializes_settings(self):
        """Test that startup loads settings correctly."""
        app = FastAPI()

        with patch(
            "quantum_core.api.lifespan.get_settings"
        ) as mock_get_settings, patch("quantum_core.api.lifespan.setup_logging"), patch(
            "quantum_core.api.lifespan.get_prediction_service"
        ):

            mock_settings = MagicMock()
            mock_settings.environment = "test"
            mock_settings.debug = False
            mock_get_settings.return_value = mock_settings

            async with lifespan(app):
                # Verify settings were loaded
                mock_get_settings.assert_called_once()

    @pytest.mark.anyio
    async def test_startup_initializes_services(self):
        """Test that startup initializes PredictionService."""
        app = FastAPI()

        with patch("quantum_core.api.lifespan.get_settings"), patch(
            "quantum_core.api.lifespan.setup_logging"
        ), patch("quantum_core.api.lifespan.get_prediction_service") as mock_service:

            async with lifespan(app):
                # Verify service was initialized
                mock_service.assert_called_once()

    @pytest.mark.anyio
    async def test_startup_handles_errors_gracefully(self):
        """Test that startup errors are logged but propagate.

        Critical: Startup failures should be visible.
        """
        app = FastAPI()

        with patch(
            "quantum_core.api.lifespan.get_settings"
        ) as mock_get_settings, patch("quantum_core.api.lifespan.setup_logging"), patch(
            "quantum_core.api.lifespan.get_prediction_service"
        ):

            mock_get_settings.side_effect = Exception("Settings load failed")

            # Startup should propagate error
            with pytest.raises(Exception, match="Settings load failed"):
                async with lifespan(app):
                    pass


# ─────────────────────────────────────────────────────────────────────────
# TESTS - Shutdown Events
# ─────────────────────────────────────────────────────────────────────────


class TestLifespanShutdown:
    """Tests for application shutdown events."""

    @pytest.mark.anyio
    async def test_shutdown_executes_successfully(self):
        """Test that shutdown completes without errors."""
        app = FastAPI()

        with patch("quantum_core.api.lifespan.get_settings"), patch(
            "quantum_core.api.lifespan.setup_logging"
        ), patch("quantum_core.api.lifespan.get_prediction_service"), patch(
            "quantum_core.api.lifespan.cleanup_services"
        ):

            # Execute full lifecycle (startup + shutdown)
            async with lifespan(app):
                pass  # Exit context triggers shutdown

            # If we reach here, shutdown succeeded
            assert True

    @pytest.mark.anyio
    async def test_shutdown_logs_are_emitted(self):
        """Test that shutdown emits log messages.

        Critical for monitoring: Shutdown logs indicate clean termination.
        """
        app = FastAPI()

        with patch("quantum_core.api.lifespan.logger") as mock_logger, patch(
            "quantum_core.api.lifespan.get_settings"
        ), patch("quantum_core.api.lifespan.setup_logging"), patch(
            "quantum_core.api.lifespan.get_prediction_service"
        ), patch(
            "quantum_core.api.lifespan.cleanup_services"
        ):

            async with lifespan(app):
                pass  # Exit triggers shutdown

            # Verify shutdown log was emitted
            mock_logger.info.assert_any_call("👋 Shutting down Mon_PS API")

    @pytest.mark.anyio
    async def test_shutdown_cleanup_runs(self):
        """Test that cleanup tasks run on shutdown."""
        app = FastAPI()

        with patch("quantum_core.api.lifespan.get_settings"), patch(
            "quantum_core.api.lifespan.setup_logging"
        ), patch("quantum_core.api.lifespan.get_prediction_service"), patch(
            "quantum_core.api.lifespan.cleanup_services"
        ) as mock_cleanup:

            async with lifespan(app):
                pass  # Exit triggers shutdown

            # Verify cleanup was called
            mock_cleanup.assert_called_once()

    @pytest.mark.anyio
    async def test_shutdown_handles_errors_gracefully(self):
        """Test that shutdown errors are logged but don't prevent termination.

        Critical: Shutdown failures shouldn't hang application.
        """
        app = FastAPI()

        with patch("quantum_core.api.lifespan.logger") as mock_logger, patch(
            "quantum_core.api.lifespan.get_settings"
        ), patch("quantum_core.api.lifespan.setup_logging"), patch(
            "quantum_core.api.lifespan.get_prediction_service"
        ), patch(
            "quantum_core.api.lifespan.cleanup_services"
        ) as mock_cleanup:

            mock_cleanup.side_effect = Exception("Cleanup failed")

            # Shutdown error should be handled gracefully
            async with lifespan(app):
                pass

            # Verify error was logged (exception method)
            mock_logger.exception.assert_called_once()


# ─────────────────────────────────────────────────────────────────────────
# TESTS - State Management
# ─────────────────────────────────────────────────────────────────────────


class TestLifespanStateManagement:
    """Tests for state management during lifecycle."""

    @pytest.mark.anyio
    async def test_app_state_available_during_lifespan(self):
        """Test that app state is accessible during lifespan."""
        app = FastAPI()
        app.state.test_value = None

        with patch("quantum_core.api.lifespan.get_settings"), patch(
            "quantum_core.api.lifespan.setup_logging"
        ), patch("quantum_core.api.lifespan.get_prediction_service"), patch(
            "quantum_core.api.lifespan.cleanup_services"
        ):

            async with lifespan(app):
                # Should be able to access/modify app state
                app.state.test_value = "initialized"
                assert app.state.test_value == "initialized"

    @pytest.mark.anyio
    async def test_multiple_lifespan_cycles(self):
        """Test that lifespan can be reused across multiple cycles.

        Edge case: Some test suites restart app multiple times.
        """
        app = FastAPI()

        with patch("quantum_core.api.lifespan.get_settings"), patch(
            "quantum_core.api.lifespan.setup_logging"
        ), patch("quantum_core.api.lifespan.get_prediction_service"), patch(
            "quantum_core.api.lifespan.cleanup_services"
        ):

            # Cycle 1
            async with lifespan(app):
                app.state.cycle = 1

            # Cycle 2
            async with lifespan(app):
                app.state.cycle = 2

            # Both cycles should complete successfully
            assert True
