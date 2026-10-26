"""Compara la estrategia contra no intervenir y contra el azar.

Cada corrida tiene su semilla hija. Dentro de la corrida, las tres políticas
usan el mismo paciente cero y la misma cinta aleatoria de contagios.
"""

from __future__ import annotations

import hashlib
import json

import numpy as np

from engine.config import Params
from engine.network import build_city, describe_person, pool_for_locus
from engine.seir import apply_initial_state, simulate
from engine.strategies import compute_betweenness, pick_targets

POLICIES = ("estrategia", "azar", "nada")


def derive_seed(master: int, *parts: int) -> int:
    ss = np.random.SeedSequence([int(master) & 0x7FFFFFFF, *[int(p) & 0x7FFFFFFF for p in parts]])
    return int(ss.generate_state(1, dtype=np.uint32)[0])


def run_scenario(params: Params) -> dict:
    city = build_city(params.population, params.seed)
    betweenness = compute_betweenness(city) if params.criterio == "betweenness" else None

    per_policy_incidence: dict[str, list[int]] = {name: [] for name in POLICIES}
    per_policy_peak: dict[str, list[int]] = {name: [] for name in POLICIES}
    curve_sum = {name: np.zeros((params.days + 1, 4), dtype=np.float64) for name in POLICIES}
    zombie_runs = {name: [] for name in POLICIES}
    saved_vs_none: list[int] = []
    saved_vs_random: list[int] = []
    preview = None
    patient_zeros: list[int] = []

    for run in range(params.n_runs):
        run_seed = derive_seed(params.seed, 1000 + run)
        patient = _patient_zero(city, params, run_seed)
        patient_zeros.append(patient)
        transmission_seed = derive_seed(run_seed, 7)
        outcomes = {}
        for policy in POLICIES:
            targets = _targets(city, params, policy, patient, run_seed, betweenness)
            state, sus, weights = apply_initial_state(
                city.n,
                patient,
                targets,
                params.intervention if policy != "nada" else "vacuna",
                params.vaccine_efficacy if policy != "nada" else 1.0,
                city.edge_u,
                city.edge_v,
                city.weight,
                city.layer,
            )
            result = simulate(
                city.edge_u,
                city.edge_v,
                weights,
                city.n,
                params.days,
                params.beta,
                params.sigma,
                params.gamma,
                state,
                sus,
                transmission_seed,
            )
            outcomes[policy] = result
            per_policy_incidence[policy].append(result["incidence"])
            per_policy_peak[policy].append(result["peak_i"])
            curve_sum[policy] += result["hist"]
            zombie_runs[policy].append(result["hist"][:, 2].astype(np.float64))
            if policy == "estrategia" and preview is None:
                preview = [_person_out(city, node, betweenness) for node in targets[:12]]

        saved_vs_none.append(outcomes["nada"]["incidence"] - outcomes["estrategia"]["incidence"])
        saved_vs_random.append(outcomes["azar"]["incidence"] - outcomes["estrategia"]["incidence"])

    strategies = {}
    for policy in POLICIES:
        incidence = np.asarray(per_policy_incidence[policy], dtype=np.float64)
        peak = np.asarray(per_policy_peak[policy], dtype=np.float64)
        mean_curve = curve_sum[policy] / params.n_runs
        zombies = np.vstack(zombie_runs[policy])
        strategies[policy] = {
            "incidencia_media": _round(float(incidence.mean())),
            "incidencia_p05": _round(float(np.percentile(incidence, 5))),
            "incidencia_p95": _round(float(np.percentile(incidence, 95))),
            "pico_medio": _round(float(peak.mean())),
            "ataque_medio": _round(float(incidence.mean()) / city.n),
            "curvas": {
                "S": _series(mean_curve[:, 0]),
                "E": _series(mean_curve[:, 1]),
                "I": _series(mean_curve[:, 2]),
                "R": _series(mean_curve[:, 3]),
            },
            "zombies_p05": _series(np.percentile(zombies, 5, axis=0)),
            "zombies_p95": _series(np.percentile(zombies, 95, axis=0)),
        }

    saved_none = np.asarray(saved_vs_none, dtype=np.float64)
    saved_random = np.asarray(saved_vs_random, dtype=np.float64)
    base = strategies["nada"]["incidencia_media"]
    smart = strategies["estrategia"]["incidencia_media"]
    reduction = 0.0 if base <= 0 else (base - smart) / base

    payload = {
        "params": params.to_dict(),
        "red": city.summary,
        "dias": list(range(params.days + 1)),
        "estrategias": strategies,
        "comparacion": {
            "salvados_vs_nada_media": _round(float(saved_none.mean())),
            "salvados_vs_nada_p05": _round(float(np.percentile(saved_none, 5))),
            "salvados_vs_nada_p95": _round(float(np.percentile(saved_none, 95))),
            "salvados_vs_azar_media": _round(float(saved_random.mean())),
            "salvados_vs_azar_p05": _round(float(np.percentile(saved_random, 5))),
            "salvados_vs_azar_p95": _round(float(np.percentile(saved_random, 95))),
            "reduccion_vs_nada": _round(float(reduction)),
            "corridas_mejor_que_nada": int(np.sum(saved_none > 0)),
            "corridas_mejor_que_azar": int(np.sum(saved_random > 0)),
            "corridas": params.n_runs,
        },
        "recomendacion": _recomendacion(params, saved_none.mean(), reduction),
        "muestra_prioridad": preview or [],
        "pacientes_cero": patient_zeros,
        "leyenda": {
            "S": "Sano",
            "E": "Mordido",
            "I": "Zombie",
            "R": "Exorcizado",
            "estrategia": _label(params),
            "azar": "Al azar, mismo presupuesto",
            "nada": "Sin intervención",
        },
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    payload["huella"] = hashlib.sha256(encoded.encode()).hexdigest()[:16]
    return payload


def run_one(params: Params, run: int) -> dict:
    """Una corrida Monte Carlo con las tres políticas. La usa la Lambda del mapa."""

    city = build_city(params.population, params.seed)
    betweenness = compute_betweenness(city) if params.criterio == "betweenness" else None
    run_seed = derive_seed(params.seed, 1000 + run)
    patient = _patient_zero(city, params, run_seed)
    transmission_seed = derive_seed(run_seed, 7)
    out: dict = {"run": run, "patient_zero": patient, "incidencias": {}, "picos": {}, "zombies": {}}
    for policy in POLICIES:
        targets = _targets(city, params, policy, patient, run_seed, betweenness)
        if policy == "nada":
            targets = []
        state, sus, weights = apply_initial_state(
            city.n,
            patient,
            targets,
            params.intervention if policy != "nada" else "vacuna",
            params.vaccine_efficacy if policy != "nada" else 1.0,
            city.edge_u,
            city.edge_v,
            city.weight,
            city.layer,
        )
        result = simulate(
            city.edge_u,
            city.edge_v,
            weights,
            city.n,
            params.days,
            params.beta,
            params.sigma,
            params.gamma,
            state,
            sus,
            transmission_seed,
        )
        out["incidencias"][policy] = result["incidence"]
        out["picos"][policy] = result["peak_i"]
        out["zombies"][policy] = result["hist"][:, 2].astype(int).tolist()
    return out


def _targets(city, params: Params, policy: str, patient: int, run_seed: int, betweenness):
    if policy == "nada":
        return []
    if policy == "azar":
        rng = np.random.default_rng(derive_seed(run_seed, 3))
        return pick_targets(city, params.vaccines, patient, "random", rng, betweenness)
    return pick_targets(city, params.vaccines, patient, params.criterio, None, betweenness)


def _patient_zero(city, params: Params, run_seed: int) -> int:
    if params.patient_zero != "aleatorio":
        return int(params.patient_zero) % city.n
    rng = np.random.default_rng(derive_seed(run_seed, 1))
    pool = pool_for_locus(city, params.locus)
    return int(rng.choice(pool))


def _person_out(city, node: int, betweenness) -> dict:
    data = describe_person(city, node)
    if betweenness is not None:
        data["betweenness"] = round(float(betweenness[node]), 4)
    return data


def _label(params: Params) -> str:
    criterio = {
        "puentes": "centralidad de puentes",
        "degree": "grado",
        "betweenness": "intermediación",
        "anillo": "anillo del caso y grado",
    }[params.criterio]
    if params.intervention == "cuarentena":
        return f"Cuarentena por {criterio}"
    return f"Vacunación por {criterio}"


def _recomendacion(params: Params, saved: float, reduction: float) -> str:
    recurso = "dosis" if params.intervention == "vacuna" else "aislamientos"
    acuerdo = "asignadas" if recurso == "dosis" else "asignados"
    if saved > 1:
        pct = reduction * 100
        pct_txt = f"{pct:.1f}" if pct >= 99 else f"{pct:.0f}"
        return (
            f"Con {params.vaccines} {recurso} {acuerdo} por {_criterio_corto(params.criterio)}, "
            f"se evitan en promedio {saved:.0f} contagios frente a no hacer nada "
            f"({pct_txt}% menos en la muestra). "
            f"Misma semilla {params.seed}, {params.n_runs} corridas."
        )
    if saved > 0:
        return (
            f"La estrategia apenas supera a no intervenir ({saved:.1f} personas). "
            "Conviene subir el presupuesto o bajar el contagio antes de confiar en el plan."
        )
    return (
        "Con estos parámetros la estrategia no supera a no intervenir. "
        "Revisa contagio, presupuesto, eficacia o el lugar del brote: el plan actual no se recomienda."
    )


def _criterio_corto(criterio: str) -> str:
    return {
        "puentes": "puentes entre grupos (bus, mercado, aulas)",
        "degree": "grado en la red",
        "betweenness": "intermediación",
        "anillo": "el hogar y los contactos del caso, y luego el grado",
    }[criterio]


def _series(values: np.ndarray) -> list[float]:
    return [round(float(v), 2) for v in values]


def _round(value: float) -> float:
    return round(float(value), 4)
