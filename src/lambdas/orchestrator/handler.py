"""Orquestador. Valida el escenario, fija la semilla y responde o lanza el mapa.

La ruta de la demo es síncrona: el jurado cambia parámetros y ve el resultado
en la misma petición. Si las corridas superan SYNC_MAX_RUNS y existe una
state machine, el trabajo queda en DynamoDB y Step Functions lo reparte.
"""

from __future__ import annotations

import json
import os
import traceback
import uuid
from datetime import datetime, timedelta, timezone

from engine.compare import run_scenario
from engine.config import RUNS_MAX, Params, parse_params

SYNC_MAX = int(os.environ.get("SYNC_MAX_RUNS", str(RUNS_MAX)))
BATCH_MAX = int(os.environ.get("BATCH_MAX_RUNS", "400"))


def handler(event, _context=None):
    method = _method(event)
    path = _path(event)
    if method == "OPTIONS":
        return _response(204, {})
    try:
        if method == "GET" and path.rstrip("/").endswith("/health"):
            return _response(200, {"ok": True, "servicio": "orquestador"})
        if method == "GET" and path.rstrip("/").endswith("/defaults"):
            return _response(200, Params().to_dict())
        if method == "POST" and path.rstrip("/").endswith("/simulate"):
            return _simulate(_body(event))
        if method == "GET" and "/jobs/" in path:
            return _get_job(path.rstrip("/").split("/")[-1])
        return _response(404, {"error": "Ruta no encontrada."})
    except ValueError as exc:
        return _response(400, {"error": str(exc)})
    except Exception:
        print(traceback.format_exc())
        return _response(500, {"error": "Falló la simulación. Revisa los parámetros."})


def _simulate(body: dict):
    params = parse_params(body, max_runs=BATCH_MAX)
    job_id = str(uuid.uuid4())
    if params.n_runs <= SYNC_MAX or not os.environ.get("STATE_MACHINE_ARN"):
        if params.n_runs > SYNC_MAX and not os.environ.get("STATE_MACHINE_ARN"):
            raise ValueError(
                f"Este despliegue simula hasta {SYNC_MAX} corridas por petición. "
                "Para un Monte Carlo más grande configura la state machine."
            )
        result = run_scenario(params)
        result["job_id"] = job_id
        result["estado"] = "SUCCEEDED"
        _persist(job_id, "SUCCEEDED", params, result)
        return _response(200, result)

    _start_map(job_id, params)
    queued = {"job_id": job_id, "estado": "RUNNING", "corridas": params.n_runs}
    return _response(202, queued)


def _start_map(job_id: str, params: Params) -> None:
    import boto3

    bucket = os.environ["RESULTS_BUCKET"]
    key = f"jobs/{job_id}/runs.jsonl"
    lines = [
        json.dumps({"run": index, "params": params.to_dict()}, separators=(",", ":"))
        for index in range(params.n_runs)
    ]
    boto3.client("s3").put_object(
        Bucket=bucket,
        Key=key,
        Body=("\n".join(lines) + "\n").encode(),
        ContentType="application/x-ndjson",
    )
    boto3.client("stepfunctions").start_execution(
        stateMachineArn=os.environ["STATE_MACHINE_ARN"],
        name=job_id,
        input=json.dumps(
            {
                "bucket": bucket,
                "runsKey": key,
                "resultsPrefix": f"jobs/{job_id}/map/",
                "jobId": job_id,
                "params": params.to_dict(),
            }
        ),
    )
    _persist(job_id, "RUNNING", params, None)


def _get_job(job_id: str):
    table_name = os.environ.get("JOBS_TABLE")
    if not table_name:
        return _response(404, {"error": "No hay tabla de trabajos en este entorno.", "job_id": job_id})
    import boto3

    item = boto3.resource("dynamodb").Table(table_name).get_item(Key={"job_id": job_id}).get("Item")
    if not item:
        return _response(404, {"error": "Trabajo no encontrado.", "job_id": job_id})
    if item.get("status") == "SUCCEEDED" and item.get("result_key"):
        body = boto3.client("s3").get_object(
            Bucket=os.environ["RESULTS_BUCKET"], Key=item["result_key"]
        )["Body"].read()
        payload = json.loads(body)
        payload["estado"] = "SUCCEEDED"
        return _response(200, payload)
    return _response(200, {"job_id": job_id, "estado": item.get("status", "RUNNING")})


def _persist(job_id: str, status: str, params: Params, result: dict | None) -> None:
    table_name = os.environ.get("JOBS_TABLE")
    bucket = os.environ.get("RESULTS_BUCKET")
    if not table_name or not bucket:
        return
    import boto3

    result_key = None
    if result is not None:
        result_key = f"jobs/{job_id}/resultado.json"
        boto3.client("s3").put_object(
            Bucket=bucket,
            Key=result_key,
            Body=json.dumps(result).encode(),
            ContentType="application/json",
        )
    ttl = int((datetime.now(timezone.utc) + timedelta(days=14)).timestamp())
    boto3.resource("dynamodb").Table(table_name).put_item(
        Item={
            "job_id": job_id,
            "status": status,
            "seed": params.seed,
            "result_key": result_key or "",
            "ttl": ttl,
        }
    )


def _method(event: dict) -> str:
    return (
        event.get("httpMethod")
        or event.get("requestContext", {}).get("http", {}).get("method")
        or ""
    ).upper()


def _path(event: dict) -> str:
    return event.get("path") or event.get("rawPath") or ""


def _body(event: dict) -> dict:
    raw = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        import base64

        raw = base64.b64decode(raw).decode()
    if isinstance(raw, dict):
        return raw
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("El cuerpo debe ser un objeto JSON.")
    return parsed


def _response(status: int, payload: dict):
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": os.environ.get("CORS_ORIGIN", "*"),
            "Access-Control-Allow-Headers": "content-type",
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
        },
        "body": json.dumps(payload),
    }
