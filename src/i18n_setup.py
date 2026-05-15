from pathlib import Path
import ctypes

import i18n


def run_once(func):
    """Décorateur pour s'assurer qu'une fonction ne s'exécute qu'une fois"""

    def wrapper(*args, **kwargs):
        if not hasattr(wrapper, "has_run"):
            wrapper.has_run = True
            return func(*args, **kwargs)

        return None

    return wrapper


def get_display_language():
    try:
        language_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
        # Tous les codes de langue français commencent par 0x0C
        if (language_id & 0x00FF) == 0x000C:  # Toutes variantes du français
            return "fr"
        elif (language_id & 0x00FF) == 0x0009:  # Toutes variantes de l'anglais
            return "en"
        else:
            return "en"  # défaut

    except AttributeError:
        return "en"  # Fallback pour les systèmes non-Windows


@run_once
def setup_i18n():
    """Configure i18n with the application settings"""
    locale_path = Path(__file__).parents[1] / "locale"
    i18n.load_path.append(locale_path)
    i18n.set("fallback", "en")
    i18n.set("locale", get_display_language())
    i18n.set("enable_memoization", True)
