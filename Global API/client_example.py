"""Tiny client to test the IDS Global API.

The /predict endpoint takes a multipart form with these fields:

    model_id   - required, one of the IDs from GET /models
    file       - optional, a CSV with the feature columns (batch path)
    features   - optional, a comma-separated string of values (single-row path)
    top_k      - optional, defaults to 5

You must send EITHER `file` OR `features`, not both.

Examples (PowerShell):

    # 1) List models
    python client_example.py --api http://127.0.0.1:8000 --list

    # 2) Predict on the first CSV row using a chosen model
    python client_example.py --api http://127.0.0.1:8000 \
        --model-id random_forest.joblib \
        --csv "..\\ASEADOS_SDN_IoT.csv"

    # 3) Predict using the public ngrok URL
    python client_example.py --api https://abcd-1234.ngrok-free.app \
        --model-id lstm_model.keras \
        --features-from-csv "..\\ASEADOS_SDN_IoT.csv"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import requests


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://127.0.0.1:8000", help="Base URL of the API")
    ap.add_argument("--model-id", help="Model filename, e.g. random_forest.joblib or lstm_model.keras")
    ap.add_argument("--csv", help="Path to a CSV file. The full file (up to 200 rows) is sent for batch prediction.")
    ap.add_argument(
        "--features-from-csv",
        help="Path to a CSV file. Only the first row is sent as a comma-separated string.",
    )
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--list", action="store_true", help="Just list available models and exit.")
    args = ap.parse_args()

    base = args.api.rstrip("/")

    if args.list:
        r = requests.get(f"{base}/models", timeout=60)
        r.raise_for_status()
        print(json.dumps(r.json(), indent=2))
        return 0

    if not args.model_id:
        print("--model-id is required (or pass --list).", file=sys.stderr)
        return 2

    if not args.csv and not args.features_from_csv:
        print("Provide --csv or --features-from-csv.", file=sys.stderr)
        return 2

    if args.csv and args.features_from_csv:
        print("Use only one of --csv / --features-from-csv.", file=sys.stderr)
        return 2

    data = {"model_id": args.model_id, "top_k": str(args.top_k)}
    files = None

    if args.csv:
        path = Path(args.csv)
        files = {"file": (path.name, path.open("rb"), "text/csv")}
    else:
        # Build a comma-separated single row from the first CSV record.
        import pandas as pd

        models_resp = requests.get(f"{base}/models", timeout=60)
        models_resp.raise_for_status()
        # We still need the column order; the UI bakes it in but the API
        # used to expose /features. For the client we read it from the CSV
        # header order itself: if the CSV came from training preprocessing
        # the columns will already match the model's expectations.
        path = Path(args.features_from_csv)
        df = pd.read_csv(path, nrows=1)
        values = df.iloc[0].astype(float).tolist()
        data["features"] = ",".join(repr(v) for v in values)

    try:
        r = requests.post(f"{base}/predict", data=data, files=files, timeout=180)
    finally:
        if files:
            files["file"][1].close()

    if not r.ok:
        print(f"HTTP {r.status_code}", file=sys.stderr)
    print(json.dumps(r.json(), indent=2))
    return 0 if r.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
