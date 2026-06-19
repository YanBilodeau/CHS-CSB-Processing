"""
Header Component module.

Contains the HeaderComponent for handling application header functionality.
"""

import i18n
from nicegui import ui

from .protocols import ThemeManagerProtocol
from .section_menu import SectionMenu
from .section_switcher import SectionSwitcherComponent


class HeaderComponent:
    """Component for application header."""

    def __init__(
        self,
        theme_manager: ThemeManagerProtocol,
        section_switcher: SectionSwitcherComponent | None = None,
    ):
        """
        Initialise le composant d'en-tête.

        :param theme_manager: Gestionnaire de thème.
        :type theme_manager: ThemeManagerProtocol
        :param section_switcher: Gestionnaire de navigation entre sections.
        :type section_switcher: SectionSwitcherComponent | None
        """
        self.theme_manager = theme_manager
        self.section_switcher = section_switcher
        self._section_menu: SectionMenu | None = None

    def create(self):
        """Create the header section."""
        with ui.row().classes("w-full justify-between items-center mb-6"):
            # Left zone: section menu + theme button
            with ui.row().classes("items-center gap-2"):
                if self.section_switcher:
                    labels = self.section_switcher._section_labels
                    sections = list(labels.values())
                    if sections:
                        self._section_menu = SectionMenu(
                            sections=sections,
                            active_section=self.section_switcher.active_section,
                            on_change=self.section_switcher.switch_to,
                        )
                        self._section_menu.create()
                self.theme_manager.create_theme_button()

            # Page title - centered
            with ui.column().classes("flex-1 items-center"):
                ui.html(
                    f"<h1 class='text-4xl font-bold text-center text-blue-600'>"
                    f"{i18n.t('app.component.header.title')}</h1>",
                    sanitize=False,
                )

            # Spacer for symmetry (right)
            ui.element().classes("w-32")

        ui.markdown(i18n.t("app.component.header.subtitle")).classes(
            "text-center text-gray-600 mb-6"
        )
