# Replacing the OS — Armbian Trixie on the Sovol Zero board

The Klipper migration in [MIGRATION.md](MIGRATION.md) leaves Sovol's stock OS image untouched — Klipper lives in `/home/sovol`, so swapping the Klipper layer never rewrites the rootfs or the bootloader. For a fully vendor-free machine the last layer is the OS on the eMMC. This is the harder, destructive step (it rewrites the whole boot device), so it lives on its own page here.

The canonical, battle-tested walkthrough is [asnajder/zero-config](https://github.com/asnajder/zero-config). This page records the facts that matter and points there for the ordered step-by-step rather than restating it.

## The board, the eMMC, and why FEL is off the table

- The host is an **Allwinner H616** soldered onto Sovol's all-in-one control board — not a removable CB1/CM4 module. The **eMMC, though, is a removable module**: it is visible on the board, and Sovol sells a reader for it.
- **The stock 8 GB eMMC is too small for a clean Armbian install — a 32 GB module is the documented requirement.** Reusing the original 8 GB module will not fit the image.
- **There is no exposed USB-C / OTG port on this board.** The usual Allwinner recovery trick — FEL mode + `sunxi-fel` + U-Boot `ums` to expose the eMMC as a USB mass-storage device — needs device-mode USB, which this board does not bring out. eMMC imaging is therefore done by pulling the module, not over USB.

## Imaging the eMMC

Three ways to read/write the eMMC, cleanest first:

1. **Pull the module + an eMMC reader (cleanest — what the OS swap needs).** Remove the eMMC module, drop it into a USB eMMC reader (an MKS EMMC-ADAPTER V2 or equivalent), and image it with `dd` / Etcher / Armbian Imager from another machine. This sees *every* partition — the eMMC hardware boot partitions (`mmcblk0boot0`/`mmcblk0boot1`), the ext-CSD, SPL/U-Boot — so it is the only method that yields a faithful full backup and a clean full write.
2. **Live `dd` of `/dev/mmcblk0` from the running printer (backup only, partial).** No extra hardware, but it reads just the user-data area: it misses the hardware boot partitions and the ext-CSD, and it is crash-consistent (the rootfs is mounted live). Fine as a "grab the configs and the device tree" snapshot, not as a restore image.
3. **FEL + U-Boot UMS over USB — not available here** (no OTG port, see above).

Take a full backup (method 1) before writing anything.

## Flashing Armbian Trixie

The verified recipe (per asnajder's guide) writes **Armbian Trixie, minimal/CLI**, to a 32 GB eMMC with the Armbian Imager, using the **BigTreeTech CB1** board profile. The H616 CB1 device tree drives this board even though it is not literally a CB1 — the operative fact is `fdtfile=sun50i-h616-bigtreetech-cb1-emmc.dtb` in `/boot/armbianEnv.txt`.

Three device-tree **overlays** have to be enabled in `/boot/armbianEnv.txt` for the board's peripherals (the UART, the WS2812 screen LEDs, and the SPI used by the display / sensors):

```ini
overlay_prefix=sun50i-h616
fdtfile=sun50i-h616-bigtreetech-cb1-emmc.dtb
overlays=sun50i-h6-uart3 sun50i-h616-ws2812 sun50i-h616-spidev1_1
```

After first boot:

- Mask `systemd-networkd-wait-online.service` — it otherwise stalls boot waiting for the network.
- Bring CAN up under **`systemd-networkd`**: a `25-can.network` link at 1 Mbit, plus a udev rule setting `tx_queue_len=128` on the `can*` interface.
- Install the stack with **[KIAUH](https://github.com/dw-0/kiauh)** — Klipper + Moonraker + Mainsail + Crowsnest.
- The eddy probe needs **`scipy`** in the Klipper venv (and `python3-serial`).

From there the MCU and config work is the same as [MIGRATION.md](MIGRATION.md): build/flash mainline firmware for each MCU, pick up the new CAN UUIDs, and translate the vendor config. As on the firmware side, the LDC1612 eddy probe runs on **software I2C** here too — hardware I2C is not reliable on this board, a finding [asnajder/zero-config](https://github.com/asnajder/zero-config) reaches independently.

See [asnajder/zero-config](https://github.com/asnajder/zero-config) for the complete ordered walkthrough — eMMC partitioning, the exact `armbianEnv.txt`, the CAN unit files, Wi-Fi via `armbian-config`, and the full eddy calibration flow.
