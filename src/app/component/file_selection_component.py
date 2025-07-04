"""
File Selection Component module.

Contains the FileSelectionComponent for handling file selection functionality.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Generator
import tempfile

from nicegui import ui, app, events
from loguru import logger

from .protocols import FileManagerProtocol, ValidatorProtocol, FileDisplayProtocol

LOGGER = logger.bind(name="CSB-Processing.FileSelection")


class FileSelectionComponentABC(ABC):
    """ABC for file selection component."""

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

    @abstractmethod
    def create(self) -> None:
        """Create the file selection section."""
        ...

    def set_warning_visible(self, visible: bool):
        """Set the visibility of the warning label."""
        if self.files_warning_label is not None:
            self.files_warning_label.visible = visible


class FileSelectionComponentNative(FileSelectionComponentABC):
    """Component for file selection in the native application."""

    def __init__(
        self,
        file_manager: FileManagerProtocol,
        validator: ValidatorProtocol,
        file_display: FileDisplayProtocol,
    ):
        super().__init__(file_manager, validator, file_display)

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

        with ui.row().classes("justify-center items-center mb-6"):
            ui.markdown(
                """
            Accepted formats: .csv, .txt, .xyz, .geojson, .*
            """
            ).classes("text-center text-gray-600")

            with ui.icon("info").classes("text-blue-500 cursor-pointer ml-2"):
                with ui.menu() as menu:
                    with ui.card().classes("max-w-lg p-4"):
                        ui.markdown(
                            """
                        **Supported file formats:**

                        - **OFM**: `.xyz` extension with at least the columns LON, LAT, DEPTH, TIME in the header.
                        - **DCDB**: `.csv` extension with at least the columns LON, LAT, DEPTH, TIME in the header.
                        - **Lowrance**: `.csv` extension with at least the columns Longitude[°WGS84], Latitude[°WGS84], WaterDepth[Feet], DateTime[UTC] in the header. These files are the result of SL3 files from Lowrance exported by the tool [SL3Reader](https://github.com/halmaia/SL3Reader).
                        - **Actisense**: coming soon.
                        - **BlackBox**: `.TXT` extension without header with columns in the order Time, Date, Latitude, Longitude, Speed (km/h) and Depth (m).
                        - **[WIBL](https://github.com/CCOMJHC/WIBL/tree/main)**: numeric extension (e.g., `.1`, `.2`, `.3`, etc.).
                        """
                        ).classes("text-sm")

        # Warning label for files selection
        self.files_warning_label = ui.label(
            "⚠️ Required: Please select at least one file to process"
        ).classes("text-sm text-red-500")

        # Files display using FileDisplay component
        self.file_display.create()

    async def _open_file_dialog(self):
        """Open file selection dialog using native method."""
        try:
            result = await app.native.main_window.create_file_dialog(
                allow_multiple=True
            )
            if result:
                self._add_selected_files(result)
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


class FileSelectionComponentWeb(FileSelectionComponentABC):
    """Component for file selection in the web application."""

    def __init__(
        self,
        file_manager: FileManagerProtocol,
        validator: ValidatorProtocol,
        file_display: FileDisplayProtocol,
    ):
        super().__init__(file_manager, validator, file_display)
        self.upload_component = None

    def create(self) -> None:
        """Create the file selection section."""
        ui.label("File Selection *").classes("text-lg font-bold text-red-600")

        # File upload section
        with ui.row().classes("w-full gap-4 items-center"):
            self.upload_component = (
                ui.upload(
                    on_upload=self._handle_upload,
                    on_rejected=self._handle_rejected,
                    multiple=True,
                    max_file_size=100_000_000,  # 100MB max per file
                    max_total_size=500_000_000,  # 500MB max total
                    max_files=50,  # Maximum 50 files
                    auto_upload=True,
                )
                .props("color=primary accept='.csv,.txt,.xyz,.geojson,.*'")
                .classes("w-full")
            )

            ui.button(
                "Clear selection",
                on_click=self._clear_files,
                icon="clear",
            ).props("color=negative outline")

            self.file_display.create()

        with ui.row().classes("justify-center items-center mb-6"):
            ui.markdown(
                """
            Accepted formats: .csv, .txt, .xyz, .geojson, .*
            Max file size: 100MB | Max total: 500MB | Max files: 50
            """
            ).classes("text-center text-gray-600")

            with ui.icon("info").classes("text-blue-500 cursor-pointer ml-2"):
                with ui.menu() as menu:
                    with ui.card().classes("max-w-lg p-4"):
                        ui.markdown(
                            """
                        **Supported file formats:**

                        - **OFM**: `.xyz` extension with at least the columns LON, LAT, DEPTH, TIME in the header.
                        - **DCDB**: `.csv` extension with at least the columns LON, LAT, DEPTH, TIME in the header.
                        - **Lowrance**: `.csv` extension with at least the columns Longitude[°WGS84], Latitude[°WGS84], WaterDepth[Feet], DateTime[UTC] in the header. These files are the result of SL3 files from Lowrance exported by the tool [SL3Reader](https://github.com/halmaia/SL3Reader).
                        - **Actisense**: coming soon.
                        - **BlackBox**: `.TXT` extension without header with columns in the order Time, Date, Latitude, Longitude, Speed (km/h) and Depth (m).
                        - **[WIBL](https://github.com/CCOMJHC/WIBL/tree/main)**: numeric extension (e.g., `.1`, `.2`, `.3`, etc.).
                        """
                        ).classes("text-sm")

        # Warning label for files selection
        self.files_warning_label = ui.label(
            "⚠️ Required: Please select at least one file to process"
        ).classes("text-sm text-red-500")

    def _handle_upload(self, event: events.UploadEventArguments):
        """Handle file upload event."""
        try:
            file_path_generator = self._save_uploaded_file(event)
            file_path = next(
                file_path_generator, None
            )  # Get the file path from the generator
            if file_path and file_path.exists():
                self._add_uploaded_files((file_path,))

        except Exception as ex:
            LOGGER.error(f"Error handling upload: {ex}")
            ui.notification(f"Error uploading files: {str(ex)}", type="negative")

    @staticmethod
    def _handle_rejected(event: events.UiEventArguments):
        """Handle rejected file uploads."""
        message = "Some files were rejected"
        ui.notification(message, type="warning")

    @staticmethod
    def _save_uploaded_file(
        file_info: events.UploadEventArguments,
    ) -> Generator[Path, None, None]:
        """Save uploaded file content and return file path."""
        try:
            temp_dir = Path(tempfile.gettempdir())
            file_path = temp_dir / file_info.name

            # Créer le fichier avec le nom original
            file_info.content.seek(0)
            with open(file_path, "wb") as temp_file:
                temp_file.write(file_info.content.read())

            yield file_path

            if file_path.exists():
                file_path.unlink()

        except Exception as ex:
            LOGGER.error(f"Error saving uploaded file {file_info.name}: {ex}")

    def _add_uploaded_files(self, file_paths):
        """Add uploaded files to file manager."""
        try:
            added_count = self.file_manager.add_files(file_paths)
            self.file_display.update()

            if self.validator.validate_file_selection():
                self.set_warning_visible(False)

            if added_count > 0:
                ui.notification(
                    f"{added_count} file(s) uploaded successfully", type="positive"
                )
            elif len(file_paths) > 0:
                ui.notification("No new files added", type="info")

        except Exception as ex:
            LOGGER.error(f"Error adding uploaded files: {ex}")
            ui.notification(f"Error adding files: {str(ex)}", type="negative")

    def _clear_files(self):
        """Clear all selected files."""
        self.file_manager.clear_files()
        self.file_display.update()

        # Reset upload component
        if self.upload_component:
            self.upload_component.reset()

        if not self.validator.validate_file_selection():
            self.set_warning_visible(True)
        ui.notification("All files have been removed", type="info")
