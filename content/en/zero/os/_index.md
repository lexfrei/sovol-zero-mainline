---
title: OS
weight: 5
bookCollapseSection: true
---

# OS — Layer 3

What boots from the eMMC. The vendor ships a rebadged BigTreeTech CB1 image (Debian 11, an old kernel); the mainline target is vanilla Armbian plus one device-tree overlay. Replacing the OS is optional — the Klipper migration never touches the rootfs — but it's the last vendor layer, and it's where the machine's one genuinely non-CB1 quirk lives: the eMMC must run at 40 MHz, not the CB1's 120/150.

This layer has several entry points depending on your hardware and goal:

- **[Easy install]({{< relref "quickstart" >}})** — the friendly path for most people: flash a base image to a microSD, boot, and answer a short SSH wizard. No offline editing. **Start here** unless you have a reason not to.
- **[Vanilla Armbian]({{< relref "armbian" >}})** — the reference: what "almost a CB1" means, the 40 MHz overlay, the headless preseed, and how to verify the eMMC clock. Read this before any hands-on OS work.
- **[Clean-slate with an eMMC reader]({{< relref "clean-slate" >}})** — the fully-offline expert install: pull the module, flash offline, preseed everything into the rootfs, boot configured with no wizard.
- **[In place, no eMMC reader]({{< relref "in-place" >}})** — put a fresh OS on the eMMC from the running board, via the microSD slot.
- **[Updatable Armbian]({{< relref "updatable" >}})** — keep the OS updatable across `apt`/kernel upgrades. The 40 MHz overlay is already upgrade-proof; only the kernel is held, and only for onboard ethernet.
- **[Recovery]({{< relref "recovery" >}})** — a machine that won't boot, and the backups that make every OS step reversible.

> [!NOTE]
> **Layer 2 survives layer 3.** The MCU firmware lives in the MCUs, not on the eMMC — wiping or replacing the OS does not touch it, and the CAN UUIDs stay stable. A machine whose OS died boots a fresh OS and finds its MCUs exactly as they were.
