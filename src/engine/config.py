"""Parámetros del escenario y validación.

El motor no conoce AWS. La API y las Lambdas solo traducen JSON a `Params`.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

LOCUS = ("cualquiera", "hogar", "colegio", "bus", "mercado")
CRITERIOS = ("anillo", "degree", "puentes", "betweenness")
INTERVENCIONES = ("vacuna", "cuarentena")

POP_MIN, POP_MAX = 80, 1200
DAYS_MIN, DAYS_MAX = 7, 90
RUNS_MIN, RUNS_MAX = 1, 30


@dataclass
class Params:
    """Escenario reproducible.

    `seed` fija la ciudad, el paciente cero de cada corrida y la suerte de
    cada contacto. Cambiar solo la estrategia no cambia esa suerte: las tres
    políticas se comparan con números aleatorios emparejados.
    """

    seed: int = 42
    population: int = 480
    days: int = 40
    beta: float = 0.16
    sigma: float = 0.5
    gamma: float = 0.25
    vaccines: int = 40
    vaccine_efficacy: float = 1.0
    patient_zero: str = "aleatorio"
    locus: str = "cualquiera"
    n_runs: int = 8
    criterio: str = "anillo"
    intervention: str = "vacuna"

    def to_dict(self) -> dict:
        return asdict(self)


def parse_params(raw: dict | None, max_runs: int = RUNS_MAX) -> Params:
    """Acepta el subconjunto de campos conocido. El resto se ignora."""

    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise ValueError("El cuerpo debe ser un objeto JSON.")

    base = asdict(Params())
    data = dict(base)
    for key, value in raw.items():
        if key in data and value is not None:
            data[key] = value

    data["seed"] = _as_int(data["seed"], "semilla")
    if data["seed"] < 0 or data["seed"] > 2_147_483_647:
        raise ValueError("La semilla debe ser un entero entre 0 y 2147483647.")

    data["population"] = _as_int(data["population"], "población")
    if not POP_MIN <= data["population"] <= POP_MAX:
        raise ValueError(f"La población debe estar entre {POP_MIN} y {POP_MAX}.")

    data["days"] = _as_int(data["days"], "días")
    if not DAYS_MIN <= data["days"] <= DAYS_MAX:
        raise ValueError(f"Los días deben estar entre {DAYS_MIN} y {DAYS_MAX}.")

    data["n_runs"] = _as_int(data["n_runs"], "corridas")
    if not RUNS_MIN <= data["n_runs"] <= max_runs:
        raise ValueError(
            f"Las corridas deben estar entre {RUNS_MIN} y {max_runs} "
            "(el tope protege el tiempo de la demo y la cuenta AWS)."
        )

    data["vaccines"] = _as_int(data["vaccines"], "vacunas")
    if data["vaccines"] < 0 or data["vaccines"] > data["population"]:
        raise ValueError("Las vacunas deben estar entre 0 y la población del escenario.")

    data["beta"] = _as_unit("beta (contagio)", data["beta"], low=0.0, high=1.0)
    data["sigma"] = _as_unit("sigma (incubación)", data["sigma"], low=0.01, high=1.0)
    data["gamma"] = _as_unit("gamma (recuperación)", data["gamma"], low=0.01, high=1.0)
    data["vaccine_efficacy"] = _as_unit(
        "eficacia", data["vaccine_efficacy"], low=0.0, high=1.0
    )

    locus = str(data["locus"]).strip().lower()
    if locus not in LOCUS:
        raise ValueError(f"Lugar del brote inválido. Usa uno de: {', '.join(LOCUS)}.")
    data["locus"] = locus

    criterio = str(data["criterio"]).strip().lower()
    if criterio not in CRITERIOS:
        raise ValueError(f"Criterio inválido. Usa uno de: {', '.join(CRITERIOS)}.")
    data["criterio"] = criterio

    intervention = str(data["intervention"]).strip().lower()
    if intervention not in INTERVENCIONES:
        raise ValueError(
            f"Intervención inválida. Usa una de: {', '.join(INTERVENCIONES)}."
        )
    data["intervention"] = intervention

    pz = data["patient_zero"]
    if isinstance(pz, bool) or pz is None:
        raise ValueError("El paciente cero debe ser 'aleatorio' o un id entero.")
    if isinstance(pz, (int, float)) and not isinstance(pz, bool):
        pz_int = int(pz)
        if pz_int < 0:
            raise ValueError("El id del paciente cero no puede ser negativo.")
        data["patient_zero"] = str(pz_int)
    else:
        text = str(pz).strip().lower()
        if text == "aleatorio":
            data["patient_zero"] = "aleatorio"
        elif text.isdigit():
            data["patient_zero"] = str(int(text))
        else:
            raise ValueError("El paciente cero debe ser 'aleatorio' o un id entero.")

    return Params(**data)


def _as_int(value: object, label: str) -> int:
    if isinstance(value, bool) or isinstance(value, float) and not float(value).is_integer():
        raise ValueError(f"'{label}' debe ser un entero.")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"'{label}' debe ser un entero.") from exc


def _as_unit(label: str, value: object, low: float, high: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"'{label}' debe ser un número.") from exc
    if number != number or number in (float("inf"), float("-inf")):
        raise ValueError(f"'{label}' debe ser un número finito.")
    if number < low or number > high:
        raise ValueError(f"'{label}' debe estar entre {low} y {high}.")
    return number
