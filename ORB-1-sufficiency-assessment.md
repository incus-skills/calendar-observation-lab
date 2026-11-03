# ORB-1 sufficiency assessment

**Status:** Bounded diagnostic completed; sufficient for the narrow ORB-1 frame-comparison question.  
**Assessment date:** 2026-11-03  
**Implementation:** `libephemeris==3.2.2`, Skyfield backend forced explicitly  
**Reference:** JPL Horizons observer-table quantity 31

## 1. Question under investigation

Does the default `libephemeris` apparent geocentric Sun/Moon position calculation agree with an independently generated JPL Horizons reference, and does `FLG_NONUT` improve or worsen that agreement?

This is not a general certification of astronomical accuracy or a verification of the full Calendar Artifact Specification.

## 2. Controlled observation definition

| Dimension | ORB-1 definition |
|---|---|
| Observer origin | Earth geocentre (`500@399`) |
| Targets | Sun (`10`) and Moon (`301`) |
| Epochs | 2026-02-03, 2026-05-03, 2026-08-03, 2026-11-03; each at 12:00:00 |
| Time input | Nominal UTC civil timestamp supplied to Horizons as `TIME_TYPE=UT`; same UT Julian Day supplied to `calc_ut` |
| Horizons quantity | 31: observer-centred apparent ecliptic longitude and latitude of date |
| Apparent-place corrections | Horizons quantity 31 includes light-time, gravitational deflection and stellar aberration |
| Compared variants | `FLG_SPEED` (default frame) and `FLG_SPEED | FLG_NONUT` |
| Derived quantity | Lunar phase elongation = (Moon longitude − Sun longitude) modulo 360° |

Horizons identifies DE441 as the reference ephemeris. Its output states that post-1962 time tags are UTC civil time kept within 0.9 seconds of UT1. The nominal UTC-to-UT treatment is therefore recorded as a practical approximation, not as an assertion that UTC and UT1 are identical.

## 3. Results

### Default frame residuals against Horizons

Residuals are signed angular differences in arcseconds.

| Epoch | Sun longitude | Moon longitude | Sun latitude | Moon latitude | Phase |
|---|---:|---:|---:|---:|---:|
| 2026-02-03 | +0.0437 | +0.0058 | −0.0390 | +0.0372 | −0.0379 |
| 2026-05-03 | +0.0451 | +0.0261 | +0.0079 | −0.0203 | −0.0189 |
| 2026-08-03 | +0.0435 | −0.0001 | +0.0394 | −0.0190 | −0.0437 |
| 2026-11-03 | +0.0433 | −0.0041 | −0.0064 | +0.0389 | −0.0474 |

Across this sample, the largest absolute default-frame residuals were:

- Longitude: **0.0451 arcseconds** (Sun, 2026-05-03).
- Latitude: **0.0394 arcseconds** (Sun, 2026-08-03).
- Derived phase: **0.0474 arcseconds** (2026-11-03).

These are observed residuals, not a proposed acceptance tolerance.

### Effect of `FLG_NONUT`

The non-nutation variant produces a common longitude displacement for Sun and Moon, with epoch-dependent magnitudes:

| Epoch | Sun longitude residual | Moon longitude residual |
|---|---:|---:|
| 2026-02-03 | −7.2974″ | −7.3353″ |
| 2026-05-03 | −5.5370″ | −5.5560″ |
| 2026-08-03 | −9.2013″ | −9.2449″ |
| 2026-11-03 | −8.2410″ | −8.2884″ |

The derived phase residual is unchanged to the reported precision. This is consistent with a largely common rotation of the longitude origin: subtracting the two longitudes cancels that shared displacement.

The epoch-dependent displacement is consistent with the expected time-varying nutation contribution to the frame orientation, rather than a constant longitude bias. The four-epoch pattern supports interpreting this as a frame-convention effect. It is not, by itself, a complete decomposition of the nutation series or proof that nutation is the sole contributor.

The default frame is therefore the substantially closer match to this Horizons quantity-31 convention at all four sampled epochs. The experiment supports that comparative conclusion; it does not independently prove every detail of the underlying frame model.

