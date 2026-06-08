# Flashing over SWD with a Flipper Zero (DAP Link)

The toolhead Katapult is request-only and can't be recovered over CAN once an app is broken, so an SWD probe is the safety net. Any CMSIS-DAP probe works — an ST-Link V2 clone, or a Flipper Zero running the **DAP Link** app.

> **Verified scope.** Everything here was tested only on the **F103 toolhead**, and only with a **Flipper Zero** (DAP Link app). An ST-Link should behave the same (it is standard SWD), and the H750 section below is reasoned, not tested. Corrections and additions are welcome — open a PR.

## The probe (Flipper Zero)

- Use the **DAP Link** app — *not* "SWD Probe" (that one only reads, it can't flash). DAP Link presents to the host as a CMSIS-DAP probe (`Combined VCP and CMSIS-DAP Adapter`).
- Default DAP Link GPIO: SWC (SWCLK) = pin 10, SWD (SWDIO) = pin 12, GND = pin 11, 3V3 = pin 9. Confirm in the app's *Config → Help and Pinout*.
- openocd drives it with `adapter driver cmsis-dap` + `transport select swd`.

## F103 toolhead — verified

Target `stm32f1x`. Header: the 4-pin `5V3 IO CK G` near the F103 (see [PINOUT.md](PINOUT.md)). Disconnect the head from the printer — the probe's 3.3 V powers the MCU (a blue LED confirms power).

```bash
# sanity: read the chip (expect Cortex-M3, device id 0x...410)
openocd -c "adapter driver cmsis-dap" -c "transport select swd" -c "adapter speed 1000" \
  -f target/stm32f1x.cfg -c "init" -c "dap info" -c "shutdown"

# dump the factory firmware first (the only exact rollback for the toolhead)
openocd -c "adapter driver cmsis-dap" -c "transport select swd" -c "adapter speed 1000" \
  -f target/stm32f1x.cfg -c "init" -c "halt" \
  -c "dump_image factory.bin 0x08000000 0x10000" -c "shutdown"

# erase + write Katapult (0x08000000) + Klipper (0x08002000) + run
openocd -c "adapter driver cmsis-dap" -c "transport select swd" -c "adapter speed 1000" \
  -f target/stm32f1x.cfg -c "init" -c "reset halt" \
  -c "stm32f1x mass_erase 0" \
  -c "flash write_image katapult.bin 0x08000000" \
  -c "flash write_image klipper.bin 0x08002000" \
  -c "reset run" -c "shutdown"
```

A valid dump starts with a sane vector table (initial SP in RAM `0x2000xxxx`, reset vector in flash `0x0800xxxx`), not all `0xFF`/`0x00`.

## H750 mainboard — not tested here

Target `stm32h7x`. SWD pins are PA13 (SWDIO) / PA14 (SWCLK); the header is on the mainboard, harder to reach than the toolhead. SWD is the H750's read / recovery path, with one caveat:

- The Klipper app lives at `0x8020000` — outside the 128 KiB internal flash, in the board's extra (QSPI) flash. openocd writes internal flash out of the box; writing that external region needs an external-flash driver configured, which is non-trivial. The internal region (Katapult) can be written over SWD, but the app cannot without that setup.
- In practice the H750 is flashed over **USB-Katapult** (see [MIGRATION.md](MIGRATION.md)), not SWD. Reserve SWD for the case where the app is corrupted and USB-Katapult can no longer be entered.

If you have flashed the H750 over SWD (with external-flash config), or used an ST-Link on either chip, a PR refining this is welcome.
