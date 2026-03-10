# Coastal Dynamics Models using DisSModel

This repository demonstrates how to build **spatial simulation models using the [DisSModel](https://github.com/lambdageo/dissmodel) framework**.

The project implements a set of **coastal ecosystem processes**, including:

- sea-level rise
- flooding dynamics
- mangrove migration

These processes are implemented as **example models** to illustrate how DisSModel can be used to design and execute **spatially explicit simulations**.

To highlight the flexibility of the framework, the same ecological processes are implemented using two spatial representations:

- **Raster models** based on GeoTIFF grids
- **Vector models** based on Shapefile polygons

This dual implementation shows how DisSModel supports different spatial backends while maintaining the same model logic, enabling experiments comparing **spatial modeling strategies, performance, and simulation behavior**.

---

# Repository Structure

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
│
├── examples
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

# Installation

## 1. Clone the repository

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

# Example Datasets

The repository includes **synthetic datasets** for testing.

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

The script performs:

1. Loading the Shapefile dataset into a GeoDataFrame
2. Constructing the spatial topology (Queen neighborhood)
3. Running `FloodVectorModel` and `MangroveModel` step by step
4. Updating polygon attributes during the simulation

---

# Model Processes

## Flood Dynamics

The flooding model simulates **sea-level rise propagation** across the landscape.

Main processes:

- Sea level increases over time at a configurable rate (default: 0.011 m/year — IPCC RCP8.5)
- Flooded cells propagate water to neighboring cells
- Terrain elevation dynamically adjusts due to water flux

## Mangrove Migration

The mangrove model simulates **ecosystem migration under rising sea levels**.

Processes include:

- Inland mangrove migration
- Soil type transitions
- Tidal influence threshold
- Optional sediment accretion based on Alongi (2008)

---

# Simulation Metrics

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

# Scientific Motivation

Coastal ecosystems such as mangroves are highly sensitive to **sea-level rise and hydrological dynamics**.

This project explores how different **spatial representations** influence:

- diffusion processes
- ecological transitions
- computational performance
- scalability of spatial models

By implementing the same processes using **raster and vector spatial backends**, this repository supports comparative experiments in spatial simulation modeling.

---

# Requirements

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

# License

This repository is part of the **LambdaGEO research initiative**.

---

# Authors

**Sergio Souza Costa, PhD**
Associate Professor – Computer Engineering
Federal University of Maranhão (UFMA)
Lead Researcher – LambdaGEO

GitHub: [https://github.com/profsergiocosta](https://github.com/profsergiocosta)
Research Group: [https://lambdageo.github.io](https://lambdageo.github.io)
