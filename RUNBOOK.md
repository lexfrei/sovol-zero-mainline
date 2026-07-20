# Runbook — blank eMMC to a ready printer

The default install path, start to finish. This is the exact sequence used to (re)build the machine this guide documents — twice — so every step here has survived contact with reality. Background and one-off details live in the other docs; this file is just the order of operations.

Prerequisites: the eMMC module in a USB reader, a Linux machine or VM for the offline edits (macOS cannot write ext4 — see [OS.md](OS.md)), and the MCUs already on mainline Katapult + Klipper per [MIGRATION.md](MIGRATION.md). If the MCUs ran mainline before, they still do — skip nothing else.

## 1. Flash Sovobian

Grab the Sovol Zero image from [lexfrei/sovobian](https://github.com/lexfrei/sovobian/releases) — it is upstream Armbian CB1 minimal with the 40 MHz eMMC overlay pre-installed — verify it against `SHA256SUMS`, and write it to the module:

```bash
xz --decompress --stdout Sovobian_*_Sovol-Zero_*.img.xz | sudo dd of=/dev/rdiskN bs=4m
```

## 2. Preseed the rootfs offline

Mount the ext4 rootfs (partition 2) on the Linux side and bake in everything the first boot needs. The mechanics (loop mount, chroot for `useradd`/`chpasswd`) are in [OS.md](OS.md); the checklist of what to bake:

- hostname + `/etc/hosts`
- SSH `authorized_keys` for root and your user; user with `sudo` (add a `NOPASSWD` drop-in — several installers below run `sudo` non-interactively and fail without it)
- netplan: WiFi with `key-management: "psk"` pinned (see [OS.md](OS.md) on why), and `optional: true` on **both** WiFi and Ethernet — otherwise a missing link hangs boot for 90 s in `systemd-networkd-wait-online`
- CAN host plumbing: `can`+`can_raw` in `/etc/modules-load.d/`, a `systemd.network` file setting 1 Mbit on `can*`, and a udev rule for `tx_queue_len` 128
- **hold the kernel**: `chroot ... apt-mark hold linux-image-current-sunxi64 linux-dtb-current-sunxi64` — see [TROUBLESHOOTING.md](TROUBLESHOOTING.md#armbian-kernel-branches-and-onboard-ethernet) for why this is load-bearing
- delete `/root/.not_logged_in_yet` so the first-login wizard never runs

Write the rootfs back, boot the board, confirm it takes DHCP and the eMMC runs DDR52 at 37.5 MHz effective ([OS.md](OS.md)).

## 3. Update packages

`apt-get update && apt-get full-upgrade` is safe **only** with the kernel held (step 2). Without the hold, the first upgrade replaces the kernel in place and takes onboard Ethernet with it.

## 4. Application stack — KIAUH

Clone [dw-0/kiauh](https://github.com/dw-0/kiauh) and install, in order: Klipper, Moonraker, Mainsail, Mainsail-Config, Crowsnest. Two post-install fixes from [TROUBLESHOOTING.md](TROUBLESHOOTING.md): point the Crowsnest camera at its `/dev/v4l/by-id/` path (the video index shifts between kernels) and add the Crowsnest v5 `update_manager` snippet verbatim from `~/crowsnest/resources/moonraker_update.txt`.

## 5. Plugins

- `sovol_codes.py` from [`klipper-plugin/`](klipper-plugin/) → `~/klipper/klippy/extras/`
- `scipy` into the Klipper venv (`~/klippy-env/bin/pip install scipy`) — required by the eddy probe. If PyPI stalls from the board, sideload wheels ([TROUBLESHOOTING.md](TROUBLESHOOTING.md#pip-downloads-from-the-board-stall-forever))
- moonraker-timelapse: clone, symlink `component/timelapse.py` into `~/moonraker/moonraker/components/`, copy `klipper_macro/timelapse.cfg` to the config dir, add `[timelapse]` + its `update_manager` section to `moonraker.conf`
- Shake&Tune: upstream installer (this is one of the things that needs the `NOPASSWD` sudo from step 2)

## 6. Configs

Restore `printer.cfg` **with its `SAVE_CONFIG` block** — the eddy frequency table, `tap_threshold` and bed mesh live there and cannot be retyped — plus `saved_variables.cfg`. Fix absolute paths if the OS user changed (`[save_variables]` filename is the classic one). If klippy reports an unknown section or option, the matching plugin is missing or the config carries an option a newer plugin dropped — install/trim accordingly, don't delete whole sections blindly.

## 7. Verify

```bash
systemctl is-active klipper moonraker crowsnest   # all active
curl -s localhost:7125/printer/info               # state: ready
```

Klippy `ready` with both CAN UUIDs connected is the proof the whole stack — host, bridge MCU, toolhead — is alive. Then a supervised first print: the tap reference survives a config restore, but only plastic proves it.

## Optional hardware add-ons

Dead onboard WiFi replacement (USB dongle) and the BTT SFS V2.0 filament sensor are covered in [EXTRAS.md](EXTRAS.md).
