"""
Fonctions partagées de validation de fichiers pour le CLI et l'interface web.

Ce module évite la duplication de ``is_valid_file`` et ``get_files`` entre
``src/cli.py`` et ``src/app/processing_handler.py``.
"""

from collections.abc import Collection
from pathlib import Path

#: Extensions de fichier acceptées par défaut pour les données bathymétriques brutes.
DEFAULT_ALLOWED_EXTENSIONS: frozenset[str] = frozenset(
    {".csv", ".txt", ".xyz", ".geojson"}
)


def is_valid_file(
    file: Path,
    *,
    allowed_extensions: frozenset[str] | set[str] | None = None,
    allow_numeric: bool = True,
) -> bool:
    """
    Vérifie si le fichier est valide pour le traitement.

    Un fichier est valide si son extension (suffixe) appartient à l'ensemble
    ``allowed_extensions`` ou, lorsque ``allow_numeric`` est activé, si son
    extension est un nombre (ex: ``.1``, ``.2``, ``.3``).

    :param file: Chemin du fichier à vérifier.
    :type file: Path
    :param allowed_extensions: Extensions autorisées.
        Par défaut : ``{".csv", ".txt", ".xyz", ".geojson"}``.
    :type allowed_extensions: frozenset[str] | set[str] | None
    :param allow_numeric: Accepter les extensions numériques (ex: .1, .2, .3).
    :type allow_numeric: bool
    :return: Vrai si le fichier est valide, faux sinon.
    :rtype: bool
    """
    if allowed_extensions is None:
        allowed_extensions = DEFAULT_ALLOWED_EXTENSIONS

    extension: str = file.suffix.lower()

    if extension in allowed_extensions:
        return True

    if allow_numeric and extension.startswith(".") and extension[1:].isdigit():
        return True

    return False


def get_files(
    paths: Collection[Path],
    *,
    allowed_extensions: frozenset[str] | set[str] | None = None,
    allow_numeric: bool = True,
) -> list[Path]:
    """
    Récupère les fichiers à traiter à partir d'une collection de chemins.

    Les répertoires sont explorés récursivement (``**/*``).

    :param paths: Chemins des fichiers ou répertoires.
    :type paths: Collection[Path]
    :param allowed_extensions: Extensions autorisées.
        Par défaut : ``{".csv", ".txt", ".xyz", ".geojson"}``.
    :type allowed_extensions: frozenset[str] | set[str] | None
    :param allow_numeric: Accepter les extensions numériques.
    :type allow_numeric: bool
    :return: Liste des fichiers valides trouvés.
    :rtype: list[Path]
    """
    files: list[Path] = []

    for path in paths:
        path = Path(path)

        if path.is_file() and is_valid_file(
            path, allowed_extensions=allowed_extensions, allow_numeric=allow_numeric
        ):
            files.append(path)

        elif path.is_dir():
            files.extend(
                file
                for file in path.glob("**/*")
                if is_valid_file(
                    file,
                    allowed_extensions=allowed_extensions,
                    allow_numeric=allow_numeric,
                )
            )

    return files
