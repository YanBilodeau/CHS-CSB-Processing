"""Theme Manager for NiceGUI Application"""

from nicegui import ui
from loguru import logger

LOGGER = logger.bind(name="CSB-Processing.ThemeManager")


class ThemeManager:
    """Gestionnaire des thèmes de l'interface utilisateur."""

    def __init__(self, dark_mode: bool = True) -> None:
        self.dark_mode = ui.dark_mode(value=dark_mode)
        self.theme_button = None

    def create_theme_button(self) -> ui.button:
        """Crée le bouton de basculement de thème."""
        self.theme_button = (
            ui.button(
                icon=("light_mode" if not self.dark_mode.value else "dark_mode"),
                on_click=self.toggle_theme,
            )
            .props("flat round")
            .tooltip("Toggle theme")
        )
        return self.theme_button

    def toggle_theme(self) -> None:
        """Bascule entre le thème clair et sombre."""
        # Toggle dark mode
        self.dark_mode.value = not self.dark_mode.value

        # Change the icon based on the current theme
        if self.dark_mode.value:
            # For dark theme, use moon icon
            self.theme_button.icon = "dark_mode"
            ui.notification("Dark theme activated", type="info")
        else:
            # For light theme, use sun icon
            self.theme_button.icon = "light_mode"
            ui.notification("Light theme activated", type="info")

        LOGGER.debug(
            f"Theme switched to: {'Dark' if self.dark_mode.value else 'Light'}"
        )

    @staticmethod
    def add_theme_styles() -> None:
        """Ajoute les styles CSS personnalisés pour les thèmes."""
        ui.add_head_html(
            """
        <style>
        .status-flashing {
            animation: statusFlash 4s ease-in-out infinite;
        }

        @keyframes statusFlash {
            0%, 100% {
                opacity: 1;
            }
            50% {
                opacity: 0.3;
            }
        }
        </style>
        """
        )
