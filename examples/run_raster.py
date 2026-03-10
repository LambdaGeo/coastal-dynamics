"""
run.py — Simulation entry point
===============================
Couples FloodModel + MangroveModel + RasterMap in the same
DisSModel Environment, sharing a single RasterBackend.

Execution order per step (instantiation order):
    1. FloodModel     — Hydrology: elevation + flooding
    2. MangroveModel  — Mangrove: land-use/soil migration + accretion
    3. RasterMap      — visualization

Usage
-----
    python -m run flood_p000_0.000m.tif

    # interactive mode (requires display):
    RASTER_MAP_INTERACTIVE=1 python -m run flood_p000_0.000m.tif

    # multiple maps:
    python -m run flood_p000_0.000m.tif --bands uso alt solo

    # do not save result:
    python -m run flood_p000_0.000m.tif --no-save
"""
from __future__ import annotations

import argparse
import pathlib
import sys

from dissmodel.core import Environment
from dissmodel.visualization.raster_map import RasterMap

from coastal_dynamics.common.constants import (
    USO_COLORS, USO_LABELS,
    SOLO_COLORS, SOLO_LABELS,
    MAR, TIFF_BANDS, CRS
)

from dissmodel.geo.raster.io import load_geotiff, save_geotiff

from coastal_dynamics.raster.flood_model import FloodModel
from coastal_dynamics.raster.mangrove_model import MangroveModel


# ── simulation configuration ──────────────────────────────────────────────────

SEA_LEVEL_RISE_RATE = 0.011   # m/year — IPCC RCP8.5
TIDE_HEIGHT         = 6.0     # base tide level in meters
END_TIME            = 88      # steps (2012–2100)

# visualization configuration per band
BAND_CONFIG: dict[str, dict] = {
    "uso": dict(
        color_map = USO_COLORS,
        labels    = USO_LABELS,
        title     = "Land Use",
    ),
    "solo": dict(
        color_map = SOLO_COLORS,
        labels    = SOLO_LABELS,
        title     = "Soil",
    ),
    "alt": dict(
        cmap            = "terrain",
        colorbar_label  = "Elevation (m)",
        mask_band       = "uso",
        mask_value      = MAR,
        title           = "Elevation",
    ),
}


# ── main ──────────────────────────────────────────────────────────────────────

def run(
    tif_path:      str | pathlib.Path,
    bands:         list[str]  = ("uso",),
    acrecao_ativa: bool       = False,
    save:          bool       = True,
) -> None:
    tif_path = pathlib.Path(tif_path)

    # ── load initial state ────────────────────────────────────────────────────
    print(f"Loading {tif_path}...")
    backend, meta = load_geotiff(
        tif_path,
        band_spec=TIFF_BANDS
    )

    tags = meta.get("tags", {})

    print(
        f"  shape={backend.shape}  "
        f"step={tags.get('passo',0)}  "
        f"sea_level={tags.get('nivel_mar',0)}m  "
        f"crs={meta['crs']}"
    )

    start = int(tags.get("passo", 0)) + 1

    env = Environment(start_time=start, end_time=END_TIME)

    # ── models — share the same backend ───────────────────────────────────────
    FloodModel(
        backend       = backend,
        taxa_elevacao = SEA_LEVEL_RISE_RATE,
        aim_base      = TIDE_HEIGHT,
    )

    MangroveModel(
        backend       = backend,
        taxa_elevacao = SEA_LEVEL_RISE_RATE,
        altura_mare   = TIDE_HEIGHT,
        acrecao_ativa = acrecao_ativa,
    )

    # ── visualization — one RasterMap per requested band ──────────────────────
    for band in bands:
        if band not in BAND_CONFIG:
            print(f"  warning: band '{band}' has no visual configuration — using viridis")
        RasterMap(backend=backend, band=band, **BAND_CONFIG.get(band, {}))

    # ── run simulation ────────────────────────────────────────────────────────
    print(f"Running steps {start} → {END_TIME}...")
    env.run()
    print("Finished.")

    # ── save final state ──────────────────────────────────────────────────────
    if save:

        sea_level_final = END_TIME * SEA_LEVEL_RISE_RATE

        out_path = tif_path.with_name(
            tif_path.stem + "_result.tif"
        )

        save_geotiff(
            backend,
            out_path,
            band_spec=TIFF_BANDS,
            crs=CRS,
            transform=meta["transform"],
        )

        print(f"Saved: {out_path}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="python -m run",
        description="Raster-based coastal simulation using DisSModel",
    )
    p.add_argument("tif", help="Input GeoTIFF (initial state)")
    p.add_argument(
        "--bands", nargs="+", default=["uso"],
        choices=list(BAND_CONFIG), metavar="BAND",
        help="Bands to visualize: uso solo alt (default: uso)",
    )
    p.add_argument(
        "--acrecao", action="store_true",
        help="Enable mangrove accretion model (Alongi 2008)",
    )
    p.add_argument(
        "--no-save", dest="save", action="store_false",
        help="Do not save output GeoTIFF",
    )
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    run(
        tif_path      = args.tif,
        bands         = args.bands,
        acrecao_ativa = args.acrecao,
        save          = args.save,
    )