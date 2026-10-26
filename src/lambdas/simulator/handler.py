"""Una corrida del mapa: misma semilla hija, tres políticas."""

from __future__ import annotations

from engine.compare import run_one
from engine.config import parse_params


def handler(event, _context=None):
    params = parse_params(event["params"], max_runs=10_000)
    run = int(event["run"])
    if run < 0 or run >= params.n_runs:
        raise ValueError("La corrida está fuera del escenario.")
    return run_one(params, run)
