# examples/coastal_raster_executor.py
from __future__ import annotations

import geopandas as gpd

from dissmodel.executor     import ExperimentRecord, ModelExecutor
from dissmodel.executor.cli import run_cli
from dissmodel.io           import load_dataset, save_dataset

from coastal_dynamics.common.constants import (
    MAR, TIFF_BANDS, CRS,
    USO_COLORS, USO_LABELS,
    SOLO_COLORS, SOLO_LABELS,
)
from coastal_dynamics.raster.flood_model    import FloodModel
from coastal_dynamics.raster.mangrove_model import MangroveModel

# ── visualization config ──────────────────────────────────────────────────────

BAND_CONFIG: dict[str, dict] = {
    "uso": dict(color_map=USO_COLORS, labels=USO_LABELS, title="Land Use"),
    "solo": dict(color_map=SOLO_COLORS, labels=SOLO_LABELS, title="Soil"),
    "alt": dict(
        cmap           = "terrain",
        colorbar_label = "Elevation (m)",
        mask_band      = "uso",
        mask_value     = MAR,
        title          = "Elevation",
    ),
}

SHAPEFILE_DEFAULTS: dict[str, int | float] = {
    "uso":  5,
    "alt":  0.0,
    "solo": 1,
}


class CoastalRasterExecutor(ModelExecutor):
    """
    Executor for the raster-based coastal dynamics simulation.

    Accepts GeoTIFF (resume) or vector (new simulation) as input.
    Couples FloodModel + MangroveModel over a shared RasterBackend.
    Works both as a platform executor (via API) and locally (via CLI).

    Equivalent to run.py but following the ModelExecutor contract.
    """

    name = "coastal_raster"

    def load(self, record: ExperimentRecord):
        """
        Load RasterBackend from GeoTIFF or rasterize a vector file.
        Returns (backend, meta, start_time).
        """
        from dissmodel.io.convert    import vector_to_raster_backend

        params     = record.parameters
        uri        = record.source.uri
        fmt        = record.input_format

        # Auto-detect format from extension if not specified
        if fmt == "auto":
            fmt = _detect_format(uri)

        if fmt == "tiff":
            (backend, meta), checksum = load_dataset(uri, fmt="raster",
                                                     band_spec=TIFF_BANDS)
            record.source.checksum = checksum

            # Apply band_map if dataset uses non-canonical names
            for canonical, real in record.band_map.items():
                backend.rename_band(real, canonical)

            tags  = meta.get("tags", {})
            start = int(tags.get("passo", 0)) + 1
            record.add_log(
                f"Loaded GeoTIFF: shape={backend.shape} "
                f"start={start} crs={meta.get('crs')}"
            )

        else:
            # Vector input — rasterize into RasterBackend
            gdf, checksum = load_dataset(uri, fmt="vector")
            record.source.checksum = checksum

            if record.column_map:
                gdf = gdf.rename(columns={v: k for k, v in record.column_map.items()})

            resolution = params.get("resolution", 100.0)
            crs        = params.get("crs", CRS)

            backend = vector_to_raster_backend(
                source      = gdf,
                resolution  = resolution,
                attrs       = SHAPEFILE_DEFAULTS,
                crs         = crs,
                all_touched = False,
                nodata      = 0,
            )
            meta  = {"crs": crs, "transform": None, "tags": {}}
            start = 1
            record.add_log(
                f"Rasterized vector: shape={backend.shape} "
                f"resolution={resolution}m"
            )

        return backend, meta, start

    def validate(self, record: ExperimentRecord) -> None:
        backend, *_ = self.load(record)
        expected    = {"uso", "alt", "solo"}
        actual      = set(backend.band_names())
        missing     = expected - actual

        if missing:
            hint = "band_map" if record.input_format == "tiff" else "column_map"
            raise ValueError(
                f"Bands missing after mapping: {missing}\n"
                f"Pass '{hint}' in the request to map non-canonical names.\n"
                f"Available bands: {list(actual)}"
            )

        # Sanity check elevation range
        if "alt" in actual:
            alt = backend.get("alt")
            if alt.min() < -500 or alt.max() > 9000:
                raise ValueError(
                    f"Band 'alt' has implausible values: "
                    f"[{alt.min():.1f}, {alt.max():.1f}]. "
                    f"Check band_map — 'alt' should be elevation in meters."
                )

    def run(self, record: ExperimentRecord):
        from dissmodel.core           import Environment
        from dissmodel.visualization.raster_map import RasterMap

        params        = record.parameters
        end_time      = params.get("end_time",      88)
        taxa_elevacao = params.get("taxa_elevacao", 0.5)
        altura_mare   = params.get("altura_mare",   6.0)
        acrecao_ativa = params.get("acrecao_ativa", False)
        bands         = params.get("bands",         ["uso"])

        backend, meta, start = self.load(record)

        env = Environment(start_time=start, end_time=end_time)

        FloodModel(
            backend       = backend,
            taxa_elevacao = taxa_elevacao,
        )

        MangroveModel(
            backend       = backend,
            taxa_elevacao = taxa_elevacao,
            altura_mare   = altura_mare,
            acrecao_ativa = acrecao_ativa,
        )

        # Visualization only in interactive mode — skipped in headless worker
        if params.get("interactive", False):
            for band in bands:
                if band not in BAND_CONFIG:
                    print(f"  warning: band '{band}' has no visual config — using viridis")
                RasterMap(
                    backend     = backend,
                    band        = band,
                    save_frames = False,
                    **BAND_CONFIG.get(band, {}),
                )

        record.add_log(f"Running steps {start} → {end_time}...")
        env.run()
        record.add_log("Simulation complete")

        return backend, meta

    def save(self, result, record: ExperimentRecord) -> ExperimentRecord:
        from dissmodel.io.raster import save_geotiff

        backend, meta = result

        uri      = record.output_path or \
                   f"s3://dissmodel-outputs/experiments/{record.experiment_id}/output.tif"
        checksum = save_geotiff(
            (backend, meta), uri,
            band_spec = TIFF_BANDS,
            crs       = meta.get("crs") or CRS,
            transform = meta.get("transform"),
        )

        record.output_path   = uri
        record.output_sha256 = checksum
        record.status        = "completed"
        record.add_log(f"Saved to {uri}")
        return record


# ── helpers ───────────────────────────────────────────────────────────────────

def _detect_format(uri: str) -> str:
    """Infer input format from URI extension."""
    import zipfile, pathlib

    ext = pathlib.Path(uri.split("?")[0]).suffix.lower()

    if ext in {".tif", ".tiff"}:
        return "tiff"

    if ext == ".zip":
        # Inspect zip contents to decide
        try:
            with zipfile.ZipFile(uri) as zf:
                names = zf.namelist()
            for name in names:
                e = pathlib.Path(name).suffix.lower()
                if e in {".tif", ".tiff"}:
                    return "tiff"
                if e in {".shp", ".geojson", ".gpkg"}:
                    return "vector"
        except Exception:
            pass

    return "vector"


if __name__ == "__main__":
    run_cli(CoastalRasterExecutor)