# Replacing the OS — vanilla Armbian on the Sovol Zero board

The Klipper migration in [MIGRATION.md](MIGRATION.md) leaves Sovol's stock OS image untouched — Klipper lives in `/home/sovol`, so swapping the Klipper layer never rewrites the rootfs or the bootloader. For a fully vendor-free machine the last layer is the OS on the eMMC. This is the harder, destructive step (it rewrites the whole boot device), so it lives on its own page here.

This page is a verified end-to-end recipe for **vanilla Armbian on the stock 8 GB eMMC module** — no custom OS build, no replacement module. The original Armbian-on-Zero walkthrough is [asnajder/zero-config](https://github.com/asnajder/zero-config), which this guide builds on; where the two disagree (most notably on the 8 GB module), the difference is explained below.

If you keep the vendor OS for now (rather than reflashing), one quick de-vendoring step is worth doing: the host ships named **`SPI-XI`** (the manufacturer's company name). Rename it — `sudo hostnamectl set-hostname <name>` — and **also fix `/etc/hosts`**, because `hostnamectl` does not touch it and a leftover `127.0.1.1 SPI-XI` (plus the `::1 … SPI-XI` line) makes `sudo` print `unable to resolve host` on every command. Restart `avahi-daemon` and `moonraker` afterwards (or reboot). A fresh Armbian install below sets its own hostname, so this only applies to the kept vendor OS.

## What "almost a CB1" actually means

The host is an Allwinner H616 with the same peripheral wiring as a BigTreeTech CB1, and the vendor OS is a rebadged BTT CB1 image (Debian 11, kernel `5.16.17-sun50iw9`, U-Boot 2021.10). How compatible is it really? Diffing the decompiled device trees answers it exactly. Pull `sun50i-h616-sovol-emmc.dtb` from the official Sovol image (`H616_2.3.3_debian_sovol-1.3.7.zip`, linked from the Sovol wiki) and `sun50i-h616-biqu-emmc.dtb` from the BTT CB1 v2.3.4 image — same BSP kernel generation — and decompile both:

```bash
dtc -I dtb -O dts -o sovol-emmc.dts sun50i-h616-sovol-emmc.dtb
dtc -I dtb -O dts -o biqu-emmc.dts  sun50i-h616-biqu-emmc.dtb
diff biqu-emmc.dts sovol-emmc.dts
```

The whole diff is **one property**: `max-frequency` of `mmc2`, the eMMC controller. The `-sd` dtb variants are byte-identical.

| Device tree | `mmc2` (eMMC) `max-frequency` |
| --- | --- |
| Sovol vendor (`sovol-emmc`) | 40 MHz (`0x2625a00`) |
| BTT CB1 (`biqu-emmc`) | 120 MHz (`0x7270e00`) |
| Armbian (`bigtreetech-cb1-emmc`) | 150 MHz (`0x8f0d180`) |

Sovol validated this board's eMMC path at 40 MHz. Everything else — pins, WiFi (RTL8189FTV on SDIO), UART, CAN, LEDs — is a CB1. Two practical consequences:

- A stock BTT CB1 image (`fdtfile=sun50i-h616-biqu-emmc`) drives the eMMC at 3× the validated clock. It may appear to boot and then fail unpredictably — don't use it as-is.
- Armbian's CB1 profile is fine for this board **once `mmc2` is capped back to 40 MHz**, which a 249-byte device-tree overlay does (below). This also explains the folklore that "the stock 8 GB eMMC will not work with Armbian, a 32 GB module is required": capacity was never the problem (Armbian minimal is a 1.7 GiB image; the installed system uses ~1.2 GiB), the clock was. A fresh 32 GB module happens to tolerate 150 MHz; the stock module at the vendor's 40 MHz works just as well.

## The board, the eMMC, and why FEL is off the table

- The host is an **Allwinner H616** soldered onto Sovol's all-in-one control board — not a removable CB1/CM4 module. The **eMMC, though, is a removable module**: it is visible on the board, and Sovol sells a reader for it.
- **There is no exposed USB-C / OTG port on this board.** The usual Allwinner recovery trick — FEL mode + `sunxi-fel` + U-Boot `ums` to expose the eMMC as a USB mass-storage device — needs device-mode USB, which this board does not bring out. eMMC imaging is therefore done by pulling the module, not over USB.
- The BROM boots from the eMMC user area (SPL at the 8 KiB offset, 256 KiB fallback) before trying the SD slot, so a plain `dd` of a bootable image to the module is all it takes.

## Imaging the eMMC

Three ways to read/write the eMMC, cleanest first:

1. **Pull the module + an eMMC reader (cleanest — what the OS swap needs).** Remove the eMMC module, drop it into a USB eMMC reader (an MKS EMMC-ADAPTER V2 or equivalent), and image it with `dd` / Etcher / Armbian Imager from another machine. This sees *every* partition — the eMMC hardware boot partitions (`mmcblk1boot0`/`mmcblk1boot1`), the ext-CSD, SPL/U-Boot — so it is the only method that yields a faithful full backup and a clean full write.
2. **Live `dd` of the eMMC block device from the running printer (backup only, partial).** No extra hardware, but it reads just the user-data area: it misses the hardware boot partitions and the ext-CSD, and it is crash-consistent (the rootfs is mounted live). Fine as a "grab the configs and the device tree" snapshot, not as a restore image.
3. **FEL + U-Boot UMS over USB — not available here** (no OTG port, see above).

Take a full backup (method 1) before writing anything.

## Flashing vanilla Armbian

Verified with **Armbian 26.2.1 Trixie minimal/CLI for the BigTreeTech CB1** (kernel `6.12.68-current-sunxi64`, U-Boot 2024.01) from [armbian.com/bigtreetech-cb1](https://www.armbian.com/bigtreetech-cb1/), written to the stock 8 GB module. Newer builds of the same board profile should behave the same.

### The 40 MHz overlay

Compile a user overlay that caps the eMMC controller at the vendor-validated clock:

```dts
/dts-v1/;
/plugin/;

/ {
    compatible = "bigtreetech,cb1", "allwinner,sun50i-h616";

    fragment@0 {
        target-path = "/soc/mmc@4022000";
        __overlay__ {
            max-frequency = <40000000>;
        };
    };
};
```

```bash
dtc -I dts -O dtb -o sovol-zero-emmc-40mhz.dtbo sovol-zero-emmc-40mhz.dts
```

It goes into `overlay-user/` on the BOOT (FAT) partition — `/boot/overlay-user/` from the running system — and is enabled by the `user_overlays=` line below. Because it is a user overlay, it survives `apt` kernel upgrades that replace the kernel-provided dtbs.

### armbianEnv.txt

On the BOOT partition, keep the `rootdev` UUID the image shipped with and set:

```ini
verbosity=1
bootlogo=false
console=both
overlay_prefix=sun50i-h616
fdtfile=sun50i-h616-bigtreetech-cb1-emmc.dtb
rootdev=UUID=<as shipped in the image>
rootfstype=ext4
overlays=sun50i-h6-uart3 sun50i-h616-ws2812 sun50i-h616-spidev1_1
user_overlays=sovol-zero-emmc-40mhz
```

The three kernel-provided overlays are the same trio the vendor's `BoardEnv.txt` enables (UART, the WS2812 screen LEDs, the SPI used by the display/sensors); all three ship in the Armbian image.

### Headless preseed — why WiFi has to be baked in

Armbian's own preseed file (`/root/.not_logged_in_yet`) configures the network **at first interactive login, not at boot** (`armbian-firstlogin` vs `armbian-firstrun`). On a WiFi-only headless box that is a chicken-and-egg: no network until someone logs in, no login until there is network. So bake the WiFi config directly into the rootfs and use the preseed only for the interactive bits (user creation, locale, timezone).

The minimal image manages the network with **netplan → systemd-networkd + wpa_supplicant** (NetworkManager is not installed). Two files make WiFi come up deterministically on first boot:

`/etc/systemd/network/10-wlan0.link` — pin the interface name so the netplan match is stable:

```ini
[Match]
Driver=8189fs
Type=wlan

[Link]
Name=wlan0
```

`/etc/netplan/30-wifi.yaml` — **must be mode 0600**, and note the pinned `key-management`:

```yaml
network:
  version: 2
  wifis:
    wlan0:
      dhcp4: yes
      dhcp6: yes
      regulatory-domain: "<your country code>"
      access-points:
        "<your SSID>":
          auth:
            key-management: "psk"
            password: "<your passphrase>"
```

The explicit `key-management: "psk"` matters on WPA2/WPA3-transition networks: the out-of-tree `8189fs` driver (RTL8189FTV) cannot complete SAE, so the association must be pinned to WPA-PSK — the same failure mode as on the vendor stack (see the WiFi note in [ARCHITECTURE.md](ARCHITECTURE.md)).

Also worth baking in: `/etc/hostname` (plus the matching `127.0.1.1` line in `/etc/hosts`) and `/root/.ssh/authorized_keys` (dir `0700`, file `0600`). For a fully non-interactive first login, fill `/root/.not_logged_in_yet` — note the `*_KEY` presets are **URLs** fetched with `curl`, e.g. `https://github.com/<your-github-user>.keys`:

```bash
PRESET_NET_CHANGE_DEFAULTS=0
PRESET_CONNECT_WIRELESS=n
SET_LANG_BASED_ON_LOCATION=n
PRESET_LOCALE=en_US.UTF-8
PRESET_TIMEZONE=<your timezone>
PRESET_ROOT_PASSWORD=<root password>
PRESET_ROOT_KEY=https://github.com/<your-github-user>.keys
PRESET_USER_NAME=<user>
PRESET_USER_PASSWORD=<user password>
PRESET_DEFAULT_REALNAME=<name>
PRESET_USER_SHELL=bash
PRESET_USER_KEY=https://github.com/<your-github-user>.keys
```

### Editing the image offline

Doing all of the above **in the `.img` file before writing** means one `dd` and a board that comes up configured. On Linux, `losetup --find --show --partscan armbian.img` and mount both partitions. On macOS (which cannot mount the 0xEA-typed FAT partition or ext4 at all), `mtools` and `debugfs` from Homebrew's `e2fsprogs` work directly on the image at the partition byte offsets from `fdisk` (for the current Armbian sunxi layout: FAT at sector 8192 → offset 4194304, ext4 at sector 532480 → offset 272629760):

```bash
# FAT boot partition
mcopy -o -i 'armbian.img@@4194304' armbianEnv.txt ::/armbianEnv.txt
mmd   -i 'armbian.img@@4194304' ::/overlay-user
mcopy -o -i 'armbian.img@@4194304' sovol-zero-emmc-40mhz.dtbo ::/overlay-user/

# ext4 rootfs: write files, then fix modes (debugfs creates 0644 root:root)
debugfs -w -R 'write 30-wifi.yaml /etc/netplan/30-wifi.yaml' 'armbian.img?offset=272629760'
debugfs -w -R 'sif /etc/netplan/30-wifi.yaml mode 0100600'   'armbian.img?offset=272629760'
```

Then write the image to the module through the reader (`sudo dd if=armbian.img of=/dev/<module> bs=4M`), put the module back, and power up. First boot expands the rootfs to the full module automatically.

## First boot — verifying the eMMC clock

The controller-to-device mapping is not what the dts labels suggest: the eMMC (`4022000.mmc`) probes as **`mmc_host mmc1` / `mmcblk1`**, the SDIO WiFi (`4021000.mmc`) as `mmc2`, and the empty SD slot (`4020000.mmc`) as `mmc0`. So the overlay is verified against `mmc1`:

```bash
cat /sys/kernel/debug/mmc1/ios
# clock:        40000000 Hz
# actual clock: 37500000 Hz
# bus width:    3 (8 bits)
# timing spec:  8 (mmc DDR52)
```

40 MHz requested, 37.5 MHz after the divider, 8-bit DDR52 — exactly the vendor-validated operating point, on the stock 8 GB module.

## After first boot

- Mask `systemd-networkd-wait-online.service` — it otherwise stalls boot waiting for the (cable-less) ethernet.
- Reference cameras by `/dev/v4l/by-id/...`, never by a bare index: kernel 6.18 enumerates the H616's Cedrus VPU as `/dev/video0`, displacing a USB camera to `/dev/video1` — a crowsnest config pointing at the old index dies silently (service active, nothing served on the stream port).
- Bring CAN up under **`systemd-networkd`**: a `25-can.network` link at 1 Mbit, plus a udev rule setting `tx_queue_len=128` on the `can*` interface.
- Install the stack with **[KIAUH](https://github.com/dw-0/kiauh)** — Klipper + Moonraker + Mainsail + Crowsnest.
- The eddy probe needs **`scipy`** in the Klipper venv (and `python3-serial`).

From there the MCU and config work is the same as [MIGRATION.md](MIGRATION.md): build/flash mainline firmware for each MCU, pick up the new CAN UUIDs, and translate the vendor config. As on the firmware side, the LDC1612 eddy probe runs on **software I2C** here too — hardware I2C is not reliable on this board, a finding [asnajder/zero-config](https://github.com/asnajder/zero-config) reaches independently.

See [asnajder/zero-config](https://github.com/asnajder/zero-config) for the original ordered walkthrough this page grew out of — including the interactive (`armbian-config`) route if you'd rather configure WiFi on a console than preseed it.
