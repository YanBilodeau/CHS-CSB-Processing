"""Handles the conversion workflow for geospatial data files."""

import asyncio
from pathlib import Path

import i18n
from loguru import logger

from converter import convert_files_to_formats
from config.processing_config import FileTypes

from .component.log_display import LogDisplay
from .component.notifications import show_notification
from .component.status_display import StatusDisplay
from .config_manager import ConfigManager
from .file_manager import FileManager

LOGGER = logger.bind(name="CSB-Processing.ConvertHandler")


class ConvertHandler:
    """Handles the file conversion workflow."""

    def __init__(
        self,
        config_manager: ConfigManager,
        file_manager: FileManager,
        status_display: StatusDisplay,
        log_display: LogDisplay,
        log_settings: dict | None = None,
    ):
        """
        Initialise le gestionnaire de conversion.

        :param config_manager: Gestionnaire de configuration partagé.
        :type config_manager: ConfigManager
        :param file_manager: Gestionnaire de fichiers pour la conversion.
        :type file_manager: FileManager
        :param status_display: Affichage du statut partagé.
        :type status_display: StatusDisplay
        :param log_display: Affichage des logs partagé.
        :type log_display: LogDisplay
        :param log_settings: Paramètres de log pour le handler UI.
        :type log_settings: dict | None
        """
        self.config_manager = config_manager
        self.file_manager = file_manager
        self.status_display = status_display
        self.log_display = log_display
        self.log_settings = log_settings

        # État de la conversion
        self.selected_formats: set[FileTypes] = set()
        self.group_by_iho_order: bool = False

    async def convert_files(self) -> None:
        """Convert the selected files to the chosen formats."""
        # Show logs during conversion
        if self.log_display:
            self.log_display.show()
            self.log_display.clear_logs()

        LOGGER.info(i18n.t("app.convert_handler.starting_conversion_log"))

        # Validate inputs
        validation_errors = self._validate_convert_inputs()
        if validation_errors:
            await self._handle_validation_errors(validation_errors)
            return

        # Update status and start conversion
        self.status_display.set_status(
            i18n.t("app.convert_handler.status_processing"), "processing"
        )
        show_notification(i18n.t("app.convert_handler.notif_started"), type="info")
        await asyncio.sleep(0.5)

        try:
            await self._execute_conversion_workflow()
            await self._handle_success()

        except Exception as e:
            await self._handle_error(e)

    def _validate_convert_inputs(self) -> list[str]:
        """
        Valide les entrées de la conversion.

        :return: Liste des messages d'erreur de validation.
        :rtype: list[str]
        """
        errors: list[str] = []

        # Check files
        files = self.file_manager.get_file_paths()
        if not files:
            errors.append(i18n.t("app.convert_handler.no_valid_files"))

        # Check formats
        if not self.selected_formats:
            errors.append(i18n.t("app.convert_handler.no_format_selected"))

        # Check output path
        if (
            not self.config_manager.output_path
            or self.config_manager.output_path == Path()
        ):
            errors.append(i18n.t("app.convert_handler.no_output_path"))

        return errors

    async def _handle_validation_errors(self, validation_errors: list[str]) -> None:
        """Handle validation errors."""
        for error in validation_errors:
            show_notification(error, type="negative")

        if self.log_display:
            self.log_display.show()

    async def _execute_conversion_workflow(self) -> None:
        """Execute the main conversion workflow."""
        files_paths = self.file_manager.get_file_paths()
        LOGGER.info(
            i18n.t(
                "app.convert_handler.converting_files",
                count=len(files_paths),
            )
        )

        self.status_display.set_status(
            i18n.t("app.convert_handler.status_validating"), "processing"
        )
        await asyncio.sleep(1)

        output = self.config_manager.output_path
        config = self.config_manager.get_effective_config_path()

        # Create output directory
        output.mkdir(parents=True, exist_ok=True)
        LOGGER.info(
            i18n.t("app.convert_handler.output_dir_created", output=str(output))
        )

        self.status_display.set_status(
            i18n.t("app.convert_handler.status_executing"), "processing"
        )
        await asyncio.sleep(1)

        await self._run_conversion_workflow(files_paths, output, config)

    async def _run_conversion_workflow(
        self,
        files_paths: list[Path],
        output: Path,
        config: Path,
    ) -> None:
        """Run the conversion workflow in a separate thread."""

        def run_conversion():
            LOGGER.info(i18n.t("app.convert_handler.conversion_started"))
            convert_files_to_formats(
                input_files=files_paths,
                output_path=output,
                file_types=self.selected_formats,
                config_path=config,
                group_by_iho_order=self.group_by_iho_order,
            )
            LOGGER.info(i18n.t("app.convert_handler.conversion_completed"))

        LOGGER.info(i18n.t("app.convert_handler.launching_background"))
        await asyncio.get_event_loop().run_in_executor(None, run_conversion)

    async def _handle_success(self) -> None:
        """Handle successful conversion completion."""
        success_msg = i18n.t(
            "app.convert_handler.status_success",
            output_path=str(self.config_manager.output_path),
        )
        self.status_display.set_status(success_msg, "success")
        show_notification(
            i18n.t("app.convert_handler.notif_completed"), type="positive"
        )
        LOGGER.info(i18n.t("app.convert_handler.conversion_completed"))

    async def _handle_error(self, error: Exception) -> None:
        """Handle conversion errors."""
        error_msg = i18n.t("app.convert_handler.status_error", error=str(error))
        self.status_display.set_status(error_msg, "error")
        show_notification(
            i18n.t("app.convert_handler.notif_error", error=str(error)),
            type="negative",
        )
        LOGGER.error(i18n.t("app.convert_handler.conversion_failed", error=str(error)))

        if self.log_display:
            self.log_display.show()
