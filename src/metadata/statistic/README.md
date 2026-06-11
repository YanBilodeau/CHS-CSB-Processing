# Module de Statistiques de Levé Bathymétrique

Module SOLID pour le calcul de statistiques de distance et temps à partir de données de sondage bathymétrique.

## Architecture

Le module est organisé selon les principes SOLID :

```
statistic/
├── __init__.py                  # API publique
├── models.py                    # Dataclasses (résultats)
├── crs_operations.py            # Validation/projection CRS
├── temporal_operations.py       # Opérations temporelles
├── distance_calculator.py       # Calcul distances
├── time_calculator.py           # Calcul durées
├── boundary_handler.py          # Gestion frontières de journée
├── filters.py                   # Filtres (pattern Strategy)
├── statistics_aggregator.py     # Agrégation stats
├── pipeline.py                  # Orchestrateur principal
├── example_usage.py             # Exemple d'utilisation
└── _test_distance.py            # Ancien code (référence)
```

## Utilisation

### Installation

```bash
# Dépendances
uv sync
```

### Exemple Simple

```python
from metadata.statistic import compute_survey_statistics
import geopandas as gpd
import pandas as pd

# Charger données
gdf = gpd.read_file("survey.gpkg")

# Calculer statistiques
stats = compute_survey_statistics(
    gdf,
    deltatime_threshold=pd.Timedelta("1min"),
    reset_boundaries=True,
)

# Accéder aux résultats
print(f"Distance totale : {stats.total_distance.kilometers} km")
print(f"Temps total : {stats.total_time.total_hours} h")
print(f"Points filtrés : {stats.points_removed}")

# Statistiques par jour
for day in stats.daily_stats:
    print(f"{day.date} : {day.distance.nautical_miles} NM")
```

### Paramètres

- **gdf** : `GeoDataFrame` avec colonnes `Time_UTC` (datetime) et `geometry` (Point)
- **time_column** : Nom de la colonne temporelle (défaut: `"Time_UTC"`)
- **deltatime_threshold** : Seuil max de temps entre points (défaut: `pd.Timedelta("1min")`)
- **reset_boundaries** : Neutraliser trajets retour au port (défaut: `True`)

### Résultats

L'objet `SurveyStatistics` retourné contient :

```python
@dataclass(frozen=True)
class SurveyStatistics:
    daily_stats: list[DailyStats]      # Stats par jour
    total_distance: DistanceStats       # Distance totale
    total_time: TimeStats               # Temps total
    total_points: int                   # Nombre de points
    start_date: str                     # Date début (ISO)
    end_date: str                       # Date fin (ISO)
    filtering_threshold: str            # Seuil appliqué
    points_removed: int                 # Points filtrés
```

Chaque `DailyStats` contient :

```python
@dataclass(frozen=True)
class DailyStats:
    date: str                   # Date (YYYY-MM-DD)
    distance: DistanceStats     # Distance (m, km, NM)
    time: TimeStats             # Temps (s, min, h, jours)
    point_count: int            # Nombre de points
```

## Principes SOLID

| Principe | Application |
|----------|-------------|
| **S - Single Responsibility** | Chaque module a une seule responsabilité (CRS, temps, distance, filtres) |
| **O - Open/Closed** | Filtres extensibles via classe abstraite `Filter` |
| **L - Liskov Substitution** | Toutes implémentations de `Filter` sont substituables |
| **I - Interface Segregation** | Dataclasses séparées (DistanceStats, TimeStats) |
| **D - Dependency Inversion** | Pipeline dépend d'abstractions, pas d'implémentations |

## Workflow

1. **Validation CRS** → WGS84 (EPSG:4326)
2. **Index temporel** → DatetimeIndex UTC trié
3. **Calcul deltatime** → Temps entre points consécutifs
4. **Calcul distance** → Projection UTM automatique + distances en mètres
5. **Reset frontières** → NaN/NaT aux 1ers points de journée (optionnel)
6. **Filtrage** → Exclusion points avec deltatime > seuil
7. **Agrégation** → Stats journalières + totales

## Gestion Frontières de Journée

Le workflow neutralise automatiquement les trajets retour au port :

- **Premier point de chaque journée UTC** → `distance_m = NaN`, `deltatime = NaT`
- **Effet** : ces points sont conservés par le filtre mais exclus des sommes
- **Raison** : le trajet port → zone de sondage n'est pas du sondage

## Extension

### Ajouter un Nouveau Filtre

```python
from metadata.statistic.filters import Filter
import geopandas as gpd

class SpeedFilter(Filter):
    """Filtre par vitesse maximale."""
    
    def __init__(self, max_speed_knots: float):
        self.max_speed_knots = max_speed_knots
    
    def apply(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        # Calculer vitesse, filtrer
        return gdf[gdf["speed_kn"] <= self.max_speed_knots].copy()

# Utilisation
from metadata.statistic.filters import apply_filters, DeltatimeFilter

filters = [
    DeltatimeFilter(pd.Timedelta("1min")),
    SpeedFilter(max_speed_knots=8.0),
]
gdf_filtered = apply_filters(gdf, filters)
```

## Migration depuis `_test_distance.py`

### Avant (ancien code)

```python
from pathlib import Path
import geopandas as gpd
from _test_distance import process_file, compute_daily_distances

gdf = process_file(Path("survey.gpkg"))
daily = compute_daily_distances(gdf)
print(daily)  # pandas DataFrame
```

### Après (nouveau module)

```python
import geopandas as gpd
import pandas as pd
from metadata.statistic import compute_survey_statistics

gdf = gpd.read_file("survey.gpkg")
stats = compute_survey_statistics(gdf, deltatime_threshold=pd.Timedelta("1min"))

for day in stats.daily_stats:
    print(f"{day.date}: {day.distance.kilometers} km, {day.time.total_hours} h")
```

## Avantages

✅ **Testabilité** : Chaque fonction pure testable isolément  
✅ **Réutilisabilité** : Modules CRS/temps/distance réutilisables  
✅ **Maintenabilité** : Modification d'un calcul n'impacte qu'un module  
✅ **Extensibilité** : Ajout de filtres sans toucher au code existant  
✅ **Type Safety** : Dataclasses fournissent structure claire  
✅ **API Publique** : Interface simple et documentée  

## Exemples

Voir `example_usage.py` pour un exemple complet avec export CSV.

## Tests

```bash
# À venir : tests unitaires pour chaque module
pytest tests/metadata/statistic/
```

