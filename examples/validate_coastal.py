"""
validate_coastal.py
====================
Validates equivalence between vector and raster substrates
for the coastal dynamics models (flood + mangrove).

Usage:
    python validate_coastal.py data/synthetic_grid_60x60_shp.zip
    python validate_coastal.py data/elevacao_pol.zip --resolution 30 --crs EPSG:5880

Output:
    coastal_validation_report.md
    coastal_validation_scatter.png
"""
from __future__ import annotations

import argparse
import pathlib
import time

import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from dissmodel.core import Environment
from dissmodel.geo.raster.backend import RasterBackend
from dissmodel.geo.raster.io import shapefile_to_raster_backend

from coastal_dynamics.raster.flood_model    import FloodModel as RasterFlood
from coastal_dynamics.raster.mangrove_model import MangroveModel as RasterMangue
from coastal_dynamics.vector.flood_model    import FloodModel as VectorFlood
from coastal_dynamics.vector.mangrove_model   import MangroveModel as VectorMangue
from coastal_dynamics.common.constants      import TIFF_BANDS, CRS

# ── configuration ─────────────────────────────────────────────────────────────

SEA_LEVEL_RISE_RATE = 0.011
TIDE_HEIGHT         = 6.0
N_STEPS             = 10       # enough to see divergence
TOLERANCE           = 0.05     # 5% tolerance — floating point accumulates

# ── helpers ───────────────────────────────────────────────────────────────────

def metrics(a: np.ndarray, b: np.ndarray, tol: float = TOLERANCE) -> dict:
    diff = np.abs(a - b)
    return {
        "match_pct": float((diff <= tol).mean() * 100),
        "mae":       float(diff.mean()),
        "rmse":      float(np.sqrt((diff**2).mean())),
        "max_err":   float(diff.max()),
        "n_cells":   len(a),
    }


def build_raster_from_gdf(gdf: gpd.GeoDataFrame) -> tuple[RasterBackend, np.ndarray, np.ndarray]:
    """
    Build RasterBackend directly from shapefile row/col attributes.
    Guarantees perfect cell-to-cell alignment with the vector GeoDataFrame.
    """
    rows   = gdf["row"].astype(int).values
    cols   = gdf["col"].astype(int).values
    n_rows = int(rows.max()) + 1
    n_cols = int(cols.max()) + 1

    b = RasterBackend(shape=(n_rows, n_cols))

    mask = np.zeros((n_rows, n_cols), dtype=bool)
    mask[rows, cols] = True
    b.set("mask", mask)

    for col in ["uso", "alt", "solo"]:
        if col in gdf.columns:
            arr = np.zeros((n_rows, n_cols), dtype=np.float32)
            arr[rows, cols] = gdf[col].astype(float).values
            b.set(col, arr)

    return b, rows, cols


# ── runners ───────────────────────────────────────────────────────────────────

def run_vector(gdf: gpd.GeoDataFrame, n_steps: int = N_STEPS) -> tuple[gpd.GeoDataFrame, float]:
    gdf = gdf.copy()
    env = Environment(start_time=1, end_time=n_steps)
    VectorFlood(
        gdf=gdf,
        taxa_elevacao=SEA_LEVEL_RISE_RATE,
        aim_base=TIDE_HEIGHT,
    )
    VectorMangue(
        gdf=gdf,
        taxa_elevacao=SEA_LEVEL_RISE_RATE,
        altura_mare=TIDE_HEIGHT,
    )
    t0 = time.perf_counter()
    env.run()
    ms = (time.perf_counter() - t0) * 1000 / n_steps
    return gdf, ms


def run_raster(gdf_orig: gpd.GeoDataFrame, n_steps: int = N_STEPS) -> tuple[RasterBackend, np.ndarray, np.ndarray, float]:
    b, rows, cols = build_raster_from_gdf(gdf_orig)
    env = Environment(start_time=1, end_time=n_steps)
    RasterFlood(
        backend=b,
        taxa_elevacao=SEA_LEVEL_RISE_RATE,
        aim_base=TIDE_HEIGHT,
    )
    RasterMangue(
        backend=b,
        taxa_elevacao=SEA_LEVEL_RISE_RATE,
        altura_mare=TIDE_HEIGHT,
    )
    t0 = time.perf_counter()
    env.run()
    ms = (time.perf_counter() - t0) * 1000 / n_steps
    return b, rows, cols, ms


# ── scatter plot ──────────────────────────────────────────────────────────────

