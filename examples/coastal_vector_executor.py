# examples/cli/experiments/coastal_vector_executor.py
from __future__ import annotations

import geopandas as gpd
from matplotlib.colors import BoundaryNorm, ListedColormap

from dissmodel.executor     import ExperimentRecord, ModelExecutor
from dissmodel.executor.cli import run_cli
from dissmodel.io           import load_dataset, save_dataset

from coastal_dynamics.common.constants import (
    SOLO_COLORS, SOLO_LABELS,
    USO_COLORS,  USO_LABELS,
)
from coastal_dynamics.vector.flood_model    import FloodModel
from coastal_dynamics.vector.mangrove_model import MangroveModel

# ── colormaps ─────────────────────────────────────────────────────────────────

_vals    = sorted(USO_COLORS)
USO_CMAP = ListedColormap([USO_COLORS[k] for k in _vals])
USO_NORM = BoundaryNorm([v - 0.5 for v in _vals] + [_vals[-1] + 0.5], USO_CMAP.N)

_svals    = sorted(SOLO_COLORS)
SOLO_CMAP = ListedColormap([SOLO_COLORS[k] for k in _svals])
SOLO_NORM = BoundaryNorm([v - 0.5 for v in _svals] + [_svals[-1] + 0.5], SOLO_CMAP.N)


class CoastalVectorExecutor(ModelExecutor):
    """
    Executor for the vector-based coastal dynamics simulation.

    Couples FloodModel + MangroveModel over a shared GeoDataFrame.
    Works both as a platform executor (via API) and locally (via CLI).

    Equivalent to run_vector.py but following the ModelExecutor contract,
    enabling reproducibility tracking and platform integration.
    """

    name = "coastal_vector"

    def load(self, record: ExperimentRecord) -> gpd.GeoDataFrame:
        gdf, checksum          = load_dataset(record.source.uri)
        record.source.checksum = checksum

        if record.column_map:
            gdf = gdf.rename(columns={v: k for k, v in record.column_map.items()})

        record.add_log(f"Loaded GDF: {len(gdf)} features  crs={gdf.crs}")
        return gdf

    def validate(self, record: ExperimentRecord) -> None:
        params   = record.parameters
        attr_uso = params.get("attr_uso", "uso")
        attr_alt = params.get("attr_alt", "alt")
        attr_solo = params.get("attr_solo", "solo")

        gdf     = self.load(record)
        missing = {attr_uso, attr_alt, attr_solo} - set(gdf.columns)

        if missing:
            raise ValueError(
                f"Required columns missing after column_map: {missing}\n"
                f"Dataset columns: {list(gdf.columns)}"
            )

    def run(self, record: ExperimentRecord) -> gpd.GeoDataFrame:
        from dissmodel.core import Environment

        params    = record.parameters
        end_time  = params.get("end_time",      88)
        attr_uso  = params.get("attr_uso",      "uso")
        attr_alt  = params.get("attr_alt",      "alt")
        attr_solo = params.get("attr_solo",     "solo")

        gdf = self.load(record)

        env = Environment(
            start_time = params.get("start_time", 1),
            end_time   = end_time,
        )

        FloodModel(
            gdf           = gdf,
            taxa_elevacao = params.get("taxa_elevacao", 0.5),
            attr_uso      = attr_uso,
            attr_alt      = attr_alt,
        )

        MangroveModel(
            gdf           = gdf,
            taxa_elevacao = params.get("taxa_elevacao", 0.5),
            altura_mare   = params.get("altura_mare",   6.0),
            acrecao_ativa = params.get("acrecao_ativa", False),
            attr_uso      = attr_uso,
            attr_alt      = attr_alt,
            attr_solo     = attr_solo,
        )

        # Map and Chart only shown in interactive mode — skipped in headless worker
        if params.get("interactive", False):
            from dissmodel.visualization import Chart, Map
            Map(gdf=gdf, plot_params={
                "column": attr_uso,
                "cmap":   USO_CMAP,
                "norm":   USO_NORM,
                "legend": False,
            })
            if params.get("show_chart", False):
                Chart(select={"flooded_cells", "mangrove_migrated"})

        record.add_log(f"Running steps 1 → {end_time}...")
        env.run()
        record.add_log("Simulation complete")
        return gdf

    def save(self, result: gpd.GeoDataFrame, record: ExperimentRecord) -> ExperimentRecord:
        # CLI sets output_path to a local file before calling save()
        # Platform runner sets output_path to s3:// URI
        uri      = record.output_path or \
                   f"s3://dissmodel-outputs/experiments/{record.experiment_id}/output.gpkg"
        checksum = save_dataset(result, uri)

        record.output_path   = uri
        record.output_sha256 = checksum
        record.status        = "completed"
        record.add_log(f"Saved to {uri}")
        return record


if __name__ == "__main__":
    run_cli(CoastalVectorExecutor)