"""
Process Panel component module.

Contains the ProcessPanel for handling the Process section UI
and delegating processing execution to ProcessingHandler.
"""

import i18n
from nicegui import ui
from loguru import logger

LOGGER = logger.bind(name="CSB-Processing.ProcessPanel")


class ProcessPanel:
    """Panneau de traitement — UI et orchestration du traitement."""

    def __init__(
        self,
        processing_handler,
        file_selection_component,
        options_component,
        config_manager,
        ui_event_handler,
    ) -> None:
        """
        Initialise le panneau de traitement.

        :param processing_handler: Gestionnaire de traitement (ProcessingHandler).
        :param file_selection_component: Composant de sélection de fichiers.
        :param options_component: Composant d'options de traitement.
        :param config_manager: Gestionnaire de configuration partagé.
        :param ui_event_handler: Gestionnaire d'événements UI.
        """
        self.processing_handler = processing_handler
        self.file_selection_component = file_selection_component
        self.options_component = options_component
        self.config_manager = config_manager
        self.ui_event_handler = ui_event_handler

        # UI state
        self.panel: ui.element | None = None
        self.process_button: ui.button | None = None

    def create(self) -> ui.element:
        """
        Crée le panneau de traitement complet.

        :return: L'élément racine du panneau.
        :rtype: ui.element
        """
        self.panel = ui.element("div").classes(
            "section-panel section-panel-visible w-full"
        )
        with self.panel:
            self.file_selection_component.create()
            self.options_component.create()
            self._create_process_button()

        return self.panel

    def _create_process_button(self) -> None:
        """Crée le bouton de traitement."""
        ui.separator()
        with ui.row().classes("w-full justify-center mt-6"):
            self.process_button = (
                ui.button(
                    i18n.t("app.component.ui_sections.process_button"),
                    on_click=self._on_click,
                    icon="play_arrow",
                )
                .props("size=lg color=primary")
                .classes("px-8 py-2 big-action-btn")
            )

    async def _on_click(self, *args) -> None:
        """Wrapper qui désactive le bouton, exécute le traitement, puis le réactive."""
        if self.process_button:
            try:
                self.process_button.disable()
            except Exception:
                self.process_button.props("disabled")

        try:
            await self.processing_handler.process_files()
        finally:
            if self.process_button:
                try:
                    self.process_button.enable()
                except (Exception, RuntimeError):
                    pass

    def remove_file(self, file_info: dict) -> bool:
        """
        Retire un fichier de la liste de traitement.

        :param file_info: Informations du fichier à retirer.
        :type file_info: dict
        :return: True si le retrait a réussi.
        :rtype: bool
        """
        return self.ui_event_handler.remove_file(
            file_info, self.file_selection_component
        )
