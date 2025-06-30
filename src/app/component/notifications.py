from typing import Literal

from nicegui import ui


def show_notification(
    message: str,
    type: Literal["info", "positive", "negative", "warning", "ongoing"] = "info",
) -> None:
    """Display a notification message."""
    ui.notification(message, type=type)
    ui.update()  # Ensure the UI updates immediately
