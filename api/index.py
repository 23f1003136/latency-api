
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import json
import math
import os

app = FastAPI()

# Enable CORS for POST and OPTIONS requests from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)

# Load telemetry data from the repository root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(BASE_DIR, "q-vercel-latency.json")

try:
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        DATA = json.load(f)

    if not isinstance(DATA, list):
        raise ValueError("Telemetry data must be a JSON list")

except (FileNotFoundError, json.JSONDecodeError, ValueError) as exc:
    raise RuntimeError(f"Unable to load telemetry data: {exc}") from exc


def percentile_95(values):
    """Calculate the 95th percentile using linear interpolation."""
    if not values:
        return None

    values = sorted(values)
    position = 0.95 * (len(values) - 1)

    lower = math.floor(position)
    upper = math.ceil(position)

    if lower == upper:
        return values[lower]

    return values[lower] + (
        values[upper] - values[lower]
    ) * (position - lower)


@app.post("/api/latency")
async def api(req: Request):
    try:
        body = await req.json()
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON body"
        )

    if not isinstance(body, dict):
        raise HTTPException(
            status_code=400,
            detail="Request body must be a JSON object"
        )

    regions = body.get("regions")
    threshold = body.get("threshold_ms")

    if not isinstance(regions, list):
        raise HTTPException(
            status_code=400,
            detail="'regions' must be a list"
        )

    if (
        isinstance(threshold, bool)
        or not isinstance(threshold, (int, float))
        or not math.isfinite(threshold)
    ):
        raise HTTPException(
            status_code=400,
            detail="'threshold_ms' must be a finite number"
        )

    result = {}

    for region in regions:
        if not isinstance(region, str):
            raise HTTPException(
                status_code=400,
                detail="Each region must be a string"
            )

        rows = [
            row for row in DATA
            if row.get("region") == region
        ]

        if not rows:
            raise HTTPException(
                status_code=404,
                detail=f"No telemetry data found for region: {region}"
            )

        latencies = [row["latency_ms"] for row in rows]
        uptimes = [row["uptime_pct"] for row in rows]

        result[region] = {
            "avg_latency": sum(latencies) / len(latencies),
            "p95_latency": percentile_95(latencies),
            "avg_uptime": sum(uptimes) / len(uptimes),
            "breaches": sum(
                1 for latency in latencies
                if latency > threshold
            ),
        }

    return result


@app.options("/api/latency")
async def options():
    return {}
