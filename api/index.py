import json
from pathlib import Path

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

# Allow POST requests from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Locate the telemetry JSON file in the repository root.
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = BASE_DIR / "q-vercel-latency.json"

try:
    with DATA_FILE.open("r", encoding="utf-8") as f:
        telemetry = json.load(f)
except (FileNotFoundError, json.JSONDecodeError) as exc:
    raise RuntimeError(
        f"Unable to load telemetry data from {DATA_FILE}: {exc}"
    ) from exc


class AnalyticsRequest(BaseModel):
    regions: list[str]
    threshold_ms: float


def percentile_95(values):
    """Calculate the 95th percentile using NumPy's linear interpolation."""
    if len(values) == 0:
        return None

    return float(np.percentile(values, 95))


@app.post("/api/latency")
def analytics(request: AnalyticsRequest):
    result = {}

    for region in request.regions:
        records = [record for record in telemetry if record.get("region") == region]

        if not records:
            raise HTTPException(
                status_code=404,
                detail=f"No telemetry data found for region: {region}",
            )

        latencies = np.array(
            [record["latency_ms"] for record in records],
            dtype=float,
        )
        uptimes = np.array(
            [record["uptime_pct"] for record in records],
            dtype=float,
        )

        result[region] = {
            "avg_latency": float(np.mean(latencies)),
            "p95_latency": percentile_95(latencies),
            "avg_uptime": float(np.mean(uptimes)),
            "breaches": int(np.sum(latencies > request.threshold_ms)),
        }

    return result
