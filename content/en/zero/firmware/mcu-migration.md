---
title: MCU migration
weight: 3
---

# MCU migration — both MCUs onto mainline

The clean way to put both MCUs fully on upstream Klipper — app *and* bootloader, no vendor bytes in the firmware. Build everything from the **same Klipper `master` commit** (see [why master]({{< relref "/concepts" >}})). The order is: build all four images, flash the toolhead once over SWD, then the mainboard over USB-Katapult.

## Prerequisites

- **An SWD programmer** — ST-Link V2 (~$3 clone) or a Flipper Zero running the DAP Link app. Needed once, to bootstrap the toolhead: the vendor Katapult is request-only and can't be recovered over CAN, so you flash a CAN-capable mainline Katapult onto the toolhead over SWD the first time, and never open the head again.
- **ARM toolchain** — `arm-none-eabi-gcc` (already on the printer host) or `brew install --cask gcc-arm-embedded` on macOS. See [Building the firmware]({{< relref "build" >}}).
- `openocd` ≥ 0.11 for the SWD flash.
- SSH access to the printer.

## Back up first

Before erasing anything, take your rollback — the SWD dump of the toolhead especially. The full backup checklist (vendor stack, SWD dump, eMMC image) is on [the recovery page]({{< relref "/zero/os/recovery" >}}). The one that matters most here:

```bash
openocd -c "adapter driver cmsis-dap" -c "transport select swd" -c "adapter speed 1000" \
  -f target/stm32f1x.cfg -c "init" -c "halt" \
  -c "dump_image vendor-f103-FULL-flash.bin 0x08000000 0x10000" -c "shutdown"
```

A valid dump opens with a sane vector table (initial SP in RAM `0x2000xxxx`, reset vector in flash `0x0800xxxx`), not all `0xFF`/`0x00`. The mainboard's SWD header is buried, so its build-from-source rollback is a vendor-equivalent firmware compiled from your backed-up vendor `~/klipper` at the same `0x8020000` offset (USB-Katapult-flashable).

## Stage 1 — Build the firmware (from `master`)

Full toolchain notes, the offset table, per-image output names, and the reset-vector gate are on [Building the firmware]({{< relref "build" >}}). You build four images, all from the same `master` commit:

| Image | Target | Offset | How it's flashed |
| --- | --- | --- | --- |
| Toolhead Katapult | F103, **CANSERIAL** | `0x8000000` | SWD (once) |
| Toolhead Klipper | F103 | `0x8002000` | SWD (once), then CAN |
| Mainboard Katapult deployer | **`MACH_STM32H743`** | `0x8020000` | USB-Katapult |
| Mainboard Klipper | **`MACH_STM32H743`** | `0x8020000` | USB-Katapult |

Two things make this clean:

- **Build the mainboard as `MACH_STM32H743`,** not H750. On current master both targets reach the `0x8020000` offset with no patch, but H750 defaults to 480 MHz while H743 defaults to **400 MHz** — the clock this mainboard is validated at.
- **Build the toolhead Katapult `CANSERIAL`,** seeding its `.config` from the vendor `.config103` (a bare seed defaults `olddefconfig` to USB, which would be silent on the CAN bus). A CAN-capable Katapult is what lets every future toolhead update flash over CAN with no head-opening.

The mainboard Katapult **deployer** (`BUILD_DEPLOYER=y`, auto-enabled when the app offset differs from the boot offset) is what installs mainline Katapult over USB without SWD. **Gate every image on its reset vector** before flashing: bytes 4–7 (little-endian) must land at the app offset (`0x08002xxx` for the F103, `0x0802xxxx` for the mainboard). A `0x08000xxx` vector means it was built for the wrong offset and will brick the chip — rebuild.

## Stage 2 — Flash the toolhead, once, over SWD

This is the only time you open the head. It writes the CAN-capable mainline Katapult and the Klipper app; afterwards the toolhead flashes over CAN forever. The header and probe wiring are on [the toolhead pinout]({{< relref "/zero/hardware/toolhead" >}}) and [the flashing page]({{< relref "flashing" >}}). Disconnect the head; the probe's 3.3 V powers the MCU.

```bash
# sanity: read the chip (expect Cortex-M3, device id 0x...410)
openocd -c "adapter driver cmsis-dap" -c "transport select swd" -c "adapter speed 1000" \
  -f target/stm32f1x.cfg -c "init" -c "dap info" -c "shutdown"

# erase + write CANSERIAL Katapult (0x08000000) + Klipper (0x08002000) + run
openocd -c "adapter driver cmsis-dap" -c "transport select swd" -c "adapter speed 1000" \
  -f target/stm32f1x.cfg -c "init" -c "reset halt" \
  -c "stm32f1x mass_erase 0" \
  -c "flash write_image katapult-f103.bin 0x08000000" \
  -c "flash write_image klipper-f103.bin 0x08002000" \
  -c "reset run" -c "shutdown"
```

Reassemble the head, reconnect its CAN, power on. The toolhead now answers on a **new real-hardware UUID** (mainline reads the real UID instead of the vendor's fake `61755fe321ac`):

```bash
python3 ~/katapult/scripts/flashtool.py -i can0 -q     # note the new UUID
```

## Stage 3 — Flash the mainboard, over USB-Katapult, no SWD

The mainboard is the USB-CAN bridge, so it's reachable over USB even though its SWD header is buried. Replace both its bootloader (via the deployer) and its app. (`flashtool.py` is `~/katapult/scripts/flashtool.py` — run these from that directory or put it on `PATH`.)

```bash
# 1) request the bridge into its (stock) Katapult — it re-enumerates as a USB serial device
flashtool.py -i can0 -u <mainboard-uuid> -r        # stock vendor Katapult appears under /dev/serial/by-id/ as usb-katapult_stm32h750xx-*

# 2) install mainline Katapult by flashing the deployer through the stock bootloader
flashtool.py -d /dev/serial/by-id/usb-katapult_stm32h750xx-* -f deployer-mainboard.bin   # re-enumerates h750xx → h743xx = success

# 3) flash the Klipper app through the freshly-installed mainline Katapult
flashtool.py -d /dev/serial/by-id/usb-katapult_stm32h743xx-* -f klipper-mainboard.bin   # via the new mainline (H743) Katapult
```

The USB id reflects the MCU target the *bootloader* was built for, so the change from `h750xx` (stock vendor Katapult) to `h743xx` confirms the mainline (H743) Katapult is now in control — that re-enumeration is your go signal between steps 2 and 3. The bridge's USB re-enumerates during these steps (SSH/flash output may drop, the write still completes). **Don't touch power or USB mid-write** — a clean flash is recoverable through Katapult, but an interrupted write that corrupts Katapult itself is the one case that forces SWD on the buried mainboard. After it boots, the mainboard also comes up on a **new real UUID** (the fake `0d1445047cdd` is gone); `flashtool.py -i can0 -q` to read it.

If you'd rather not bootstrap the toolhead over SWD at all, the same deployer trick can in principle go over CAN through the *working* vendor toolhead app — but the toolhead has no USB and no CAN recovery if that flash corrupts, so SWD-once (Stage 2) is the safe path.

## Next

With both MCUs on mainline and their new UUIDs noted, move to the application layer: point the host at the same `master`, translate the config, and calibrate. See [Klipper config]({{< relref "/zero/application/klipper-config" >}}) and [calibration]({{< relref "/zero/application/calibration" >}}).
