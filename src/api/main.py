"""API local. Misma forma que el orquestador de Lambda: valida y llama al motor."""

from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from engine.compare import run_scenario
from engine.config import Params, parse_params

app = FastAPI(
    title="Comité de Contención — Manta",
    version="0.1.0",
    summary="Simulador SEIR de la plaga sobre la red de contactos de Manta.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"ok": True, "servicio": "motor-local"}


@app.get("/defaults")
def defaults() -> dict:
    return Params().to_dict()


@app.post("/simulate")
def simulate(body: dict = Body(...)) -> dict:
    try:
        params = parse_params(body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return run_scenario(params)
