

# Coastal Dynamics — DisSModel Example 🌊

> **A Python simulation of coastal ecosystem processes built on top of [DisSModel](https://github.com/LambdaGeo/dissmodel).**

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![DisSModel](https://img.shields.io/badge/DisSModel-%3E%3D0.3.0-orange.svg)](https://github.com/LambdaGeo/dissmodel)
[![LambdaGeo](https://img.shields.io/badge/LambdaGeo-Research-green.svg)](https://github.com/LambdaGeo)

---

## 📖 About

This repository demonstrates how to build robust, scalable spatial simulation models using the **DisSModel** framework. The project implements a set of coupled coastal ecosystem processes:

1. **Flood Dynamics:** Sea-level rise propagation and terrain elevation adjustments.
2. **Mangrove Migration:** Ecosystem response to rising sea levels, soil transitions, and sediment accretion.

### The Dual-Substrate Architecture
The exact same scientific processes are implemented on **two spatial substrates** to illustrate DisSModel's environment-agnostic capabilities:

| Substrate | Representation | Core Engine | Entry point |
|-----------|---------------|-------------|-------------|
| **Raster** | GeoTIFF → `RasterBackend` | NumPy (Vectorized) | `examples/main_raster.py` |
| **Vector** | Shapefile → `GeoDataFrame` | Iterative Polygons | `examples/main_vector.py` |

---

## 🚀 Quick Start

### 1. Installation

```bash
git clone https://github.com/lambdageo/coastal-dynamics.git
cd coastal-dynamics
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
```

### 2. Running Simulations (CLI)

**Raster Simulation (Fast / NumPy-based)**
```bash
python examples/main_raster.py run \
  --input examples/data/input/synthetic_grid_60x60_tiff.zip \
  --format tiff \
  --output examples/data/output/saida.tiff \
  --param interactive=true \
  --param end_time=20
```

**Vector Simulation (Geographic Polygons)**
```bash
python examples/main_vector.py run \
  --input examples/data/input/synthetic_grid_60x60_shp.zip \
  --output examples/data/output/saida.gpkg \
  --param interactive=true \
  --param end_time=20
```

**Running with Calibrated Parameters (TOML)**
```bash
python examples/main_raster.py run \
  --input examples/data/input/synthetic_grid_60x60_tiff.zip \
  --format tiff \
  --toml examples/model.toml
```

---

## 📊 Mathematical Benchmark

To ensure that the spatial logic is flawless regardless of the underlying data structure, this project includes a **Benchmark Executor**. It runs both Vector and Raster models simultaneously and compares their outputs.

```bash
# Run the Mathematical Benchmark suite
python examples/main_benchmark.py run \
  --input examples/data/input/synthetic_grid_60x60_shp.zip \
  --output ./benchmark/ \
  --param end_time=10 \
  --param tolerance=0.05
```

**Benchmark Results:**
The architecture guarantees absolute parity. Comparing Raster vs Vector outputs yields a **100% Match** across land use (`uso`), soil (`solo`), and elevation (`alt`), proving that the models are completely agnostic to the spatial environment.

---

## 🗂️ Repository Structure

```text
coastal-dynamics/
├── coastal_dynamics/
│   ├── executor/                    # Infrastructure Layer (CLI/API)
│   │   ├── coastal_benchmark_executor.py
│   │   ├── coastal_raster_executor.py
│   │   └── coastal_vector_executor.py
│   ├── raster/                      # NumPy-based models
│   │   ├── flood_model.py
│   │   └── mangrove_model.py
│   └── vector/                      # GeoDataFrame-based models
│       ├── flood_model.py
│       └── mangrove_model.py
├── examples/
│   ├── data/input/                  # 60x60 Synthetic Grids
│   ├── main_raster.py               # CLI entry point for Raster
│   ├── main_vector.py               # CLI entry point for Vector
│   └── model.toml                   # Configuration as Code
├── pyproject.toml
└── requirements.txt
```

---

## 🧩 Model Processes

### 🌊 Flood Dynamics (`flood_model.py`)
Simulates sea-level rise propagation across the landscape.
- Sea level increases over time at a configurable rate (default: `0.011` m/year — IPCC RCP8.5).
- Flooded cells propagate water to neighboring cells using a Push-based algorithm.
- Terrain elevation dynamically adjusts due to water flux.

### 🌿 Mangrove Migration (`mangrove_model.py`)
Simulates ecosystem transitions driven by tidal influence.
- Inland mangrove migration triggered by flooding thresholds.
- Soil type transitions (e.g., from mainland soil to mangrove mud).
- Optional sediment accretion based on Alongi (2008).

During execution, the models track temporal metrics via the DisSModel `ExperimentRecord`, such as `celulas_inundadas`, `novas_inundadas`, `nivel_mar_atual`, and `mangue_migrado`.

---

## 📚 Requirements

- **Python:** 3.11+
- **Core Framework:** `dissmodel >= 0.3.0`
- **Spatial Data:** `numpy`, `geopandas`, `rasterio`, `shapely`
- **Visualization:** `matplotlib`

*See `pyproject.toml` for the full dependency list.*

---

## 🔬 Citation

If you use this project or the DisSModel architecture in your research, please cite:

```text
Bezerra, R. (2014). Modelagem da migração de manguezais sob efeito da 
elevação do nível do mar. INPE.

Costa, S. S. et al. (2026). DisSModel — A Python framework for spatial 
discrete simulation models. LambdaGEO, UFMA.
```

---

Developed by the **[LambdaGeo](https://lambdageo.github.io)** research group.