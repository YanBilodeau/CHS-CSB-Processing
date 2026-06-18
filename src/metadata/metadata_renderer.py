"""
Rendu de l'onglet métadonnées uniquement.

Ce module extrait la logique de rendu des métadonnées
depuis plot.py pour respecter le principe de Single Responsibility.
"""

from typing import Any

import i18n

# ── Constantes de regroupement ────────────────────────────────────────────

_METADATA_GROUPS: list[tuple[str, str, tuple[str, ...]]] = [
    (
        "identification",
        "metadata.plot.group_identification",
        (
            "metadata.plot.param_vessel",
            "metadata.plot.param_start_date",
            "metadata.plot.param_end_date",
            "metadata.plot.param_datalogger_type",
            "metadata.plot.param_sounding_hardware",
            "metadata.plot.param_positioning_hardware",
            "metadata.plot.param_resolution",
        ),
    ),
    (
        "sensors",
        "metadata.plot.group_sensors",
        (
            "metadata.plot.param_horizontal_crs",
            "metadata.plot.param_vertical_crs",
            "metadata.plot.param_sounding_technique",
            "metadata.plot.param_positioning_method",
            "metadata.plot.param_sounder_draft",
        ),
    ),
    (
        "processing",
        "metadata.plot.group_processing",
        (
            "metadata.plot.param_water_level_reduction",
            "metadata.plot.param_data_processing_software",
        ),
    ),
]

_GROUP_ICONS: dict[str, str] = {
    "identification": "directions_boat",
    "sensors": "satellite_alt",
    "processing": "water",
    "other": "inventory_2",
}

_DEFAULT_ICON: str = "folder_open"


# ── Helpers internes ───────────────────────────────────────────────────────


def _format_value(value: Any) -> str:
    """
    Formate une valeur de métadonnée pour affichage HTML.

    :param value: Valeur brute issue du dictionnaire de métadonnées.
    :type value: Any
    :return: Représentation textuelle sécurisée pour HTML.
    :rtype: str
    """
    if value is None:
        return ""
    if isinstance(value, (list, tuple, set)):
        return ", ".join(str(v) for v in value)
    return str(value)


def _group_metadata(metadata: dict) -> list[dict]:
    """
    Répartit les clés du dictionnaire de métadonnées en groupes nommés.

    :param metadata: Dictionnaire brut des métadonnées.
    :type metadata: dict
    :return: Liste de dictionnaires {"id", "title", "rows"} pour le template.
    :rtype: list[dict]
    """
    groups: list[dict] = []
    seen_keys: set[str] = set()

    for group_id, title_key, keys in _METADATA_GROUPS:
        rows: list[dict] = []
        for key in keys:
            if key in metadata:
                rows.append(
                    {
                        "raw_key": key,
                        "key": i18n.t(key),
                        "value": _format_value(metadata[key]),
                    }
                )
                seen_keys.add(key)
        if rows:
            groups.append(
                {
                    "id": group_id,
                    "title": i18n.t(title_key),
                    "rows": rows,
                }
            )

    other_rows: list[dict] = [
        {
            "raw_key": key,
            "key": i18n.t(key) if key.startswith("metadata.") else key,
            "value": _format_value(value),
        }
        for key, value in metadata.items()
        if key not in seen_keys
    ]
    if other_rows:
        groups.append(
            {
                "id": "other",
                "title": i18n.t("metadata.plot.group_other"),
                "rows": other_rows,
            }
        )

    return groups


def render_metadata_sections(metadata: dict) -> str:
    """
    Génère le fragment HTML des cartes de métadonnées.

    :param metadata: Dictionnaire des métadonnées.
    :type metadata: dict
    :return: HTML des sections de métadonnées.
    :rtype: str
    """
    groups = _group_metadata(metadata)

    parts: list[str] = []
    empty_label: str = i18n.t("metadata.plot.group_empty")
    col_key: str = i18n.t("metadata.plot.column_key")
    col_value: str = i18n.t("metadata.plot.column_value")

    for group in groups:
        rows_html: list[str] = [
            f'<tr><td>{row["key"]}</td>'
            f'<td class="editable-cell" contenteditable="true" data-key="{row["raw_key"]}">'
            f'{row["value"]}</td></tr>'
            for row in group["rows"]
        ]
        body: str = (
            "\n".join(rows_html)
            if rows_html
            else f'<p class="none-text">{empty_label}</p>'
        )
        icon: str = _GROUP_ICONS.get(group["id"], _DEFAULT_ICON)
        parts.append(
            f"""
        <div class="content-card">
            <div class="content-card-title">
                <span class="material-symbols-outlined">{icon}</span>
                {group['title']}
            </div>
            <table class="table-striped">
                <thead>
                    <tr><th>{col_key}</th><th>{col_value}</th></tr>
                </thead>
                <tbody>
                    {body}
                </tbody>
            </table>
        </div>
            """.strip()
        )

    return "\n".join(parts)
