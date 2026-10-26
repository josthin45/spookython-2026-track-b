"""Elección de a quién vacunar o aislar con presupuesto K.

Regla del jurado: no se vacuna a quien ya está infectado o inmune.
Al inicio del día 0 el único no susceptible es el paciente cero.
"""

from __future__ import annotations

import numpy as np

from engine.network import City


def rank_nodes(
    city: City,
    criterio: str,
    betweenness: np.ndarray | None = None,
    patient_zero: int | None = None,
) -> np.ndarray:
    """Orden de prioridad, el más importante primero. Empates por id ascendente."""

    ids = np.arange(city.n)
    if criterio == "betweenness":
        if betweenness is None:
            raise ValueError("Falta la centralidad de intermediación.")
        score = betweenness
    elif criterio == "degree":
        score = city.degree
    elif criterio == "puentes":
        score = city.bridge_score
    elif criterio == "anillo":
        # Primero el hogar y los contactos directos del caso. Después, el grado
        # de la ciudad (comerciantes y otros hubs). El anillo usa el dato que
        # el comité sí tiene: dónde apareció el primer zombie.
        score = city.degree.astype(np.float64, copy=True)
        if patient_zero is not None:
            for node, layer in _neighbors(city, patient_zero):
                score[node] += 500.0 if layer == 0 else 80.0
    else:
        raise ValueError(f"Criterio desconocido: {criterio}")
    # lexsort: la última clave es la primaria. Id ascendente desempata.
    return np.lexsort((ids, -score))


def pick_targets(
    city: City,
    k: int,
    patient_zero: int,
    criterio: str,
    rng: np.random.Generator | None,
    betweenness: np.ndarray | None = None,
) -> list[int]:
    if k <= 0:
        return []
    if criterio == "random":
        if rng is None:
            raise ValueError("La línea base aleatoria necesita un generador.")
        candidates = np.array([i for i in range(city.n) if i != patient_zero], dtype=np.int32)
        rng.shuffle(candidates)
        return [int(x) for x in candidates[:k]]

    order = rank_nodes(city, criterio, betweenness, patient_zero)
    chosen: list[int] = []
    for node in order:
        node = int(node)
        if node == patient_zero:
            continue
        chosen.append(node)
        if len(chosen) >= k:
            break
    return chosen


def _neighbors(city: City, node: int):
    left = city.edge_u == node
    right = city.edge_v == node
    if left.any():
        for other, layer in zip(city.edge_v[left].tolist(), city.layer[left].tolist()):
            yield int(other), int(layer)
    if right.any():
        for other, layer in zip(city.edge_u[right].tolist(), city.layer[right].tolist()):
            yield int(other), int(layer)


def compute_betweenness(city: City) -> np.ndarray:
    """Intermediación con distancia = 1/peso (el contacto cercano es un camino corto)."""

    import networkx as nx

    graph = nx.Graph()
    graph.add_nodes_from(range(city.n))
    distance = 1.0 / np.maximum(city.weight, 1e-6)
    graph.add_weighted_edges_from(
        zip(
            city.edge_u.tolist(),
            city.edge_v.tolist(),
            distance.tolist(),
        ),
        weight="distance",
    )
    raw = nx.betweenness_centrality(graph, weight="distance", normalized=True)
    out = np.zeros(city.n, dtype=np.float64)
    for node, value in raw.items():
        out[int(node)] = value
    return out
