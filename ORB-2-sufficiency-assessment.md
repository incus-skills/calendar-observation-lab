# ORB-2 Sufficiency Assessment

## Status

OBSERVATION COMPLETE — runtime verification pending.

The source inspection and controlled conversion probe are complete.
Final closure of the runtime verification objective is conditional on
the CI assertion passing against the installed libephemeris runtime.

## Scope

Bounded observation of the effective `observe()` implementation in
`calendar_engine.py` at commit `5d30daed`.

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

These values come from the bounded controlled conversion probe, not from execution of the Calendar engine against the actual libephemeris runtime.

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

### Not yet runtime-verified

The actual `libephemeris.eph.julday()` runtime has not yet been
exercised. Closure path: execute the assertion in `verify_julday.py`
through CI and record the resulting run evidence.

## Classification

- Confirmed by source: effective method ignores timezone offsets and microseconds.
- Confirmed by probe: quantified consequences above.
- Not yet runtime-verified: actual libephemeris integration.
- Still unresolved: intended time semantics.

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

- Repository: `calendar-engine` at `5d30daed`
- File: `calendar_engine.py`
- Blob: `e8dc98abf2752f5a426380c149b2d0a144218a52`