def scatter_plot(ax, x, y, xlabel, ylabel, title, m):
    ax.scatter(x, y, alpha=0.4, s=6, color="steelblue")
    lim = max(float(np.max(x)), float(np.max(y))) * 1.05
    ax.plot([0, lim], [0, lim], "r--", lw=1)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.text(0.05, 0.88,
            f"match={m['match_pct']:.1f}%\nMAE={m['mae']:.5f}\nRMSE={m['rmse']:.5f}",
            transform=ax.transAxes, fontsize=7,
            bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5))


# ── report ────────────────────────────────────────────────────────────────────

def write_report(results: dict, path: pathlib.Path) -> None:
    lines = [
        "# Coastal Dynamics — Vector vs Raster Validation\n\n",
        f"Steps: {n_steps} | Tolerance: {tolerance}\n\n",
        "## Runtime\n\n",
        f"| Substrate | ms/step | Speedup |\n|---|---|---|\n",
        f"| Vector | {results['vec_ms']:.1f} | 1× |\n",
        f"| Raster | {results['ras_ms']:.1f} | {results['vec_ms']/results['ras_ms']:.1f}× |\n\n",
        "## Accuracy\n\n",
        "| Band | Match % | MAE | RMSE | Max err | N cells |\n",
        "|---|---|---|---|---|---|\n",
    ]
    for band, m in results["metrics"].items():
        lines.append(
            f"| {band} | {m['match_pct']:.2f}% | {m['mae']:.6f} | "
            f"{m['rmse']:.6f} | {m['max_err']:.6f} | {m['n_cells']} |\n"
        )
    path.write_text("".join(lines))
    print(f"Report: {path}")


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser()
    p.add_argument("shp",          help="Input shapefile zip")
    p.add_argument("--resolution", type=float, default=100.0)
    p.add_argument("--crs",        type=str,   default=None)
    p.add_argument("--steps",      type=int,   default=N_STEPS)
    p.add_argument("--tol",        type=float, default=TOLERANCE)
    args = p.parse_args()

    n_steps   = args.steps
    tolerance = args.tol
    shp_path  = pathlib.Path(args.shp)

    print("=" * 60)
    print("Coastal Dynamics: Vector vs Raster Validation")
    print("=" * 60)

    gdf_orig = gpd.read_file(str(shp_path))
    print(f"  {len(gdf_orig):,} cells  crs={gdf_orig.crs}")

    print(f"\n[1/2] Vector substrate ({N_STEPS} steps)...")
    gdf_result, vec_ms = run_vector(gdf_orig)
    print(f"  {vec_ms:.1f} ms/step")

    print(f"\n[2/2] Raster substrate ({N_STEPS} steps)...")
    backend, rows, cols, ras_ms = run_raster(gdf_orig, n_steps)
    print(f"  {ras_ms:.1f} ms/step")

    # ── align by position ─────────────────────────────────────────────────────
    print("\nComparing...")

    rc_idx = pd.MultiIndex.from_arrays(
        [gdf_orig["row"].astype(int).values,
         gdf_orig["col"].astype(int).values],
        names=["row", "col"],
    )

    band_metrics = {}
    for band in ["uso", "alt", "solo"]:
        if band not in gdf_result.columns:
            continue

        vec_vals = gdf_result[band].values.astype(float)
        ras_vals = backend.get(band)[rows, cols].astype(float)

        m = metrics(vec_vals, ras_vals, tolerance)
        band_metrics[band] = m
        print(f"  {band:6s}  match={m['match_pct']:.2f}%  MAE={m['mae']:.6f}  RMSE={m['rmse']:.6f}")

    # ── scatter plots ─────────────────────────────────────────────────────────
    n_bands = len(band_metrics)
    fig, axes = plt.subplots(1, n_bands, figsize=(6 * n_bands, 5))
    if n_bands == 1:
        axes = [axes]

    for ax, (band, m) in zip(axes, band_metrics.items()):
        vec_vals = gdf_result[band].values.astype(float)
        ras_vals = backend.get(band)[rows, cols].astype(float)
        scatter_plot(ax, vec_vals, ras_vals,
                     f"Vector {band}", f"Raster {band}",
                     f"{band} — Vector vs Raster", m)

    plt.suptitle(f"Coastal Dynamics — step {n_steps}", fontsize=11)
    plt.tight_layout()
    plt.savefig("coastal_validation_scatter.png", dpi=150)
    print("Plot: coastal_validation_scatter.png")

    write_report({
        "vec_ms": vec_ms,
        "ras_ms": ras_ms,
        "metrics": band_metrics,
    }, pathlib.Path("coastal_validation_report.md"))

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Runtime  vector={vec_ms:.1f}ms  raster={ras_ms:.1f}ms  speedup={vec_ms/ras_ms:.1f}×")
    for band, m in band_metrics.items():
        print(f"  {band:6s}  match={m['match_pct']:.2f}%  MAE={m['mae']:.6f}")


if __name__ == "__main__":
    main()
