---
title: Clean-slate (eMMC reader)
weight: 3
---

# Clean-slate install with an eMMC reader

The cleanest OS path: pull the eMMC module, flash it offline in a USB reader, bake in everything first boot needs, and power up a configured machine. This is the exact sequence used to (re)build the reference machine — twice — so every step has survived contact with reality.

Prerequisites: the eMMC module in a USB reader, a Linux machine or VM for the offline edits (macOS cannot write ext4 — see the offline-edit note below), and the MCUs already on mainline Katapult + Klipper (see [MCU migration]({{< relref "/zero/firmware/mcu-migration" >}})). If the MCUs ran mainline before, they still do — [layer 2 survives layer 3]({{< relref "/concepts" >}}).

## 1. Flash the image

Two options:

- **Sovobian (quickest).** Grab the Sovol Zero image from [lexfrei/sovobian](https://github.com/lexfrei/sovobian/releases) — upstream Armbian CB1 minimal with the 40 MHz eMMC overlay pre-installed. Verify it against `SHA256SUMS` and write it:

  ```bash
  xz --decompress --stdout Sovobian_*_Sovol-Zero_*.img.xz | sudo dd of=/dev/rdiskN bs=4m
  ```

- **Vanilla Armbian (from scratch).** Take stock Armbian CB1 and build the 40 MHz overlay yourself — the full recipe (overlay dts, `armbianEnv.txt`, the CB1 difference) is on [the vanilla Armbian page]({{< relref "armbian" >}}).

## 2. Preseed the rootfs offline

Mount the ext4 rootfs (partition 2) on the Linux side and bake in everything the first boot needs:

- hostname + `/etc/hosts`
- SSH `authorized_keys` for root and your user; user with `sudo` (add a `NOPASSWD` drop-in — several installers run `sudo` non-interactively and fail without it)
- netplan: WiFi with `key-management: "psk"` pinned (the `8189fs` driver can't complete SAE on WPA2/WPA3-transition networks), and `optional: true` on **both** WiFi and Ethernet — otherwise a missing link hangs boot for 90 s in `systemd-networkd-wait-online`
- CAN host plumbing: `can`+`can_raw` in `/etc/modules-load.d/`, a `systemd.network` file setting 1 Mbit on `can*`, and a udev rule for `tx_queue_len` 128
- **hold the kernel**: `chroot ... apt-mark hold linux-image-current-sunxi64 linux-dtb-current-sunxi64` — see [why]({{< relref "/zero/troubleshooting" >}}#armbian-kernel-branches-and-onboard-ethernet), and [the updatable-OS page]({{< relref "updatable" >}}) for the path off the hold
- delete `/root/.not_logged_in_yet` so the first-login wizard never runs

Write the rootfs back, boot the board, confirm it takes DHCP and the eMMC runs DDR52 at 37.5 MHz effective (see [verifying the clock]({{< relref "armbian" >}}#first-boot-verifying-the-emmc-clock)).

{{< hint info >}}

**Editing offline on macOS.** macOS can't mount the ext4 rootfs or the 0xEA-typed FAT partition. Use `mtools` (`mcopy`/`mmd`) for the boot partition and `debugfs` from Homebrew's `e2fsprogs` for the rootfs, operating on the image at the partition byte offsets from `fdisk`. The exact commands are on [the vanilla Armbian page]({{< relref "armbian" >}}#editing-the-image-offline).

{{< /hint >}}

## 3. Update packages

`apt-get update && apt-get full-upgrade` is safe **only** with the kernel held (step 2). Without the hold, the first upgrade replaces the kernel in place and takes onboard Ethernet with it.

## 4. Then the application stack

The OS is ready. Move to the application layer — install the [KIAUH stack]({{< relref "/zero/application/kiauh" >}}), the [plugins]({{< relref "/zero/application/plugins" >}}) you use, and [restore or translate the config]({{< relref "/zero/application/klipper-config" >}}). If you want the whole ordered path start to finish, follow [the eMMC-reader runbook]({{< relref "/zero/runbooks/emmc-reader" >}}).
