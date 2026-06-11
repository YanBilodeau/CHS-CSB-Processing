"""
Exemple d'utilisation du module de statistiques de levé bathymétrique.

Ce script montre comment utiliser l'API publique pour calculer
les statistiques de distance et temps à partir d'un GeoDataFrame.
"""

from pathlib import Path

import geopandas as gpd
import pandas as pd

from metadata.statistic import compute_survey_statistics

# ──────────────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────────────

# Chemins des fichiers d'entrée (à adapter)
files: list[Path] = [
    Path(r"D:\Mamalilikula\Komoks.gpkg"),
    Path(r"D:\Mamalilikula\Mamalilikulla.gpkg"),
]

# Seuil de filtrage (points avec deltatime > 1 min sont exclus)
THRESHOLD = pd.Timedelta("1min")


# ──────────────────────────────────────────────────────────────────────────────
# Traitement
# ──────────────────────────────────────────────────────────────────────────────


def main() -> None:
    """
    Point d'entrée principal.
    """
    for file in files:
        print(f"\n{'=' * 70}")
        print(f"Fichier : {file.name}")
        print(f"{'=' * 70}")

        # ── Lecture du fichier ────────────────────────────────────────────
        gdf = gpd.read_file(file)
        print(f"Points chargés : {len(gdf):,}")

        # ── Calcul des statistiques ───────────────────────────────────────
        stats = compute_survey_statistics(
            gdf,
            time_column="Time_UTC",
            deltatime_threshold=THRESHOLD,
            reset_boundaries=True,  # Neutraliser trajets retour au port
        )

        # ── Affichage des résultats ───────────────────────────────────────
        print(f"\nPériode : {stats.start_date} → {stats.end_date}")
        print(f"Seuil de filtrage : {stats.filtering_threshold}")
        print(f"Points filtrés : {stats.points_removed:,}")
        print(f"Points conservés : {stats.total_points:,}")

        print("\n" + "─" * 70)
        print("TOTAUX")
        print("─" * 70)

        print(f"\nDistance totale :")
        print(f"  {stats.total_distance.meters:>14,.3f} m")
        print(f"  {stats.total_distance.kilometers:>14,.3f} km")
        print(f"  {stats.total_distance.nautical_miles:>14,.3f} NM")

        print(f"\nTemps total :")
        print(f"  {stats.total_time.total_seconds:>14,.3f} s")
        print(f"  {stats.total_time.total_minutes:>14,.3f} min")
        print(f"  {stats.total_time.total_hours:>14,.3f} h")
        print(f"  {stats.total_time.total_days:>14,.3f} jours")

        print("\n" + "─" * 70)
        print("STATISTIQUES PAR JOUR")
        print("─" * 70)

        print(
            f"\n{'Date':<12} {'Points':>8} "
            f"{'Distance (NM)':>15} {'Temps (h)':>12} {'Vitesse (kn)':>15}"
        )
        print("─" * 70)

        for day in stats.daily_stats:
            # Calcul de la vitesse moyenne pour la journée
            if day.time.total_hours > 0:
                speed_kn = day.distance.nautical_miles / day.time.total_hours
            else:
                speed_kn = 0.0

            print(
                f"{day.date:<12} {day.point_count:>8,} "
                f"{day.distance.nautical_miles:>15.3f} "
                f"{day.time.total_hours:>12.3f} "
                f"{speed_kn:>15.3f}"
            )

        print("─" * 70)

        # ── Export CSV (optionnel) ────────────────────────────────────────
        csv_path = file.with_suffix(".csv")
        with open(csv_path, "w", encoding="utf-8-sig") as f:
            f.write("date,points,distance_m,distance_km,distance_nm,")
            f.write("time_s,time_min,time_h,speed_kn\n")

            for day in stats.daily_stats:
                if day.time.total_hours > 0:
                    speed_kn = day.distance.nautical_miles / day.time.total_hours
                else:
                    speed_kn = 0.0

                f.write(
                    f"{day.date},{day.point_count},"
                    f"{day.distance.meters:.3f},"
                    f"{day.distance.kilometers:.3f},"
                    f"{day.distance.nautical_miles:.3f},"
                    f"{day.time.total_seconds:.3f},"
                    f"{day.time.total_minutes:.3f},"
                    f"{day.time.total_hours:.3f},"
                    f"{speed_kn:.3f}\n"
                )

        print(f"\n💾 CSV exporté : {csv_path}")


if __name__ == "__main__":
    main()
