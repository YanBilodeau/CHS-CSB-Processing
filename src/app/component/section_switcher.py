"""
Section Switcher component module.

Contains the SectionSwitcherComponent for managing panel visibility
and section navigation in the UI.
"""

from nicegui import ui


class SectionSwitcherComponent:
    """Gère la visibilité des panneaux de section avec transition fluide."""

    def __init__(self) -> None:
        """Initialise le gestionnaire de sections."""
        self._panels: dict[str, ui.element] = {}
        self._section_labels: dict[str, str] = {}
        self.active_section: str = ""

    def register_section_labels(self, labels: dict[str, str]) -> None:
        """
        Enregistre les étiquettes de section.

        :param labels: Dictionnaire associant une clé interne à son étiquette affichée.
        :type labels: dict[str, str]
        """
        self._section_labels = labels

    def register_panel(self, section_label: str, panel: ui.element) -> None:
        """
        Enregistre un panneau pour une section donnée.

        :param section_label: Étiquette de la section.
        :type section_label: str
        :param panel: Élément UI du panneau.
        :type panel: ui.element
        """
        self._panels[section_label] = panel
        if not self.active_section:
            self.active_section = section_label

    def switch_to(self, section: str) -> None:
        """
        Bascule vers la section spécifiée avec une transition fluide.

        :param section: Étiquette de la section cible.
        :type section: str
        """
        if section == self.active_section:
            return

        # Hide current panel
        if self.active_section in self._panels:
            self._panels[self.active_section].classes(
                remove="section-panel-visible", add="section-panel-hidden"
            )

        # Show target panel
        if section in self._panels:
            self._panels[section].classes(
                remove="section-panel-hidden", add="section-panel-visible"
            )

        self.active_section = section
