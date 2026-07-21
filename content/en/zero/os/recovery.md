---
title: Recovery
weight: 6
---

# Recovery and backups

What makes every step in every path reversible, and how to get back a machine that won't boot. Recovery is mostly a backup story: take the right snapshots before you touch anything, and a dead layer becomes a restore instead of a rebuild.

## Back up first — the checklist {#back-up-first-the-checklist}

Take these before erasing anything. They are what make each later step reversible.

1. **The vendor stack** (file-level, resumable rsync — not a raw `dd` over WiFi): vendor `~/klipper` as a git bundle, `~/printer_data/config`, `~/printer_data/build/*.bin`, and the per-chip build configs `~/klipper/.config*` (useful seeds even though their flash offsets are stale).
2. **An SWD dump of the toolhead** before you erase it — the surest exact rollback for the F103:

   ```bash
   openocd -c "adapter driver cmsis-dap" -c "transport select swd" -c "adapter speed 1000" \
     -f target/stm32f1x.cfg -c "init" -c "halt" \
     -c "dump_image vendor-f103-FULL-flash.bin 0x08000000 0x10000" -c "shutdown"
   ```

   A valid dump opens with a sane vector table (initial SP in RAM `0x2000xxxx`, reset vector in flash `0x0800xxxx`), not all `0xFF`/`0x00`.
3. **A full eMMC image** (module in a USB reader): one `dd` of the whole device with its SHA256 — the only backup that captures partition table, boot partition, and rootfs. Take it *before* any OS work, not after. See [imaging the eMMC]({{< relref "armbian" >}}#imaging-the-emmc).

The [backup matrix]({{< relref "/concepts" >}}#the-backup-matrix-that-makes-every-path-cheap) shows which artifact belongs to which layer and how often it changes. The one people actually lose is the config — put it in git first.

## The OS won't boot

A dead OS never touches the MCUs — [layer 2 survives layer 3]({{< relref "/concepts" >}}). So this is an OS-only rebuild, and the MCUs come back exactly as they were:

- **Have a full eMMC image?** Restore it: one `dd` back through the reader and you're where you were.
- **No image?** Rebuild the OS from clean — [clean-slate with an eMMC reader]({{< relref "clean-slate" >}}) if you have one, or [in place]({{< relref "in-place" >}}) if you don't. Then restore the config and reconnect: klippy `ready` with both CAN UUIDs is the proof the MCUs survived.

If the cause was a kernel-in-place upgrade that killed onboard ethernet, that's a known regression, not dead hardware — see [the kernel-branch note]({{< relref "/zero/troubleshooting" >}}#armbian-kernel-branches-and-onboard-ethernet).

## A bad MCU flash {#a-bad-mcu-flash}

- **Toolhead (F103).** Recoverable over CAN as long as its CAN-capable Katapult survives. If the app itself is corrupt and you took an SWD dump, restore it over SWD (see [flashing]({{< relref "/zero/firmware/flashing" >}})). The toolhead has no USB and no CAN recovery if Katapult itself is gone — which is why the bootstrap is SWD-once.
- **Mainboard (H750).** As long as Katapult survives you re-flash over USB-Katapult. Only a **corrupted bootloader** forces SWD on the buried mainboard header. Your build-from-source rollback is a vendor-equivalent firmware compiled from your backed-up vendor `~/klipper` at the same `0x8020000` offset.
- **No backup and stuck?** [asnajder/zero-config](https://github.com/asnajder/zero-config) publishes ST-LINK-flashable vendor recovery images for the mainboard (incl. its Katapult), the toolhead, and the chamber MCU. They are third-party prebuilts of unverifiable provenance — an emergency fallback only, not a routine source.

{{< hint danger >}}

**Don't touch power or USB mid-write.** A clean flash is recoverable through Katapult, but an interrupted write that corrupts Katapult itself is the one case that forces SWD on the buried mainboard. Take your own SWD dump first — that is your rollback.

{{< /hint >}}

## Config loss

The config is the most volatile layer and the one most often lost. Restore `printer.cfg` **with its `SAVE_CONFIG` block** (the eddy freq table, `tap_threshold`, and bed mesh live there and cannot be retyped), plus `saved_variables.cfg`. Details on [the Klipper config page]({{< relref "/zero/application/klipper-config" >}}#restoring-a-config-from-backup). Then re-snapshot to git — and after every tuning session from now on.
