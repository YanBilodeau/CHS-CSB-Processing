"""
Container for dependency injection.
"""

from app import (
    ConfigManager,
    FileManager,
    Validator,
    ThemeManager,
    FileOperations,
    UILogHandler,
    LogDisplay,
    StatusDisplay,
    FileDisplay,
    FileSelectionComponentNative,
    UIEventHandler,
    ConvertHandler,
    ConvertOptionsComponent,
    OptionsComponent,
    ProcessingHandler,
)
from app.component.section_switcher import SectionSwitcherComponent
from app.component.process_panel import ProcessPanel
from app.component.convert_section import ConvertSection


class DependencyContainer:
    """Conteneur pour l'injection de dépendance."""

    def __init__(self):
        self._instances = {}

    def get_config_manager(self) -> ConfigManager:
        if "config_manager" not in self._instances:
            self._instances["config_manager"] = ConfigManager()

        return self._instances["config_manager"]

    def get_file_manager(self) -> FileManager:
        if "file_manager" not in self._instances:
            self._instances["file_manager"] = FileManager()

        return self._instances["file_manager"]

    def get_validator(self) -> Validator:
        if "validator" not in self._instances:
            self._instances["validator"] = Validator(
                self.get_file_manager().get_files, self.get_config_manager()
            )

        return self._instances["validator"]

    def get_theme_manager(self) -> ThemeManager:
        if "theme_manager" not in self._instances:
            self._instances["theme_manager"] = ThemeManager(dark_mode=True)

        return self._instances["theme_manager"]

    def get_file_operations(self) -> FileOperations:
        if "file_operations" not in self._instances:
            self._instances["file_operations"] = FileOperations(
                self.get_config_manager(), self.get_file_manager(), self.get_validator()
            )

        return self._instances["file_operations"]

    def get_log_handler(self) -> UILogHandler:
        if "log_handler" not in self._instances:
            handler = UILogHandler()
            handler.setup_logger()
            self._instances["log_handler"] = handler

        return self._instances["log_handler"]

    def get_log_display(self) -> LogDisplay:
        if "log_display" not in self._instances:
            self._instances["log_display"] = LogDisplay(self.get_log_handler())

        return self._instances["log_display"]

    def get_status_display(self) -> StatusDisplay:
        if "status_display" not in self._instances:
            self._instances["status_display"] = StatusDisplay()

        return self._instances["status_display"]

    def get_ui_event_handler(self) -> UIEventHandler:
        if "ui_event_handler" not in self._instances:
            self._instances["ui_event_handler"] = UIEventHandler(
                self.get_config_manager(),
                self.get_file_operations(),
                self.get_validator(),
                log_display=self.get_log_display(),
            )

        return self._instances["ui_event_handler"]

    def get_file_display(self) -> FileDisplay:
        if "file_display" not in self._instances:
            self._instances["file_display"] = FileDisplay(
                get_files_callback=self.get_file_manager().get_files,
                remove_callback=None,
            )

        return self._instances["file_display"]

    def get_file_selection_component(self) -> FileSelectionComponentNative:
        if "file_selection_component" not in self._instances:
            self._instances["file_selection_component"] = FileSelectionComponentNative(
                self.get_file_manager(), self.get_validator(), self.get_file_display()
            )

        return self._instances["file_selection_component"]

    def get_convert_file_manager(self) -> FileManager:
        """Retourne un FileManager pour la section Convert."""
        if "convert_file_manager" not in self._instances:
            self._instances["convert_file_manager"] = FileManager(
                allowed_extensions={".gpkg", ".geojson"},
                allow_numeric=False,
            )

        return self._instances["convert_file_manager"]

    def get_convert_file_selection_component(self) -> FileSelectionComponentNative:
        """Retourne le composant de sélection de fichiers pour la section Convert."""
        if "convert_file_selection_component" not in self._instances:
            convert_file_manager = self.get_convert_file_manager()
            convert_validator = Validator(
                convert_file_manager.get_files, self.get_config_manager()
            )
            convert_file_display = FileDisplay(
                get_files_callback=convert_file_manager.get_files,
                remove_callback=None,
            )
            self._instances["convert_file_display"] = convert_file_display
            self._instances["convert_file_selection_component"] = (
                FileSelectionComponentNative(
                    convert_file_manager,
                    convert_validator,
                    convert_file_display,
                    accept_props=".gpkg,.geojson",
                    accepted_formats_i18n_key="app.component.file_selection_component.convert_accepted_formats",
                    supported_formats_i18n_key="app.component.file_selection_component.convert_supported_formats",
                )
            )

        return self._instances["convert_file_selection_component"]

    def get_convert_file_display(self) -> FileDisplay:
        """Retourne le FileDisplay pour la section Convert."""
        if "convert_file_display" not in self._instances:
            self.get_convert_file_selection_component()

        return self._instances["convert_file_display"]

    def get_convert_options_component(self) -> ConvertOptionsComponent:
        """Retourne le composant d'options de conversion."""
        if "convert_options_component" not in self._instances:
            self._instances["convert_options_component"] = ConvertOptionsComponent()

        return self._instances["convert_options_component"]

    def get_convert_handler(self) -> ConvertHandler:
        """Retourne le gestionnaire de conversion."""
        if "convert_handler" not in self._instances:
            self._instances["convert_handler"] = ConvertHandler(
                config_manager=self.get_config_manager(),
                file_manager=self.get_convert_file_manager(),
                status_display=self.get_status_display(),
                log_display=self.get_log_display(),
                log_settings=self.get_log_handler().get_log_settings(),
            )

        return self._instances["convert_handler"]

    # ── Refactored section components ──────────────────────────────────────

    def get_section_switcher(self) -> SectionSwitcherComponent:
        """Retourne le gestionnaire de navigation entre sections."""
        if "section_switcher" not in self._instances:
            self._instances["section_switcher"] = SectionSwitcherComponent()

        return self._instances["section_switcher"]

    def get_processing_handler(self) -> ProcessingHandler:
        """Retourne le gestionnaire de traitement."""
        if "processing_handler" not in self._instances:
            self._instances["processing_handler"] = ProcessingHandler(
                config_manager=self.get_config_manager(),
                file_manager=self.get_file_manager(),
                validator=self.get_validator(),
                status_display=self.get_status_display(),
                log_display=self.get_log_display(),
                log_settings=self.get_log_handler().get_log_settings(),
            )

        return self._instances["processing_handler"]

    def get_options_component(self) -> OptionsComponent:
        """Retourne le composant d'options de traitement."""
        if "options_component" not in self._instances:
            self._instances["options_component"] = OptionsComponent(
                config_path=self.get_config_manager().config_path,
                config_manager=self.get_config_manager(),
                ui_event_handler=self.get_ui_event_handler(),
            )

        return self._instances["options_component"]

    def get_process_panel(self) -> ProcessPanel:
        """Retourne le panneau de traitement (Process)."""
        if "process_panel" not in self._instances:
            panel = ProcessPanel(
                processing_handler=self.get_processing_handler(),
                file_selection_component=self.get_file_selection_component(),
                options_component=self.get_options_component(),
                config_manager=self.get_config_manager(),
                ui_event_handler=self.get_ui_event_handler(),
            )
            self.get_file_display().remove_callback = panel.remove_file
            self._instances["process_panel"] = panel

        return self._instances["process_panel"]

    def get_convert_section(self) -> ConvertSection:
        """Retourne la section de conversion (Convert)."""
        if "convert_section" not in self._instances:
            section = ConvertSection(
                convert_handler=self.get_convert_handler(),
                convert_options_component=self.get_convert_options_component(),
                convert_file_selection_component=self.get_convert_file_selection_component(),
                convert_file_display=self.get_convert_file_display(),
                config_manager=self.get_config_manager(),
            )
            self.get_convert_file_display().remove_callback = section.remove_file
            self._instances["convert_section"] = section

        return self._instances["convert_section"]
