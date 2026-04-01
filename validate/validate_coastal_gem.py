# coastal_dynamics/executor/coastal_validation_executor.py
from __future__ import annotations

import io
import time
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")  # Garante que o plot funcione "headless" no Docker
import matplotlib.pyplot as plt

from dissmodel.core         import Environment
from dissmodel.executor     import ExperimentRecord, ModelExecutor
from dissmodel.executor.cli import run_cli
from dissmodel.io           import load_dataset
from dissmodel.geo.raster.backend import RasterBackend

from coastal_dynamics.vector.flood_model    import FloodModel as VectorFlood
from coastal_dynamics.vector.mangrove_model import MangroveModel as VectorMangue
from coastal_dynamics.raster.flood_model    import FloodModel as RasterFlood
from coastal_dynamics.raster.mangrove_model import MangroveModel as RasterMangue

CANONICAL_COLS = {"uso", "alt", "solo"}

class CoastalValidationExecutor(ModelExecutor):
    """
    Meta-executor that runs BOTH Vector and Raster (Mock 1:1) models to 
    validate mathematical equivalence across substrates.
    
    Generates a Markdown report and a Scatter Plot PNG as output.
    """

    name = "coastal_validation"

    def load(self, record: ExperimentRecord) -> gpd.GeoDataFrame:
        """Carrega a base vetorial que servirá de input para ambos os modelos."""
        gdf, checksum = load_dataset(record.source.uri, fmt="vector")
        record.source.checksum = checksum

        if record.column_map:
            gdf = gdf.rename(columns={v: k for k, v in record.column_map.items()})

        missing = CANONICAL_COLS - set(gdf.columns)
        if missing:
            raise ValueError(f"Required columns missing: {missing}")
            
        return gdf

    def validate(self, record: ExperimentRecord) -> None:
        if not record.source.uri:
            raise ValueError("source.uri is empty.")

        # Validate required columns including row/col for mock raster alignment
        gdf, _ = load_dataset(record.source.uri, fmt="vector")
        if record.column_map:
            gdf = gdf.rename(columns={v: k for k, v in record.column_map.items()})

        missing_canonical = CANONICAL_COLS - set(gdf.columns)
        if missing_canonical:
            raise ValueError(f"Required columns missing: {missing_canonical}")

        missing_index = {"row", "col"} - set(gdf.columns)
        if missing_index:
            raise ValueError(
                f"Columns 'row' and 'col' are required for mock raster alignment "
                f"but are missing from the dataset.\n"
                f"These columns must contain integer grid indices."
            )

    def run(self, record: ExperimentRecord) -> dict:
        params        = record.parameters
        n_steps       = params.get("end_time",      10)
        taxa_elevacao = params.get("taxa_elevacao", 0.011)
        altura_mare   = params.get("altura_mare",   6.0)
        tolerance     = params.get("tolerance",     0.05)

        # 1. Carrega o dado base
        gdf_orig = self.load(record)
        record.add_log(f"Base data loaded: {len(gdf_orig):,} cells")

        # 2. Roda o Modelo Vetorial
        record.add_log(f"Running Vector Model ({n_steps} steps)...")
        gdf_result = gdf_orig.copy()
        env_vec = Environment(start_time=1, end_time=n_steps)
        VectorFlood(gdf=gdf_result, taxa_elevacao=taxa_elevacao, attr_uso="uso", attr_alt="alt")
        VectorMangue(gdf=gdf_result, taxa_elevacao=taxa_elevacao, altura_mare=altura_mare, attr_uso="uso", attr_alt="alt", attr_solo="solo")
        
        t0 = time.perf_counter()
        env_vec.run()
        vec_ms = (time.perf_counter() - t0) * 1000 / n_steps

        # 3. Prepara o Raster (Alinhamento 1:1 Matemático) e Roda
        record.add_log(f"Running Raster Model ({n_steps} steps)...")
        backend, rows, cols = _build_mock_raster(gdf_orig)
        env_ras = Environment(start_time=1, end_time=n_steps)
        RasterFlood(backend=backend, taxa_elevacao=taxa_elevacao)
        RasterMangue(backend=backend, taxa_elevacao=taxa_elevacao, altura_mare=altura_mare)
        
        t0 = time.perf_counter()
        env_ras.run()
        ras_ms = (time.perf_counter() - t0) * 1000 / n_steps

        # 4. Comparações e Métricas
        record.add_log("Calculating metrics...")
        band_metrics = {}
        for band in ["uso", "alt", "solo"]:
            vec_vals = gdf_result[band].values.astype(float)
            ras_vals = backend.get(band)[rows, cols].astype(float)
            
            diff = np.abs(vec_vals - ras_vals)
            band_metrics[band] = {
                "match_pct": float((diff <= tolerance).mean() * 100),
                "mae":       float(diff.mean()),
                "rmse":      float(np.sqrt((diff**2).mean())),
                "max_err":   float(diff.max()),
                "n_cells":   len(vec_vals),
            }

        # 5. Gera Gráficos em Memória
        record.add_log("Generating artifacts...")
        fig, axes = plt.subplots(1, len(band_metrics), figsize=(6 * len(band_metrics), 5))
        if len(band_metrics) == 1: axes = [axes]
        
        for ax, (band, m) in zip(axes, band_metrics.items()):
            v_vals = gdf_result[band].values.astype(float)
            r_vals = backend.get(band)[rows, cols].astype(float)
            ax.scatter(v_vals, r_vals, alpha=0.4, s=6, color="steelblue")
            lim = max(float(np.max(v_vals)), float(np.max(r_vals))) * 1.05
            ax.plot([0, lim], [0, lim], "r--", lw=1)
            ax.set_title(f"{band} (Vector vs Raster)")
            ax.text(0.05, 0.88, f"Match: {m['match_pct']:.1f}%\nMAE: {m['mae']:.5f}",
                    transform=ax.transAxes, fontsize=8, bbox=dict(facecolor="wheat", alpha=0.5))
            
        plt.tight_layout()
        plot_buffer = io.BytesIO()
        plt.savefig(plot_buffer, format="png", dpi=150)
        plt.close()

        # 6. Gera Relatório Markdown
        report_md = _build_markdown(n_steps, tolerance, vec_ms, ras_ms, band_metrics)

        # Retorna um dicionário com os artefatos
        return {
            "plot_bytes": plot_buffer.getvalue(),
            "report_str": report_md,
            "metrics":    band_metrics
        }
    
    def save(self, result: dict, record: ExperimentRecord) -> ExperimentRecord:
        """Salva os múltiplos artefatos (PNG e MD) gerados pela validação apenas localmente."""
        import hashlib
        from pathlib import Path

        # Define um diretório local padrão se o usuário não enviou um via CLI/API
        base_uri = record.output_path or f"./outputs/validation_{record.experiment_id}"
        
        out_dir = Path(base_uri)
        out_dir.mkdir(parents=True, exist_ok=True)
        
        # Grava os bytes da imagem e a string do relatório no disco
        (out_dir / "scatter.png").write_bytes(result["plot_bytes"])
        (out_dir / "report.md").write_text(result["report_str"], encoding="utf-8")

        # Atualiza o registro (record) com os metadados do salvamento
        record.output_path = str(out_dir)
        record.status = "completed"
        record.output_sha256 = hashlib.sha256(result["report_str"].encode()).hexdigest() 
        
        record.add_log(f"Saved artifacts locally to {out_dir.absolute()}")
        
        return record

    def save__(self, result: dict, record: ExperimentRecord) -> ExperimentRecord:
        """Salva os múltiplos artefatos (PNG e MD) gerados pela validação."""
        from dissmodel.io._storage import get_default_client
        import hashlib

        base_uri = record.output_path or f"s3://dissmodel-outputs/experiments/{record.experiment_id}/validation"
        
        if base_uri.startswith("s3://"):
            client = get_default_client()
            bucket, path = base_uri[5:].split("/", 1)
            
            # Upload PNG
            client.put_object(
                bucket_name=bucket, object_name=f"{path}/scatter.png",
                data=io.BytesIO(result["plot_bytes"]), length=len(result["plot_bytes"]),
                content_type="image/png"
            )
            # Upload MD
            md_bytes = result["report_str"].encode("utf-8")
            client.put_object(
                bucket_name=bucket, object_name=f"{path}/report.md",
                data=io.BytesIO(md_bytes), length=len(md_bytes),
                content_type="text/markdown"
            )
        else:
            from pathlib import Path
            out_dir = Path(base_uri)
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "scatter.png").write_bytes(result["plot_bytes"])
            (out_dir / "report.md").write_text(result["report_str"], encoding="utf-8")

        record.output_path = base_uri
        record.status = "completed"
        # Pode armazenar o JSON resumido das métricas direto no banco para painel rápido
        record.output_sha256 = hashlib.sha256(result["report_str"].encode()).hexdigest() 
        return record


