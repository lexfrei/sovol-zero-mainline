---
title: Extras
weight: 5
---

# Extras — optional hardware and practices

Additions that are not part of the core migration but earned their place on a real machine.

## USB WiFi dongle (when the onboard radio dies) {#usb-wifi-dongle-when-the-onboard-radio-dies}

The onboard RTL8189FTV is a known single point of failure — on this unit it died of PSU-inflicted causes (`mmc: error -110 whilst initialising SDIO card` on every boot, on stock firmware too, through ~21 attempts across two kernel stacks; software revival — power-cycling the chip via its GPIO, longer `post-power-on-delay-ms`, lower SDIO clock — changes nothing). If you see that signature, stop debugging and plug a dongle into one of the board's USB-A ports.

Pick an **MT7601U** stick (sold as LP-UW06 among others, `lsusb` ID `148f:7601`): the `mt7601u` driver is in the Armbian kernel, the firmware blob ships in the image, there is no USB mode-switch dance and no competing out-of-tree driver — it is the only truly plug-and-play option. RTL8811CU-class sticks work too but bring `usb_modeswitch` plus two rival drivers.

Two files make it drop-in (bake them at preseed time, see [clean-slate]({{< relref "/zero/os/clean-slate" >}})):

```ini
# /etc/systemd/network/10-wlan0.link — stable name off the driver
[Match]
Driver=mt7601u

[Link]
Name=wlan0
```

and the usual netplan `wifis: wlan0:` block (`key-management: "psk"`, `optional: true`). With both in place the dongle associates on first boot with zero manual steps.

## Stock PSU — keep it grounded, and a bolt-on replacement

The stock 24 V supply fails often enough to plan for, and running it **without a mains earth** is what kills it — on one machine a dying PSU took the mainboard's onboard WiFi chip with it (the failure behind [the dead radio above](#usb-wifi-dongle-when-the-onboard-radio-dies)). Always run it grounded.

For a drop-in replacement that needs no fabrication, a **MEAN WELL LRS-150-24** (24 V, 150 W) is bolt-on: two screws in the lower bay, move the cables across, done. It's a more reputable supply than the stock unit, so likely more tolerant of abuse. (A 48 V supply is a separate speed mod, not a replacement.)

## BTT SFS V2.0 filament sensor

The board's three detect ports (silkscreen legend `PLA_DET` / `TWINE_DET` / `DOOR_DET`) share the same `3V3 / GND / signal` pinout, which happens to match the SFS V2.0's two split tails: the `red-empty-blue` tail carries VCC + the runout switch signal, the `empty-black-green` tail carries GND + the motion signal — the module powers up only with both plugged. Any two ports work; the signal pins by legend order are `PB2` (PLA_DET), `PE7` (TWINE_DET), `PE8` (DOOR_DET). Cable colours vary between batches — trust the module PCB's own port markings over wire colour.

Installing the SFS needs some disassembly, but only the chamber's **rear wall** — that's the whole teardown. The tempting mistake is to rip out the old stock sensor and its cable entirely while you're in there. Don't: that cable is routed the length of the printer (chamber → lower bay → door jamb), so a full removal means opening the lower bay too, cleaning the compound off its motherboard port, cutting every zip tie along the run, and reassembling it all in reverse. Instead, unclip only the old sensor from the cable end, zip-tie the loose end out of the way with the ties in the box, and leave the cable in its potted port. Feed the SFS's own cable in through the chamber's side window and land it on two adjacent free ports (`PE7` + `PE8` below).

Klipper config for green→PE7 (motion), blue→PE8 (runout), stock PB2 sensor removed from the path:

```ini
[filament_switch_sensor sfs_runout]
pause_on_runout: False
switch_pin: PE8
runout_gcode:
    PAUSE
    M117 SFS-S Empty
insert_gcode:
    M117 SFS-S Inserted

[filament_motion_sensor sfs_motion]
pause_on_runout: False
switch_pin: PE7
detection_length: 4.99
extruder: extruder
runout_gcode:
    PAUSE
    M117 SFS-M Static
insert_gcode:
    M117 SFS-M Moving
```

`detection_length: 4.99` is deliberately forgiving — BTT's 2.88 "high accuracy" value false-triggers on retract-heavy prints. Do not add `[pause_resume]` — `mainsail.cfg` already ships it and a duplicate section fails config parsing. If the stock PB2 sensor is physically out of the filament path, delete its config section too: a floating input is a false-runout generator. Verify polarity live with `QUERY_FILAMENT_SENSOR` with filament in and out; invert with `!` on the pin if needed.

## Backups that make experiments cheap

Two layers, both proven in anger:

1. **Full eMMC image** (module in a USB reader): `dd` the whole device, keep the SHA256. This is the only backup that captures everything — partition table, boot partition, rootfs — and restoring it is one `dd` back. Take one before any risky campaign.
2. **On-board tar pair** for kernel experiments, taken while the system runs: `tar czf /root/boot.tar.gz /boot` and `tar czf /root/modules.tar.gz /lib/modules/$(uname -r)`. Armbian kernel packages replace files **in place** (`/boot` is vfat — no symlinks, and the old `/lib/modules/<ver>` is deleted on upgrade), so a restore script that untars both plus a dead-man systemd unit (no network N minutes after boot → restore + reboot) turns a kernel test into a reversible operation even with no second access channel. A WiFi dongle as an independent path (see above) makes it fully safe.
