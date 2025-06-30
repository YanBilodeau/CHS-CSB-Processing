"""
This module provides a web graphical interface for processing bathymetric data files using NiceGUI.

It allows executing the same functionalities as the CLI but through a web interface.
"""

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
    FileSelectionComponent,
    OptionsComponent,
    HeaderComponent,
    ProcessingHandler,
    ConfigManager,
    FileOperations,
    UIEventHandler,
    ProcessingSection,
    StatusSection,
    LogSection,
)

LOGGER = logger.bind(name="CSB-Processing.UI")


class CSBProcessingUI:
    def __init__(self):
        # Configuration management
        self.config_manager = ConfigManager()

        # File management
        self.file_manager = FileManager()

        # Initialize validation
        self.validator = Validator(self.file_manager.get_files, self.config_manager)

        # Theme management
        self.theme_manager = ThemeManager(dark_mode=True)

        # File operations
        self.file_operations = FileOperations(
            self.config_manager, self.file_manager, self.validator
        )

        # Log handling
        self.log_handler = UILogHandler()
        self.log_handler.setup_logger()
        self.log_display = LogDisplay(self.log_handler)

        # UI elements
        self.status_display = StatusDisplay()
        self.main_container = None

        # Processing handler
        self.processing_handler = None

        # Event handler
        self.ui_event_handler = UIEventHandler(
            self.config_manager,
            self.file_operations,
            self.validator,
            log_display=self.log_display,
        )

        # Initialize UI components
        self.file_display = FileDisplay(
            get_files_callback=self.file_manager.get_files,
            remove_callback=self.remove_file,
        )
        self.file_selection_component = FileSelectionComponent(
            self.file_manager, self.validator, self.file_display
        )

    def remove_file(self, file_info):
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
    runner = UIRunner(CSBProcessingUI())

    try:
        runner.run()

    except Exception as e:
        LOGGER.exception(e)
        LOGGER.error(f"Failed to start the application: {str(e)}")


if __name__ == "__main__":
    main()
