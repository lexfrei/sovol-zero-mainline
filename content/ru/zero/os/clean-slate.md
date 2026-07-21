---
title: С чистого листа (eMMC-ридер)
weight: 3
---

# Установка с чистого листа с eMMC-ридером

Самый чистый путь ОС: снять eMMC-модуль, прошить его офлайн в USB-ридере, запечь всё, что нужно первой загрузке, и включить настроенную машину. Это ровно та последовательность, которой (пере)собирали референсную машину — дважды — так что каждый шаг пережил контакт с реальностью.

Что нужно: eMMC-модуль в USB-ридере, Linux-машина или VM для офлайн-правок (macOS не может писать ext4 — см. заметку про офлайн-правки ниже), и MCU уже на mainline Katapult + Klipper (см. [Миграцию MCU]({{< relref "/zero/firmware/mcu-migration" >}})). Если MCU были на mainline раньше, они на нём и остаются — [слой 2 переживает слой 3]({{< relref "/concepts" >}}).

## 1. Прошей образ

Два варианта:

- **Sovobian (быстрее всего).** Возьми образ Sovol Zero из [lexfrei/sovobian](https://github.com/lexfrei/sovobian/releases) — upstream Armbian CB1 minimal с предустановленным eMMC-оверлеем 40 МГц. Сверь его с `SHA256SUMS` и запиши:

  ```bash
  xz --decompress --stdout Sovobian_*_Sovol-Zero_*.img.xz | sudo dd of=/dev/rdiskN bs=4m
  ```

- **Ванильный Armbian (с нуля).** Возьми стоковый Armbian CB1 и собери оверлей 40 МГц сам — полный рецепт (dts оверлея, `armbianEnv.txt`, разница с CB1) на [странице ванильного Armbian]({{< relref "armbian" >}}).

## 2. Пресиди rootfs офлайн

Смонтируй ext4 rootfs (раздел 2) на стороне Linux и запеки всё, что нужно первой загрузке:

- hostname + `/etc/hosts`
- SSH `authorized_keys` для root и твоего пользователя; пользователь с `sudo` (добавь `NOPASSWD` drop-in — некоторые инсталляторы гоняют `sudo` неинтерактивно и падают без него)
- netplan: WiFi с запиненным `key-management: "psk"` (драйвер `8189fs` не может завершить SAE на сетях WPA2/WPA3-transition), и `optional: true` на **обоих** — WiFi и Ethernet — иначе отсутствующий линк вешает загрузку на 90 с в `systemd-networkd-wait-online`
- CAN-обвязка хоста: `can`+`can_raw` в `/etc/modules-load.d/`, файл `systemd.network`, задающий 1 Mbit на `can*`, и udev-правило для `tx_queue_len` 128
- **заморозь ядро**: `chroot ... apt-mark hold linux-image-current-sunxi64 linux-dtb-current-sunxi64` — см. [почему]({{< relref "/zero/troubleshooting" >}}#armbian-kernel-branches-and-onboard-ethernet), и [страницу про обновляемую ОС]({{< relref "updatable" >}}) ради пути со снятием заморозки
- удали `/root/.not_logged_in_yet`, чтобы мастер первого логина никогда не запускался

Запиши rootfs обратно, загрузи плату, убедись, что она берёт DHCP и eMMC работает DDR52 на эффективных 37.5 МГц (см. [проверку клока]({{< relref "armbian" >}}#first-boot-verifying-the-emmc-clock)).

> [!NOTE]
> **Правка офлайн на macOS.** macOS не может смонтировать ext4 rootfs или FAT-раздел типа 0xEA. Используй `mtools` (`mcopy`/`mmd`) для boot-раздела и `debugfs` из Homebrew-овского `e2fsprogs` для rootfs, работая по образу на байтовых офсетах разделов из `fdisk`. Точные команды — на [странице ванильного Armbian]({{< relref "armbian" >}}#editing-the-image-offline).

## 3. Обнови пакеты

`apt-get update && apt-get full-upgrade` безопасен **только** с замороженным ядром (шаг 2). Без заморозки первый апгрейд заменяет ядро на месте и уносит с собой встроенный Ethernet.

## 4. Потом стек приклада

ОС готова. Переходи к слою приклада — установи [стек KIAUH]({{< relref "/zero/application/kiauh" >}}), нужные тебе [плагины]({{< relref "/zero/application/plugins" >}}), и [восстанови или переведи конфиг]({{< relref "/zero/application/klipper-config" >}}). Если хочешь весь упорядоченный путь от начала до конца, следуй [runbook-у с eMMC-ридером]({{< relref "/zero/runbooks/emmc-reader" >}}).
