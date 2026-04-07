# examples/main_benchmark.py
from __future__ import annotations

# Blindagem do Matplotlib (sempre no topo!)
import matplotlib
matplotlib.use('qtagg') # ou 'Agg', dependendo do seu ambiente Linux

from dissmodel.executor.cli import run_cli
from coastal_dynamics.executor.coastal_benchmark_executor import CoastalBenchmarkExecutor

if __name__ == "__main__":
    run_cli(CoastalBenchmarkExecutor)