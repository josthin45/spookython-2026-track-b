"""Un paso diario S → E → I → R sobre el grafo.

Estados del reto:
  0 Sano (susceptible)
  1 Mordido (expuesto, todavía no contagia)
  2 Zombie (infeccioso)
  3 Exorcizado (inmune: recuperado o vacunado con eficacia total)

La suerte de cada arista y de cada persona se consume SIEMPRE, esté o no
contagiando. Así dos estrategias con la misma semilla comparten la misma
suerte y la diferencia es solo a quién se protegió.
"""

from __future__ import annotations

import numpy as np

S, E, I, R = 0, 1, 2, 3
STATE_NAMES = ("S", "E", "I", "R")


def transmission_probability(beta: float, weight: np.ndarray) -> np.ndarray:
    """Probabilidad diaria de que un infeccioso contagie por esa arista.

    Peso 1 es un contacto de hogar. Un peso menor (bus, mercado) contagia menos:
    p = 1 - (1 - β) ** peso.
    """

    beta = float(beta)
    if beta <= 0:
        return np.zeros_like(weight)
    if beta >= 1:
        return np.where(weight > 0, 1.0, 0.0)
    return 1.0 - np.exp(weight * np.log1p(-beta))


def simulate(
    edge_u: np.ndarray,
    edge_v: np.ndarray,
    weight: np.ndarray,
    n: int,
    days: int,
    beta: float,
    sigma: float,
    gamma: float,
    initial_state: np.ndarray,
    susceptibility: np.ndarray,
    seed: int,
) -> dict:
    states = initial_state.astype(np.int8, copy=True)
    sus = susceptibility.astype(np.float64, copy=True)
    ever = (states == I) | (states == E)
    hist = np.zeros((days + 1, 4), dtype=np.int32)
    hist[0] = np.bincount(states, minlength=4)

    rng = np.random.default_rng(np.random.SeedSequence([int(seed) & 0x7FFFFFFF, 404]))
    prob = transmission_probability(beta, weight)
    n_edges = len(weight)

    for day in range(days):
        roll_uv = rng.random(n_edges)
        roll_vu = rng.random(n_edges)
        roll_prog = rng.random(n)

        su = states[edge_u]
        sv = states[edge_v]
        infect_v = (su == I) & (sv == S) & (roll_uv < prob * sus[edge_v])
        infect_u = (sv == I) & (su == S) & (roll_vu < prob * sus[edge_u])

        newly = np.zeros(n, dtype=bool)
        if infect_v.any():
            newly[edge_v[infect_v]] = True
        if infect_u.any():
            newly[edge_u[infect_u]] = True

        to_i = (states == E) & (roll_prog < sigma)
        to_r = (states == I) & (roll_prog < gamma)

        states[newly] = E
        ever[newly] = True
        states[to_i] = I
        states[to_r] = R
        hist[day + 1] = np.bincount(states, minlength=4)

    peak_day = int(np.argmax(hist[:, I]))
    return {
        "hist": hist,
        "incidence": int(ever.sum()),
        "peak_i": int(hist[:, I].max()),
        "peak_day": peak_day,
        "final_state": states,
    }


def apply_initial_state(
    n: int,
    patient_zero: int,
    targets: list[int],
    intervention: str,
    efficacy: float,
    edge_u: np.ndarray,
    edge_v: np.ndarray,
    weight: np.ndarray,
    layer: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Devuelve estado inicial, susceptibilidad y pesos (copia si hay cuarentena).

    La cuarentena corta solo contactos públicos (aula, bus, mercado, puente).
    La persona sigue en su hogar: no es lo mismo que vacunarla.
    """

    state = np.zeros(n, dtype=np.int8)
    sus = np.ones(n, dtype=np.float64)
    state[patient_zero] = I
    weights = weight

    if intervention == "cuarentena" and targets:
        banned = np.zeros(n, dtype=bool)
        banned[np.asarray(targets, dtype=np.int32)] = True
        weights = weight.copy()
        drop = banned[edge_u] | banned[edge_v]
        if layer is not None:
            drop = drop & (layer != 0)
        weights[drop] = 0.0
        return state, sus, weights

    if intervention == "vacuna":
        full = efficacy >= 0.999
        for node in targets:
            if full:
                state[node] = R
                sus[node] = 0.0
            else:
                sus[node] = 1.0 - efficacy
    return state, sus, weights
