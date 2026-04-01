"""
validate_coastal.py
====================
Validates equivalence between vector and raster substrates
for the coastal dynamics models (flood + mangrove) using Executors.

Usage:
    python validate_coastal.py data/synthetic_grid_60x60_shp.zip
    python validate_coastal.py data/elevacao_pol.zip --resolution 30 --crs EPSG:31983

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

from dissmodel.executor import ExperimentRecord
from dissmodel.executor.schemas  import DataSource # Ajuste o import conforme seu projeto

# Importando os novos executors
from coastal_dynamics.executor.coastal_raster_executor import CoastalRasterExecutor
from coastal_dynamics.executor.coastal_vector_executor import CoastalVectorExecutor

# ── configuration ─────────────────────────────────────────────────────────────

SEA_LEVEL_RISE_RATE = 0.011
TIDE_HEIGHT         = 6.0
N_STEPS             = 10       
TOLERANCE           = 0.05     

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

def build_raster_from_gdf(gdf: gpd.GeoDataFrame):
    """Constrói o RasterBackend garantindo alinhamento 1:1 para validação."""
    rows   = gdf["row"].astype(int).values
    cols   = gdf["col"].astype(int).values
    n_rows = int(rows.max()) + 1
    n_cols = int(cols.max()) + 1

    from dissmodel.geo.raster.backend import RasterBackend
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

# ── runners (USANDO EXECUTORS) ────────────────────────────────────────────────

def run_vector(uri: str, args) -> tuple[gpd.GeoDataFrame, float]:
    record = ExperimentRecord(
        experiment_id = "val_vec",
        model_name    = "coastal_vector",
        source        = DataSource(uri=uri, type="local"),
        parameters    = {
            "start_time":    1,
            "end_time":      args.steps,
            "taxa_elevacao": SEA_LEVEL_RISE_RATE,
            "altura_mare":   TIDE_HEIGHT,
        }
    )
    
    executor = CoastalVectorExecutor()
    
    t0 = time.perf_counter()
    gdf_result = executor.run(record)
    ms = (time.perf_counter() - t0) * 1000 / args.steps
    
    return gdf_result, ms


class MathValidationRasterExecutor(CoastalRasterExecutor):
    """
    Executor Mock para forçar o alinhamento 1:1 na leitura do arquivo
    apenas para fins de validação matemática contra o modelo vetorial.
    """
    def load(self, record):
        gdf = gpd.read_file(record.source.uri)
        backend, _, _ = build_raster_from_gdf(gdf)
        meta = {"crs": record.parameters.get("crs"), "transform": None}
        return backend, meta, 1


def run_raster(uri: str, args) -> tuple[any, float]:
    record = ExperimentRecord(
        experiment_id = "val_ras",
        model_name    = "coastal_raster",
        source        = DataSource(uri=uri, type="local"),
        input_format  = "vector", 
        parameters    = {
            "end_time":      args.steps,
            "taxa_elevacao": SEA_LEVEL_RISE_RATE,
            "altura_mare":   TIDE_HEIGHT,
            "crs":           args.crs,
        }
    )
    
    executor = MathValidationRasterExecutor()
    
    t0 = time.perf_counter()
    backend, meta = executor.run(record)
    ms = (time.perf_counter() - t0) * 1000 / args.steps
    
    return backend, ms


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

def write_report(results: dict, path: pathlib.Path,
                 n_steps: int = N_STEPS, tolerance: float = TOLERANCE) -> None:
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
    print(f"\nReport: {path}")


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser()
    p.add_argument("shp",          help="Input shapefile zip")
    p.add_argument("--resolution", type=float, default=100.0)
    p.add_argument("--crs",        type=str,   default="EPSG:31983")
    p.add_argument("--steps",      type=int,   default=N_STEPS)
    p.add_argument("--tol",        type=float, default=TOLERANCE)
    args = p.parse_args()

    print("=" * 60)
    print("Coastal Dynamics: Vector vs Raster Validation (Executor Mode)")
    print("=" * 60)

    # Lemos o GDF original apenas para extrair as linhas e colunas para o alinhamento
    gdf_orig = gpd.read_file(args.shp)
    print(f"  {len(gdf_orig):,} cells  crs={gdf_orig.crs}")

    print(f"\n[1/2] Vector substrate ({args.steps} steps)...")
    gdf_result, vec_ms = run_vector(args.shp, args)
    print(f"  {vec_ms:.1f} ms/step")

    print(f"\n[2/2] Raster substrate ({args.steps} steps)...")
    backend, ras_ms = run_raster(args.shp, args)
    print(f"  {ras_ms:.1f} ms/step")

    # ── align by position ─────────────────────────────────────────────────────
    print("\nComparing...")

    # Extraímos as posições do arquivo original para garantir o alinhamento 1:1 no scatter
    rows = gdf_orig["row"].astype(int).values
    cols = gdf_orig["col"].astype(int).values

    band_metrics = {}
    for band in ["uso", "alt", "solo"]:
        if band not in gdf_result.columns:
            continue

        vec_vals = gdf_result[band].values.astype(float)
        ras_vals = backend.get(band)[rows, cols].astype(float)

        m = metrics(vec_vals, ras_vals, args.tol)
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

    plt.suptitle(f"Coastal Dynamics — step {args.steps}", fontsize=11)
    plt.tight_layout()
    plt.savefig("coastal_validation_scatter.png", dpi=150)
    print("Plot: coastal_validation_scatter.png")

    write_report({
        "vec_ms": vec_ms,
        "ras_ms": ras_ms,
        "metrics": band_metrics,
    }, pathlib.Path("coastal_validation_report.md"),
    n_steps=args.steps, tolerance=args.tol)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Runtime  vector={vec_ms:.1f}ms  raster={ras_ms:.1f}ms  speedup={vec_ms/ras_ms:.1f}×")
    for band, m in band_metrics.items():
        print(f"  {band:6s}  match={m['match_pct']:.2f}%  MAE={m['mae']:.6f}")


if __name__ == "__main__":
    main()