# Coastal Dynamics — DisSModel Example

This repository demonstrates how to build **spatial simulation models using the [DisSModel](https://github.com/lambdageo/dissmodel) framework**.

The project implements a set of **coastal ecosystem processes**:

- Sea-level rise and flooding dynamics
- Mangrove migration and soil transitions

The same processes are implemented on **two spatial substrates** to illustrate DisSModel's dual-backend architecture:

| Substrate | Representation | Entry point |
|-----------|---------------|-------------|
| **Raster** | GeoTIFF / Shapefile → `RasterBackend` | `examples/run_raster.py` |
| **Vector** | Shapefile → `GeoDataFrame` | `examples/run_vector.py` |

---

## Repository Structure

```
coastal-dynamics/
├── coastal_dynamics/
│   ├── common/
│   │   └── constants.py       land-use codes, colours, band specs
│   ├── raster/
│   │   ├── flood_model.py     FloodModel (NumPy vectorized)
│   │   └── mangrove_model.py  MangroveModel (NumPy vectorized)
│   └── vector/
│       ├── flood_model.py     FloodModel (GeoDataFrame)
│       └── mangue_model.py    MangroveModel (GeoDataFrame)
├── data/
│   ├── elevacao_pol/          real Maranhão coast dataset
│   ├── synthetic_grid_60x60_shp.zip
│   └── synthetic_grid_60x60_tiff.zip
├── examples/
│   ├── run_raster.py
│   └── run_vector.py
└── pyproject.toml
```

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/lambdageo/coastal-dynamics.git
cd coastal-dynamics
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate      # Linux / macOS
# .venv\Scripts\activate       # Windows
```

### 3. Install in editable mode

```bash
pip install -e .
```

This installs `coastal_dynamics` as a package — no `PYTHONPATH` tricks needed.

---

## Running the Simulations

### Raster — from GeoTIFF (plain or zipped)

```bash
python examples/run_raster.py data/synthetic_grid_60x60_tiff.zip
```

### Raster — from Shapefile (rasterized on the fly)

```bash
python examples/run_raster.py data/elevacao_pol.zip \
    --resolution 30 \
    --crs EPSG:5880 \
    --bands uso alt solo \
    --format vector
```

### Vector

```bash
python examples/run_vector.py data/synthetic_grid_60x60_shp.zip
```

### Common options

| Option | Description | Default |
|--------|-------------|---------|
| `--bands` | Bands to visualize: `uso solo alt` | `uso` |
| `--resolution` | Cell size in CRS units (shapefile input only) | `100` |
| `--crs` | Target CRS, e.g. `EPSG:5880` | native |
| `--format` | Force `tiff` or `vector` (auto-detected from extension) | auto |
| `--acrecao` | Enable sediment accretion (Alongi 2008) | off |
| `--no-save` | Skip saving the output GeoTIFF | — |

---

## Example Datasets

| File | Type | Description |
|------|------|-------------|
| `synthetic_grid_60x60_tiff.zip` | GeoTIFF | 60×60 synthetic coastal grid |
| `synthetic_grid_60x60_shp.zip` | Shapefile | Same grid as polygons |
| `elevacao_pol.zip` | Shapefile | Real Maranhão coast (~50k cells, 30m resolution) |

---

## Model Processes

### Flood Dynamics

Simulates sea-level rise propagation across the landscape. At each step:

- Sea level increases by `taxa_elevacao` m/year (default: 0.011 m — IPCC RCP8.5)
- Flooded cells propagate water to lower-elevation neighbours
- Terrain elevation adjusts due to water flux

### Mangrove Migration

Simulates ecosystem response to rising sea levels:

- Mangrove cells migrate inland following soil type transitions
- Tidal influence threshold (`altura_mare`) controls migration range
- Optional sediment accretion process based on Alongi (2008)

---

## Performance

Both substrates produce equivalent results. Performance differs significantly:

| Substrate | ~50k cells | Notes |
|-----------|-----------|-------|
| Raster | ~8 ms/step | NumPy vectorized |
| Vector | ~2 min/step | GeoDataFrame per-cell |

---

## Requirements

- Python 3.11+
- dissmodel >= 0.3.0
- numpy, geopandas, rasterio

See `pyproject.toml` for the full dependency list.

---

## License

MIT — [LambdaGEO Research Group](https://lambdageo.github.io), UFMA

## Authors

**Sergio Souza Costa, PhD**  
Associate Professor — Federal University of Maranhão (UFMA)  
[github.com/profsergiocosta](https://github.com/profsergiocosta) · [lambdageo.github.io](https://lambdageo.github.io)
