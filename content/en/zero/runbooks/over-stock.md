---
title: Over stock firmware
weight: 1
---

# Runbook — migrating in place over the stock firmware

The printer works and you migrate on top of it. The vendor OS stays, the application and MCU firmware move to upstream, and the OS is an optional last step. This is the incremental de-vendoring path.

Each step below is a link into the component that does the work — this page is only the order.

## 1. Back up everything first

Vendor stack rsync, an SWD dump of the toolhead, and ideally a full eMMC image. The backups are what make every later step reversible. → [Recovery: back up first]({{< relref "/zero/os/recovery" >}}#back-up-first-the-checklist)

## 2. Build the firmware

Four images from one pinned `master` commit, on the printer host or a Mac, each gated on its reset vector. → [Building the firmware]({{< relref "/zero/firmware/build" >}})

## 3. Flash both MCUs

Toolhead once over SWD, then the mainboard over USB-Katapult — both onto new real-hardware UUIDs. → [MCU migration]({{< relref "/zero/firmware/mcu-migration" >}})

## 4. Point the host at master and translate the config

Same `master` checkout + a venv from its `requirements.txt`, `channel: dev`; then eddy on software I2C, tap, `homing_override`, the new UUIDs, and drop the vendor-only modules. → [Klipper config]({{< relref "/zero/application/klipper-config" >}}) (install any [plugins]({{< relref "/zero/application/plugins" >}}) you use)

## 5. Calibrate and verify

Drive current, the eddy freq→height table, tap threshold, input shaper, then a supervised first print. → [Calibration]({{< relref "/zero/application/calibration" >}})

## 6. OS — optional

Once the firmware and application are upstream, the only vendor layer left is the OS image. Replacing it is destructive and needs the eMMC pulled; do it when you want a fully vendor-free machine. → [OS]({{< relref "/zero/os" >}})
