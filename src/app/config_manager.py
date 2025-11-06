"""
Configuration manager for the CSB Processing UI.
Handles all configuration-related operations and state.
"""

from pathlib import Path
from csb_processing import CONFIG_FILE


class ConfigManager:
    """Manages configuration state for the UI application."""

    def __init__(self):
        self.output_path: Path = Path()
        self.config_path: Path = Path(CONFIG_FILE)
        self.vessel_id: str = ""
        self.waterline_value: float = 0.0
        self.use_vessel: bool = False
        self.use_waterline: bool = False
        self.apply_water_level: bool = True

    def update_output_path(self, path_str: str) -> None:
        """Update output path from string input."""
        LOGGER.debug(f"Updating output path with input: {path_str}")
        self.output_path = Path(path_str).expanduser().resolve() if path_str else Path()
        LOGGER.debug(f"Output path updated to: {self.output_path}")


    def update_config_path(self, path_str: str) -> None:
        """Update config path from string input."""
        LOGGER.debug(f"Updating config path with input: {path_str}")
        self.config_path = Path(path_str).expanduser().resolve() if path_str else Path()
        LOGGER.debug(f"Config path updated to: {self.config_path}")

    def get_effective_config_path(self) -> Path:
        """Get the effective config path, falling back to default if needed."""
        return self.config_path if self.config_path != Path() else Path(CONFIG_FILE)

    def toggle_vessel_mode(self) -> bool:
        """Toggle vessel mode and handle mutual exclusivity. Returns True if changed."""
        if self.use_vessel and self.use_waterline:
            self.use_waterline = False
            return True
        return False

    def toggle_waterline_mode(self) -> bool:
        """Toggle waterline mode and handle mutual exclusivity. Returns True if changed."""
        if self.use_waterline and self.use_vessel:
            self.use_vessel = False
            return True
        return False
