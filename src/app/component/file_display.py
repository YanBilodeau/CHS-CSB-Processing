"""
Reusable UI component for displaying selected files in a card format.
"""

from nicegui import ui
from typing import Callable


class FileDisplay:
    """Component for displaying selected files."""

    def __init__(
        self, get_files_callback: Callable[[], list[dict]], remove_callback: Callable
    ) -> None:
        self.get_files: Callable[[], list[dict]] = get_files_callback
        self.remove_callback: Callable = remove_callback
        self.container = None

    def create(self) -> ui.column:
        """Create the file display component."""
        self.container = ui.column().classes("w-full gap-2 mt-2")
        self.update()

        return self.container

    def update(self) -> None:
        """Update the file display."""
        if not self.container:
            return

        # Get current files from callback
        files: list[dict] = self.get_files()

        # Clear existing content
        self.container.clear()

        with self.container:
            if not files or len(files) == 0:
                ui.label("No files selected").classes("text-gray-500 italic")
            else:
                ui.label(f"Selected files ({len(files)}):").classes(
                    "font-bold text-blue-600"
                )

                # Create cards for each file
                for file_info in files:
                    self._create_file_card(file_info)

        ui.update()

    def _create_file_card(self, file_info: dict) -> None:
        """Create a card for a single file."""
        with ui.card().classes("w-full p-3 border-l-4 border-blue-400"):
            with ui.row().classes("w-full items-center gap-3"):
                # File icon and info
                with ui.row().classes("items-center gap-2 flex-1"):
                    ui.icon("description").classes("text-blue-500 text-xl")
                    with ui.column().classes("gap-0"):
                        ui.label(file_info["name"]).classes("font-medium text-gray-800")
                        ui.label(str(file_info["path"])).classes(
                            "text-xs text-gray-500 break-all"
                        )

                # File size
                if file_info["size"] > 0:
                    size_text = self._format_file_size(file_info["size"])
                    ui.label(size_text).classes("text-sm text-gray-600 font-mono")

                # Remove button
                remove_btn = (
                    ui.button(icon="delete")
                    .props("size=sm color=red outline round")
                    .tooltip("Remove this file")
                )
                remove_btn.on_click(lambda file=file_info: self._handle_remove(file))

    def _handle_remove(self, file_info: dict) -> None:
        """Handle file removal and update display."""
        # Call the remove callback
        self.remove_callback(file_info)
        # Force immediate update of the display
        self.update()

    @staticmethod
    def _format_file_size(size_bytes: int) -> str:
        """Format file size in human readable format."""
        size_mb: float = size_bytes / (1024 * 1024)
        if size_mb >= 1:
            return f"{size_mb:.1f} MB"
        else:
            size_kb = size_bytes / 1024
            return f"{size_kb:.1f} KB"
