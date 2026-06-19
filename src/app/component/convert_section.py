"""
Convert Section component module.

Contains the ConvertSection for handling the Convert panel UI
and delegating conversion execution to ConvertHandler.
"""

from pathlib import Path

import i18n
from nicegui import ui, app
from loguru import logger

LOGGER = logger.bind(name="CSB-Processing.ConvertSection")


class ConvertSection:
    """Panneau de conversion — UI et orchestration de la conversion."""

    def __init__(
        self,
        convert_handler,
        convert_options_component,
        convert_file_selection_component,
        convert_file_display,
        config_manager,
    ) -> None:
        """
        Initialise le panneau de conversion.

        :param convert_handler: Gestionnaire de conversion (ConvertHandler).
        :param convert_options_component: Composant d'options de conversion.
        :param convert_file_selection_component: Composant de sélection de fichiers.
        :param convert_file_display: Affichage des fichiers de conversion.
        :param config_manager: Gestionnaire de configuration partagé.
        """
        self.convert_handler = convert_handler
        self.convert_options_component = convert_options_component
        self.convert_file_selection_component = convert_file_selection_component
        self.convert_file_display = convert_file_display
        self.config_manager = config_manager

        # UI state
        self.panel: ui.element | None = None
        self.convert_button: ui.button | None = None
        self.convert_output_input: ui.input | None = None
        self.convert_output_warning_label: ui.label | None = None

    def create(self) -> ui.element:
        """
        Crée le panneau de conversion complet.

        :return: L'élément racine du panneau.
        :rtype: ui.element
        """
        self.panel = ui.element("div").classes(
            "section-panel section-panel-hidden w-full"
        )
        with self.panel:
            self.convert_file_selection_component.create()
            self._create_output_section()
            self.convert_options_component.create()

            # Bouton de conversion
            ui.separator()
            with ui.row().classes("w-full justify-center mt-6"):
                self.convert_button = (
                    ui.button(
                        i18n.t("app.component.ui_sections.convert_button"),
                        on_click=self._convert_files,
                        icon="swap_horiz",
                    )
                    .props("size=lg color=secondary")
                    .classes("px-8 py-2 big-action-btn")
                )

        return self.panel

    def _create_output_section(self) -> None:
        """Crée la section de sélection du répertoire de sortie."""
        ui.separator()
        ui.label(i18n.t("app.component.ui_sections.convert_output_dir_label")).classes(
            "text-lg font-bold text-red-600 mt-4"
        )

        with ui.row().classes("w-full gap-2"):
            self.convert_output_input = (
                ui.input(
                    placeholder=i18n.t(
                        "app.component.ui_sections.convert_output_dir_placeholder"
                    ),
                )
                .classes("flex-1")
                .on("update:model-value", self._handle_output_path_change)
            )

            if self.config_manager and self.config_manager.output_path != Path():
                self.convert_output_input.value = str(self.config_manager.output_path)

            ui.button(
                icon="folder",
                on_click=self._handle_select_output_directory,
            ).props("color=primary outline").tooltip(
                i18n.t("app.component.ui_sections.convert_output_dir_select_tooltip")
            )

        self.convert_output_warning_label = ui.label(
            i18n.t("app.component.ui_sections.convert_output_dir_warning")
        ).classes("text-sm text-red-500")

    def _handle_output_path_change(self, e) -> None:
        """Gère le changement du chemin de sortie."""
        self.config_manager.update_output_path(e.args[0] if e.args else "")
        if self.convert_output_warning_label:
            if e.args and e.args[0] and e.args[0].strip():
                self.convert_output_warning_label.style("visibility: hidden")
            else:
                self.convert_output_warning_label.style("visibility: visible")

    async def _handle_select_output_directory(self) -> None:
        """Gère la sélection du répertoire de sortie."""
        try:
            initial_dir = (
                str(self.config_manager.output_path)
                if self.config_manager.output_path != Path()
                else ""
            )
            result = await app.native.main_window.create_file_dialog(
                dialog_type=20,
                allow_multiple=True,
                directory=initial_dir,
            )
            if result:
                selected = result[0] if isinstance(result, (list, tuple)) else result
                selected_str = str(selected).strip('"')
                self.config_manager.update_output_path(selected_str)
                if self.convert_output_input:
                    self.convert_output_input.value = selected_str
                if self.convert_output_warning_label and selected_str.strip():
                    self.convert_output_warning_label.style("visibility: hidden")
        except Exception as ex:
            LOGGER.error(f"Error in convert output directory dialog: {ex}")

    async def _convert_files(self) -> None:
        """Lance la conversion via ConvertHandler."""
        self.convert_handler.selected_formats = (
            self.convert_options_component.selected_formats
        )
        self.convert_handler.group_by_iho_order = (
            self.convert_options_component.group_by_iho_order
        )

        if self.convert_button:
            try:
                self.convert_button.disable()
            except Exception:
                self.convert_button.props("disabled")

        try:
            await self.convert_handler.convert_files()
        finally:
            if self.convert_button:
                try:
                    self.convert_button.enable()
                except (Exception, RuntimeError):
                    pass

    def remove_file(self, file_info: dict) -> bool:
        """
        Retire un fichier de la liste de conversion.

        :param file_info: Informations du fichier à retirer.
        :type file_info: dict
        :return: True si le retrait a réussi.
        :rtype: bool
        """
        self.convert_handler.file_manager.remove_file(file_info)
        self.convert_file_display.update()
        return True