## 4. Implementation and ephemeris provenance

The workflow recorded:

- Python 3.12.16
- `libephemeris==3.2.2`
- `skyfield==1.55`
- `skyfield-data==7.0.0`
- Skyfield backend explicitly selected and verified by `get_calc_mode()`

The comparison runtime downloaded and retained:

- `de440.bsp` at `/home/runner/.libephemeris/de440.bsp`
- Size: 119,799,808 bytes
- SHA-256: `a4ce9bf9b3282becc9f4b2ac3cebe03a2ae7599981aabd7265fd8482fff7c4b5`

The `skyfield_data` package also contains `de421.bsp` (SHA-256 `a20a7139da04cbc462454634918e9a9ca69127044e2cc9d4f9c16e238d2deedc`). The runtime download/cache activity identifies DE440 as the file loaded during the comparison; the packaged DE421 is recorded as an available dependency resource, not conflated with the runtime-loaded DE440.

Horizons used DE441. Thus the comparison is independent in implementation and reference pipeline, but does not use identical ephemeris data.

The observed 0.04–0.05 arcsecond maximum residuals are plausibly at the scale expected from differences between the DE440 and DE441 solutions and the remaining pipeline/frame details. They should not be treated as a precision target to tighten or as evidence of a defect merely because they are non-zero. However, this experiment did not isolate the DE440/DE441 contribution by repeating the comparison with matched ephemeris data and harmonised conventions. Accordingly, the residual level is an observed comparison floor for this setup, not a proven irreducible floor attributable solely to the ephemeris-version difference.

## 5. Sufficiency judgement

The original ORB-1 purpose was to establish a reproducible independent reference and discriminate between the default and `FLG_NONUT` frame variants.

That purpose is sufficiently met for the narrow geocentric baseline because:

1. The reference definition, epoch, observer origin, target, quantity, request parameters and raw Horizons responses are retained.
2. The implementation under test was forced onto the Skyfield calculation path rather than a Horizons-backed path.
3. Four dates across the year were compared, including different lunar positions/configurations.
4. The default-frame agreement remained close at all four dates.
5. The `FLG_NONUT` variant showed a repeatable, materially larger common longitude displacement, while phase cancellation behaved consistently.
6. The runtime-loaded ephemeris file and its hash are recorded.

**Conclusion:** For ORB-1, the evidence supports retaining the default `libephemeris` frame rather than applying `FLG_NONUT` when matching the selected Horizons quantity-31 apparent geocentric reference. No numerical tolerance is declared by this investigation.

## 6. Explicit limits and work not authorised by this conclusion

This result does not establish:

- Universal accuracy across arbitrary dates, bodies, epochs or ephemeris versions.
- Topocentric or observer-location-dependent correctness. ORB-1 is deliberately geocentric.
- The intended interpretation of “relative to a location” in the frozen Calendar specification.
- End-to-end validation of the Calendar engine's time-zone/time-scale conversion. The comparison supplied the same nominal UTC/UT epoch directly to the reference and calculation paths; it did not exercise the engine's datetime normalisation path.
- A normative precision requirement for Calendar.
- Correctness of the current `calendar-engine` integration, including its duplicate/shadowing `observe()` method and time-scale ambiguity.

Those are separate questions. In particular, the topocentric baseline should only be opened if the specification's location obligation is to be tested; it should not be silently folded into ORB-1.

## 7. Reproduction and evidence

- [Workflow run](https://github.com/incus-skills/calendar-observation-lab/actions/runs/41732076154)
- [Workflow evidence artifact](https://github.com/incus-skills/calendar-observation-lab/actions/runs/41732076154/artifacts/13277915896)
- [Reference capture script](https://github.com/incus-skills/calendar-observation-lab/blob/main/capture_horizons_reference.py)
- [Comparison script](https://github.com/incus-skills/calendar-observation-lab/blob/main/compare_orb1.py)
- [Workflow definition](https://github.com/incus-skills/calendar-observation-lab/blob/main/.github/workflows/orb1-comparison.yml)

Run the workflow on push or manually. It captures the four Horizons epochs, runs the comparison, and uploads raw responses, manifests, results and environment provenance.
