import json

from lambdas.aggregator.handler import _collect, _summarize
from lambdas.orchestrator.handler import handler as orchestrate
from lambdas.simulator.handler import handler as simulate_one


def test_orquestador_sincrono_devuelve_la_huella():
    event = {
        "httpMethod": "POST",
        "path": "/api/simulate",
        "body": json.dumps(
            {"seed": 8, "n_runs": 2, "population": 120, "days": 12, "vaccines": 8, "criterio": "degree"}
        ),
    }
    first = orchestrate(event)
    second = orchestrate(event)
    assert first["statusCode"] == 200
    body_a = json.loads(first["body"])
    body_b = json.loads(second["body"])
    assert body_a["huella"] == body_b["huella"]
    assert body_a["estado"] == "SUCCEEDED"
    assert "Access-Control-Allow-Origin" in first["headers"]


def test_orquestador_rechaza_parametros():
    event = {"httpMethod": "POST", "path": "/api/simulate", "body": json.dumps({"days": 1})}
    response = orchestrate(event)
    assert response["statusCode"] == 400


def test_simulador_de_una_corrida():
    from engine.config import Params

    params = Params()
    params.n_runs = 2
    params.population = 100
    params.days = 10
    result = simulate_one({"run": 1, "params": params.to_dict()})
    assert result["run"] == 1
    assert set(result["incidencias"]) == {"estrategia", "azar", "nada"}


def test_agregador_lee_resultados_anidados():
    run = {
        "incidencias": {"estrategia": 10, "azar": 14, "nada": 20},
        "picos": {"estrategia": 4, "azar": 6, "nada": 9},
        "zombies": {
            "estrategia": [0, 2, 1],
            "azar": [0, 3, 2],
            "nada": [0, 5, 4],
        },
    }
    found: list[dict] = []
    _collect({"ResultWriterDetails": {"payload": [run, run]}}, found)
    assert len(found) == 2
    summary = _summarize(found)
    assert summary["comparacion"]["salvados_vs_nada_media"] == 10
    assert summary["estrategias"]["nada"]["incidencia_media"] == 20
