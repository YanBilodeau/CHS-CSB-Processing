"""Handles the processing workflow for CSB data files."""

import asyncio
from pathlib import Path
from typing import Any, Iterable

from loguru import logger

from csb_processing import processing_workflow
from vessel import UNKNOWN_VESSEL_CONFIG, UNKNOWN_DATE, Waterline

from .component.log_display import LogDisplay
from .component.notifications import show_notification
from .component.status_display import StatusDisplay
from .config_manager import ConfigManager
from .file_manager import FileManager
from .ui_validation import Validator

LOGGER = logger.bind(name="CSB-Processing.ProcessingHandler")


def is_valid_file(file: Path) -> bool:
    """
    Vérifie si le fichier est valide pour le traitement.

    :param file: Chemin du fichier.
    :type file: Path
    :return: Vrai si le fichier est valide, faux sinon.
    :rtype: bool
    """
    return file.suffix.lower() in {".csv", ".txt", ".xyz", ".geojson"}


def get_files(paths: Iterable[Path]) -> list[Path]:
    """
    Récupère les fichiers à traiter.

    :param paths: Chemins des fichiers ou répertoires.
    :type paths: Iterable[Path]
    :return: Liste des fichiers à traiter.
    :rtype: list[Path]
    """
    files: list[Path] = []

    for path in paths:
        path = Path(path)

        if path.is_file() and is_valid_file(path):
            files.append(path)

        elif path.is_dir():
            files.extend(file for file in path.glob("**/*") if is_valid_file(file))

    return files


class ProcessingHandler:
    """Handles the file processing workflow."""

    def __init__(
        self,
        config_manager: ConfigManager,
        file_manager: FileManager,
        validator: Validator,
        status_display: StatusDisplay,
        log_display: LogDisplay,
        log_settings: dict | None = None,
    ):
        self.config_manager = config_manager
        self.file_manager = file_manager
        self.validator = validator
        self.status_display = status_display
        self.log_display = log_display
        self.log_settings = log_settings

    async def process_files(self) -> None:
        """Process the uploaded files."""
        # Show logs during processing
        if self.log_display:
            self.log_display.show()
            self.log_display.clear_logs()

        LOGGER.info("Starting CSB Processing Workflow")

        # Validate inputs using the validator
        validation_errors = self.validator.validate_inputs()
        if validation_errors:
            await self._handle_validation_errors(validation_errors)
            return

        # Update status and start processing
        self.status_display.set_status("🔄 Processing in progress...", "processing")
        show_notification("Processing started...", type="info")
        await asyncio.sleep(0.5)

        try:
            await self._execute_processing_workflow()
            await self._handle_success()

        except Exception as e:
            await self._handle_error(e)

    def _perform_validation(self) -> list[str]:
        """Perform comprehensive validation and return list of errors."""
        # Log validation status for debugging
        validations = {
            "File selection": self.validator.validate_file_selection(),
            "Output path": self.validator.validate_output_path(),
            "Mutual exclusivity": self.validator.validate_mutual_exclusivity(),
            "Vessel configuration": self.validator.validate_vessel_configuration(),
            "Waterline configuration": self.validator.validate_waterline_configuration(),
        }

        failed_validations = [
            name for name, passed in validations.items() if not passed
        ]

        if failed_validations:
            LOGGER.warning(
                f"Validation issues detected: {', '.join(failed_validations)}"
            )

        # Return the comprehensive validation from validator
        return self.validator.validate_inputs()

    async def _handle_validation_errors(self, validation_errors: list[str]) -> None:
        """Handle validation errors."""
        for error in validation_errors:
            show_notification(error, type="negative")

        if self.log_display:
            self.log_display.show()

    async def _execute_processing_workflow(self) -> None:
        """Execute the main processing workflow."""
        # Get and validate files
        files_paths = self.file_manager.get_file_paths()
        LOGGER.info(f"Processing files: {[str(p) for p in files_paths]}")

        self.status_display.set_status("🔍 Validating files...", "processing")
        await asyncio.sleep(1)

        valid_files = get_files(files_paths)
        if not valid_files:
            raise ValueError("No valid files found for processing")

        LOGGER.info(f"Found {len(valid_files)} valid files for processing")

        # Prepare processing parameters
        self.status_display.set_status(
            f"📁 Preparing {len(valid_files)} valid file(s)...", "processing"
        )
        await asyncio.sleep(1)

        output = self.config_manager.output_path
        config = self.config_manager.get_effective_config_path()
        vessel_config = self._prepare_vessel_config()

        # Create output directory
        output.mkdir(parents=True, exist_ok=True)
        LOGGER.info(f"Created output directory: {output}")

        # Execute processing
        self.status_display.set_status(
            "⚙️ Executing processing workflow...", "processing"
        )
        await asyncio.sleep(1)

        await self._run_processing_workflow(valid_files, vessel_config, output, config)

    def _prepare_vessel_config(self) -> Any:
        """Prepare vessel configuration based on current settings."""
        vessel_config = (
            self.config_manager.vessel_id
            if self.config_manager.use_vessel and self.config_manager.vessel_id
            else UNKNOWN_VESSEL_CONFIG
        )

        # Handle waterline configuration
        if (
            self.config_manager.use_waterline
            and self.config_manager.waterline_value is not None
        ):
            LOGGER.info(f"Using waterline: {self.config_manager.waterline_value}m")
            UNKNOWN_VESSEL_CONFIG.waterline = [
                Waterline(
                    time_stamp=UNKNOWN_DATE, z=-self.config_manager.waterline_value
                )
            ]
            vessel_config = UNKNOWN_VESSEL_CONFIG

        return vessel_config

    async def _run_processing_workflow(
        self, valid_files: list, vessel_config: Any, output: Path, config: Path
    ) -> None:
        """Run the processing workflow in a separate thread."""

        def run_processing():
            LOGGER.info("Starting bathymetric data processing...")
            processing_workflow(
                files=valid_files,
                vessel=vessel_config,
                output=output,
                config_path=config,
                apply_water_level=self.config_manager.apply_water_level,
                extra_logger=(self.log_settings,),
            )
            LOGGER.info("Processing workflow completed successfully")

        LOGGER.info("Launching processing in background thread...")
        await asyncio.get_event_loop().run_in_executor(None, run_processing)

    async def _handle_success(self) -> None:
        """Handle successful processing completion."""
        success_msg = f"✅ Processing completed! Files have been saved to {self.config_manager.output_path}"
        self.status_display.set_status(success_msg, "success")
        show_notification("Processing completed successfully!", type="positive")
        LOGGER.info("CSB Processing Workflow Completed")

    async def _handle_error(self, error: Exception) -> None:
        """Handle processing errors."""
        error_msg = f"An error occurred during processing: {str(error)}"
        self.status_display.set_status(f"❌ {error_msg}", "error")
        show_notification(error_msg, type="negative")
        LOGGER.error(f"Processing failed with error: {str(error)}")
        LOGGER.error("CSB Processing Workflow Failed")

        if self.log_display:
            self.log_display.show()
