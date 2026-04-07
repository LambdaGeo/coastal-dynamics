# coastal_dynamics/executor/__init__.py

from .coastal_raster_executor import CoastalRasterExecutor
from .coastal_vector_executor import CoastalVectorExecutor
from .coastal_benchmark_executor import CoastalBenchmarkExecutor

# A variável mágica __all__ define exatamente o que é exportado
# quando alguém faz `from coastal_dynamics.executor import *`
__all__ = [
    "CoastalRasterExecutor",
    "CoastalVectorExecutor",
    "CoastalBenchmarkExecutor",
    "EXECUTOR_REGISTRY", # Exportando o registro também
]

# BÔNUS PARA A API/WORKER:
# Um dicionário que mapeia a string do request (JSON) para a Classe real
EXECUTOR_REGISTRY = {
    CoastalRasterExecutor.name: CoastalRasterExecutor,
    CoastalVectorExecutor.name: CoastalVectorExecutor,
    CoastalBenchmarkExecutor.name: CoastalBenchmarkExecutor,
}