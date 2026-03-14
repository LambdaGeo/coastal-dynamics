"""
run.py — Simulation entry point
===============================
Couples FloodModel + MangroveModel + RasterMap in the same
DisSModel Environment, sharing a single RasterBackend.

Supports two input formats:
    - GeoTIFF (.tif / .tiff) — loads directly via load_geotiff
    - Shapefile / GeoJSON / GPKG — rasterizes via shapefile_to_raster_backend

Execution order per step (instantiation order):
    1. FloodModel     — Hydrology: elevation + flooding
    2. MangroveModel  — Mangrove: land-use/soil migration + accretion
    3. RasterMap      — visualization

Usage
-----
    # from GeoTIFF (original behaviour)
    python -m run flood_p000_0.000m.tif

    # from Shapefile (new)
    python -m run mangue_grid.shp --resolution 100 --crs EPSG:31984

    # interactive mode (requires display):
    RASTER_MAP_INTERACTIVE=1 python -m run mangue_grid.shp --resolution 100

    # multiple maps:
    python -m run mangue_grid.shp --resolution 100 --bands uso alt solo

    # do not save result:
    python -m run mangue_grid.shp --resolution 100 --no-save
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

# ── provisional import — move to dissmodel.geo.raster.io when stable ──────────
from coastal_dynamics.common.raster_io import shapefile_to_raster_backend

from coastal_dynamics.raster.flood_model import FloodModel
from coastal_dynamics.raster.mangrove_model import MangroveModel


# ── simulation configuration ──────────────────────────────────────────────────

#SEA_LEVEL_RISE_RATE = 0.011   # m/year — IPCC RCP8.5
SEA_LEVEL_RISE_RATE = 0.5   # m/year — IPCC RCP8.5
TIDE_HEIGHT         = 6.0     # base tide level in meters
END_TIME            = 88      # steps (2012–2100)

# default attribute columns and their nodata fill values
SHAPEFILE_ATTRS: dict[str, int | float] = {
    "uso":  5,     # bare soil as default land use
    "alt":  0.0,   # sea level as default elevation
    "solo": 1,     # default soil class
}

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

import zipfile

SHAPEFILE_EXTENSIONS = {".shp", ".geojson", ".gpkg", ".json", ".zip"}
TIFF_EXTENSIONS      = {".tif", ".tiff"}


def _detect_zip_format(path: pathlib.Path) -> str:
    """
    Inspect a .zip archive and return 'tiff' or 'vector'
    based on the extensions of the files inside.
    """
    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()

    for name in names:
        ext = pathlib.Path(name).suffix.lower()
        if ext in TIFF_EXTENSIONS:
            return "tiff"
        if ext in {".shp", ".geojson", ".gpkg"}:
            return "vector"

    raise ValueError(
        f"Cannot determine format from zip contents: {names}\n"
        f"Expected .tif/.tiff or .shp/.geojson/.gpkg inside the archive."
    )


# ── loaders ───────────────────────────────────────────────────────────────────

def _load_tiff(path: pathlib.Path):
    """Load RasterBackend from GeoTIFF (plain or zipped) and return (backend, meta, start_time)."""
    print(f"Loading GeoTIFF: {path}")
    backend, meta = load_geotiff(path, band_spec=TIFF_BANDS)

    tags = meta.get("tags", {})
    print(
        f"  shape={backend.shape}  "
        f"step={tags.get('passo', 0)}  "
        f"sea_level={tags.get('nivel_mar', 0)}m  "
        f"crs={meta['crs']}"
    )
    start = int(tags.get("passo", 0)) + 1
    return backend, meta, start


def _resolve_vector_path(path: pathlib.Path) -> str:
    """
    Return a path string that GeoPandas/Fiona can open.

    GeoPandas reads .zip files natively — no zip:// prefix needed.
    Just pass the plain file path for all formats.
    """
    return str(path)


def _load_shapefile(
    path: pathlib.Path,
    resolution: float,
    crs: str | None,
    attrs: dict[str, int | float] | None,
):
    """Rasterize shapefile (or zipped shapefile) into RasterBackend."""
    vector_path = _resolve_vector_path(path)
    print(f"Loading vector file: {vector_path}")
    print(f"  resolution={resolution}  crs={crs or 'native'}")

    backend = shapefile_to_raster_backend(
        path       = vector_path,
        resolution = resolution,
        attrs      = attrs or SHAPEFILE_ATTRS,
        crs        = crs,
        all_touched= False,
        nodata     = 0,
    )

    print(f"  shape={backend.shape}  cells={backend.shape[0] * backend.shape[1]:,}")

    meta = {"crs": crs, "transform": None, "tags": {}}
    start = 1
    return backend, meta, start


# ── main ──────────────────────────────────────────────────────────────────────

def run(
    input_path:    str | pathlib.Path,
    bands:         list[str]       = ("uso",),
    acrecao_ativa: bool            = False,
    save:          bool            = True,
    resolution:    float           = 100.0,
    crs:           str | None      = None,
    attrs:         dict | None     = None,
    fmt:           str | None      = None,   # "tiff" | "vector" | None (auto)
) -> None:
    input_path = pathlib.Path(input_path)
    ext = input_path.suffix.lower()

    # ── detect format ─────────────────────────────────────────────────────────
    if fmt is None and ext == ".zip":
        fmt = _detect_zip_format(input_path)
        print(f"  zip contents detected as: {fmt}")

    if fmt == "tiff" or (fmt is None and ext in TIFF_EXTENSIONS):
        backend, meta, start = _load_tiff(input_path)
    elif fmt == "vector" or (fmt is None and ext in SHAPEFILE_EXTENSIONS):
        backend, meta, start = _load_shapefile(input_path, resolution, crs, attrs)
    else:
        print(
            f"Cannot determine input format for '{input_path.name}'.\n"
            f"Use --format tiff or --format vector to force.",
            file=sys.stderr,
        )
        sys.exit(1)

    # ── environment ───────────────────────────────────────────────────────────
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
            print(f"  warning: band '{band}' has no visual config — using viridis")
        RasterMap(backend=backend, band=band, **BAND_CONFIG.get(band, {}))

    # ── run ───────────────────────────────────────────────────────────────────
    print(f"Running steps {start} → {END_TIME}...")
    env.run()
    print("Finished.")

    # ── save final state ──────────────────────────────────────────────────────
    if save:
        out_path = input_path.with_name(input_path.stem + "_result.tif")
        save_geotiff(
            backend,
            out_path,
            band_spec=TIFF_BANDS,
            crs=meta.get("crs") or CRS,
            transform=meta.get("transform"),
        )
        print(f"Saved: {out_path}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="python -m run",
        description="Raster-based coastal simulation using DisSModel",
    )
    p.add_argument(
        "input",
        help="Input file: GeoTIFF (.tif) or vector file (.shp, .geojson, .gpkg)",
    )
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

    # shapefile-specific options
    shp = p.add_argument_group("Shapefile options (ignored for GeoTIFF input)")
    shp.add_argument(
        "--resolution", type=float, default=100.0, metavar="METRES",
        help="Cell size in CRS units when rasterizing a shapefile (default: 100)",
    )
    shp.add_argument(
        "--crs", type=str, default=None, metavar="EPSG",
        help="Target CRS for reprojection, e.g. EPSG:31984 (default: native CRS)",
    )
    p.add_argument(
        "--format", dest="fmt", choices=["tiff", "vector"], default=None,
        help=(
            "Force input format. "
            "Use 'vector' for .zip archives containing a shapefile, "
            "or when the extension is ambiguous."
        ),
    )

    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    run(
        input_path    = args.input,
        bands         = args.bands,
        acrecao_ativa = args.acrecao,
        save          = args.save,
        resolution    = args.resolution,
        crs           = args.crs,
        fmt           = args.fmt,
    )