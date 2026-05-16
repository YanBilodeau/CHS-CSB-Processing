"""
Configuration manager for the CSB Processing UI.
Handles all configuration-related operations and state.
"""

from pathlib import Path

from loguru import logger
import i18n

from csb_processing import CONFIG_FILE
from config import get_data_config
from config.processing_config import Filter, CSBprocessingConfig

LOGGER = logger.bind(name="CSB-Processing.ConfigManager")


class ConfigManager:
    """Manages configuration state for the UI application."""

    def __init__(self):
        self.output_path: Path = Path()
        self.config_path: Path = Path(CONFIG_FILE)
        self.vessel_id: str = ""
        self.vessel_name: str = ""
        self.waterline_value: float = 0.0
        self.use_vessel: bool = False
        self.use_waterline: bool = False
        self.apply_water_level: bool = True
        self.already_at_chart_datum: bool = False
        self.merge_files: bool = True

        # Initialiser les filtres et options depuis la config TOML par défaut
        try:
            default_config = get_data_config(config_file=Path(CONFIG_FILE))
            default_filters = {
                f if isinstance(f, str) else f.value
                for f in (default_config.filter.filter_to_apply or [])
            }

        except Exception as e:
            LOGGER.error(f"Error initialising configuration: {e}")
            default_filters = {
                Filter.LATITUDE_FILTER,
                Filter.LONGITUDE_FILTER,
                Filter.TIME_FILTER,
                Filter.SPEED_FILTER,
            }

        self.filter_depth: bool = Filter.DEPTH_FILTER in default_filters
        self.filter_speed: bool = Filter.SPEED_FILTER in default_filters
        self.filter_latitude: bool = Filter.LATITUDE_FILTER in default_filters
        self.filter_longitude: bool = Filter.LONGITUDE_FILTER in default_filters
        self.filter_time: bool = Filter.TIME_FILTER in default_filters

    def update_output_path(self, path_str: str) -> None:
        """Update output path from string input."""
        LOGGER.debug(i18n.t("app.config_manager.updating_output_path", path=path_str))
        self.output_path = Path(path_str).expanduser().resolve() if path_str else Path()
        LOGGER.debug(
            i18n.t("app.config_manager.output_path_updated", path=str(self.output_path))
        )

    def update_config_path(self, path_str: str) -> None:
        """Update config path from string input."""
        LOGGER.debug(i18n.t("app.config_manager.updating_config_path", path=path_str))
        self.config_path = Path(path_str).expanduser().resolve() if path_str else Path()
        LOGGER.debug(
            i18n.t("app.config_manager.config_path_updated", path=str(self.config_path))
        )

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

    def build_processing_config(self) -> CSBprocessingConfig:
        """
        Construit un CSBprocessingConfig avec les filtres sélectionnés dans l'interface.

        :return: La configuration de traitement avec les filtres sélectionnés.
        :rtype: CSBprocessingConfig
        """
        base_config = get_data_config(config_file=self.get_effective_config_path())

        selected_filters = []
        if self.filter_depth:
            selected_filters.append(Filter.DEPTH_FILTER)
        if self.filter_speed:
            selected_filters.append(Filter.SPEED_FILTER)
        if self.filter_latitude:
            selected_filters.append(Filter.LATITUDE_FILTER)
        if self.filter_longitude:
            selected_filters.append(Filter.LONGITUDE_FILTER)
        if self.filter_time:
            selected_filters.append(Filter.TIME_FILTER)

        updated_filter = base_config.filter.model_copy(
            update={"filter_to_apply": selected_filters}
        )
        return base_config.model_copy(update={"filter": updated_filter})
