# Module de Génération de Rapports HTML avec Statistiques

Module SOLID pour générer des rapports HTML interactifs combinant métadonnées et visualisations Plotly de statistiques de levé bathymétrique.

## Architecture

```
metadata/
├── plot.py                           # Routeur principal (métadonnées vs stats)
├── metadata_renderer.py              # Rendu métadonnées seulement
├── templates/
│   └── metadata_export.html.j2       # Template HTML principal
└── statistic/
    └── plotting/                     # Package visualisation
        ├── __init__.py               # API publique
        ├── constants.py              # Config Plotly (couleurs, layouts)
        ├── figure_builder.py         # Construction figures Plotly
        ├── table_builder.py          # Construction tableaux HTML
        ├── template_builder.py       # Rendu template statistiques
        ├── page_assembler.py         # Assemblage page complète
        └── report_generator.py       # Orchestrateur principal
```

## Figures Disponibles

### 1. Tableau Récapitulatif (HTML)
- Période, points totaux/filtrés
- Distance totale (m, km, NM)
- Temps total (h, jours)
- Vitesse moyenne (nœuds)

### 2. Histogramme Distance + Temps par Jour
- Barres groupées avec deux axes Y
- Distance (NM) et Temps (h)

### 3. Courbe de Vitesse Moyenne
- Vitesse par jour (nœuds)
- Ligne de référence (moyenne globale)

### 4. Diagramme Circulaire — Contribution
- Proportion de chaque journée
- Métrique : distance ou temps

### 5. Graphique Densité de Points
- Barres colorées par quantité
- Nombre de points par jour

### 6. Box Plot Distribution Distance
- Statistiques : Min, Q1, Médiane, Q3, Max
- Outliers identifiés

### 7. Scatter Plot Distance vs Temps
- Corrélation avec ligne de tendance
- Régression linéaire

## Utilisation

### Mode Simple (Métadonnées Seulement)

```python
from metadata.plot import plot_metadata

# Métadonnées seulement (ancien comportement)
plot_metadata(
    metadata=metadata_dict,
    title="CH-WIBL-SHIP01-2024-06-01-2024-06-10",
    output_path=Path("output/metadata.json")
)
```

### Mode Complet (Métadonnées + Statistiques)

```python
from metadata.plot import plot_metadata
from metadata.statistic import compute_survey_statistics
import geopandas as gpd
import pandas as pd

# 1. Calculer statistiques
gdf = gpd.read_file("survey.gpkg")
stats = compute_survey_statistics(
    gdf,
    deltatime_threshold=pd.Timedelta("1min")
)

# 2. Préparer métadonnées
metadata = {
    "metadata.plot.param_vessel": "SHIP01",
    "metadata.plot.param_start_date": "2024-06-01",
    "metadata.plot.param_end_date": "2024-06-10",
    # ... autres clés i18n
}

# 3. Générer rapport complet
plot_metadata(
    metadata=metadata,
    title="CH-WIBL-SHIP01-2024-06-01-2024-06-10",
    output_path=Path("output/report.json"),
    statistics=stats,              # ← Statistiques optionnelles
    show_in_browser=True           # ← Ouvrir automatiquement
)
```

### API Avancée (Directe)

```python
from metadata.statistic.plotting import generate_statistics_report
from metadata.metadata_renderer import render_metadata_sections

# Rendu métadonnées
metadata_html = render_metadata_sections(metadata_dict)

# Génération rapport complet
generate_statistics_report(
    stats=survey_statistics,
    metadata_sections_html=metadata_html,
    title="Rapport de Levé",
    output_path=Path("report.html"),
    show_in_browser=True
)
```

## Principes SOLID

| Principe | Application |
|----------|-------------|
| **S - Single Responsibility** | Chaque module une seule tâche (figures, tableaux, templates, assemblage) |
| **O - Open/Closed** | Nouvelles figures ajoutables dans `figure_builder` sans toucher au reste |
| **L - Liskov Substitution** | Toutes les fonctions `build_*_chart()` retournent `go.Figure` |
| **I - Interface Segregation** | API publique minimale (`generate_statistics_report`, `plot_metadata`) |
| **D - Dependency Inversion** | Orchestrateurs dépendent d'abstractions (fonctions), pas d'implémentations |

## Personnalisation

### Ajouter une Nouvelle Figure

1. **Créer la fonction dans `figure_builder.py`** :

```python
def build_my_custom_chart(daily_stats: list[DailyStats]) -> go.Figure:
    """Ma figure personnalisée."""
    fig = go.Figure()
    # ... construction
    fig.update_layout(**LAYOUT_DEFAULTS)
    return fig
```

2. **Ajouter dans `report_generator.py`** :

```python
figures = {
    # ...existing...
    "fig-custom": build_my_custom_chart(stats.daily_stats),
}
```

3. **Ajouter dans `template_builder.py`** :

```python
html_parts.append("""
    <div class="content-card">
        <div class="content-card-title">
            <span class="material-symbols-outlined">my_icon</span>
            Mon Graphique Personnalisé
        </div>
        {chart}
    </div>
""".format(chart=figures_html.get("chart-custom", "")))
```

### Modifier les Couleurs

Éditer `constants.py` :

```python
COLOR_PALETTE: dict[str, str] = {
    "distance": "#your_color",  # Ex: "#3498db"
    "time": "#your_color",
    # ...
}
```

## Tests

```python
# Test génération sans stats (mode simple)
from metadata.plot import plot_metadata

plot_metadata(
    metadata={"metadata.plot.param_vessel": "TEST"},
    title="Test Métadonnées Seulement",
    output_path=Path("test_metadata.html")
)

# Test génération avec stats (mode complet)
from metadata.statistic import compute_survey_statistics
import geopandas as gpd

gdf = gpd.read_file("test.gpkg")
stats = compute_survey_statistics(gdf)

plot_metadata(
    metadata={"metadata.plot.param_vessel": "TEST"},
    title="Test Complet",
    output_path=Path("test_full.html"),
    statistics=stats,
    show_in_browser=True
)
```

## Dépendances

```toml
plotly>=5.0.0
jinja2>=3.1.0
pandas>=2.0.0
geopandas>=0.10.0
numpy>=1.20.0
```

## Avantages

✅ **SOLID** : Architecture modulaire extensible  
✅ **DRY** : Aucune duplication de code  
✅ **Backward Compatible** : API `plot_metadata()` inchangée  
✅ **Type Safety** : Annotations complètes  
✅ **Responsive** : Bootstrap 5.3 + Material Symbols  
✅ **Standalone** : Aucune dépendance externe runtime  

## Fichiers Générés

- **Métadonnées seulement** : HTML avec onglet stats vide
- **Complet** : HTML avec 7 figures interactives Plotly + tableaux détaillés

Les fichiers HTML sont complètement autonomes (pas de dépendances externes) et peuvent être partagés directement.

