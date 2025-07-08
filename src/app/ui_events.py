"""
UI Event Handler for CSB-Processing
"""

from typing import Any, Protocol

from loguru import logger

from .component.log_display import LogDisplay
from .component.notifications import show_notification
from .config_manager import ConfigManager
from .file_operations import FileOperations
from .ui_validation import Validator

LOGGER = logger.bind(name="CSB-Processing.UI.Events")


class FileSelectionComponentProtocol(Protocol):
    """Protocol for file selection component."""

    def set_warning_visible(self, visible: bool) -> None:
        """Set the visibility of the warning label."""
        ...


class UIEventHandler:
    def __init__(
        self,
        config_manager: ConfigManager,
        file_operations: FileOperations,
        validator: Validator,
        log_display: LogDisplay,
    ):
        self.config_manager = config_manager
        self.file_operations = file_operations
        self.validator = validator
        self.log_display = log_display

    def remove_file(
        self,
        file_info: dict[str, Any],
        file_selection_component: FileSelectionComponentProtocol,
    ) -> None:
        """Remove a file from the upload list."""
        try:
            no_files_remaining = self.file_operations.remove_file(file_info)

            # Show warning label if no files remain
            if no_files_remaining:
                file_selection_component.set_warning_visible(True)

        except Exception as ex:
            LOGGER.error(f"Error removing file {file_info['name']}: {ex}")
            show_notification(f"Error during removal: {str(ex)}", type="negative")

    # Options-related methods for use as callbacks
    def update_output_path(self, path: str) -> None:
        """Update output_path when input changes."""
        self.config_manager.update_output_path(path)

    def update_config_path(self, path: str) -> None:
        """Update config_path when input changes."""
        self.config_manager.update_config_path(path)

    async def select_output_directory(self) -> str:
        """Select output directory and return the selected path."""
        try:
            selected_path = await self.file_operations.select_output_directory()
            if selected_path:
                return selected_path

            return ""

        except Exception as ex:
            LOGGER.error(f"Error in select_output_directory: {ex}")
            if self.log_display:
                self.log_display.show()
            raise

    async def select_config_file(self) -> str:
        """Select config file and return the selected path."""
        try:
            selected_path = await self.file_operations.select_config_file()
            if selected_path:
                return selected_path

            return ""

        except Exception as ex:
            LOGGER.error(f"Error in select_config_file: {ex}")
            if self.log_display:
                self.log_display.show()
            raise

    def toggle_vessel(self) -> bool:
        """Toggle vessel option and return True if waterline was disabled."""
        waterline_was_disabled = self.config_manager.toggle_vessel_mode()

        # Validate mutual exclusivity and vessel configuration
        if not self.validator.validate_mutual_exclusivity():
            show_notification(
                "Invalid configuration: mutual exclusivity violated", type="negative"
            )

        if (
            self.config_manager.use_vessel
            and not self.validator.validate_vessel_configuration()
        ):
            show_notification("Please specify a vessel identifier", type="warning")

        return waterline_was_disabled

    def toggle_waterline(self) -> bool:
        """Toggle waterline option and return True if vessel was disabled."""
        vessel_was_disabled = self.config_manager.toggle_waterline_mode()

        # Validate mutual exclusivity and waterline configuration
        if not self.validator.validate_mutual_exclusivity():
            show_notification(
                "Invalid configuration: mutual exclusivity violated", type="negative"
            )

        if (
            self.config_manager.use_waterline
            and not self.validator.validate_waterline_configuration()
        ):
            show_notification(
                "Please specify a valid waterline value (> 0)", type="warning"
            )

        return vessel_was_disabled
