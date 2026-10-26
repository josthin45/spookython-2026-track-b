"""Junta las corridas que escribió el mapa y guarda el resumen del trabajo."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone

import numpy as np

POLICIES = ("estrategia", "azar", "nada")


def handler(event, _context=None):
    import boto3

    bucket = event["bucket"]
    prefix = event["resultsPrefix"]
    job_id = event["jobId"]
    runs = _load_runs(boto3.client("s3"), bucket, prefix)
    if not runs:
        raise RuntimeError(f"El mapa no dejó corridas en s3://{bucket}/{prefix}")

    summary = _summarize(runs)
    summary["job_id"] = job_id
    summary["estado"] = "SUCCEEDED"
    summary["params"] = event.get("params")
    key = f"jobs/{job_id}/resultado.json"
    boto3.client("s3").put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(summary).encode(),
        ContentType="application/json",
    )
    table_name = os.environ.get("JOBS_TABLE")
    if table_name:
        ttl = int((datetime.now(timezone.utc) + timedelta(days=14)).timestamp())
        boto3.resource("dynamodb").Table(table_name).update_item(
            Key={"job_id": job_id},
            UpdateExpression="SET #s = :s, result_key = :k, #t = :t",
            ExpressionAttributeNames={"#s": "status", "#t": "ttl"},
            ExpressionAttributeValues={":s": "SUCCEEDED", ":k": key, ":t": ttl},
        )
    return {"job_id": job_id, "corridas": len(runs), "resultado": key}


def _summarize(runs: list[dict]) -> dict:
    saved_none = []
    saved_random = []
    strategies = {}
    for policy in POLICIES:
        incidence = np.array([r["incidencias"][policy] for r in runs], dtype=np.float64)
        peak = np.array([r["picos"][policy] for r in runs], dtype=np.float64)
        zombies = np.vstack([np.asarray(r["zombies"][policy], dtype=np.float64) for r in runs])
        strategies[policy] = {
            "incidencia_media": round(float(incidence.mean()), 4),
            "incidencia_p05": round(float(np.percentile(incidence, 5)), 4),
            "incidencia_p95": round(float(np.percentile(incidence, 95)), 4),
            "pico_medio": round(float(peak.mean()), 4),
            "zombies_media": [round(float(v), 2) for v in zombies.mean(axis=0)],
        }
    for run in runs:
        saved_none.append(run["incidencias"]["nada"] - run["incidencias"]["estrategia"])
        saved_random.append(run["incidencias"]["azar"] - run["incidencias"]["estrategia"])
    saved_none_arr = np.asarray(saved_none, dtype=np.float64)
    saved_random_arr = np.asarray(saved_random, dtype=np.float64)
    return {
        "estrategias": strategies,
        "comparacion": {
            "salvados_vs_nada_media": round(float(saved_none_arr.mean()), 4),
            "salvados_vs_nada_p05": round(float(np.percentile(saved_none_arr, 5)), 4),
            "salvados_vs_nada_p95": round(float(np.percentile(saved_none_arr, 95)), 4),
            "salvados_vs_azar_media": round(float(saved_random_arr.mean()), 4),
            "corridas": len(runs),
        },
    }


def _load_runs(s3, bucket: str, prefix: str) -> list[dict]:
    found: list[dict] = []
    token = None
    while True:
        kwargs = {"Bucket": bucket, "Prefix": prefix}
        if token:
            kwargs["ContinuationToken"] = token
        page = s3.list_objects_v2(**kwargs)
        for obj in page.get("Contents", []):
            raw = s3.get_object(Bucket=bucket, Key=obj["Key"])["Body"].read()
            _collect(json.loads(raw), found)
        if not page.get("IsTruncated"):
            break
        token = page.get("NextContinuationToken")
    return found


def _collect(node, found: list[dict]) -> None:
    if isinstance(node, dict):
        if "incidencias" in node and "zombies" in node:
            found.append(node)
            return
        for value in node.values():
            _collect(value, found)
    elif isinstance(node, list):
        for value in node:
            _collect(value, found)
