"""
Module d'export PDF pour les tableaux de métadonnées.

Utilise l'API orientée objet de matplotlib afin de ne pas dépendre de Chrome
ni de Kaleido. Chaque étape de la construction du PDF est isolée dans sa propre
fonction (principe de responsabilité unique).
"""

import textwrap
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd
from loguru import logger

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure
    from matplotlib.table import Table


LOGGER = logger.bind(name="CSB-Processing.Metadata.PdfExport")

# ── Constantes de couleur ─────────────────────────────────────────────────────
# Correspondent aux constantes HEADER_COLOR / CELL_COLOR de plot.py,
# recopiées ici pour éviter toute importation circulaire.

#: Couleur d'en-tête : "rgba(205,92,92, 1.0)" convertie en tuple RGBA [0-1].
_HEADER_RGBA: tuple[float, float, float, float] = (205 / 255, 92 / 255, 92 / 255, 1.0)

#: Couleur de fond des cellules de données.
_CELL_COLOR: str = "lavender"

# ── Constantes de mise en page ────────────────────────────────────────────────
#: Largeur de wrap (caractères) de la colonne « Metadata »,
#: calibrée sur colWidth=0.40 à fontsize 9.
_WRAP_COL0: int = 32

#: Largeur de wrap (caractères) de la colonne « Value »,
#: calibrée sur colWidth=0.55 à fontsize 9.
_WRAP_COL1: int = 44

#: Hauteur visuelle par ligne de texte (pouces).
_LINE_HEIGHT_IN: float = 0.22

#: Unités de hauteur allouées à la ligne d'en-tête (plus haute que les données).
_HEADER_UNITS: float = 1.5

#: Fraction de la hauteur d'axes occupée par le tableau (marge autour du bord).
_TABLE_FRACTION: float = 0.88

#: Largeur de page A4 en pouces.
_PAGE_WIDTH_IN: float = 8.27

#: Hauteur maximale de page A4 en pouces.
_PAGE_MAX_HEIGHT_IN: float = 11.69


# ── Fonctions internes ────────────────────────────────────────────────────────


def _format_cell_value(metadata: str, value: object) -> str:
    """
    Applique les règles de formatage métier à la valeur d'une cellule.

    :param metadata: Nom de la métadonnée (clé de la ligne).
    :type metadata: str
    :param value: Valeur brute de la cellule.
    :type value: object
    :return: Valeur formatée en chaîne de caractères.
    :rtype: str
    """
    if metadata == "Sounding Count Within Order":
        try:
            return f"{int(value):,}"  # type: ignore[arg-type]
        except (ValueError, TypeError):
            pass
    try:
        if pd.isna(value):  # type: ignore[arg-type]
            return ""
    except (TypeError, ValueError):
        pass
    return str(value)


def _wrap_row(meta: str, val: str) -> tuple[str, str, int]:
    """
    Enveloppe le texte d'une ligne de tableau selon les largeurs de colonne
    configurées et retourne le nombre maximal de lignes de texte physiques.

    :param meta: Texte brut de la colonne « Metadata ».
    :type meta: str
    :param val: Texte brut de la colonne « Value ».
    :type val: str
    :return: Tuple ``(col0_wrapped, col1_wrapped, max_line_count)``.
    :rtype: tuple[str, str, int]
    """
    wrapped0 = textwrap.wrap(meta, width=_WRAP_COL0)
    wrapped1 = textwrap.wrap(val, width=_WRAP_COL1)

    col0 = "\n".join(wrapped0) if wrapped0 else meta
    col1 = "\n".join(wrapped1) if wrapped1 else val

    n_lines = max(col0.count("\n") + 1, col1.count("\n") + 1)
    return col0, col1, n_lines


def _prepare_table_data(
    df: pd.DataFrame,
) -> tuple[list[list[str]], list[int]]:
    """
    Construit les données de tableau avec retour à la ligne automatique et
    calcule le nombre de lignes de texte physiques par ligne de tableau.

    :param df: DataFrame avec colonnes [« Metadata », « Value »].
    :type df: pd.DataFrame
    :return: Tuple ``(cell_text, row_line_counts)``.
    :rtype: tuple[list[list[str]], list[int]]
    """
    wrapped_cell_text: list[list[str]] = []
    row_line_counts: list[int] = []

    for _, row in df.iterrows():
        meta = str(row["Metadata"])
        val = _format_cell_value(meta, row["Value"])
        col0, col1, n_lines = _wrap_row(meta, val)
        wrapped_cell_text.append([col0, col1])
        row_line_counts.append(n_lines)

    return wrapped_cell_text, row_line_counts


