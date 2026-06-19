"""
File Selection Component module.

Contains the FileSelectionComponent for handling file selection functionality.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Generator, Collection
import tempfile

import i18n
from nicegui import ui, app, events
from loguru import logger

from .protocols import FileManagerProtocol, ValidatorProtocol, FileDisplayProtocol

LOGGER = logger.bind(name="CSB-Processing.FileSelection")


class FileSelectionComponentABC(ABC):
    """ABC for file selection component."""

    def __init__(
        self,
        file_manager: FileManagerProtocol,
        validator: ValidatorProtocol,
        file_display: FileDisplayProtocol,
    ):
        self.file_manager = file_manager
        self.validator = validator
        self.file_display = file_display

        self.files_warning_label = None

    @abstractmethod
    def create(self) -> None:
        """Create the file selection section."""
        ...

    def set_warning_visible(self, visible: bool):
        """Set the visibility of the warning label."""
        if self.files_warning_label is not None:
            self.files_warning_label.visible = visible


class FileSelectionComponentNative(FileSelectionComponentABC):
    """Component for file selection in the native application."""

    def __init__(
        self,
        file_manager: FileManagerProtocol,
        validator: ValidatorProtocol,
        file_display: FileDisplayProtocol,
        accept_props: str = ".csv,.txt,.xyz,.geojson,.*",
        accepted_formats_i18n_key: str = "app.component.file_selection_component.accepted_formats",
        supported_formats_i18n_key: str = "app.component.file_selection_component.supported_formats",
    ):
        """
        Initialise le composant de sélection de fichiers natif.

        :param file_manager: Gestionnaire de fichiers.
        :param validator: Validateur.
        :param file_display: Affichage des fichiers.
        :param accept_props: Extensions acceptées pour le dialogue natif.
        :param accepted_formats_i18n_key: Clé i18n pour les formats acceptés affichés.
        :param supported_formats_i18n_key: Clé i18n pour les formats supportés détaillés.
        """
        super().__init__(file_manager, validator, file_display)
        self.accept_props = accept_props
        self.accepted_formats_i18n_key = accepted_formats_i18n_key
        self.supported_formats_i18n_key = supported_formats_i18n_key

    def create(self):
        """Create the file selection section."""
        ui.label(
            i18n.t("app.component.file_selection_component.file_selection_label")
        ).classes("text-lg font-bold text-red-600")

        # File selection with dialog
        with ui.row().classes("w-full gap-4 items-center"):
            ui.button(
                i18n.t("app.component.file_selection_component.select_files_button"),
                on_click=self._open_file_dialog,
                icon="folder_open",
            ).props("color=primary")

            ui.button(
                i18n.t("app.component.file_selection_component.clear_selection_button"),
                on_click=self._clear_files,
                icon="clear",
            ).props("color=negative outline")

        with ui.row().classes("text-lg items-center mb-6"):
            ui.markdown(i18n.t(self.accepted_formats_i18n_key)).classes(
                "text-center text-gray-600"
            )

            with ui.icon("info").classes("text-blue-500 cursor-pointer ml-2"):
                with ui.menu():
                    with ui.card().classes("max-w-lg p-4"):
                        ui.markdown(i18n.t(self.supported_formats_i18n_key)).classes(
                            "text-sm"
                        )

        # Warning label for files selection (Native)
        self.files_warning_label = ui.label(
            i18n.t("app.component.file_selection_component.files_warning")
        ).classes("text-sm text-red-500")

        # Files display using FileDisplay component
        self.file_display.create()

    async def _open_file_dialog(self):
        """Open file selection dialog using native method."""
        try:
            result = await app.native.main_window.create_file_dialog(
                allow_multiple=True
            )
            if result:
                self._add_selected_files(result)
            else:
                ui.notification(
                    i18n.t("app.component.file_selection_component.no_file_selected"),
                    type="info",
                )

        except Exception as ex:
            LOGGER.error(
                i18n.t(
                    "app.component.file_selection_component.error_open_dialog",
                    error=str(ex),
                )
            )
            ui.notification(
                i18n.t(
                    "app.component.file_selection_component.error_open_dialog",
                    error=str(ex),
                ),
                type="negative",
            )

    def _add_selected_files(self, file_paths: Collection[Path]):
        """Add selected files from dialog."""
        try:
            added_count = self.file_manager.add_files(file_paths)
            self.file_display.update()

            if self.validator.validate_file_selection():
                self.set_warning_visible(False)

            if added_count > 0:
                ui.notification(
                    i18n.t(
                        "app.component.file_selection_component.files_added",
                        count=added_count,
                    ),
                    type="positive",
                )
            elif len(file_paths) > 0:
                ui.notification(
                    i18n.t("app.component.file_selection_component.no_new_files"),
                    type="info",
                )

        except Exception as ex:
            LOGGER.error(
                i18n.t(
                    "app.component.file_selection_component.error_adding_files",
                    error=str(ex),
                )
            )
            ui.notification(
                i18n.t(
                    "app.component.file_selection_component.error_adding_files",
                    error=str(ex),
                ),
                type="negative",
            )

    def _clear_files(self):
        """Clear all selected files."""
        self.file_manager.clear_files()
        self.file_display.update()

        if not self.validator.validate_file_selection():
            self.set_warning_visible(True)
        ui.notification(
            i18n.t("app.component.file_selection_component.all_files_removed"),
            type="info",
        )


class FileSelectionComponentWeb(FileSelectionComponentABC):
    """Component for file selection in the web application."""

    def __init__(
        self,
        file_manager: FileManagerProtocol,
        validator: ValidatorProtocol,
        file_display: FileDisplayProtocol,
        accept_props: str = ".csv,.txt,.xyz,.geojson,.*",
        accepted_formats_i18n_key: str = "app.component.file_selection_component.web_accepted_formats",
        supported_formats_i18n_key: str = "app.component.file_selection_component.supported_formats",
    ):
        """
        Initialise le composant de sélection de fichiers web.

        :param file_manager: Gestionnaire de fichiers.
        :param validator: Validateur.
        :param file_display: Affichage des fichiers.
        :param accept_props: Extensions acceptées pour l'upload HTML.
        :param accepted_formats_i18n_key: Clé i18n pour les formats acceptés affichés.
        :param supported_formats_i18n_key: Clé i18n pour les formats supportés détaillés.
        """
        super().__init__(file_manager, validator, file_display)
        self.upload_component = None
        self.accept_props = accept_props
        self.accepted_formats_i18n_key = accepted_formats_i18n_key
        self.supported_formats_i18n_key = supported_formats_i18n_key

    def create(self) -> None:
        """Create the file selection section."""
        ui.label(
            i18n.t("app.component.file_selection_component.file_selection_label")
        ).classes("text-lg font-bold text-red-600")

        # File upload section
        with ui.row().classes("w-full gap-4 items-center"):
            self.upload_component = (
                ui.upload(
                    on_upload=self._handle_upload,
                    on_rejected=self._handle_rejected,
                    multiple=True,
                    max_file_size=100_000_000,  # 100MB max per file
                    max_total_size=500_000_000,  # 500MB max total
                    max_files=50,  # Maximum 50 files
                    auto_upload=True,
                )
                .props(f"color=primary accept='{self.accept_props}'")
                .classes("w-full")
            )

            ui.button(
                i18n.t("app.component.file_selection_component.clear_selection_button"),
                on_click=self._clear_files,
                icon="clear",
            ).props("color=negative outline")

            self.file_display.create()

        with ui.row().classes("justify-center items-center mb-6"):
            ui.markdown(i18n.t(self.accepted_formats_i18n_key)).classes(
                "text-center text-gray-600"
            )

            with ui.icon("info").classes("text-blue-500 cursor-pointer ml-2"):
                with ui.menu():
                    with ui.card().classes("max-w-lg p-4"):
                        ui.markdown(i18n.t(self.supported_formats_i18n_key)).classes(
                            "text-sm"
                        )

        # Warning label for files selection (Web)
        self.files_warning_label = ui.label(
            i18n.t("app.component.file_selection_component.files_warning")
        ).classes("text-sm text-red-500")

    def _handle_upload(self, event: events.UploadEventArguments):
        """Handle file upload event."""
        try:
            file_path_generator = self._save_uploaded_file(event)
            file_path = next(file_path_generator, None)
            if file_path and file_path.exists():
                self._add_uploaded_files((file_path,))

        except Exception as ex:
            LOGGER.error(
                i18n.t(
                    "app.component.file_selection_component.error_handling_upload",
                    error=str(ex),
                )
            )
            ui.notification(
                i18n.t(
                    "app.component.file_selection_component.error_handling_upload",
                    error=str(ex),
                ),
                type="negative",
            )

    @staticmethod
    def _handle_rejected(event: events.UiEventArguments):
        """Handle rejected file uploads."""
        ui.notification(
            i18n.t("app.component.file_selection_component.files_rejected"),
            type="warning",
        )

    @staticmethod
    def _save_uploaded_file(
        file_info: events.UploadEventArguments,
    ) -> Generator[Path, None, None]:
        """Save uploaded file content and return file path."""
        try:
            temp_dir = Path(tempfile.gettempdir())
            file_path = temp_dir / file_info.name

            # Créer le fichier avec le nom original
            file_info.content.seek(0)
            with open(file_path, "wb") as temp_file:
                temp_file.write(file_info.content.read())

            yield file_path

            if file_path.exists():
                file_path.unlink()

        except Exception as ex:
            LOGGER.error(
                i18n.t(
                    "app.component.file_selection_component.error_saving_upload",
                    name=file_info.name,
                    error=str(ex),
                )
            )

    def _add_uploaded_files(self, file_paths: Collection[Path]):
        """Add uploaded files to file manager."""
        try:
            added_count = self.file_manager.add_files(file_paths)
            self.file_display.update()

            if self.validator.validate_file_selection():
                self.set_warning_visible(False)

            if added_count > 0:
                ui.notification(
                    i18n.t(
                        "app.component.file_selection_component.files_uploaded",
                        count=added_count,
                    ),
                    type="positive",
                )
            elif len(file_paths) > 0:
                ui.notification(
                    i18n.t("app.component.file_selection_component.no_new_files"),
                    type="info",
                )

        except Exception as ex:
            LOGGER.error(
                i18n.t(
                    "app.component.file_selection_component.error_adding_uploaded",
                    error=str(ex),
                )
            )
            ui.notification(
                i18n.t(
                    "app.component.file_selection_component.error_adding_uploaded",
                    error=str(ex),
                ),
                type="negative",
            )

    def _clear_files(self):
        """Clear all selected files."""
        self.file_manager.clear_files()
        self.file_display.update()

        # Reset upload component
        if self.upload_component:
            self.upload_component.reset()

        if not self.validator.validate_file_selection():
            self.set_warning_visible(True)
        ui.notification(
            i18n.t("app.component.file_selection_component.all_files_removed"),
            type="info",
        )
