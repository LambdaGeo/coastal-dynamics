"""
validate_coastal.py
====================
Validates equivalence between vector and raster substrates
for the coastal dynamics models (flood + mangrove).

Uses CoastalVectorExecutor and CoastalRasterExecutor directly —
the same code path that runs on the platform. Catches regressions
in load(), column_map handling, and model logic simultaneously.

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
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from dissmodel.executor.schemas import ExperimentRecord, DataSource

from coastal_dynamics.executor.coastal_raster_executor import CoastalRasterExecutor
from coastal_dynamics.executor.coastal_vector_executor import CoastalVectorExecutor
from coastal_dynamics.common.constants                 import CRS

# ── configuration ─────────────────────────────────────────────────────────────

SEA_LEVEL_RISE_RATE = 0.011
TIDE_HEIGHT         = 6.0
N_STEPS             = 10
TOLERANCE           = 0.05     # 5% — floating point accumulates over steps

# ── record factory ────────────────────────────────────────────────────────────

def _base_record(uri: str, resolution: float, crs: str) -> ExperimentRecord:
    """
    Minimal ExperimentRecord for local validation — no registry, no platform.
    Mirrors what the runner builds from a JobRequest, but inline.
    model_commit='local-inline' signals this record is not reproducible via
    the registry (same convention as POST /submit_job_inline).
    """
    return ExperimentRecord(
        model_name    = "coastal_dynamics",
        model_commit  = "local-inline",
        code_version  = "dev",
        resolved_spec = {
            "model": {
                "name":  "coastal_dynamics",
                "class": "coastal_raster",   # overridden per executor below
                "bands": {"uso": "Land use", "alt": "Elevation", "solo": "Soil"},
                "parameters": {
                    "taxa_elevacao": SEA_LEVEL_RISE_RATE,
                    "altura_mare":  TIDE_HEIGHT,
                    "end_time":     N_STEPS,
                    "resolution":   resolution,
                    "crs":          crs,
                },
            }
        },
        source       = DataSource(uri=uri, type="local"),
        input_format = "vector",
        parameters   = {
            "taxa_elevacao": SEA_LEVEL_RISE_RATE,
            "altura_mare":  TIDE_HEIGHT,
            "end_time":     N_STEPS,
            "resolution":   resolution,
            "crs":          crs,
            "interactive":  False,
        },
    )


# ── runners ───────────────────────────────────────────────────────────────────

def run_vector(uri: str, resolution: float, crs: str,
               column_map: dict | None = None) -> tuple:
    """
    Run CoastalVectorExecutor.load() + .run().
    Returns (gdf_result, logs, ms_per_step).
    save() is intentionally skipped — validation only compares, never persists.
    """
    record = _base_record(uri, resolution, crs)
    if column_map:
        record.column_map = column_map

    executor = CoastalVectorExecutor()
    executor.validate(record)

    t0         = time.perf_counter()
    gdf_result = executor.run(record)
    ms         = (time.perf_counter() - t0) * 1000 / N_STEPS

    return gdf_result, record.logs, ms


def run_raster(uri: str, resolution: float, crs: str,
               column_map: dict | None = None) -> tuple:
    """
    Run CoastalRasterExecutor.load() + .run() with vector input
    (input_format='vector' so it rasterizes the same shapefile).
    Returns (backend, rows, cols, logs, ms_per_step).
    save() is intentionally skipped — validation only compares, never persists.
    """
    record = _base_record(uri, resolution, crs)
    if column_map:
        record.column_map = column_map

    executor = CoastalRasterExecutor()
    executor.validate(record)

    # load() once to get rows/cols for alignment — run() calls load() again
    # internally (single load contract), so we call load() here separately
    # just to capture the grid indices before env.run() mutates the backend.
    gdf_pre, _ = __import__("dissmodel.io", fromlist=["load_dataset"]).load_dataset(uri)
    if column_map:
        gdf_pre = gdf_pre.rename(columns={v: k for k, v in column_map.items()})
    rows = gdf_pre["row"].astype(int).values
    cols = gdf_pre["col"].astype(int).values

    t0              = time.perf_counter()
    backend, meta   = executor.run(record)
    ms              = (time.perf_counter() - t0) * 1000 / N_STEPS

    return backend, rows, cols, record.logs, ms


# ── metrics ───────────────────────────────────────────────────────────────────

def compute_metrics(a: np.ndarray, b: np.ndarray, tol: float = TOLERANCE) -> dict:
    diff = np.abs(a - b)
    return {
        "match_pct": float((diff <= tol).mean() * 100),
        "mae":       float(diff.mean()),
        "rmse":      float(np.sqrt((diff ** 2).mean())),
        "max_err":   float(diff.max()),
        "n_cells":   len(a),
    }


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
    vec_ms  = results["vec_ms"]
    ras_ms  = results["ras_ms"]
    speedup = vec_ms / ras_ms if ras_ms > 0 else float("inf")

    lines = [
        "# Coastal Dynamics — Vector vs Raster Validation\n\n",
        f"Steps: {N_STEPS} | Tolerance: {TOLERANCE}\n\n",
        "## Runtime\n\n",
        "| Substrate | ms/step | Speedup |\n|---|---|---|\n",
        f"| Vector | {vec_ms:.1f} | 1× |\n",
        f"| Raster | {ras_ms:.1f} | {speedup:.1f}× |\n\n",
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
    p.add_argument("shp",          help="Input shapefile zip (vector input for both substrates)")
    p.add_argument("--resolution", type=float, default=100.0)
    p.add_argument("--crs",        type=str,   default=CRS)
    p.add_argument("--steps",      type=int,   default=N_STEPS)
    p.add_argument("--tol",        type=float, default=TOLERANCE)
    args = p.parse_args()

    uri        = str(pathlib.Path(args.shp).resolve())
    resolution = args.resolution
    crs        = args.crs

    print("=" * 60)
    print("Coastal Dynamics: Vector vs Raster Validation")
    print("(using CoastalVectorExecutor + CoastalRasterExecutor)")
    print("=" * 60)

    print(f"\n[1/2] Vector substrate ({N_STEPS} steps)...")
    gdf_result, vec_logs, vec_ms = run_vector(uri, resolution, crs)
    for log in vec_logs:
        print(f"  {log}")
    print(f"  {vec_ms:.1f} ms/step")

    print(f"\n[2/2] Raster substrate ({N_STEPS} steps)...")
    backend, rows, cols, ras_logs, ras_ms = run_raster(uri, resolution, crs)
    for log in ras_logs:
        print(f"  {log}")
    print(f"  {ras_ms:.1f} ms/step")

    # ── compare cell-by-cell ──────────────────────────────────────────────────
    # rows/cols align the flat GDF index to the 2D raster grid.
    print("\nComparing...")

    band_metrics = {}
    for band in ["uso", "alt", "solo"]:
        if band not in gdf_result.columns:
            continue

        vec_vals = gdf_result[band].values.astype(float)
        ras_vals = backend.get(band)[rows, cols].astype(float)

        m = compute_metrics(vec_vals, ras_vals, args.tol)
        band_metrics[band] = m
        print(
            f"  {band:6s}  match={m['match_pct']:.2f}%  "
            f"MAE={m['mae']:.6f}  RMSE={m['rmse']:.6f}"
        )

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

    plt.suptitle(f"Coastal Dynamics — step {N_STEPS}", fontsize=11)
    plt.tight_layout()
    plt.savefig("coastal_validation_scatter.png", dpi=150)
    print("Plot: coastal_validation_scatter.png")

    write_report({
        "vec_ms":  vec_ms,
        "ras_ms":  ras_ms,
        "metrics": band_metrics,
    }, pathlib.Path("coastal_validation_report.md"))

    speedup = vec_ms / ras_ms if ras_ms > 0 else float("inf")
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Runtime  vector={vec_ms:.1f}ms  raster={ras_ms:.1f}ms  speedup={speedup:.1f}×")
    for band, m in band_metrics.items():
        print(f"  {band:6s}  match={m['match_pct']:.2f}%  MAE={m['mae']:.6f}")


if __name__ == "__main__":
    main()
