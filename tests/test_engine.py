import numpy as np
import pytest

from engine.compare import run_one, run_scenario
from engine.config import Params, parse_params
from engine.network import build_city
from engine.strategies import pick_targets


def test_misma_semilla_misma_huella():
    params = parse_params({"seed": 42, "n_runs": 4, "population": 240, "days": 20})
    first = run_scenario(params)
    second = run_scenario(params)
    assert first["huella"] == second["huella"]
    assert first["estrategias"] == second["estrategias"]


def test_otra_semilla_puede_cambiar_el_resultado():
    base = {"n_runs": 3, "population": 200, "days": 20, "beta": 0.16, "vaccines": 20}
    a = run_scenario(parse_params({**base, "seed": 1}))
    b = run_scenario(parse_params({**base, "seed": 2}))
    assert a["huella"] != b["huella"]


def test_eficacia_cero_equivale_a_no_intervenir():
    params = parse_params(
        {
            "seed": 7,
            "n_runs": 3,
            "population": 200,
            "days": 18,
            "vaccine_efficacy": 0,
            "vaccines": 25,
        }
    )
    result = run_scenario(params)
    assert result["estrategias"]["estrategia"]["incidencia_media"] == result["estrategias"]["nada"]["incidencia_media"]


def test_no_vacuna_al_paciente_cero_y_gasta_el_presupuesto():
    city = build_city(180, seed=3)
    patient = 5
    targets = pick_targets(city, k=15, patient_zero=patient, criterio="degree", rng=None)
    assert patient not in targets
    assert len(targets) == 15
    assert len(set(targets)) == 15


def test_azar_tambien_respeta_presupuesto_y_semilla():
    city = build_city(160, seed=9)
    rng = np.random.default_rng(123)
    first = pick_targets(city, k=10, patient_zero=0, criterio="random", rng=rng)
    rng_again = np.random.default_rng(123)
    second = pick_targets(city, k=10, patient_zero=0, criterio="random", rng=rng_again)
    assert first == second
    assert 0 not in first
    assert len(first) == 10


def test_estrategia_supera_las_dos_lineas_base():
    result = run_scenario(Params())
    comp = result["comparacion"]
    assert comp["salvados_vs_nada_media"] > 100
    assert comp["salvados_vs_azar_media"] > 50
    # Alguna corrida puede empatar si el brote se apaga solo. No puede perder la media.
    assert comp["corridas_mejor_que_nada"] >= result["params"]["n_runs"] - 1
    assert comp["corridas_mejor_que_azar"] >= result["params"]["n_runs"] - 1
    assert result["estrategias"]["estrategia"]["incidencia_media"] < 3
    curves = result["estrategias"]
    assert curves["estrategia"]["curvas"]["R"][0] == pytest.approx(result["params"]["vaccines"])
    assert curves["nada"]["curvas"]["R"][0] == 0


def test_parametros_invalidos():
    with pytest.raises(ValueError):
        parse_params({"beta": 2})
    with pytest.raises(ValueError):
        parse_params({"locus": "playa"})
    with pytest.raises(ValueError):
        parse_params({"n_runs": 0})
    with pytest.raises(ValueError):
        parse_params({"patient_zero": "nadie"})


def test_corrida_individual_coincide_con_el_agregado():
    params = parse_params({"seed": 11, "n_runs": 2, "population": 180, "days": 15, "vaccines": 12})
    full = run_scenario(params)
    incidences = []
    for run in range(2):
        one = run_one(params, run)
        incidences.append(one["incidencias"]["estrategia"])
    assert round(sum(incidences) / 2, 4) == full["estrategias"]["estrategia"]["incidencia_media"]


def test_cuarentena_no_es_identica_a_vacunar_con_eficacia_total():
    common = {"seed": 4, "n_runs": 3, "population": 220, "days": 20, "vaccines": 18, "beta": 0.16}
    vacuna = run_scenario(parse_params({**common, "intervention": "vacuna"}))
    cuarentena = run_scenario(parse_params({**common, "intervention": "cuarentena"}))
    assert (
        vacuna["estrategias"]["estrategia"]["incidencia_media"]
        != cuarentena["estrategias"]["estrategia"]["incidencia_media"]
    )
