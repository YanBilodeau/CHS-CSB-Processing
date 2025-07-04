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
)


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
            # Note: remove_callback sera défini dans CSBProcessingUI
            self._instances["file_display"] = FileDisplay(
                get_files_callback=self.get_file_manager().get_files,
                remove_callback=None,  # Sera configuré plus tard
            )

        return self._instances["file_display"]

    def get_file_selection_component(self) -> FileSelectionComponentNative:
        if "file_selection_component" not in self._instances:
            self._instances["file_selection_component"] = FileSelectionComponentNative(
                self.get_file_manager(), self.get_validator(), self.get_file_display()
            )

        return self._instances["file_selection_component"]
