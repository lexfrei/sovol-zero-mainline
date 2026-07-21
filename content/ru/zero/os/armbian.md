---
title: Ванильный Armbian
weight: 2
---

# Ванильный Armbian на плате Sovol Zero

Миграция Klipper оставляет стоковый образ ОС от Sovol нетронутым — Klipper живёт в `/home/sovol`, так что замена слоя Klipper никогда не переписывает rootfs или загрузчик. Для полностью вендор-фри машины последний слой — это ОС на eMMC. Это более трудный, деструктивный шаг (он переписывает всё загрузочное устройство).

Это проверенный от начала до конца рецепт **ванильного Armbian на стоковом 8 ГБ eMMC-модуле** — без кастомной сборки ОС, без замены модуля. Оригинальный разбор Armbian-на-Zero — [asnajder/zero-config](https://github.com/asnajder/zero-config), на нём это и строится; где они расходятся (в первую очередь на 8 ГБ модуле), разница объяснена ниже.

Если ты пока оставляешь вендорскую ОС, один быстрый шаг де-вендоринга стоит сделать: хост приезжает с именем **`SPI-XI`** (название компании-производителя). Переименуй — `sudo hostnamectl set-hostname <name>` — и **ещё поправь `/etc/hosts`**, потому что `hostnamectl` его не трогает, а оставшийся `127.0.1.1 SPI-XI` (плюс строка `::1 … SPI-XI`) заставляет `sudo` печатать `unable to resolve host` на каждой команде. После этого перезапусти `avahi-daemon` и `moonraker` (или перезагрузись). Свежая установка Armbian ниже задаёт своё имя хоста, так что это касается только оставленной вендорской ОС.

## Что на самом деле значит «почти CB1» {#what-almost-a-cb1-actually-means}

Хост — это Allwinner H616 с той же разводкой периферии, что у BigTreeTech CB1, и вендорская ОС — это переклеенный образ BTT CB1 (Debian 11, ядро `5.16.17-sun50iw9`, U-Boot 2021.10). Насколько он реально совместим? Diff декомпилированных device tree отвечает точно. Достань `sun50i-h616-sovol-emmc.dtb` из официального образа Sovol и `sun50i-h616-biqu-emmc.dtb` из образа BTT CB1 v2.3.4 — то же поколение BSP-ядра — и декомпилируй оба:

```bash
dtc -I dtb -O dts -o sovol-emmc.dts sun50i-h616-sovol-emmc.dtb
dtc -I dtb -O dts -o biqu-emmc.dts  sun50i-h616-biqu-emmc.dtb
diff biqu-emmc.dts sovol-emmc.dts
```

Весь diff — это **одно свойство**: `max-frequency` у `mmc2`, контроллера eMMC. Варианты dtb с `-sd` байт-в-байт идентичны.

| Device tree | `mmc2` (eMMC) `max-frequency` |
| --- | --- |
| Вендорский Sovol (`sovol-emmc`) | 40 МГц (`0x2625a00`) |
| BTT CB1 (`biqu-emmc`) | 120 МГц (`0x7270e00`) |
| Armbian (`bigtreetech-cb1-emmc`) | 150 МГц (`0x8f0d180`) |

Sovol валидировал eMMC-путь этой платы на 40 МГц. Всё остальное — пины, WiFi (RTL8189FTV на SDIO), UART, CAN, LED — это CB1. Два практических следствия:

- Стоковый образ BTT CB1 (`fdtfile=sun50i-h616-biqu-emmc`) гоняет eMMC на 3× валидированного клока. Он может как будто загрузиться, а потом непредсказуемо отвалиться — не используй его как есть.
- CB1-профиль Armbian нормально подходит этой плате, **как только `mmc2` укорочен обратно до 40 МГц**, что и делает device-tree оверлей на 249 байт (ниже). Это заодно объясняет фольклор о том, что «стоковый 8 ГБ eMMC не заработает с Armbian, нужен 32 ГБ модуль»: проблемой была никогда не ёмкость (Armbian minimal — это образ 1.7 GiB; установленная система занимает ~1.2 GiB), а клок. Свежий 32 ГБ модуль просто так терпит 150 МГц; стоковый модуль на вендорских 40 МГц работает ровно так же.

## Плата, eMMC, и почему FEL отпадает {#the-board-the-emmc-and-why-fel-is-off-the-table}

- Хост — это **Allwinner H616**, распаянный на all-in-one плате управления Sovol, а не съёмный CB1/CM4 модуль. А вот **eMMC — съёмный модуль**: он виден на плате, и Sovol продаёт под него ридер.
- **На этой плате нет выведенного порта USB-C / OTG.** Обычный трюк восстановления Allwinner — режим FEL + `sunxi-fel` + `ums` в U-Boot, чтобы выставить eMMC как USB mass storage — требует USB в device-режиме, который эта плата не выводит. Поэтому образ eMMC снимают, вынимая модуль, а не по USB.
- BROM грузится из user-области eMMC (SPL по офсету 8 KiB, фолбэк 256 KiB) прежде чем пробовать SD-слот, так что достаточно простого `dd` загрузочного образа на модуль.

## Снятие образа eMMC {#imaging-the-emmc}

Три способа читать/писать eMMC, от самого чистого:

1. **Снять модуль + eMMC-ридер (самое чистое — то, что нужно для замены ОС).** Вынь eMMC-модуль, вставь в USB eMMC-ридер (MKS EMMC-ADAPTER V2 или аналог) и сними образ через `dd` / Etcher / Armbian Imager с другой машины. Он видит *каждый* раздел — аппаратные boot-разделы eMMC (`mmcblk1boot0`/`mmcblk1boot1`), ext-CSD, SPL/U-Boot — так что это единственный метод, дающий точный полный бэкап и чистую полную запись.
2. **Живой `dd` блочного устройства eMMC с работающего принтера (только бэкап, частичный).** Без доп-железа, но читает только user-data область: он пропускает аппаратные boot-разделы и ext-CSD, и он crash-consistent (rootfs смонтирован вживую). Годится как снапшот «схватить конфиги и device tree», но не как образ для восстановления.
3. **FEL + U-Boot UMS по USB — тут недоступно** (нет OTG-порта, см. выше).

Сними полный бэкап (метод 1), прежде чем что-то писать.

## Оверлей 40 МГц {#the-40-mhz-overlay}

Проверено с **Armbian 26.2.1 Trixie minimal/CLI для BigTreeTech CB1** (ядро `6.12.68-current-sunxi64`, U-Boot 2024.01), записанным на стоковый 8 ГБ модуль. Скомпилируй пользовательский оверлей, который укорачивает контроллер eMMC до вендор-валидированного клока:

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

Он кладётся в `overlay-user/` на BOOT (FAT) разделе — `/boot/overlay-user/` из работающей системы — и включается строкой `user_overlays=` ниже. Поскольку это пользовательский оверлей, он переживает `apt`-апгрейды ядра, которые заменяют предоставляемые ядром dtb.

## armbianEnv.txt

На BOOT разделе оставь `rootdev` UUID, с которым приехал образ, и задай:

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

Три предоставляемых ядром оверлея — та же тройка, что включает вендорский `BoardEnv.txt` (UART, WS2812-светодиоды экрана, SPI для дисплея/датчиков); все три идут в образе Armbian.

## Headless-пресид — почему WiFi надо запечь {#headless-preseed-why-wifi-has-to-be-baked-in}

Собственный preseed-файл Armbian (`/root/.not_logged_in_yet`) настраивает сеть **при первом интерактивном логине, а не при загрузке** (`armbian-firstlogin` против `armbian-firstrun`). На headless-коробке только с WiFi это курица-и-яйцо: нет сети, пока кто-то не залогинится, нет логина, пока нет сети. Так что запеки конфиг WiFi прямо в rootfs, а пресид используй только для интерактивных вещей (создание пользователя, локаль, таймзона).

Minimal-образ управляет сетью через **netplan → systemd-networkd + wpa_supplicant** (NetworkManager не установлен). Два файла делают так, чтобы WiFi детерминированно поднимался на первой загрузке:

`/etc/systemd/network/10-wlan0.link` — запинь имя интерфейса, чтобы match у netplan был стабильным:

```ini
[Match]
Driver=8189fs
Type=wlan

[Link]
Name=wlan0
```

`/etc/netplan/30-wifi.yaml` — **должен быть в режиме 0600**, и обрати внимание на запиненный `key-management`:

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

Явный `key-management: "psk"` важен на сетях WPA2/WPA3-transition: out-of-tree драйвер `8189fs` (RTL8189FTV) не может завершить SAE, так что ассоциацию надо запинить на WPA-PSK — тот же режим отказа, что и на вендорском стеке (см. заметку про WiFi в [Архитектуре]({{< relref "/zero/hardware/architecture" >}})).

Ещё стоит запечь: `/etc/hostname` (плюс соответствующую строку `127.0.1.1` в `/etc/hosts`) и `/root/.ssh/authorized_keys` (директория `0700`, файл `0600`). Для полностью неинтерактивного первого логина заполни `/root/.not_logged_in_yet` — учти, что пресеты `*_KEY` — это **URL**, которые тянутся через `curl`, например `https://github.com/<your-github-user>.keys`:

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

## Редактирование образа офлайн {#editing-the-image-offline}

Сделать всё вышеперечисленное **в `.img` файле до записи** означает один `dd` и плату, которая поднимается настроенной. На Linux — `losetup --find --show --partscan armbian.img` и смонтируй оба раздела. На macOS (который вообще не может смонтировать FAT-раздел типа 0xEA или ext4) `mtools` и `debugfs` из Homebrew-овского `e2fsprogs` работают прямо по образу на байтовых офсетах разделов из `fdisk` (для текущего sunxi-лейаута Armbian: FAT на секторе 8192 → офсет 4194304, ext4 на секторе 532480 → офсет 272629760):

```bash
# FAT boot partition
mcopy -o -i 'armbian.img@@4194304' armbianEnv.txt ::/armbianEnv.txt
mmd   -i 'armbian.img@@4194304' ::/overlay-user
mcopy -o -i 'armbian.img@@4194304' sovol-zero-emmc-40mhz.dtbo ::/overlay-user/

# ext4 rootfs: write files, then fix modes (debugfs creates 0644 root:root)
debugfs -w -R 'write 30-wifi.yaml /etc/netplan/30-wifi.yaml' 'armbian.img?offset=272629760'
debugfs -w -R 'sif /etc/netplan/30-wifi.yaml mode 0100600'   'armbian.img?offset=272629760'
```

Потом запиши образ на модуль через ридер (`sudo dd if=armbian.img of=/dev/<module> bs=4M`), верни модуль на место и включи питание. Первая загрузка автоматически расширяет rootfs на весь модуль.

## Первая загрузка — проверка клока eMMC {#first-boot-verifying-the-emmc-clock}

Маппинг контроллер→устройство не такой, как намекают лейблы в dts: eMMC (`4022000.mmc`) пробится как **`mmc_host mmc1` / `mmcblk1`**, SDIO WiFi (`4021000.mmc`) — как `mmc2`, а пустой SD-слот (`4020000.mmc`) — как `mmc0`. Так что оверлей проверяется против `mmc1`:

```bash
cat /sys/kernel/debug/mmc1/ios
# clock:        40000000 Hz
# actual clock: 37500000 Hz
# bus width:    3 (8 bits)
# timing spec:  8 (mmc DDR52)
```

40 МГц запрошено, 37.5 МГц после делителя, 8-битный DDR52 — ровно вендор-валидированная рабочая точка, на стоковом 8 ГБ модуле.

## После первой загрузки

- Замаскируй `systemd-networkd-wait-online.service` — иначе он тормозит загрузку, ожидая (безкабельный) ethernet.
- Ссылайся на камеры по `/dev/v4l/by-id/...`, никогда по голому индексу: ядро 6.18 нумерует Cedrus VPU у H616 как `/dev/video0`, сдвигая USB-камеру на `/dev/video1` — конфиг crowsnest, указывающий на старый индекс, тихо умирает.
- Подними CAN под **`systemd-networkd`**: линк `25-can.network` на 1 Mbit, плюс udev-правило, задающее `tx_queue_len=128` на интерфейсе `can*`.
- Установи стек через **[KIAUH]({{< relref "/zero/application/kiauh" >}})** — Klipper + Moonraker + Mainsail + Crowsnest.
- Eddy-пробе нужен **`scipy`** в venv Klipper (и `python3-serial`).

Дальше работа с MCU и конфигом та же, что в [миграции прошивки]({{< relref "/zero/firmware/mcu-migration" >}}): собрать/прошить mainline-прошивку под каждый MCU, подхватить новые CAN-UUID, и [перевести вендорский конфиг]({{< relref "/zero/application/klipper-config" >}}). Как и на стороне прошивки, eddy-проба LDC1612 работает здесь тоже на **software I2C**.

См. [asnajder/zero-config](https://github.com/asnajder/zero-config) ради оригинального упорядоченного разбора, из которого выросла эта страница — включая интерактивный (`armbian-config`) путь, если тебе удобнее настроить WiFi в консоли, чем пресидить его.
