"""
Section Menu component module.

Contains the SectionMenu for handling section navigation in the header.
"""

from typing import Callable

import i18n
from nicegui import ui


class SectionMenu:
    """Dropdown menu for switching between application sections."""

    def __init__(
        self,
        sections: list[str],
        active_section: str | None = None,
        on_change: Callable[[str], None] | None = None,
    ):
        """
        Initialise le menu de sélection de section.

        :param sections: Liste des étiquettes de section.
        :type sections: list[str]
        :param active_section: Section active au démarrage (première section si ``None``).
        :type active_section: str | None
        :param on_change: Callback appelé avec l'étiquette de la section sélectionnée.
        :type on_change: Callable[[str], None] | None
        """
        self.on_change = on_change
        self.active_section = active_section or (sections[0] if sections else "")
        self._sections = sections
        self._menu: ui.menu | None = None
        self._items: dict[str, ui.menu_item] = {}

    def create(self) -> None:
        """Crée le bouton et le menu déroulant."""
        with (
            ui.button(
                icon="view_list",
                color=None,
            )
            .props("flat round size=lg")
            .tooltip(i18n.t("app.component.header.section_menu"))
        ):
            with ui.menu() as self._menu:
                self._build_items()

    def _build_items(self) -> None:
        """Construit les items du menu."""
        for section in self._sections:
            item = ui.menu_item(
                section,
                on_click=lambda _, s=section: self.select(s),
            )
            self._items[section] = item
            if section == self.active_section:
                item.props("active")

    def select(self, section: str) -> None:
        """
        Sélectionne une section et notifie le callback.

        :param section: Étiquette de la section à activer.
        :type section: str
        """
        if section == self.active_section:
            return
        self._update_active(section)
        self.active_section = section
        if self.on_change:
            self.on_change(section)
        if self._menu:
            self._menu.close()

    def _update_active(self, new_section: str) -> None:
        """Met à jour l'état visuel actif/inactif des items."""
        for s, item in self._items.items():
            if s == new_section:
                item.props("active")
            else:
                item.props(remove="active")
