"""Corre el escenario por defecto y muestra la comparación. Uso: python -m engine"""

from __future__ import annotations

import json
import sys

from engine.compare import run_scenario
from engine.config import Params, parse_params


def main() -> None:
    raw = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}
    params = parse_params(raw) if raw else Params()
    result = run_scenario(params)
    comp = result["comparacion"]
    print(result["recomendacion"])
    print(f"huella {result['huella']}")
    for name, block in result["estrategias"].items():
        print(
            f"{name:12} incidencia {block['incidencia_media']:.1f} "
            f"[{block['incidencia_p05']:.1f}–{block['incidencia_p95']:.1f}] "
            f"ataque {block['ataque_medio'] * 100:.1f}%"
        )
    print(
        "salvados vs nada "
        f"{comp['salvados_vs_nada_media']:.1f} "
        f"[{comp['salvados_vs_nada_p05']:.1f}–{comp['salvados_vs_nada_p95']:.1f}]"
    )


if __name__ == "__main__":
    main()
