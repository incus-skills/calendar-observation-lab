# ORB-2 Sufficiency Assessment

## Status

CLOSED — bounded observation and library-level runtime verification complete.

The source inspection, controlled conversion probe, and isolated
`libephemeris.eph.julday()` runtime assertion are complete for the
defined objective. This closure does not resolve the Calendar engine's
datetime semantics or validate its end-to-end datetime-to-Julian-date
path.

## Scope

Bounded observation of the effective `observe()` implementation in
`calendar_engine.py` at commit `5d30daed`, plus direct runtime
verification of the installed `libephemeris.eph.julday()` function
against one known epoch.

## Findings

### Source-confirmed behaviour

- Two `observe()` definitions exist; the second is effective (Python class semantics).
- The effective method passes calendar fields directly to `julday()`.
- The effective method does not inspect `tzinfo`.
- The effective method does not include microseconds.
- The effective method returns `timestamp=dt` while using `dt`'s fields for the JD.
- The shadowed method contains UTC normalisation and microsecond handling.

### Probe-confirmed consequences

The expected Julian date for 2026-11-03 12:00:00 UTC is JD 2461348.0.

- 12:00 UTC aware → JD 2461348.000000 (matches expected)
- 12:00 naive → JD 2461348.000000 (matches numerically; intent unspecified)
- 17:30 +05:30 → JD 2461348.229167 (5.5 hours late)
- 05:00 -07:00 → JD 2461347.708333 (7 hours early)
- 12:00:00.5 UTC → JD 2461348.000000 (0.5 seconds discarded)

These values come from the bounded controlled conversion probe, not
from execution of the Calendar engine against the actual libephemeris
runtime.

### Data-integrity finding

For timezone-aware inputs with a non-zero UTC offset, the effective
method preserves the original datetime in `RawObservation.timestamp`
but calculates astronomical positions using its unconverted calendar
fields.

Consequently, the timestamp represents one instant while the positions
correspond to another. This produces internally inconsistent
`RawObservation` objects.

For naive inputs, the corresponding problem cannot be classified
without first establishing the intended timezone semantics. The method
uses the supplied wall-clock fields directly, but the intended instant
is unspecified.

The separate microsecond omission also means that fractional-second
precision is lost when calculating the Julian date.

### Inference

The duplicate definition probably resulted from an incomplete edit.
The most recent commit (`5d30daed`) added the UTC-normalising
implementation first but did not remove the older implementation
below it.

### Unresolved specification question

The intended time semantics remain unresolved. The presence of the
UTC-normalising implementation is evidence of intent, not proof that
it was the intended specification.

### Runtime verification completed

The isolated assertion in `verify_julday.py` was executed successfully
in GitHub Actions on both Python 3.12 and Python 3.13.

- Installed `libephemeris`: 3.2.2
- Epoch: 2026-11-03 12:00:00
- Expected Julian date: 2461348.0
- Observed assertion result: PASS on both matrix jobs
- Workflow run: [Calendar Engine Test #6](https://github.com/incus-skills/calendar-engine/actions/runs/41737699690)

The assertion exercises the actual installed library runtime. It is a
library-level check only; it does not execute the Calendar engine's
`observe()` method or establish that the engine supplies the correct
epoch to `julday()`.

## Classification

- Confirmed by source: effective method ignores timezone offsets and microseconds.
- Confirmed by controlled probe: quantified consequences above.
- Runtime-verified: installed `libephemeris.eph.julday()` returns the expected JD for the tested epoch in both CI Python versions.
- Still unresolved: intended time semantics and end-to-end Calendar engine datetime handling.

## What the runtime assertion establishes

Passing `verify_julday.py` establishes that the installed
`libephemeris` runtime returns the expected Julian date for this known
epoch. It does not establish that the Calendar engine passes the
correct epoch to `julday()`. That remains a separate question already
exposed by this observation.

## No implementation correction proposed

The observation has produced a substantive finding. No implementation
correction is proposed at this stage.

## Provenance

- Calendar engine observation target commit: `5d30daed6379f1e9861d35c487cac41f34ea0483`
- Source file: `calendar_engine.py`
- Source blob: `e8dc98abf2752f5a426380c149b2d0a144218a52`
- Runtime verifier commit: [`3f691a4`](https://github.com/incus-skills/calendar-engine/commit/3f691a4a36df930b9a24f45748590d8ff8823fb8)
- CI workflow commit: [`ed83c10`](https://github.com/incus-skills/calendar-engine/commit/ed83c10d3506344a538dbf84cfd2fbb0966a907e)
- CI run: [41737699690](https://github.com/incus-skills/calendar-engine/actions/runs/41737699690)
- Observation lab assessment commit: pending this update
