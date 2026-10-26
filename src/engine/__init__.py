"""Motor epidemiológico puro. Misma semilla y mismos parámetros → mismo resultado."""

from engine.compare import run_scenario
from engine.config import Params, parse_params

__all__ = ["Params", "parse_params", "run_scenario"]
