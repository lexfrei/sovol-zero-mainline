---
title: Calibration
weight: 4
---

# Calibrate and verify

With both MCUs on mainline, the config translated, and plugins in, calibrate the eddy probe and motion, then prove it with plastic.

## Eddy and tap

Run in order, `SAVE_CONFIG` after each:

1. `LDC_CALIBRATE_DRIVE_CURRENT`
2. `PROBE_EDDY_CURRENT_CALIBRATE` — builds the freq→height table
3. `PROBE_EDDY_CURRENT_TAP_CALIBRATE` — sets `tap_threshold`

## Input shaper

`TEST_RESONANCES` — mainline's chunked-FIFO LIS2DW read gives a clean trace, and with a wide `[resonance_tester]` window (not the vendor's pinned 35–45 Hz) the real resonance surfaces. On this host the diagonal test needs the camera stopped — see [troubleshooting]({{< relref "/zero/troubleshooting" >}}).

## Functional check

- `G28` homes via eddy.
- `BED_MESH_CALIBRATE METHOD=rapid_scan` completes.
- A test print runs.

Set `max_accel` to the binding per-axis `SHAPER_CALIBRATE` limit for clean geometry, not the resonance-test ceiling.

## The first print is the real proof

Klippy `ready` with both CAN UUIDs connected proves the stack is alive, but only a supervised first print proves the tap reference. The tap reference survives a config restore — but watch the first layer anyway. Only plastic proves it.
