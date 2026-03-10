
# Coastal Dynamics Models using DisSModel

# Coastal Dynamics Models using DisSModel

This repository demonstrates how to build **spatial simulation models using the DisSModel framework**.

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
│       └── mangue_model.py
│
├── data
│   ├── synthetic_grid_60x60_shp.zip
│   └── synthetic_grid_60x60_tiff.zip
│
├── examples
│   ├── run_raster.py
│   └── run_vector.py
│
└── requirements

````

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
````

---

## 2. Create a Python virtual environment

```bash
python -m venv .venv
```

Activate it.

### Linux / macOS

```bash
source .venv/bin/activate
```

### Windows

```bash
.venv\Scripts\activate
```

---

## 3. Install project dependencies

```bash
pip install -r requirements
```

---

## 4. Install DisSModel

Clone and install the DisSModel framework:

```bash
git clone https://github.com/lambdageo/dissmodel.git
cd dissmodel
pip install -e .
```

Return to this repository:

```bash
cd ../coastal-dynamics
```

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

* `uso` → land use
* `alt` → elevation
* `solo` → soil type

### Vector dataset

Contains a **Shapefile grid** with the same attributes stored as polygon fields.

Both represent a **60×60 synthetic coastal grid** used for simulation experiments.

---

# Running the Simulations

The example scripts expect the dataset path as a command-line argument.

Since the project is not installed as a Python package, you must include the project root in `PYTHONPATH`.

---

# Running the Raster Simulation

Raster simulations operate on **GeoTIFF grids**.

Run:

```bash
PYTHONPATH=. python examples/run_raster.py data/synthetic_grid_60x60_tiff.zip
```

The script performs:

1. Loading the raster dataset
2. Building a raster backend using DisSModel
3. Running the Flood and Mangrove models
4. Updating raster arrays at each simulation step

---

# Running the Vector Simulation

Vector simulations operate on **polygon cells stored in a Shapefile**.

Run:

```bash
PYTHONPATH=. python examples/run_vector.py data/synthetic_grid_60x60_shp.zip
```

The script performs:

1. Loading the Shapefile dataset
2. Constructing the spatial topology
3. Executing the ecological processes
4. Updating polygon attributes during the simulation

---

# Model Processes

## Flood Dynamics

The flooding model simulates **sea-level rise propagation** across the landscape.

Main processes:

* Sea level increases over time
* Flooded cells propagate water to neighboring cells
* Terrain elevation dynamically adjusts due to water flux

---

## Mangrove Migration

The mangrove model simulates **ecosystem migration under rising sea levels**.

Processes include:

* Inland mangrove migration
* Soil type transitions
* Tidal influence threshold
* Optional **sediment accretion process** based on Alongi (2008)

---

# Simulation Metrics

During execution the models track several indicators:

* flooded cells
* newly flooded cells
* mangrove migration
* soil migration
* current sea level

These metrics can be used for **analysis, benchmarking, and visualization**.

---

# Scientific Motivation

Coastal ecosystems such as mangroves are highly sensitive to **sea-level rise and hydrological dynamics**.

This project explores how different **spatial representations** influence:

* diffusion processes
* ecological transitions
* computational performance
* scalability of spatial models

By implementing the same processes using **raster and vector spatial backends**, this repository supports comparative experiments in spatial simulation modeling.

---

# Requirements

Typical dependencies include:

* Python 3.11+
* numpy
* geopandas
* rasterio
* shapely

See the `requirements` file for the full list.

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



---
