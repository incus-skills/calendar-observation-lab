#!/usr/bin/env python3
"""Capture a reproducible geocentric apparent Sun/Moon reference from JPL Horizons.

Uses only the Python standard library. No API key or third-party package is
required.

Baseline:
  epoch:       2026-11-03 12:00:00 (nominal UTC; sent to Horizons as UT)
  centre:      Earth geocentre (500@399)
  quantities:  31 (observer-centred ecliptic longitude and latitude)
  corrections: Horizons observer-table apparent-place corrections
  frame:       IAU 1976/1980 ecliptic of date (Horizons quantity 31)

Important time note:
Horizons observer tables accept TIME_TYPE=UT, not UTC. This script sends the
same nominal civil timestamp as UT. UTC and UT1 differ by DUT1 (currently less
than one second); for this planetary-longitude baseline the resulting angular
difference is negligible at the precision we are initially recording. The
exact request parameters and complete raw response are saved so the time
convention can be refined without losing provenance.

The script deliberately does not calculate a lunar phase from rounded output.
It captures source observations first; phase derivation belongs in the
subsequent comparison/fixture step.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API_URL = "https://ssd.jpl.nasa.gov/api/horizons.api"
DEFAULT_EPOCH = "2026-11-03 12:00:00"
TARGETS = {
    "sun": "10",
    "moon": "301",
}


def capture(target_name: str, target_id: str, epoch: str, timeout: float) -> tuple[dict, str]:
    params = {
        "format": "text",
        "COMMAND": target_id,
        "OBJ_DATA": "NO",
        "MAKE_EPHEM": "YES",
        "EPHEM_TYPE": "OBSERVER",
        "CENTER": "500@399",
        "TIME_TYPE": "UT",
        "TLIST_TYPE": "CAL",
        "TLIST": f"'{epoch}'",
        "QUANTITIES": "31",
        "ANG_FORMAT": "DEG",
        "CSV_FORMAT": "YES",
        "TIME_DIGITS": "SECONDS",
    }
    url = f"{API_URL}?{urlencode(params)}"
    request = Request(
        url,
        headers={"User-Agent": "calendar-observation-lab/0.1 (reference capture)"},
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
            status = response.status
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Horizons returned HTTP {exc.code} for {target_name}:\n{detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Could not reach JPL Horizons for {target_name}: {exc}") from exc

    metadata = {
        "target": target_name,
        "target_id": target_id,
        "endpoint": API_URL,
        "request_url": url,
        "parameters": params,
        "http_status": status,
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "epoch_interpretation": "nominal UTC timestamp supplied as UT to Horizons",
        "observer_origin": "Earth geocentre (500@399)",
        "quantity_31_definition": (
            "Observer-centered IAU76/80 ecliptic-of-date longitude and latitude; "
            "apparent position with light-time, gravitational deflection, and "
            "stellar aberration corrections."
        ),
    }
    return metadata, body


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--epoch", default=DEFAULT_EPOCH, help="Horizons UT calendar time (default: %(default)s)")
    parser.add_argument("--output-dir", type=Path, default=Path("reference-data/horizons"))
    parser.add_argument("--timeout", type=float, default=45.0)
    args = parser.parse_args()

    # Validate the expected calendar form before making network requests.
    try:
        datetime.strptime(args.epoch, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        parser.error("--epoch must use YYYY-MM-DD HH:MM:SS")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "baseline_id": "ORB-1",
        "epoch": args.epoch,
        "epoch_scale_sent_to_horizons": "UT",
        "requested_epoch_label": "nominal UTC",
        "observer_origin": "Earth geocentre (500@399)",
        "targets": {},
    }

    for name, target_id in TARGETS.items():
        print(f"Requesting {name} ({target_id}) from JPL Horizons...", flush=True)
        metadata, body = capture(name, target_id, args.epoch, args.timeout)
        stem = f"{args.epoch[:10]}_{name}".replace("-", "")
        raw_path = args.output_dir / f"{stem}.txt"
        metadata_path = args.output_dir / f"{stem}.request.json"
        raw_path.write_text(body, encoding="utf-8")
        metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
        manifest["targets"][name] = {
            "raw_response": str(raw_path),
            "request_metadata": str(metadata_path),
        }
        print(f"Saved response: {raw_path}")
        print(f"Saved request:  {metadata_path}")
        print(f"----- BEGIN {name.upper()} HORIZONS RESPONSE -----")
        print(body.rstrip())
        print(f"----- END {name.upper()} HORIZONS RESPONSE -----")
        time.sleep(1.0)  # Be courteous to the public API.

    manifest_path = args.output_dir / "ORB-1-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"\nCapture complete. Manifest: {manifest_path}")
    print("Please relay both complete Horizons response blocks and the manifest.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
