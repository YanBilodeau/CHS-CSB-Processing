"""
Options Component module.

Contains the OptionsComponent for handling processing options functionality.
"""

from pathlib import Path

from nicegui import ui
from loguru import logger

from .protocols import ConfigManagerProtocol, EventHandlerProtocol

LOGGER = logger.bind(name="CSB-Processing.Options")


class OptionsComponent:
    """Component for processing options."""

    def __init__(
        self,
        config_path: Path,
        config_manager: ConfigManagerProtocol,
        ui_event_handler: EventHandlerProtocol,
    ) -> None:
        self.config_path = config_path
        self.output_input = None
        self.config_input = None
        self.vessel_input = None
        self.waterline_input = None
        self.output_warning_label = None

        self.ui_event_handler = ui_event_handler
        self.config_manager = config_manager

    def _handle_output_path_change(self, e):
        """Handle output path change."""
        self.ui_event_handler.update_output_path(e.args[0])
        # Update warning visibility based on validation result
        if self.output_warning_label:
            # Assume empty path is invalid for simplicity
            self.output_warning_label.visible = not bool(
                e.args[0] and e.args[0].strip()
            )

    def _handle_config_path_change(self, e):
        """Handle config path change."""
        self.ui_event_handler.update_config_path(e.args[0])

    def _handle_select_output_directory(self):
        """Handle output directory selection."""
        try:
            selected_path = self.ui_event_handler.select_output_directory()
            if selected_path and self.output_input:
                self.output_input.value = selected_path
                # Cacher le label d'avertissement si un chemin valide est sélectionné
                if self.output_warning_label and selected_path.strip():
                    self.output_warning_label.visible = False

        except Exception as ex:
            LOGGER.error(f"Error in select_output_directory: {ex}")
            ui.notification(
                f"Error opening directory dialog: {str(ex)}", type="negative"
            )

    def _handle_select_config_file(self):
        """Handle config file selection."""
        try:
            selected_path = self.ui_event_handler.select_config_file()
            if selected_path and self.config_input:
                self.config_input.value = selected_path
        except Exception as ex:
            LOGGER.error(f"Error in select_config_file: {ex}")
            ui.notification(f"Error opening file dialog: {str(ex)}", type="negative")

    def _handle_vessel_toggle(self):
        """Handle vessel option toggle."""
        try:
            waterline_disabled = self.ui_event_handler.toggle_vessel()
            if waterline_disabled:
                ui.notification("Waterline option disabled", type="info")
        except Exception as ex:
            LOGGER.error(f"Error in vessel toggle: {ex}")
            ui.notification(f"Error toggling vessel option: {str(ex)}", type="negative")

    def _handle_waterline_toggle(self):
        """Handle waterline option toggle."""
        try:
            vessel_disabled = self.ui_event_handler.toggle_waterline()
            if vessel_disabled:
                ui.notification("Vessel identifier option disabled", type="info")
        except Exception as ex:
            LOGGER.error(f"Error in waterline toggle: {ex}")
            ui.notification(
                f"Error toggling waterline option: {str(ex)}", type="negative"
            )

    def create(self):
        """Create the options section."""
        ui.separator()
        ui.label("Processing Options").classes("text-lg font-bold mt-4")

        with ui.row().classes("w-full gap-8"):
            self._create_left_column()
            self._create_right_column()

        if self.config_manager:
            ui.checkbox("Apply water level reduction", value=True).bind_value(
                self.config_manager, "apply_water_level"
            )

    def _create_left_column(self):
        """Create left column of options."""
        with ui.column().classes("flex-1"):
            ui.label("Output Directory *").classes("font-bold text-red-600")

            with ui.row().classes("w-full gap-2"):
                self.output_input = (
                    ui.input(
                        placeholder="Output directory path",
                        validation={
                            "Required": lambda value: bool(value and value.strip())
                        },
                    )
                    .classes("flex-1")
                    .on("update:model-value", self._handle_output_path_change)
                )

                if self.config_manager and self.config_manager.output_path != Path():
                    self.output_input.value = str(self.config_manager.output_path)

                ui.button(
                    icon="folder",
                    on_click=self._handle_select_output_directory,
                ).props("color=primary outline").tooltip("Select directory")

            self.output_warning_label = ui.label(
                "⚠️ Required: Specify where to save processed files"
            ).classes("text-sm text-red-500")

            if self.config_manager:
                ui.checkbox(
                    "Use vessel identifier", on_change=self._handle_vessel_toggle
                ).bind_value(self.config_manager, "use_vessel")

                self.vessel_input = ui.input("Vessel identifier").bind_value(
                    self.config_manager, "vessel_id"
                )
                self.vessel_input.bind_visibility_from(
                    self.config_manager, "use_vessel"
                )

    def _create_right_column(self):
        """Create right column of options."""
        with ui.column().classes("flex-1"):
            ui.label("Configuration File").classes("font-bold")

            with ui.row().classes("w-full gap-2"):
                self.config_input = (
                    ui.input(
                        value=str(self.config_path),
                        placeholder="Configuration file path (optional)",
                    )
                    .classes("flex-1")
                    .on("update:model-value", self._handle_config_path_change)
                )

                ui.button(
                    icon="settings",
                    on_click=self._handle_select_config_file,
                ).props("color=secondary outline").tooltip("Select TOML file")

            ui.label(
                "If no configuration file is provided, the default file will be used."
            ).classes("text-sm text-gray-500")

            if self.config_manager:
                ui.checkbox(
                    "Specify waterline", on_change=self._handle_waterline_toggle
                ).bind_value(self.config_manager, "use_waterline")

                self.waterline_input = ui.number(
                    "Waterline (m)", min=0.0, step=0.001, format="%.3f"
                ).bind_value(self.config_manager, "waterline_value")
                self.waterline_input.bind_visibility_from(
                    self.config_manager, "use_waterline"
                )
