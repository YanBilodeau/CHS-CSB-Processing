"""
UI sections for CSB Processing application.
"""

from typing import Callable

from nicegui import ui

from .log_display import LogDisplay
from .status_display import StatusDisplay


class ProcessingSection:
    """Component for the processing section."""

    def __init__(self, process_callback: callable):
        self.process_callback = process_callback

    def create(self):
        """Create processing section."""
        ui.separator()
        with ui.row().classes("w-full justify-center mt-6"):
            (
                ui.button(
                    "Process files",
                    on_click=self.process_callback,
                    icon="play_arrow",
                )
                .props("size=lg color=primary")
                .classes("px-8 py-2")
            )


class StatusSection:
    """Component for the status section."""

    def __init__(self, status_display: StatusDisplay):
        self.status_display = status_display

    def create(self):
        """Create status section."""
        ui.separator()
        ui.label("Processing Status").classes("text-lg font-bold mt-4")

        # Create status display component
        self.status_display.create()


class LogSection:
    """Component for the log section."""

    def __init__(self, log_display: LogDisplay):
        self.log_display = log_display

    def create(self):
        """Create log output section."""
        ui.separator()

        # Create log display component
        self.log_display.create()