def _compute_figure_height(total_units: float) -> float:
    """
    Calcule la hauteur de figure adaptée au contenu, bornée entre un minimum
    lisible et la hauteur d'une page A4.

    :param total_units: Somme totale des unités de hauteur (en-tête + données).
    :type total_units: float
    :return: Hauteur en pouces.
    :rtype: float
    """
    return min(max(total_units * _LINE_HEIGHT_IN + 0.8, 5.0), _PAGE_MAX_HEIGHT_IN)


def _build_figure(fig_height: float) -> tuple["Figure", "Axes"]:
    """
    Crée la figure matplotlib et son axe avec un canvas PDF non-interactif.

    L'utilisation directe de ``Figure`` (API OO) évite toute interaction avec
    l'état global de ``pyplot`` et ne nécessite pas de backend graphique.

    :param fig_height: Hauteur de la figure en pouces.
    :type fig_height: float
    :return: Tuple ``(figure, axe)``.
    :rtype: tuple[Figure, Axes]
    """
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_pdf import FigureCanvasPdf  # type: ignore[import]

    fig = Figure(figsize=(_PAGE_WIDTH_IN, fig_height), dpi=150)
    FigureCanvasPdf(fig)  # attache le canvas PDF non-interactif
    ax = fig.add_subplot(111)
    ax.axis("off")
    return fig, ax


def _style_table(
    table: "Table",
    n_rows: int,
    row_line_counts: list[int],
    total_units: float,
) -> None:
    """
    Applique les couleurs, polices et hauteurs individuelles aux cellules du
    tableau matplotlib.

    Les hauteurs sont proportionnelles au nombre de lignes de texte physiques
    de chaque ligne, de façon à ce que le texte enveloppé ne déborde pas.

    :param table: Objet ``Table`` matplotlib à styler.
    :type table: Table
    :param n_rows: Nombre de lignes de données (hors en-tête).
    :type n_rows: int
    :param row_line_counts: Nombre de lignes de texte par ligne de données.
    :type row_line_counts: list[int]
    :param total_units: Somme totale des unités de hauteur (en-tête + données).
    :type total_units: float
    """
    header_h = (_HEADER_UNITS / total_units) * _TABLE_FRACTION

    # En-tête (ligne 0)
    for col in range(2):
        cell = table[0, col]
        cell.set_height(header_h)
        cell.set_facecolor(_HEADER_RGBA)
        cell.set_text_props(color="white", fontweight="bold", fontsize=10)
        cell.set_edgecolor("white")

    # Lignes de données
    for row_idx in range(1, n_rows + 1):
        row_h = (row_line_counts[row_idx - 1] / total_units) * _TABLE_FRACTION
        for col in range(2):
            cell = table[row_idx, col]
            cell.set_height(row_h)
            cell.set_facecolor(_CELL_COLOR)
            cell.set_edgecolor("white")


# ── Point d'entrée public ─────────────────────────────────────────────────────


def export_metadata_table_as_pdf(df: pd.DataFrame, output_path: Path) -> None:
    """
    Exporte le tableau de métadonnées en PDF via matplotlib, sans Chrome ni
    Kaleido.

    Le texte long est automatiquement enveloppé (``textwrap``) et la hauteur de
    chaque ligne est ajustée en conséquence. La figure est dimensionnée pour
    tenir sur une page A4.

    :param df: DataFrame avec colonnes [« Metadata », « Value »].
    :type df: pd.DataFrame
    :param output_path: Chemin de sortie du fichier PDF.
    :type output_path: Path
    """
    from matplotlib.table import table as mpl_table

    wrapped_cell_text, row_line_counts = _prepare_table_data(df)

    n_rows = len(wrapped_cell_text)
    total_units = _HEADER_UNITS + sum(row_line_counts)
    fig_height = _compute_figure_height(total_units)

    fig, ax = _build_figure(fig_height)

    the_table = mpl_table(
        ax,
        cellText=wrapped_cell_text,
        colLabels=["Metadata", "Value"],
        loc="center",
        cellLoc="left",
        colWidths=[0.40, 0.55],  # proportions [2, 3] du tableau Plotly original
    )
    the_table.auto_set_font_size(False)
    the_table.set_fontsize(9)

    _style_table(the_table, n_rows, row_line_counts, total_units)

    fig.tight_layout(pad=0.5)
    fig.savefig(str(output_path), format="pdf", bbox_inches="tight")
    LOGGER.debug(f"PDF de métadonnées exporté via matplotlib : {output_path}")
