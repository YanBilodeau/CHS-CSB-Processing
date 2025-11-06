"""
UI sections for CSB Processing application.
"""

import asyncio
import inspect
from typing import Callable

from nicegui import ui

from .log_display import LogDisplay
from .status_display import StatusDisplay


class ProcessingSection:
    """Component for the processing section."""

    def __init__(self, process_callback: Callable):
        self.process_callback = process_callback
        self.process_button = None

    def create(self):
        """Create processing section."""
        ui.separator()
        with ui.row().classes("w-full justify-center mt-6"):
            self.process_button = (
                ui.button(
                    "Process files",
                    on_click=self._on_click,
                    icon="play_arrow",
                )
                .props("size=lg color=primary")
                .classes("px-8 py-2")
            )

    async def _on_click(self, *args):
        """Wrapper that disables the button, runs the callback, then re-enables the button."""
        if self.process_button:
            # disable the button
            try:
                self.process_button.disable()
            except Exception:
                # fallback si disable() n'est pas disponible
                self.process_button.props("disabled")

        cb = self.process_callback
        try:
            if inspect.iscoroutinefunction(cb):
                await cb()
            else:
                # exécute la fonction synchrone dans un thread pour ne pas bloquer l'event loop
                await asyncio.to_thread(cb)
        finally:
            # réactiver le bouton (seulement si le client existe encore)
            if self.process_button:
                try:
                    self.process_button.enable()
                except (Exception, RuntimeError):
                    pass


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
