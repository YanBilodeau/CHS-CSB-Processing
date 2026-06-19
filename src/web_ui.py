"""
This module provides a web graphical interface for processing bathymetric data files using NiceGUI.

It allows executing the same functionalities as the CLI but through a web interface.
"""

import i18n
from loguru import logger
from nicegui import ui

from app import (
    StatusDisplay,
    LogDisplay,
    StatusSection,
    LogSection,
    GuiType,
    UIRunner,
    DependencyContainer,
)
from app.component.header import HeaderComponent
from app.component.section_switcher import SectionSwitcherComponent
from app.component.theme_manager import ThemeManager
from app.component.process_panel import ProcessPanel
from app.component.convert_section import ConvertSection


LOGGER = logger.bind(name="CSB-Processing.UI")

# ── CSS for smooth section transitions ──────────────────────────────────
_SECTION_TRANSITION_CSS = """
<style>
.section-panel {
    transition: opacity 0.35s cubic-bezier(0.4, 0, 0.2, 1),
                transform 0.35s cubic-bezier(0.4, 0, 0.2, 1);
    will-change: opacity, transform;
}
.section-panel-hidden {
    opacity: 0;
    pointer-events: none;
    position: absolute;
    width: 100%;
    transform: translateY(8px);
}
.section-panel-visible {
    opacity: 1;
    pointer-events: auto;
    position: relative;
    transform: translateY(0);
}

/* ── Big action icons (Process / Convert) ── */
.big-action-btn .q-icon {
    font-size: 28px;
}
</style>
"""


class CSBProcessingUI:
    """Orchestrateur principal de l'interface utilisateur."""

    def __init__(
        self,
        section_switcher: SectionSwitcherComponent,
        theme_manager: ThemeManager,
        status_display: StatusDisplay,
        log_display: LogDisplay,
        process_panel: ProcessPanel,
        convert_section: ConvertSection,
    ):
        """
        Initialise l'interface utilisateur principale.

        :param section_switcher: Gestionnaire de navigation entre sections.
        :type section_switcher: SectionSwitcherComponent
        :param theme_manager: Gestionnaire de thème.
        :type theme_manager: ThemeManager
        :param status_display: Affichage du statut.
        :type status_display: StatusDisplay
        :param log_display: Affichage des logs.
        :type log_display: LogDisplay
        :param process_panel: Panneau de traitement.
        :type process_panel: ProcessPanel
        :param convert_section: Panneau de conversion.
        :type convert_section: ConvertSection
        """
        self.section_switcher = section_switcher
        self.theme_manager = theme_manager
        self.status_display = status_display
        self.log_display = log_display
        self.process_panel = process_panel
        self.convert_section = convert_section

    def create_ui(self):
        """Create the main UI with section switching via header menu."""
        self.theme_manager.add_theme_styles()
        ui.add_head_html(_SECTION_TRANSITION_CSS)

        # Register section labels in the switcher
        process_label = i18n.t("app.component.header.section_process")
        convert_label = i18n.t("app.component.header.section_convert")
        self.section_switcher.register_section_labels(
            {"process": process_label, "convert": convert_label}
        )

        # Main container with theme classes
        main_container = ui.card().classes(
            "w-full max-w-6xl mx-auto p-6 shadow-lg theme-container theme-light"
        )

        with main_container:
            # Header with section menu
            HeaderComponent(
                theme_manager=self.theme_manager,
                section_switcher=self.section_switcher,
            ).create()

            # Panel container — relative for absolute positioning of hidden panel
            with (
                ui.element("div").classes("relative w-full").style("min-height: 100px")
            ):
                # ── Process panel ──────────────────────────────────
                process_panel_element = self.process_panel.create()
                self.section_switcher.register_panel(
                    process_label, process_panel_element
                )

                # ── Convert panel ──────────────────────────────────
                convert_panel_element = self.convert_section.create()
                self.section_switcher.register_panel(
                    convert_label, convert_panel_element
                )

            # Shared sections (below panels)
            StatusSection(self.status_display).create()
            LogSection(self.log_display).create()


def main():
    """Main function to run the application."""
    container = DependencyContainer()

    main_ui = CSBProcessingUI(
        section_switcher=container.get_section_switcher(),
        theme_manager=container.get_theme_manager(),
        status_display=container.get_status_display(),
        log_display=container.get_log_display(),
        process_panel=container.get_process_panel(),
        convert_section=container.get_convert_section(),
    )

    runner = UIRunner(main_ui=main_ui, gui=GuiType.NATIVE)

    try:
        runner.run()

    except Exception as e:
        LOGGER.exception(e)
        LOGGER.error(i18n.t("web_ui.startup_error", error=str(e)))


if __name__ == "__main__":
    main()