# ── helpers ───────────────────────────────────────────────────────────────────

def _build_mock_raster(gdf: gpd.GeoDataFrame) -> tuple[RasterBackend, np.ndarray, np.ndarray]:
    """Cria a matriz 1:1 ignorando a geografia real para validar a matemática."""
    rows, cols = gdf["row"].astype(int).values, gdf["col"].astype(int).values
    n_rows, n_cols = int(rows.max()) + 1, int(cols.max()) + 1

    b = RasterBackend(shape=(n_rows, n_cols))
    mask = np.zeros((n_rows, n_cols), dtype=bool)
    mask[rows, cols] = True
    b.set("mask", mask)

    for col in CANONICAL_COLS:
        if col in gdf.columns:
            arr = np.zeros((n_rows, n_cols), dtype=np.float32)
            arr[rows, cols] = gdf[col].astype(float).values
            b.set(col, arr)
    return b, rows, cols

def _build_markdown(n_steps, tol, vec_ms, ras_ms, metrics) -> str:
    lines = [
        "# Coastal Dynamics Validation Report\n",
        f"**Steps:** {n_steps} | **Tolerance:** {tol}\n\n",
        "## Runtime Performance\n",
        f"| Substrate | ms/step | Speedup |\n|---|---|---|\n",
        f"| Vector | {vec_ms:.1f} | 1.0x |\n",
        f"| Raster | {ras_ms:.1f} | {vec_ms/ras_ms:.1f}x |\n\n",
        "## Accuracy Metrics\n",
        "| Band | Match % | MAE | RMSE | Max Err | N Cells |\n|---|---|---|---|---|---|\n"
    ]
    for band, m in metrics.items():
        lines.append(f"| {band} | {m['match_pct']:.2f}% | {m['mae']:.6f} | {m['rmse']:.6f} | {m['max_err']:.6f} | {m['n_cells']} |\n")
    return "".join(lines)


if __name__ == "__main__":
    run_cli(CoastalValidationExecutor)