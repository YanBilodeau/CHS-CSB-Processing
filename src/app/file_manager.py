"""
File management utilities for the CSB Processing application.
"""

from collections.abc import Sequence
from pathlib import Path
from typing import Any, Iterable

from nicegui import app
from loguru import logger
import webview

LOGGER = logger.bind(name="CSB-Processing.FileManager")


class FileManager:
    """Handles file operations for the application."""

    ALLOWED_EXTENSIONS = {".csv", ".txt", ".xyz", ".geojson"}
    # This set contains the allowed file extensions for bathymetric data files.
    # WIBL files are not included in the allowed extensions, as they are handled separately wwith _is_numeric_extension.

    def __init__(self) -> None:
        self.files: list[dict[str, Any]] = []

    @staticmethod
    def _is_numeric_extension(extension: str) -> bool:
        """Check if the extension is numeric (e.g., .1, .2, .3)."""
        return extension.startswith(".") and extension[1:].isdigit()

    @staticmethod
    async def open_directory_dialog(initial_dir: str = "") -> str:
        """Open directory selection dialog and return selected directory."""
        try:
            result = await app.native.main_window.create_file_dialog(
                dialog_type=webview.FOLDER_DIALOG,
                allow_multiple=True,
                directory=initial_dir,
            )

            if result:
                if isinstance(result, Sequence) and len(result) > 0:
                    return str(result[0])

                return str(result)

            return ""

        except Exception as ex:
            LOGGER.error(f"Error opening directory dialog: {ex}")

            return ""

    @staticmethod
    async def open_config_dialog(initial_dir: str = "") -> str:
        """Open config file selection dialog and return selected file."""
        try:
            # Define file types for TOML files
            file_types: list[str] = [
                "TOML files (*.toml)",
                "All files (*.*)",
            ]
            result = await app.native.main_window.create_file_dialog(
                directory=initial_dir,
                file_types=file_types,
            )

            if result:
                if isinstance(result, Sequence) and len(result) > 0:
                    return str(result[0])

                return str(result)

            return ""

        except Exception as ex:
            LOGGER.error(f"Error opening config file dialog: {ex}")
            raise

    def add_files(self, file_paths: Iterable[Path]) -> int:
        """Add files to the collection and return number of added files."""
        added_count: int = 0

        for file_path_str in file_paths:
            try:
                file_path: Path = Path(file_path_str)
                file_name: str = file_path.name

                LOGGER.debug(f"Attempting to add file: {file_name}")

                # Check for duplicates
                if self._is_duplicate(file_name):
                    LOGGER.debug(f"Duplicate file ignored: {file_name}")
                    continue

                # Check if file exists
                if not file_path.exists():
                    LOGGER.debug(f"File not found: {file_path}")
                    continue

                # Check file extension (known extensions or numeric extensions)
                extension = file_path.suffix.lower()
                if (
                    extension not in self.ALLOWED_EXTENSIONS
                    and not self._is_numeric_extension(extension)
                ):
                    LOGGER.debug(f"Unsupported format: {file_name}")
                    continue

                # Get file size
                file_size = file_path.stat().st_size

                # Store file info
                self.files.append(
                    {"name": file_name, "path": file_path, "size": file_size}
                )

                LOGGER.debug(f"File added successfully: {file_name}")
                added_count += 1

            except Exception as ex:
                LOGGER.error(f"Error adding file {file_path_str}: {ex}")

        return added_count

    def remove_file(self, file_info: dict[str, Any]) -> bool:
        """Remove a file from the collection."""
        try:
            self.files.remove(file_info)
            LOGGER.debug(f"File removed from list: {file_info['name']}")

            return True

        except ValueError:
            LOGGER.error(f"File not found in list: {file_info.get('name', 'Unknown')}")

            return False

    def clear_files(self):
        """Clear all files from the collection."""
        self.files.clear()
        LOGGER.debug("All files cleared from selection")

    def get_files(self) -> list[dict[str, Any]]:
        """Get all files in the collection."""
        return self.files.copy()

    def get_file_paths(self) -> list[Path]:
        """Get file paths for processing."""
        return [f["path"] for f in self.files]

    def _is_duplicate(self, file_name: str) -> bool:
        """Check if file name already exists in collection."""
        existing_names = [f["name"] for f in self.files]

        return file_name in existing_names
