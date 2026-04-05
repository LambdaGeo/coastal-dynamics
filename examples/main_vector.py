from coastal_dynamics.executor.coastal_vector_executor import CoastalVectorExecutor

import matplotlib
matplotlib.use('tkagg')

from dissmodel.executor.cli import run_cli

if __name__ == "__main__":
    run_cli(CoastalVectorExecutor)