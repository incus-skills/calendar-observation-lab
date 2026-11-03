#!/usr/bin/env python3
"""Compare libephemeris Skyfield results with the captured ORB-1 Horizons reference.

This is a diagnostic, not a pass/fail accuracy test. It records both the
default coordinate-frame result and FLG_NONUT so their frame-dependent
difference can be examined without presuming which convention matches
Horizons quantity 31.

The Horizons reference must already have been captured by
capture_horizons_reference.py.
"""

from __future__ import annotations

import csv
import importlib.metadata
import json
from datetime import datetime
from pathlib import Path

import libephemeris as eph
from libephemeris.constants import FLG_NONUT, FLG_SPEED, MOON, SUN

REFERENCE_DIR = Path("reference-data/horizons")
OUTPUT_DIR = Path("results")


def parse_horizons_row(path: Path) -> tuple[float, float]:
    """Return (longitude, latitude) from the single quantity-31 data row."""
    text = path.read_text(encoding="utf-8")
    if "$$SOE" not in text or "$$EOE" not in text:
        raise ValueError(f"{path} does not contain a complete Horizons data block")

    data = text.split("$$SOE", 1)[1].split("$$EOE", 1)[0]
    rows = [row for row in csv.reader(data.splitlines()) if row and any(x.strip() for x in row)]
    if len(rows) != 1:
        raise ValueError(f"Expected exactly one Horizons data row in {path}; found {len(rows)}")

    # Observer-table rows contain blank columns between timestamp and
    # ObsEcLon/ObsEcLat. Select the final two non-empty fields.
    values = [float(value.strip()) for value in rows[0][1:] if value.strip()]
    if len(values) != 2:
        raise ValueError(f"Expected longitude and latitude in {path}; parsed {values!r}")
    return values[0], values[1]


def signed_angle_difference_deg(value: float, reference: float) -> float:
    """Smallest signed angular difference, in [-180, 180) degrees."""
    return (value - reference + 180.0) % 360.0 - 180.0


def main() -> int:
    manifest_path = REFERENCE_DIR / "ORB-1-manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"Missing {manifest_path}; run capture_horizons_reference.py first"
        )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    epoch_text = manifest["epoch"]
    epoch = datetime.strptime(epoch_text, "%Y-%m-%d %H:%M:%S")
    hour = epoch.hour + epoch.minute / 60.0 + epoch.second / 3600.0
    jd = float(eph.julday(epoch.year, epoch.month, epoch.day, hour))

    # Explicitly force the local Skyfield path; do not allow auto mode to
    # select a Horizons-backed calculation for this comparison.
    eph.set_calc_mode("skyfield")
    calculation_mode = eph.get_calc_mode()
    if calculation_mode != "skyfield":
        raise RuntimeError(f"Could not force Skyfield backend; active mode={calculation_mode!r}")

    reference = {
        "sun": parse_horizons_row(REFERENCE_DIR / f"{epoch:%Y%m%d}_sun.txt"),
        "moon": parse_horizons_row(REFERENCE_DIR / f"{epoch:%Y%m%d}_moon.txt"),
    }
    phase_reference = (reference["moon"][0] - reference["sun"][0]) % 360.0

    variants = {
        "default": FLG_SPEED,
        "nonut": FLG_SPEED | FLG_NONUT,
    }
    bodies = {"sun": SUN, "moon": MOON}
    results: dict[str, dict] = {}

    for variant, flags in variants.items():
        positions: dict[str, list[float]] = {}
        returned_flags: dict[str, int] = {}
        for name, body in bodies.items():
            position, retflags = eph.calc_ut(jd, body, flags)
            positions[name] = list(position)
            returned_flags[name] = int(retflags)

        phase = (positions["moon"][0] - positions["sun"][0]) % 360.0
        results[variant] = {
            "requested_flags": int(flags),
            "returned_flags": returned_flags,
            "positions": {
                name: {
                    "longitude_deg": positions[name][0],
                    "latitude_deg": positions[name][1],
                }
                for name in bodies
            },
            "phase_elongation_deg": phase,
            "residuals_vs_horizons": {
                name: {
                    "longitude_arcsec": (
                        signed_angle_difference_deg(
                            positions[name][0], reference[name][0]
                        ) * 3600.0
                    ),
                    "latitude_arcsec": (
                        (positions[name][1] - reference[name][1]) * 3600.0
                    ),
                }
                for name in bodies
            },
            "phase_residual_arcsec": (
                signed_angle_difference_deg(phase, phase_reference) * 3600.0
            ),
        }

    report = {
        "baseline_id": manifest.get("baseline_id", "ORB-1"),
        "epoch": epoch_text,
        "julian_day_ut": jd,
        "reference_source": "JPL Horizons quantity 31; captured raw responses",
        "reference": {
            name: {
                "longitude_deg": reference[name][0],
                "latitude_deg": reference[name][1],
            }
            for name in bodies
        },
        "reference_phase_elongation_deg": phase_reference,
        "implementation": {
            "package": "libephemeris",
            "version": importlib.metadata.version("libephemeris"),
            "calculation_mode": calculation_mode,
            "backend_policy": "Skyfield forced explicitly; Horizons backend not selected",
        },
        "variants": results,
        "interpretation": {
            "status": "diagnostic_only",
            "tolerance_deg": None,
            "note": (
                "No accuracy threshold is imposed. Compare frame variants and "
                "residuals before assigning a tolerance or declaring equivalence."
            ),
        },
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "ORB-1-comparison.json"
    output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(f"ORB-1 comparison written to {output_path}")
    print(f"libephemeris version: {report['implementation']['version']}")
    print(f"Calculation mode: {calculation_mode}")
    print(f"Horizons phase: {phase_reference:.9f} deg")
    for variant, result in results.items():
        print(f"\n[{variant}]")
        for name in bodies:
            pos = result["positions"][name]
            residual = result["residuals_vs_horizons"][name]
            print(
                f"{name}: lon={pos['longitude_deg']:.9f} deg "
                f"lat={pos['latitude_deg']:+.9f} deg "
                f"dLon={residual['longitude_arcsec']:+.4f} arcsec "
                f"dLat={residual['latitude_arcsec']:+.4f} arcsec"
            )
        print(
            f"phase={result['phase_elongation_deg']:.9f} deg "
            f"dPhase={result['phase_residual_arcsec']:+.4f} arcsec"
        )

    print("\nDiagnostic completed. No numerical tolerance has been asserted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
