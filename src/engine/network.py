"""Red de contactos sintética de un escenario en Manta.

No es el censo persona por persona. Es una muestra del tamaño pedido, con la
misma lógica de mezcla que el reto describe: hogar, aula, bus y mercado.
La semilla fija hogares, roles y aristas.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

BARRIOS = ("Manta", "Tarqui", "Eloy Alfaro", "San Mateo", "San Lorenzo")
MERCADOS = ("Mercado Central", "Mercado Los Esteros", "Mercado Tarqui")
COLEGIOS = (
    "UE Manta",
    "UE Tarqui",
    "UE Eloy Alfaro",
    "UE San Mateo",
)

# Capas. La estrategia "puentes" solo mira bus, mercado y aristas entre aulas.
HOGAR = 0
AULA = 1
BUS = 2
MERCADO = 3
PUENTE = 4
PRIORITY_LAYERS = (BUS, MERCADO, PUENTE)

# Distribución nacional de tamaño de hogar, Censo 2022 (INEC), tamaños 1 a 6.
# 16,6% + 20,1% + 21,7% + 20,8% y el 20,9% de hogares de 5 o más repartido
# entre 5 y 6 para que el promedio quede cerca de 3,2.
HOUSEHOLD_SIZES = np.array([1, 2, 3, 4, 5, 6])
HOUSEHOLD_WEIGHTS = np.array([0.166, 0.201, 0.217, 0.208, 0.130, 0.078])
HOUSEHOLD_WEIGHTS = HOUSEHOLD_WEIGHTS / HOUSEHOLD_WEIGHTS.sum()

# Manabí, Censo 2022: 25,8% tiene 0–14 años. Los tratamos como estudiantes.
STUDENT_FRACTION = 0.258
BUS_FRACTION = 0.45
CLASS_SIZE = 20
BUS_SIZE = 16


@dataclass
class City:
    n: int
    seed: int
    barrio: np.ndarray
    role: np.ndarray  # 0 estudiante, 1 adulto, 2 comerciante
    household: np.ndarray
    school: np.ndarray  # -1 si no aplica
    classroom: np.ndarray
    bus: np.ndarray
    market: np.ndarray
    edge_u: np.ndarray
    edge_v: np.ndarray
    weight: np.ndarray
    layer: np.ndarray
    degree: np.ndarray
    bridge_score: np.ndarray
    summary: dict

    @property
    def people_preview_index(self) -> np.ndarray:
        return np.arange(self.n)


def build_city(n: int, seed: int) -> City:
    rng = np.random.default_rng(_mix(seed, 11))
    barrio = np.empty(n, dtype=np.int8)
    role = np.empty(n, dtype=np.int8)
    household = np.empty(n, dtype=np.int32)
    school = np.full(n, -1, dtype=np.int16)
    classroom = np.full(n, -1, dtype=np.int16)
    bus = np.full(n, -1, dtype=np.int16)
    market = np.empty(n, dtype=np.int8)

    # Hogares hasta completar n. El último se recorta.
    cursor = 0
    hid = 0
    household_barrio: list[int] = []
    while cursor < n:
        size = int(rng.choice(HOUSEHOLD_SIZES, p=HOUSEHOLD_WEIGHTS))
        size = min(size, n - cursor)
        b = int(rng.integers(0, len(BARRIOS)))
        household[cursor : cursor + size] = hid
        barrio[cursor : cursor + size] = b
        household_barrio.append(b)
        cursor += size
        hid += 1

    students = rng.random(n) < STUDENT_FRACTION
    role[:] = 1
    role[students] = 0

    _assign_schools(rng, n, barrio, role, school, classroom)
    _assign_buses(rng, n, role, bus)
    _assign_markets(rng, n, barrio, role, market)

    edges: dict[tuple[int, int], tuple[float, int]] = {}

    def add(a: int, b: int, weight: float, layer: int) -> None:
        if a == b:
            return
        i, j = (a, b) if a < b else (b, a)
        prev = edges.get((i, j))
        if prev is None or weight > prev[0]:
            edges[(i, j)] = (weight, layer)

    for h in range(hid):
        members = np.flatnonzero(household == h)
        _clique(members, 1.0, HOGAR, add)

    # El aula no es un clique: cada estudiante ve a pocos compañeros.
    # Si el aula fuera completa, el grado se concentra ahí y las vacunas
    # se gastan dentro de un solo salón en vez de cortar caminos entre grupos.
    classrooms = [c for c in np.unique(classroom) if c >= 0]
    for c in classrooms:
        members = np.flatnonzero(classroom == c)
        _sparse(rng, members, 4, 0.4, AULA, add)

    _add_class_bridges(rng, classroom, school, add)

    buses = [b for b in np.unique(bus) if b >= 0]
    for b in buses:
        members = np.flatnonzero(bus == b)
        _sparse(rng, members, 3, 0.28, BUS, add)

    for m in range(len(MERCADOS)):
        members = np.flatnonzero(market == m)
        vendors = members[role[members] == 2]
        shoppers = members[role[members] != 2]
        for person in shoppers:
            _link_sample(rng, int(person), shoppers, 2, 0.12, MERCADO, add)
        # El puesto del mercado es el hub: muchas personas pasan por pocas.
        for vendor in vendors:
            _link_sample(rng, int(vendor), shoppers, 22, 0.48, MERCADO, add)

    keys = sorted(edges)
    edge_u = np.fromiter((i for i, _ in keys), dtype=np.int32, count=len(keys))
    edge_v = np.fromiter((j for _, j in keys), dtype=np.int32, count=len(keys))
    weight = np.fromiter((edges[k][0] for k in keys), dtype=np.float64, count=len(keys))
    layer = np.fromiter((edges[k][1] for k in keys), dtype=np.int8, count=len(keys))

    degree = np.zeros(n, dtype=np.float64)
    bridge = np.zeros(n, dtype=np.float64)
    np.add.at(degree, edge_u, weight)
    np.add.at(degree, edge_v, weight)
    priority = np.isin(layer, PRIORITY_LAYERS)
    np.add.at(bridge, edge_u[priority], weight[priority])
    np.add.at(bridge, edge_v[priority], weight[priority])

    summary = {
        "poblacion": int(n),
        "semilla_ciudad": int(seed),
        "aristas": int(len(keys)),
        "hogares": int(hid),
        "estudiantes": int(np.sum(role == 0)),
        "adultos": int(np.sum(role == 1)),
        "comerciantes": int(np.sum(role == 2)),
        "aulas": int(len(classrooms)),
        "buses": int(len(buses)),
        "mercados": len(MERCADOS),
        "grado_medio": round(float(degree.mean()), 2),
        "barrios": {BARRIOS[i]: int(np.sum(barrio == i)) for i in range(len(BARRIOS))},
        "nota": (
            "Muestra sintética de un escenario en Manta, no el cantón completo. "
            "INEC Censo 2022: Manta 271.145 habitantes; hogar promedio nacional 3,2 personas; "
            "Manabí 25,8% de 0 a 14 años."
        ),
    }
    return City(
        n=n,
        seed=seed,
        barrio=barrio,
        role=role,
        household=household,
        school=school,
        classroom=classroom,
        bus=bus,
        market=market,
        edge_u=edge_u,
        edge_v=edge_v,
        weight=weight,
        layer=layer,
        degree=degree,
        bridge_score=bridge,
        summary=summary,
    )


def describe_person(city: City, index: int) -> dict:
    roles = ("estudiante", "adulto", "comerciante")
    school_id = int(city.school[index])
    market_id = int(city.market[index])
    bus_id = int(city.bus[index])
    return {
        "id": int(index),
        "barrio": BARRIOS[int(city.barrio[index])],
        "rol": roles[int(city.role[index])],
        "hogar": int(city.household[index]),
        "colegio": COLEGIOS[school_id] if school_id >= 0 else None,
        "bus": f"Ruta {bus_id}" if bus_id >= 0 else None,
        "mercado": MERCADOS[market_id],
        "grado": round(float(city.degree[index]), 2),
        "puentes": round(float(city.bridge_score[index]), 2),
    }


def pool_for_locus(city: City, locus: str) -> np.ndarray:
    if locus == "colegio":
        pool = np.flatnonzero(city.role == 0)
    elif locus == "bus":
        pool = np.flatnonzero(city.bus >= 0)
    elif locus == "mercado":
        pool = np.flatnonzero(city.role == 2)
    else:
        # hogar y cualquiera: cualquier persona. El hogar ya está en las aristas.
        pool = np.arange(city.n)
    if len(pool) == 0:
        return np.arange(city.n)
    return pool


def _assign_schools(rng, n, barrio, role, school, classroom) -> None:
    students = np.flatnonzero(role == 0)
    # Aula global incremental. Cada colegio llena aulas de CLASS_SIZE.
    next_class = 0
    buckets: dict[int, list[int]] = {s: [] for s in range(len(COLEGIOS))}
    for sid in students:
        preferred = int(barrio[sid]) % len(COLEGIOS)
        chosen = preferred if rng.random() < 0.75 else int(rng.integers(0, len(COLEGIOS)))
        buckets[chosen].append(int(sid))
    for sid, members in buckets.items():
        rng.shuffle(members)
        for offset, person in enumerate(members):
            school[person] = sid
            if offset % CLASS_SIZE == 0:
                class_id = next_class
                next_class += 1
            classroom[person] = class_id


def _assign_buses(rng, n, role, bus) -> None:
    riders = np.flatnonzero(role != 0)
    rng.shuffle(riders)
    take = riders[: int(len(riders) * BUS_FRACTION)]
    if len(take) == 0:
        return
    n_routes = max(1, int(np.ceil(len(take) / BUS_SIZE)))
    for i, person in enumerate(take):
        bus[person] = i % n_routes


def _assign_markets(rng, n, barrio, role, market) -> None:
    # 3 comerciantes por mercado, elegidos entre adultos. El resto compra.
    adults = np.flatnonzero(role == 1)
    rng.shuffle(adults)
    vendors_needed = 3 * len(MERCADOS)
    vendor_ids = adults[: min(vendors_needed, len(adults))]
    for i, person in enumerate(vendor_ids):
        role[person] = 2
        market[person] = i % len(MERCADOS)
    # Preferencia de mercado según el barrio, con fuga al azar.
    preferred = {
        0: 0,  # Manta → Central
        1: 1,  # Tarqui → Los Esteros (barrio colindante en el escenario)
        2: 0,  # Eloy Alfaro → Central
        3: 2,  # San Mateo → Tarqui
        4: 2,  # San Lorenzo → Tarqui
    }
    for person in range(n):
        if role[person] == 2:
            continue
        fav = preferred[int(barrio[person])]
        market[person] = fav if rng.random() < 0.7 else int(rng.integers(0, len(MERCADOS)))


def _add_class_bridges(rng, classroom, school, add) -> None:
    """Dos estudiantes de cada aula quedan ligados al aula vecina del mismo colegio."""

    by_school: dict[int, list[int]] = {}
    for class_id in np.unique(classroom):
        if class_id < 0:
            continue
        members = np.flatnonzero(classroom == class_id)
        if len(members) == 0:
            continue
        sid = int(school[members[0]])
        by_school.setdefault(sid, []).append(int(class_id))
    for classes in by_school.values():
        if len(classes) < 2:
            continue
        for a, b in zip(classes, classes[1:] + classes[:1]):
            left = np.flatnonzero(classroom == a)
            right = np.flatnonzero(classroom == b)
            if len(left) == 0 or len(right) == 0:
                continue
            src = int(rng.choice(left))
            dst = int(rng.choice(right))
            add(src, dst, 0.45, PUENTE)


def _clique(members: np.ndarray, weight: float, layer: int, add) -> None:
    ids = [int(x) for x in members]
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            add(ids[i], ids[j], weight, layer)


def _sparse(rng, members: np.ndarray, neighbors: int, weight: float, layer: int, add) -> None:
    ids = [int(x) for x in members]
    if len(ids) < 2:
        return
    for person in ids:
        others = [o for o in ids if o != person]
        take = min(neighbors, len(others))
        picked = rng.choice(np.array(others), size=take, replace=False)
        for other in np.atleast_1d(picked):
            add(person, int(other), weight, layer)


def _link_sample(rng, person: int, pool: np.ndarray, k: int, weight: float, layer: int, add) -> None:
    if len(pool) == 0:
        return
    choices = pool[pool != person]
    if len(choices) == 0:
        return
    take = min(k, len(choices))
    picked = rng.choice(choices, size=take, replace=False)
    for other in np.atleast_1d(picked):
        add(person, int(other), weight, layer)


def _mix(seed: int, salt: int) -> int:
    ss = np.random.SeedSequence([int(seed) & 0x7FFFFFFF, int(salt)])
    return int(ss.generate_state(1, dtype=np.uint32)[0])
