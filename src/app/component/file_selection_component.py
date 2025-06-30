"""
File Selection Component module.

Contains the FileSelectionComponent for handling file selection functionality.
"""

from nicegui import ui
from loguru import logger

from .protocols import FileManagerProtocol, ValidatorProtocol, FileDisplayProtocol

LOGGER = logger.bind(name="CSB-Processing.FileSelection")


class FileSelectionComponent:
    """Component for file selection functionality."""

    def __init__(
        self,
        file_manager: FileManagerProtocol,
        validator: ValidatorProtocol,
        file_display: FileDisplayProtocol,
    ):
        self.file_manager = file_manager
        self.validator = validator
        self.file_display = file_display

        self.files_warning_label = None

    def create(self):
        """Create the file selection section."""
        ui.label("File Selection *").classes("text-lg font-bold text-red-600")

        # File selection with dialog
        with ui.row().classes("w-full gap-4 items-center"):
            ui.button(
                "Select files...",
                on_click=self._open_file_dialog,
                icon="folder_open",
            ).props("color=primary")

            ui.button(
                "Clear selection",
                on_click=self._clear_files,
                icon="clear",
            ).props("color=negative outline")

        ui.label("Accepted formats: .csv, .txt, .xyz, .geojson").classes(
            "text-sm text-gray-500"
        )

        # Warning label for files selection
        self.files_warning_label = ui.label(
            "⚠️ Required: Please select at least one file to process"
        ).classes("text-sm text-red-500")

        # Files display using FileDisplay component
        self.file_display.create()

    def set_warning_visible(self, visible: bool):
        """Set the visibility of the warning label."""
        if self.files_warning_label is not None:
            self.files_warning_label.visible = visible

    def _open_file_dialog(self):
        """Open file selection dialog."""
        try:
            selected_files = self.file_manager.open_file_dialog()
            if selected_files:
                self._add_selected_files(selected_files)
            else:
                ui.notification("No file selected", type="info")

        except Exception as ex:
            LOGGER.error(f"Error opening file dialog: {ex}")
            ui.notification(f"Error opening file dialog: {str(ex)}", type="negative")

    def _add_selected_files(self, file_paths):
        """Add selected files from dialog."""
        try:
            added_count = self.file_manager.add_files(file_paths)
            self.file_display.update()

            if self.validator.validate_file_selection():
                self.set_warning_visible(False)

            if added_count > 0:
                ui.notification(
                    f"{added_count} file(s) added successfully", type="positive"
                )
            elif len(file_paths) > 0:
                ui.notification("No new files added", type="info")

        except Exception as ex:
            LOGGER.error(f"Error adding files: {ex}")
            ui.notification(f"Error adding files: {str(ex)}", type="negative")

    def _clear_files(self):
        """Clear all selected files."""
        self.file_manager.clear_files()
        self.file_display.update()

        if not self.validator.validate_file_selection():
            self.set_warning_visible(True)
        ui.notification("All files have been removed", type="info")
