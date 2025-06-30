"""
UI Validation Module
"""

from pathlib import Path
from typing import Protocol, Callable


class ConfigManagerProtocol(Protocol):
    """Protocol for configuration manager to manage settings."""

    output_path: Path
    use_vessel: bool
    use_waterline: bool
    vessel_id: str
    waterline_value: float

    def update_output_path(self, path_str: str) -> None:
        """Update output path from string input."""
        ...

    def toggle_vessel_mode(self) -> bool:
        """Toggle vessel mode and handle mutual exclusivity. Returns True if changed."""
        ...

    def toggle_waterline_mode(self) -> bool:
        """Toggle waterline mode and handle mutual exclusivity. Returns True if changed."""
        ...


class Validator:
    def __init__(
        self,
        get_files_func: Callable[[], list[dict]],
        config_manager: ConfigManagerProtocol,
    ) -> None:
        self.get_files_func = get_files_func
        self.config_manager = config_manager

    def validate_inputs(self) -> list[str]:
        """Validate all inputs and return list of errors."""
        errors = []

        if not self.get_files_func():
            errors.append("❌ Please select at least one file to process")

        # Use config_manager for all configuration properties
        output_path = self.config_manager.output_path
        if not output_path or str(output_path).strip() == "" or output_path == Path():
            errors.append("❌ Please specify an output directory")

        use_vessel = self.config_manager.use_vessel
        use_waterline = self.config_manager.use_waterline

        if use_vessel and use_waterline:
            errors.append(
                "❌ You can only use one of 'vessel identifier' or 'waterline' options"
            )

        # Additional validations for vessel and waterline values
        vessel_id = self.config_manager.vessel_id
        if use_vessel and not vessel_id.strip():
            errors.append("❌ Please specify a vessel identifier")

        waterline_value = self.config_manager.waterline_value
        if use_waterline and waterline_value <= 0:
            errors.append("❌ Please specify a valid waterline value (> 0)")

        return errors

    def validate_file_selection(self) -> bool:
        """Check if at least one file is selected."""
        return bool(self.get_files_func())

    def validate_output_path(self) -> bool:
        """Check if output path is specified."""
        output_path = self.config_manager.output_path
        return bool(output_path and output_path != Path() and str(output_path).strip())

    def validate_mutual_exclusivity(self) -> bool:
        """Check vessel and waterline options mutual exclusivity."""
        use_vessel = self.config_manager.use_vessel
        use_waterline = self.config_manager.use_waterline
        return not (use_vessel and use_waterline)

    def validate_vessel_configuration(self) -> bool:
        """Check vessel configuration validity."""
        use_vessel = self.config_manager.use_vessel
        if use_vessel:
            vessel_id = self.config_manager.vessel_id
            return bool(vessel_id.strip())

        return True

    def validate_waterline_configuration(self) -> bool:
        """Check waterline configuration validity."""
        use_waterline = self.config_manager.use_waterline
        if use_waterline:
            waterline_value = self.config_manager.waterline_value
            return waterline_value > 0

        return True
