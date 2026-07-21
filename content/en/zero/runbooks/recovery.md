---
title: Recovery
weight: 3
---

# Runbook — recovering a machine that won't come up

Route by what actually failed. Because [layer 2 survives layer 3]({{< relref "/concepts" >}}), most recoveries are narrower than they feel — a dead OS doesn't touch the MCUs, and a bad app flash doesn't touch the OS.

The backup checklist and the detailed rollbacks live on [the recovery page]({{< relref "/zero/os/recovery" >}}); this is the routing.

## The OS won't boot

The MCUs are fine. Rebuild only the OS, then reconnect.

- Have a full eMMC image → restore it: one `dd` back and you're where you were.
- No image → rebuild from clean: [with an eMMC reader]({{< relref "emmc-reader" >}}), or [in place]({{< relref "/zero/os/in-place" >}}) if you have no reader.
- Then restore the config and confirm klippy `ready` with both CAN UUIDs — that's the proof the MCUs survived.

If it died right after a kernel/`apt` upgrade, it's the [onboard-ethernet regression]({{< relref "/zero/troubleshooting" >}}#armbian-kernel-branches-and-onboard-ethernet), not dead hardware.

## A toolhead flash went bad

Recoverable over CAN as long as its CAN-capable Katapult survives. If the app is corrupt and you took an SWD dump, restore it over SWD. → [Recovery: a bad MCU flash]({{< relref "/zero/os/recovery" >}}#a-bad-mcu-flash) and [flashing]({{< relref "/zero/firmware/flashing" >}})

## A mainboard flash went bad

As long as Katapult survives, re-flash over USB-Katapult. Only a corrupted bootloader forces SWD on the buried mainboard header. Your rollback is a vendor-equivalent firmware built from your backed-up vendor `~/klipper` at `0x8020000`. → [Recovery: a bad MCU flash]({{< relref "/zero/os/recovery" >}}#a-bad-mcu-flash)

## Nothing backed up and stuck

[asnajder/zero-config](https://github.com/asnajder/zero-config) publishes ST-LINK-flashable vendor recovery images — emergency use only (third-party prebuilts of unverifiable provenance). After you're back on your feet, take the backups you didn't have: [start here]({{< relref "/zero/os/recovery" >}}#back-up-first-the-checklist).
