"""
Options Component module.

Contains the OptionsComponent for handling processing options functionality.
"""

from pathlib import Path

import i18n
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
        self.vessel_name_input = None
        self.waterline_input = None
        self.output_warning_label = None
        self.apply_water_level_checkbox = None
        self.already_at_chart_datum_warning = None

        self.ui_event_handler = ui_event_handler
        self.config_manager = config_manager

    def _handle_output_path_change(self, e):
        """Handle output path change."""
        self.ui_event_handler.update_output_path(e.args[0])
        if self.output_warning_label:
            if e.args[0] and e.args[0].strip():
                self.output_warning_label.style("visibility: hidden")
            else:
                self.output_warning_label.style("visibility: visible")

    def _handle_config_path_change(self, e):
        """Handle config path change."""
        self.ui_event_handler.update_config_path(e.args[0])

    async def _handle_select_output_directory(self):
        """Handle output directory selection."""
        try:
            selected_path = await self.ui_event_handler.select_output_directory()
            if selected_path and self.output_input:
                self.output_input.value = selected_path
                if self.output_warning_label and selected_path.strip():
                    self.output_warning_label.style("visibility: hidden")
        except Exception as ex:
            LOGGER.error(
                i18n.t(
                    "app.component.options_component.error_log_select_output",
                    error=str(ex),
                )
            )
            ui.notification(
                i18n.t(
                    "app.component.options_component.error_open_dir_dialog",
                    error=str(ex),
                ),
                type="negative",
            )

    async def _handle_select_config_file(self) -> None:
        """Handle config file selection."""
        try:
            selected_path = await self.ui_event_handler.select_config_file()
            if selected_path and self.config_input:
                self.config_input.value = selected_path
        except Exception as ex:
            LOGGER.error(
                i18n.t(
                    "app.component.options_component.error_log_select_config",
                    error=str(ex),
                )
            )
            ui.notification(
                i18n.t(
                    "app.component.options_component.error_open_file_dialog",
                    error=str(ex),
                ),
                type="negative",
            )

    def _handle_already_at_chart_datum_toggle(self, e) -> None:
        """Handle 'Already at chart datum' toggle: disable/enable Apply water level accordingly."""
        is_checked: bool = e.value
        if is_checked:
            self.config_manager.apply_water_level = False
            if self.apply_water_level_checkbox:
                self.apply_water_level_checkbox.value = False
                self.apply_water_level_checkbox.disable()
            if self.already_at_chart_datum_warning:
                self.already_at_chart_datum_warning.style("visibility: visible")
        else:
            if self.apply_water_level_checkbox:
                self.apply_water_level_checkbox.enable()
            if self.already_at_chart_datum_warning:
                self.already_at_chart_datum_warning.style("visibility: hidden")

    def _handle_vessel_toggle(self):
        """Handle vessel option toggle."""
        try:
            waterline_disabled = self.ui_event_handler.toggle_vessel()
            if waterline_disabled:
                ui.notification(
                    i18n.t("app.component.options_component.waterline_option_disabled"),
                    type="info",
                )
                if self.waterline_input:
                    self.waterline_input.style("visibility: hidden")
            if self.vessel_input:
                if self.config_manager.use_vessel:
                    self.vessel_input.style("visibility: visible")
                else:
                    self.vessel_input.style("visibility: hidden")
        except Exception as ex:
            LOGGER.error(
                i18n.t(
                    "app.component.options_component.error_log_vessel_toggle",
                    error=str(ex),
                )
            )
            ui.notification(
                i18n.t(
                    "app.component.options_component.error_notif_vessel_toggle",
                    error=str(ex),
                ),
                type="negative",
            )

    def _handle_waterline_toggle(self):
        """Handle waterline option toggle."""
        try:
            vessel_disabled = self.ui_event_handler.toggle_waterline()
            if vessel_disabled:
                ui.notification(
                    i18n.t("app.component.options_component.vessel_option_disabled"),
                    type="info",
                )
                if self.vessel_input:
                    self.vessel_input.style("visibility: hidden")
            if self.waterline_input:
                if self.config_manager.use_waterline:
                    self.waterline_input.style("visibility: visible")
                else:
                    self.waterline_input.style("visibility: hidden")
        except Exception as ex:
            LOGGER.error(
                i18n.t(
                    "app.component.options_component.error_log_waterline_toggle",
                    error=str(ex),
                )
            )
            ui.notification(
                i18n.t(
                    "app.component.options_component.error_notif_waterline_toggle",
                    error=str(ex),
                ),
                type="negative",
            )

    def create(self):
        """Create the options section."""
        ui.separator()
        ui.label(i18n.t("app.component.options_component.section_title")).classes(
            "text-lg font-bold mt-4"
        )

        with ui.row().classes("w-full gap-8"):
            self._create_left_column()
            self._create_right_column()

        if self.config_manager:
            self._create_water_vessel_rows()

            if self.config_manager.already_at_chart_datum:
                self.apply_water_level_checkbox.value = False
                self.apply_water_level_checkbox.disable()
                self.already_at_chart_datum_warning.style("visibility: visible")
            else:
                self.already_at_chart_datum_warning.style("visibility: hidden")

            self._create_filter_section()

    def _create_water_vessel_rows(self):
        """
        Three paired rows with matching flex-1 halves inside a column with uniform gap:
          Row 1 — Apply water level (left)  |  Specify waterline + input (right)
          Row 2 — Already at chart datum + warning (left)  |  Use vessel identifier + input (right)
          Row 3 — Merge files (left)  |  Vessel name input (right)
        Each checkbox is wrapped in a fixed-width div (13rem) so both inputs always
        start at the same horizontal position regardless of label length.
        All rows share the same vertical gap via the wrapping column (gap-4).
        """
        with ui.column().classes("w-full gap-4"):
            # ── Row 1 ────────────────────────────────────────────────────────────────
            with ui.row().classes("w-full items-center gap-8"):
                with ui.element("div").classes("flex-1"):
                    self.apply_water_level_checkbox = (
                        ui.checkbox(
                            i18n.t("app.component.options_component.apply_water_level")
                        )
                        .bind_value(self.config_manager, "apply_water_level")
                        .tooltip(
                            i18n.t(
                                "app.component.options_component.apply_water_level_tooltip"
                            )
                        )
                    )

                with ui.row().classes("flex-1 items-center gap-0"):
                    with ui.element("div").style("width: 13rem; flex-shrink: 0"):
                        ui.checkbox(
                            i18n.t("app.component.options_component.specify_waterline"),
                            on_change=self._handle_waterline_toggle,
                        ).bind_value(self.config_manager, "use_waterline").tooltip(
                            i18n.t(
                                "app.component.options_component.specify_waterline_tooltip"
                            )
                        )

                    self.waterline_input = (
                        ui.number(
                            i18n.t(
                                "app.component.options_component.waterline_input_label"
                            ),
                            min=0.0,
                            step=0.01,
                            format="%.3f",
                        )
                        .bind_value(self.config_manager, "waterline_value")
                        .classes("flex-1")
                    )

            if not self.config_manager.use_waterline:
                self.waterline_input.style("visibility: hidden")

            # ── Row 2 ────────────────────────────────────────────────────────────────
            with ui.row().classes("w-full items-start gap-8"):
                with ui.element("div").classes("flex-1"):
                    ui.checkbox(
                        i18n.t(
                            "app.component.options_component.already_at_chart_datum"
                        ),
                        on_change=self._handle_already_at_chart_datum_toggle,
                    ).bind_value(self.config_manager, "already_at_chart_datum").tooltip(
                        i18n.t(
                            "app.component.options_component.already_at_chart_datum_tooltip"
                        )
                    )
                    # Warning label — always occupies space (visibility: hidden keeps layout stable)
                    self.already_at_chart_datum_warning = (
                        ui.label(
                            i18n.t(
                                "app.component.options_component.already_at_chart_datum_warning"
                            )
                        )
                        .classes("text-sm text-orange-600")
                        .style("visibility: hidden")
                    )

                with ui.row().classes("flex-1 items-center gap-0"):
                    with ui.element("div").style("width: 13rem; flex-shrink: 0"):
                        ui.checkbox(
                            i18n.t(
                                "app.component.options_component.use_vessel_identifier"
                            ),
                            on_change=self._handle_vessel_toggle,
                        ).bind_value(self.config_manager, "use_vessel").tooltip(
                            i18n.t(
                                "app.component.options_component.use_vessel_identifier_tooltip"
                            )
                        )

                    self.vessel_input = (
                        ui.input(
                            i18n.t(
                                "app.component.options_component.vessel_identifier_input"
                            )
                        )
                        .bind_value(self.config_manager, "vessel_id")
                        .classes("flex-1")
                    )

            if not self.config_manager.use_vessel:
                self.vessel_input.style("visibility: hidden")

            # ── Row 3 — Merge files + Vessel name ────────────────────────────────────
            with ui.row().classes("w-full items-center gap-8"):
                with ui.element("div").classes("flex-1"):
                    ui.checkbox(
                        i18n.t("app.component.options_component.merge_files")
                    ).bind_value(self.config_manager, "merge_files").tooltip(
                        i18n.t("app.component.options_component.merge_files_tooltip")
                    )

                with ui.element("div").classes("flex-1"):
                    self.vessel_name_input = (
                        ui.input(
                            i18n.t("app.component.options_component.vessel_name_input"),
                            placeholder=i18n.t(
                                "app.component.options_component.vessel_name_placeholder"
                            ),
                        )
                        .bind_value(self.config_manager, "vessel_name")
                        .classes("w-full")
                        .tooltip(
                            i18n.t(
                                "app.component.options_component.vessel_name_tooltip"
                            )
                        )
                    )

    def _create_filter_section(self):
        """Create the filter checkboxes section."""
        ui.separator()
        ui.label(i18n.t("app.component.options_component.filters_title")).classes(
            "text-base font-bold mt-2"
        )
        ui.label(i18n.t("app.component.options_component.filters_hint")).classes(
            "text-sm text-gray-500 mb-1"
        )

        with ui.row().classes("gap-6 flex-wrap"):
            ui.checkbox(
                i18n.t("app.component.options_component.filter_depth")
            ).bind_value(self.config_manager, "filter_depth").tooltip(
                i18n.t("app.component.options_component.filter_depth_tooltip")
            )

            ui.checkbox(
                i18n.t("app.component.options_component.filter_speed")
            ).bind_value(self.config_manager, "filter_speed").tooltip(
                i18n.t("app.component.options_component.filter_speed_tooltip")
            )

            ui.checkbox(
                i18n.t("app.component.options_component.filter_latitude")
            ).bind_value(self.config_manager, "filter_latitude").tooltip(
                i18n.t("app.component.options_component.filter_latitude_tooltip")
            )

            ui.checkbox(
                i18n.t("app.component.options_component.filter_longitude")
            ).bind_value(self.config_manager, "filter_longitude").tooltip(
                i18n.t("app.component.options_component.filter_longitude_tooltip")
            )

            ui.checkbox(
                i18n.t("app.component.options_component.filter_time")
            ).bind_value(self.config_manager, "filter_time").tooltip(
                i18n.t("app.component.options_component.filter_time_tooltip")
            )

    def _create_left_column(self):
        """Create left column: output directory path."""
        with ui.column().classes("flex-1"):
            ui.label(
                i18n.t("app.component.options_component.output_dir_label")
            ).classes("font-bold text-red-600")

            with ui.row().classes("w-full gap-2"):
                self.output_input = (
                    ui.input(
                        placeholder=i18n.t(
                            "app.component.options_component.output_dir_placeholder"
                        ),
                        validation={
                            i18n.t(
                                "app.component.options_component.output_dir_validation_required"
                            ): lambda value: bool(value and value.strip())
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
                ).props("color=primary outline").tooltip(
                    i18n.t("app.component.options_component.output_dir_select_tooltip")
                )

            # CSS visibility preserves layout space — no element shift on hide
            self.output_warning_label = ui.label(
                i18n.t("app.component.options_component.output_dir_warning")
            ).classes("text-sm text-red-500")

    def _create_right_column(self):
        """Create right column: configuration file path."""
        with ui.column().classes("flex-1"):
            ui.label(
                i18n.t("app.component.options_component.config_file_label")
            ).classes("font-bold")

            with ui.row().classes("w-full gap-2"):
                self.config_input = (
                    ui.input(
                        value=str(self.config_path),
                        placeholder=i18n.t(
                            "app.component.options_component.config_file_placeholder"
                        ),
                    )
                    .classes("flex-1")
                    .on("update:model-value", self._handle_config_path_change)
                )

                ui.button(
                    icon="settings",
                    on_click=self._handle_select_config_file,
                ).props("color=secondary outline").tooltip(
                    i18n.t("app.component.options_component.config_file_select_tooltip")
                )

            ui.label(
                i18n.t("app.component.options_component.config_file_hint")
            ).classes("text-sm text-gray-500")
