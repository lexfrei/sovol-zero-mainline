---
title: With an eMMC reader
weight: 2
---

# Runbook — clean-slate build with an eMMC reader

The path a recovery or a fresh build actually takes: OS first, application on top, MCUs usually last — and often untouched, because [layer 2 survived whatever killed layer 3]({{< relref "/concepts" >}}). This is the order verified end-to-end on the reference machine.

## 1. Inventory your backups

Minimum viable: the config set (git repo or any copy) and the MCU state. Already-mainline MCUs need nothing here; vendor MCUs need the firmware steps below. A full eMMC image makes this a restore instead of a rebuild. → [Recovery]({{< relref "/zero/os/recovery" >}})

## 2. Flash the OS

Pull the module, flash it offline, preseed the rootfs, boot configured. Verify before proceeding: boots, joins WiFi, eMMC at DDR52 37.5 MHz effective. → [Clean-slate install]({{< relref "/zero/os/clean-slate" >}})

## 3. Install the application stack

KIAUH — Klipper (master), Moonraker, Mainsail + config, Crowsnest — plus the extras you use. Enable CAN on the host and install `scipy` in the Klipper venv. → [KIAUH stack]({{< relref "/zero/application/kiauh" >}}) and [plugins]({{< relref "/zero/application/plugins" >}})

## 4. Restore the config

`printer.cfg` with its `SAVE_CONFIG` block, `saved_variables.cfg`, `moonraker.conf`. Fix absolute paths if the OS user changed. A missing section means its plugin isn't installed yet — install it, don't delete the section. → [Klipper config: restoring from backup]({{< relref "/zero/application/klipper-config" >}}#restoring-a-config-from-backup)

## 5. MCUs — only if they're on vendor firmware

If they ran mainline before, they still do — klippy connecting to both CAN UUIDs is the proof. If they're on vendor firmware, do the firmware steps: [build]({{< relref "/zero/firmware/build" >}}) then [flash both MCUs]({{< relref "/zero/firmware/mcu-migration" >}}).

## 6. Verify bottom-up, then print

eMMC clock (layer 3), both MCUs respond (layer 2), klippy `ready` (layer 4), then a supervised first print — watch the first layer. The tap reference recovers from a config restore, but only a real print proves it. → [Calibration]({{< relref "/zero/application/calibration" >}})
