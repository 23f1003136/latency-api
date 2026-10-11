import json
from pathlib import Path

import numpy as np
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

# Allow browser/dashboard requests from any website
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load the telemetry file once when the function starts
DATA_FILE = Path(__file__).with_name("q-vercel-latency.json")
with DATA_FILE.open() as f:
    telemetry = json.load(f)

class AnalyticsRequest(BaseModel):
    regions: list[str]
    threshold_ms: float

@app.post("/")
def analytics(request: AnalyticsRequest):
    result = {}

    for region in request.regions:
        records = [
            record
            for record in telemetry
            if record.get("region") == region
        ]

        latencies = np.array(
            [record["latency_ms"] for record in records],
            dtype=float
        )
        uptimes = np.array(
            [record["uptime_percent"] for record in records],
            dtype=float
        )

        result[region] = {
            "avg_latency": float(np.mean(latencies)),
            "p95_latency": float(np.percentile(latencies, 95)),
            "avg_uptime": float(np.mean(uptimes)),
            "breaches": int(np.sum(latencies > request.threshold_ms)),
        }

    return result
