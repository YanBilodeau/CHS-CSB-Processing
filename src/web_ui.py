"""
This module provides a web graphical interface for processing bathymetric data files using NiceGUI.

It allows executing the same functionalities as the CLI but through a web interface.
"""

from typing import Any

from loguru import logger
from nicegui import ui

from app import (
    FileDisplay,
    FileManager,
    LogDisplay,
    UILogHandler,
    StatusDisplay,
    ThemeManager,
    Validator,
    UIRunner,
    FileSelectionComponentNative,
    OptionsComponent,
    HeaderComponent,
    ProcessingHandler,
    ConfigManager,
    FileOperations,
    UIEventHandler,
    ProcessingSection,
    StatusSection,
    LogSection,
    GuiType,
    DependencyContainer,
)


LOGGER = logger.bind(name="CSB-Processing.UI")


class CSBProcessingUI:
    def __init__(
        self,
        config_manager: ConfigManager,
        file_manager: FileManager,
        validator: Validator,
        theme_manager: ThemeManager,
        file_operations: FileOperations,
        log_handler: UILogHandler,
        log_display: LogDisplay,
        status_display: StatusDisplay,
        ui_event_handler: UIEventHandler,
        file_display: FileDisplay,
        file_selection_component: FileSelectionComponentNative,
    ):
        # Injection des dépendances
        self.config_manager = config_manager
        self.file_manager = file_manager
        self.validator = validator
        self.theme_manager = theme_manager
        self.file_operations = file_operations
        self.log_handler = log_handler
        self.log_display = log_display
        self.status_display = status_display
        self.ui_event_handler = ui_event_handler
        self.file_display = file_display
        self.file_selection_component = file_selection_component

        # Configuration du callback pour file_display
        self.file_display.remove_callback = self.remove_file

        # État interne
        self.main_container = None
        self.processing_handler = None

    def remove_file(self, file_info: dict[str, Any]):
        """Remove a file from the upload list."""
        return self.ui_event_handler.remove_file(
            file_info, self.file_selection_component
        )

    def create_ui(self):
        """Create the main UI."""
        # Add custom CSS for status label flashing animation
        self.theme_manager.add_theme_styles()

        # Main container with theme classes
        self.main_container = ui.card().classes(
            "w-full max-w-6xl mx-auto p-6 shadow-lg theme-container theme-light"
        )

        with self.main_container:
            HeaderComponent(self.theme_manager).create()
            self.file_selection_component.create()
            OptionsComponent(
                config_path=self.config_manager.config_path,
                config_manager=self.config_manager,
                ui_event_handler=self.ui_event_handler,
            ).create()

            ProcessingSection(self.process_files).create()
            StatusSection(self.status_display).create()
            LogSection(self.log_display).create()

    async def process_files(self):
        """Process the uploaded files using ProcessingHandler."""
        # Initialize processing handler if not already done
        if not self.processing_handler:
            self.processing_handler = ProcessingHandler(
                config_manager=self.config_manager,
                file_manager=self.file_manager,
                validator=self.validator,
                status_display=self.status_display,
                log_display=self.log_display,
                log_settings=self.log_handler.get_log_settings(),
            )

        # Delegate processing to the handler
        await self.processing_handler.process_files()


def main():
    """Main function to run the application."""
    # Configuration du conteneur de dépendances
    container = DependencyContainer()

    # Création de l'UI avec injection de dépendances
    main_ui = CSBProcessingUI(
        config_manager=container.get_config_manager(),
        file_manager=container.get_file_manager(),
        validator=container.get_validator(),
        theme_manager=container.get_theme_manager(),
        file_operations=container.get_file_operations(),
        log_handler=container.get_log_handler(),
        log_display=container.get_log_display(),
        status_display=container.get_status_display(),
        ui_event_handler=container.get_ui_event_handler(),
        file_display=container.get_file_display(),
        file_selection_component=container.get_file_selection_component(),
    )

    runner = UIRunner(main_ui=main_ui, gui=GuiType.NATIVE)

    try:
        runner.run()

    except Exception as e:
        LOGGER.exception(e)
        LOGGER.error(f"Failed to start the application: {str(e)}")


if __name__ == "__main__":
    main()
