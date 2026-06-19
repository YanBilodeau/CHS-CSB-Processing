"""
Convert Options Component module.

Contains the ConvertOptionsComponent for handling conversion format options.
"""

import i18n
from nicegui import ui
from loguru import logger

from config.processing_config import FileTypes

LOGGER = logger.bind(name="CSB-Processing.ConvertOptions")


class ConvertOptionsComponent:
    """Component for conversion format options."""

    def __init__(self) -> None:
        """Initialise le composant d'options de conversion."""
        self.format_checkboxes: dict[FileTypes, ui.checkbox] = {}
        self.group_by_iho_checkbox: ui.checkbox | None = None

    @property
    def selected_formats(self) -> set[FileTypes]:
        """
        Retourne les formats de sortie sélectionnés.

        :return: Ensemble des types de fichiers sélectionnés.
        :rtype: set[FileTypes]
        """
        return {fmt for fmt, cb in self.format_checkboxes.items() if cb.value}

    @property
    def group_by_iho_order(self) -> bool:
        """
        Retourne si le regroupement par ordre IHO est activé.

        :return: True si le regroupement IHO est activé.
        :rtype: bool
        """
        if self.group_by_iho_checkbox:
            return self.group_by_iho_checkbox.value

        return False

    def create(self) -> None:
        """Create the convert options section."""
        ui.label(
            i18n.t("app.component.convert_options_component.section_title")
        ).classes("text-lg font-bold mt-4")

        ui.label(
            i18n.t("app.component.convert_options_component.formats_hint")
        ).classes("text-sm text-gray-500 mb-1")

        with ui.row().classes("gap-6 flex-wrap"):
            self.format_checkboxes[FileTypes.GPKG] = ui.checkbox(
                i18n.t("app.component.convert_options_component.format_gpkg")
            )

            self.format_checkboxes[FileTypes.GEOJSON] = ui.checkbox(
                i18n.t("app.component.convert_options_component.format_geojson")
            )

            self.format_checkboxes[FileTypes.CSAR] = ui.checkbox(
                i18n.t("app.component.convert_options_component.format_csar")
            )

            self.format_checkboxes[FileTypes.PARQUET] = ui.checkbox(
                i18n.t("app.component.convert_options_component.format_parquet")
            )

            self.format_checkboxes[FileTypes.FEATHER] = ui.checkbox(
                i18n.t("app.component.convert_options_component.format_feather")
            )

            self.format_checkboxes[FileTypes.CSV] = ui.checkbox(
                i18n.t("app.component.convert_options_component.format_csv")
            )

            self.format_checkboxes[FileTypes.GEOTIFF] = ui.checkbox(
                i18n.t("app.component.convert_options_component.format_geotiff")
            )

        self.group_by_iho_checkbox = ui.checkbox(
            i18n.t("app.component.convert_options_component.group_by_iho_order")
        ).tooltip(
            i18n.t("app.component.convert_options_component.group_by_iho_order_tooltip")
        )
