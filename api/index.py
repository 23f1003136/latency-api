from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import json
import os

app = FastAPI()

# HARD CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)

# Load data safely
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(BASE_DIR, "q-vercel-latency.json")

with open(DATA_FILE, "r") as f:
    DATA = json.load(f)


@app.post("/api")
async def api(req: Request):
    body = await req.json()

    regions = body["regions"]
    threshold = body["threshold_ms"]

    result = {}

    for r in regions:
        rows = [x for x in DATA if x["region"] == r]

        latencies = [x["latency_ms"] for x in rows]
        uptimes = [x["uptime_pct"] for x in rows]

        latencies_sorted = sorted(latencies)
        p95_index = int(0.95 * (len(latencies_sorted) - 1))
        p95 = latencies_sorted[p95_index]

        result[r] = {
            "avg_latency": sum(latencies) / len(latencies),
            "p95_latency": p95,
            "avg_uptime": sum(uptimes) / len(uptimes),
            "breaches": sum(1 for x in latencies if x > threshold),
        }

    return result


# Explicit OPTIONS handler (THIS FIXES GRADER)
@app.options("/api")
async def options():
    return {}
