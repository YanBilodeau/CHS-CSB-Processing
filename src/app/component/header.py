"""
Header Component module.

Contains the HeaderComponent for handling application header functionality.
"""

import i18n
from nicegui import ui

from .protocols import ThemeManagerProtocol


class HeaderComponent:
    """Component for application header."""

    def __init__(self, theme_manager: ThemeManagerProtocol):
        self.theme_manager = theme_manager

    def create(self):
        """Create the header section."""
        with ui.row().classes("w-full justify-between items-center mb-6"):
            # Theme selector with sun/moon icon
            with ui.row().classes("items-center gap-2"):
                self.theme_manager.create_theme_button()

            # Page title - centered
            with ui.column().classes("flex-1 items-center"):
                ui.html(
                    f"<h1 class='text-4xl font-bold text-center text-blue-600'>"
                    f"{i18n.t('app.component.header.title')}</h1>",
                    sanitize=False,
                )

            # Spacer for symmetry
            ui.element().classes("w-32")

        ui.markdown(i18n.t("app.component.header.subtitle")).classes(
            "text-center text-gray-600 mb-6"
        )
