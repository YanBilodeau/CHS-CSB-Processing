"""
Protocols module for the CSB Processing application.

Contains all protocol definitions for type checking and interface contracts.
"""

from pathlib import Path
from typing import Protocol, Collection


class FileManagerProtocol(Protocol):
    """Protocol for file management operations."""

    def add_files(self, file_paths: Collection[Path]) -> int:
        """Add files to the manager and return the count of added files."""
        ...

    def clear_files(self):
        """Clear all managed files."""
        ...


class ValidatorProtocol(Protocol):
    """Protocol for validation operations."""

    def validate_file_selection(self) -> bool:
        """Validate if at least one file is selected."""
        ...


class FileDisplayProtocol(Protocol):
    """Protocol for file display operations."""

    def update(self):
        """Update the file display with current files."""
        ...

    def create(self):
        """Create the file display component."""
        ...


class ThemeManagerProtocol(Protocol):
    """Protocol for theme management operations."""

    def create_theme_button(self):
        """Create a button to toggle themes."""
        ...


class ConfigManagerProtocol(Protocol):
    """Protocol for configuration management operations."""

    output_path: Path
    config_path: Path
    vessel_id: str
    waterline_value: float
    use_vessel: bool
    use_waterline: bool
    apply_water_level: bool


class EventHandlerProtocol(Protocol):
    """Protocol for event handling operations."""

    def update_output_path(self, path: str) -> None:
        """Update the output path."""
        ...

    def update_config_path(self, path: str) -> None:
        """Update the configuration path."""
        ...

    async def select_output_directory(self) -> str:
        """Select an output directory and return the path."""
        ...

    async def select_config_file(self) -> str:
        """Select a configuration file and return the path."""
        ...

    def toggle_vessel(self) -> bool:
        """Toggle the vessel option and return True if waterline was disabled."""
        ...

    def toggle_waterline(self) -> bool:
        """Toggle the waterline option and return True if vessel was disabled."""
        ...
