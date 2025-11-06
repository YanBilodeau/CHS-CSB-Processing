from typing import Literal

from nicegui import ui
from loguru import logger

LOGGER = logger.bind(name="CSB-Processing.Notifications")


def show_notification(
    message: str,
    type: Literal["info", "positive", "negative", "warning", "ongoing"] = "info",
) -> None:
    """Display a notification message."""
    try:
        ui.notification(message, type=type)
        ui.update()  # Ensure the UI updates immediately

    except RuntimeError as e:
        LOGGER.warning(f"Failed to show notification: {e}")

