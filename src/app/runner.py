"""
Application runner for CSB Processing UI.
"""

from typing import Protocol

from loguru import logger
from nicegui import ui

from . import network_helper


class MainUIProtocol(Protocol):
    """Protocol for the main UI component."""

    def create_ui(self) -> None:
        """Create the main UI components."""
        ...


LOGGER = logger.bind(name="CSB-Processing.Runner")


class UIRunner:
    """Runner for the CSB Processing UI application."""

    def __init__(self, main_ui: MainUIProtocol) -> None:
        """
        Initialize the UIRunner with the main UI component.

        """
        self.app = main_ui

    def run(self) -> None:
        """Run the CSB Processing UI application."""
        try:
            self.app.create_ui()

            # Find a free port
            port = UIRunner._find_available_port()

            ui.run(
                title="CSB Processing Tool",
                port=port,
                show=True,
                reload=False,
                favicon="🌊",
            )

        except Exception as e:
            LOGGER.exception(e)
            LOGGER.error(f"Error running the application: {e}")

    @staticmethod
    def _find_available_port():
        """Find an available port for the application."""
        try:
            port = network_helper.find_free_port(8080)
            LOGGER.debug(f"Using port {port}")
            return port

        except RuntimeError as e:
            LOGGER.error(f"Could not find free port: {e}")
            # Try with a higher range if default range fails
            try:
                port = network_helper.find_free_port(9000, 50)
                LOGGER.debug(f"Using fallback port {port}")
                return port

            except RuntimeError:
                port = 0  # Let the system choose a port
                LOGGER.debug("Using system-assigned port")
                return port
