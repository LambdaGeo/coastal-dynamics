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
coastal-dynamics
│
├── coastal_dynamics
│   ├── common
│   │   └── constants.py
│   │
│   ├── raster
│   │   ├── flood_model.py
│   │   └── mangrove_model.py
│   │
│   └── vector
│       ├── flood_model.py
│       └── mangrove_model.py
│
├── data
│   ├── synthetic_grid_60x60_shp.zip
│   └── synthetic_grid_60x60_tiff.zip
├── examples/
│   ├── run_raster.py
│   └── run_vector.py
│
├── requirements.txt
└── pyproject.toml
```

### Main Components

**Models**

- `flood_model.py` → Simulates flooding due to sea-level rise
- `mangrove_model.py` → Simulates mangrove migration and soil dynamics

**Spatial representations**

- `raster/` → grid-based spatial modeling using GeoTIFF
- `vector/` → polygon-based spatial modeling using Shapefiles

**Examples**

- `run_raster.py` → executes the raster simulation
- `run_vector.py` → executes the vector simulation

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/lambdageo/coastal-dynamics.git
cd coastal-dynamics
```

## 2. Create a Python virtual environment

```bash
python -m venv .venv
```

Activate it:

**Linux / macOS**
```bash
source .venv/bin/activate
```

**Windows**
```bash
.venv\Scripts\activate
```

## 3. Install dependencies

```bash
pip install -e .
```

This installs the project and all dependencies, including
[DisSModel 0.2.0](https://pypi.org/project/dissmodel/).

---

## Running the Simulations

### Raster — from GeoTIFF (plain or zipped)

```bash
python examples/run_raster.py data/synthetic_grid_60x60_tiff.zip
```
data/
   synthetic_grid_60x60_tiff.zip
   synthetic_grid_60x60_shp.zip
```

### Raster dataset

Contains **GeoTIFF layers** representing:

- `uso` → land use
- `alt` → elevation
- `solo` → soil type

### Vector dataset

Contains a **Shapefile grid** with the same attributes stored as polygon fields.

Both represent a **60×60 synthetic coastal grid** used for simulation experiments.

---

# Running the Simulations

## Raster simulation

Raster simulations operate on **GeoTIFF grids**.

```bash
python examples/run_raster.py data/synthetic_grid_60x60_tiff.zip
```

The script performs:

1. Loading the raster dataset into a `RasterBackend`
2. Running `FloodRasterModel` and `MangroveModel` step by step
3. Updating raster arrays at each simulation step

## Vector simulation

Vector simulations operate on **polygon cells stored in a Shapefile**.

```bash
python examples/run_vector.py data/synthetic_grid_60x60_shp.zip
```

### Common options

1. Loading the Shapefile dataset into a GeoDataFrame
2. Constructing the spatial topology (Queen neighborhood)
3. Running `FloodVectorModel` and `MangroveModel` step by step
4. Updating polygon attributes during the simulation

---

## Example Datasets

## Flood Dynamics

The flooding model simulates **sea-level rise propagation** across the landscape.

Main processes:

- Sea level increases over time at a configurable rate (default: 0.011 m/year — IPCC RCP8.5)
- Flooded cells propagate water to neighboring cells
- Terrain elevation dynamically adjusts due to water flux

## Model Processes

### Flood Dynamics

Simulates sea-level rise propagation across the landscape. At each step:

- Inland mangrove migration
- Soil type transitions
- Tidal influence threshold
- Optional sediment accretion based on Alongi (2008)

### Mangrove Migration

Simulates ecosystem response to rising sea levels:

During execution the models track:

- `celulas_inundadas` — total flooded cells
- `novas_inundadas` — newly flooded cells per step
- `nivel_mar_atual` — current sea level (m)
- `mangue_migrado` — total migrated mangrove cells
- `solo_migrado` — total migrated soil cells

---

# DisSModel version

This project requires **DisSModel 0.2.0**, which introduced:

- `RasterBackend` and `RasterModel` — NumPy-based execution engine
- `RasterCellularAutomaton` — vectorized CA base class
- `SpatialModel` — base class for vector push/source models
- `RasterMap` — raster visualization with categorical and continuous modes

See the [DisSModel changelog](https://github.com/lambdageo/dissmodel/releases) for details.

---

## Validation

The raster and vector substrates are validated for equivalence using
`examples/validate_coastal.py`. Results on the Maranhão coast dataset
(50,496 cells, 5 steps):

| Band | Match % | MAE | Notes |
|------|---------|-----|-------|
| `uso` (land use) | **100.00%** | 0.000000 | exact |
| `solo` (soil) | **100.00%** | 0.000000 | exact |
| `alt` (elevation) | **100.00%** | 0.000037 | floating-point accumulation only |

- diffusion processes
- ecological transitions
- computational performance
- scalability of spatial models

```bash
python examples/validate_coastal.py data/elevacao_pol.zip \
    --resolution 30 --crs EPSG:5880 --steps 5
```

---

## Performance

- Python 3.11+
- dissmodel >= 0.2.0
- numpy
- geopandas
- rasterio
- shapely

See `requirements.txt` for the pinned versions.

---

# Citation

If you use this project in your research, please cite:

```
Bezerra, R. (2014). Modelagem da migração de manguezais sob efeito da
elevação do nível do mar. INPE.

Costa, S. S. et al. DisSModel — A Python framework for spatial discrete
simulation models. LambdaGEO, UFMA.
```

---

## Requirements

- Python 3.11+
- dissmodel >= 0.3.0
- numpy, geopandas, rasterio

See `pyproject.toml` for the full dependency list.

---

GitHub: [https://github.com/profsergiocosta](https://github.com/profsergiocosta)
Research Group: [https://lambdageo.github.io](https://lambdageo.github.io)
