"""
run_vector.py — Vector simulation entry point (GeoDataFrame)
============================================================

Vector-based version for comparison with run.py (RasterBackend).

Uses FloodVectorModel + MangroveModel + GeoDataFrame + Map/Chart.

Usage
-----
    python -m run_vector flood_model.shp
    python -m run_vector flood_model.gpkg --taxa 0.05
    python -m run_vector flood_model.shp --chart
    python -m run_vector flood_model.shp --accretion --no-save
"""
from __future__ import annotations

import argparse
import pathlib

import geopandas as gpd
from matplotlib.colors import ListedColormap, BoundaryNorm

from dissmodel.core import Environment
from dissmodel.visualization import Map, Chart

from coastal_dynamics.common.constants import (
    USO_COLORS, USO_LABELS,
    SOLO_COLORS, SOLO_LABELS,
)
from coastal_dynamics.vector.flood_model import FloodVectorModel
from coastal_dynamics.vector.mangrove_model import MangroveModel


# ── simulation configuration ──────────────────────────────────────────────────

#SEA_LEVEL_RISE_RATE = 0.011
SEA_LEVEL_RISE_RATE = 0.5   # m/year — IPCC RCP8.5
TIDE_HEIGHT         = 6.0
END_TIME            = 88

_vals    = sorted(USO_COLORS)
USO_CMAP = ListedColormap([USO_COLORS[k] for k in _vals])
USO_NORM = BoundaryNorm([v - 0.5 for v in _vals] + [_vals[-1] + 0.5], USO_CMAP.N)

_svals    = sorted(SOLO_COLORS)
SOLO_CMAP = ListedColormap([SOLO_COLORS[k] for k in _svals])
SOLO_NORM = BoundaryNorm([v - 0.5 for v in _svals] + [_svals[-1] + 0.5], SOLO_CMAP.N)


# ── main ──────────────────────────────────────────────────────────────────────

def run(
    shp_path:      str | pathlib.Path,
    taxa_elevacao: float = SEA_LEVEL_RISE_RATE,
    altura_mare:   float = TIDE_HEIGHT,
    acrecao_ativa: bool  = False,
    attr_uso:      str   = "uso",
    attr_alt:      str   = "alt",
    attr_solo:     str   = "solo",
    show_chart:    bool  = False,
    save:          bool  = True,
) -> None:
    shp_path = pathlib.Path(shp_path)

    # ── load data ─────────────────────────────────────────────────────────────
    print(f"Loading {shp_path}...")
    gdf = gpd.read_file(shp_path)
    print(f"  features={len(gdf)}  crs={gdf.crs}")

    # ── environment ───────────────────────────────────────────────────────────
    env = Environment(start_time=1, end_time=END_TIME)

    # ── models — share the same GeoDataFrame ──────────────────────────────────
    # Instantiation order defines execution order per step
    FloodVectorModel(
        gdf           = gdf,
        taxa_elevacao = taxa_elevacao,
        attr_uso      = attr_uso,
        attr_alt      = attr_alt,
    )

    MangroveModel(
        gdf           = gdf,
        taxa_elevacao = taxa_elevacao,
        altura_mare   = altura_mare,
        acrecao_ativa = acrecao_ativa,
        attr_uso      = attr_uso,
        attr_alt      = attr_alt,
        attr_solo     = attr_solo,
    )

    # ── visualization ─────────────────────────────────────────────────────────
    Map(gdf=gdf, plot_params={"column": attr_uso,  "cmap": USO_CMAP,  "norm": USO_NORM,  "legend": False})
    #Map(gdf=gdf, plot_params={"column": attr_alt,  "cmap": "terrain", "legend": True})
    #Map(gdf=gdf, plot_params={"column": attr_solo, "cmap": SOLO_CMAP, "norm": SOLO_NORM, "legend": False})

    if show_chart:
        Chart(select={"flooded_cells", "mangrove_migrated"})

    # ── run simulation ────────────────────────────────────────────────────────
    print(f"Running steps 1 → {END_TIME}...")
    env.run()
    print("Finished.")

    # ── save results ──────────────────────────────────────────────────────────
    if save:
        out_path = shp_path.with_name(shp_path.stem + "_result.gpkg")
        gdf.to_file(out_path, driver="GPKG", layer="vector_simulation")
        print(f"Saved: {out_path}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="python -m run_vector",
        description="Vector-based coastal simulation using DisSModel",
    )
    p.add_argument("shp", help="Input Shapefile or GeoPackage")
    p.add_argument(
        "--taxa", type=float, default=SEA_LEVEL_RISE_RATE, metavar="M/YEAR",
        help=f"Sea level rise rate in meters/year (default: {SEA_LEVEL_RISE_RATE})",
    )
    p.add_argument(
        "--altura-mare", type=float, default=TIDE_HEIGHT, metavar="M",
        help=f"Base tide height in meters (default: {TIDE_HEIGHT})",
    )
    p.add_argument(
        "--accretion", action="store_true",
        help="Enable mangrove accretion process (Alongi 2008)",
    )
    p.add_argument(
        "--attr-uso",  default="uso",  metavar="COL",
        help="Land-use column name (default: uso)",
    )
    p.add_argument(
        "--attr-alt",  default="alt",  metavar="COL",
        help="Elevation column name (default: alt)",
    )
    p.add_argument(
        "--attr-solo", default="solo", metavar="COL",
        help="Soil type column name (default: solo)",
    )
    p.add_argument(
        "--chart", action="store_true",
        help="Display metrics chart per step",
    )
    p.add_argument(
        "--no-save", dest="save", action="store_false",
        help="Do not save output GeoPackage",
    )
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    run(
        shp_path      = args.shp,
        taxa_elevacao = args.taxa,
        altura_mare   = args.altura_mare,
        acrecao_ativa = args.accretion,
        attr_uso      = args.attr_uso,
        attr_alt      = args.attr_alt,
        attr_solo     = args.attr_solo,
        show_chart    = args.chart,
        save          = args.save,
    )