"""File Operations Module"""

from pathlib import Path
from typing import Any

import i18n
from loguru import logger

from .component.notifications import show_notification
from .config_manager import ConfigManager
from .file_manager import FileManager
from .ui_validation import Validator

LOGGER = logger.bind(name="CSB-Processing.FileOperations")


class FileOperations:
    """Handles file-related operations like dialogs and file management."""

    def __init__(
        self,
        config_manager: ConfigManager,
        file_manager: FileManager,
        validator: Validator,
    ):
        self.config_manager = config_manager
        self.file_manager = file_manager
        self.validator = validator

    def remove_file(self, file_info: dict[str, Any]) -> bool:
        """Remove a file from the upload list."""
        try:
            success = self.file_manager.remove_file(file_info)
            if success:
                show_notification(
                    i18n.t("app.file_operations.file_removed", name=file_info["name"]),
                    type="info",
                )
                # Return True if no files remain (for warning display)
                return len(self.file_manager.get_files()) == 0
            else:
                show_notification(
                    i18n.t(
                        "app.file_operations.error_removing_file",
                        name=file_info["name"],
                    ),
                    type="negative",
                )
                return False

        except Exception as ex:
            LOGGER.error(
                i18n.t(
                    "app.file_operations.error_removing_log",
                    name=file_info["name"],
                    error=str(ex),
                )
            )
            show_notification(
                i18n.t("app.file_operations.error_during_removal", error=str(ex)),
                type="negative",
            )
            return False

    def get_files(self):
        """Get files from file manager - delegation method."""
        return self.file_manager.get_files()

    async def select_output_directory(self, output_warning_label=None) -> str | None:
        """Open directory selection dialog."""
        try:
            selected_directory = await self.file_manager.open_directory_dialog(
                str(self.config_manager.output_path)
                if self.config_manager.output_path != Path()
                else ""
            )

            if selected_directory:
                self.config_manager.update_output_path(selected_directory)

                # Hide warning if validation passes
                if output_warning_label and self.validator.validate_output_path():
                    output_warning_label.visible = False

                show_notification(
                    i18n.t(
                        "app.file_operations.directory_selected",
                        name=self.config_manager.output_path.name,
                    ),
                    type="positive",
                )
                LOGGER.debug(
                    i18n.t(
                        "app.file_operations.output_dir_selected_log",
                        path=str(self.config_manager.output_path),
                    )
                )
                return str(self.config_manager.output_path)
            else:
                show_notification(
                    i18n.t("app.file_operations.no_directory_selected"), type="info"
                )
                return None

        except Exception as ex:
            LOGGER.error(i18n.t("app.file_operations.error_open_dir", error=str(ex)))
            show_notification(
                i18n.t("app.file_operations.error_open_dir", error=str(ex)),
                type="negative",
            )
            return None

    async def select_config_file(self) -> str | None:
        """Open config file selection dialog."""
        try:
            selected_file = await self.file_manager.open_config_dialog(
                str(self.config_manager.config_path.parent)
                if self.config_manager.config_path != Path()
                else ""
            )

            if selected_file:
                self.config_manager.config_path = Path(selected_file)
                show_notification(
                    i18n.t(
                        "app.file_operations.config_file_selected",
                        name=self.config_manager.config_path.name,
                    ),
                    type="positive",
                )
                LOGGER.debug(
                    i18n.t(
                        "app.file_operations.config_file_selected_log",
                        path=str(self.config_manager.config_path),
                    )
                )
                return str(self.config_manager.config_path)
            else:
                show_notification(
                    i18n.t("app.file_operations.no_file_selected"), type="info"
                )
                return None

        except Exception as ex:
            LOGGER.error(
                i18n.t("app.file_operations.error_open_config_file", error=str(ex))
            )
            show_notification(
                i18n.t("app.file_operations.error_open_config_file", error=str(ex)),
                type="negative",
            )
            return None
