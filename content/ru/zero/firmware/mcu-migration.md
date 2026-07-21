---
title: Миграция MCU
weight: 3
---

# Миграция MCU — оба MCU на mainline

Чистый способ полностью перевести оба MCU на upstream Klipper — приложение *и* загрузчик, ни одного вендорского байта в прошивке. Собери всё из **одного и того же коммита Klipper `master`** (см. [почему master]({{< relref "/concepts" >}})). Порядок такой: собрать все четыре образа, прошить тулхед один раз по SWD, потом мейнборд через USB-Katapult.

## Что нужно

- **SWD-программатор** — ST-Link V2 (клон за ~$3) или Flipper Zero с приложением DAP Link. Нужен один раз, чтобы забутстрапить тулхед: вендорский Katapult работает только по запросу и не восстанавливается по CAN, так что ты первый раз прошиваешь CAN-совместимый mainline Katapult на тулхед по SWD и больше голову не вскрываешь.
- **ARM-тулчейн** — `arm-none-eabi-gcc` (уже на хосте принтера) или `brew install --cask gcc-arm-embedded` на macOS. См. [Сборку прошивки]({{< relref "build" >}}).
- `openocd` ≥ 0.11 для прошивки по SWD.
- SSH-доступ к принтеру.

## Сначала забэкапь

Прежде чем что-то стирать, сними откат — особенно SWD-дамп тулхеда. Полный чеклист бэкапов (вендорский стек, SWD-дамп, образ eMMC) — на [странице восстановления]({{< relref "/zero/os/recovery" >}}). Тот, что важнее всего здесь:

```bash
openocd -c "adapter driver cmsis-dap" -c "transport select swd" -c "adapter speed 1000" \
  -f target/stm32f1x.cfg -c "init" -c "halt" \
  -c "dump_image vendor-f103-FULL-flash.bin 0x08000000 0x10000" -c "shutdown"
```

Валидный дамп открывается вменяемой таблицей векторов (начальный SP в RAM `0x2000xxxx`, reset-вектор во флеши `0x0800xxxx`), а не сплошными `0xFF`/`0x00`. SWD-хедер мейнборда закопан, так что его откат-из-исходников — это вендор-эквивалентная прошивка, скомпилированная из твоего забэкапленного вендорского `~/klipper` под тем же офсетом `0x8020000` (прошиваемая через USB-Katapult).

## Этап 1 — Собери прошивку (из `master`)

Полные заметки по тулчейну, таблица офсетов, имена выводов по образам и проверка reset-вектора — на [Сборке прошивки]({{< relref "build" >}}). Собираешь четыре образа, все из одного коммита `master`:

| Образ | Таргет | Офсет | Как прошивается |
| --- | --- | --- | --- |
| Katapult тулхеда | F103, **CANSERIAL** | `0x8000000` | SWD (один раз) |
| Klipper тулхеда | F103 | `0x8002000` | SWD (один раз), потом CAN |
| Katapult deployer мейнборда | **`MACH_STM32H743`** | `0x8020000` | USB-Katapult |
| Klipper мейнборда | **`MACH_STM32H743`** | `0x8020000` | USB-Katapult |

Две вещи делают это чисто:

- **Собери мейнборд как `MACH_STM32H743`,** а не H750. На текущем master оба таргета достают офсет `0x8020000` без патча, но H750 по умолчанию берёт 480 МГц, а H743 — **400 МГц**, клок, на котором этот мейнборд валидирован.
- **Собери Katapult тулхеда `CANSERIAL`,** взяв затравку `.config` из вендорского `.config103` (голая затравка выставляет `olddefconfig` в USB, что молчало бы на CAN-шине). CAN-совместимый Katapult — это то, что позволяет каждое будущее обновление тулхеда прошивать по CAN без вскрытия головы.

Katapult **deployer** мейнборда (`BUILD_DEPLOYER=y`, включается автоматически, когда офсет приложения отличается от офсета загрузчика) — это то, что ставит mainline Katapult по USB без SWD. **Прогони каждый образ через проверку reset-вектора** перед прошивкой: байты 4–7 (little-endian) должны попадать в офсет приложения (`0x08002xxx` для F103, `0x0802xxxx` для мейнборда). Вектор `0x08000xxx` означает, что собрано под неверный офсет и окирпичит чип — пересобирай.

## Этап 2 — Прошей тулхед, один раз, по SWD

Это единственный раз, когда ты вскрываешь голову. Он пишет CAN-совместимый mainline Katapult и приложение Klipper; после этого тулхед прошивается по CAN навсегда. Хедер и разводка пробника — на [распиновке тулхеда]({{< relref "/zero/hardware/toolhead" >}}) и [странице прошивки]({{< relref "flashing" >}}). Отключи голову; 3.3 В с пробника питают MCU.

```bash
# sanity: read the chip (expect Cortex-M3, device id 0x...410)
openocd -c "adapter driver cmsis-dap" -c "transport select swd" -c "adapter speed 1000" \
  -f target/stm32f1x.cfg -c "init" -c "dap info" -c "shutdown"

# erase + write CANSERIAL Katapult (0x08000000) + Klipper (0x08002000) + run
openocd -c "adapter driver cmsis-dap" -c "transport select swd" -c "adapter speed 1000" \
  -f target/stm32f1x.cfg -c "init" -c "reset halt" \
  -c "stm32f1x mass_erase 0" \
  -c "flash write_image katapult-f103.bin 0x08000000" \
  -c "flash write_image klipper-f103.bin 0x08002000" \
  -c "reset run" -c "shutdown"
```

Собери голову обратно, подключи её CAN, включи питание. Тулхед теперь отвечает на **новом аппаратном UUID** (mainline читает реальный UID вместо вендорского фейкового `61755fe321ac`):

```bash
python3 ~/katapult/scripts/flashtool.py -i can0 -q     # note the new UUID
```

## Этап 3 — Прошей мейнборд, через USB-Katapult, без SWD

Мейнборд — это USB-CAN мост, так что он достижим по USB, даже несмотря на закопанный SWD-хедер. Замени и его загрузчик (через deployer), и его приложение. (`flashtool.py` — это `~/katapult/scripts/flashtool.py`; запускай из той директории или положи его в `PATH`.)

```bash
# 1) request the bridge into its (stock) Katapult — it re-enumerates as a USB serial device
flashtool.py -i can0 -u <mainboard-uuid> -r        # stock vendor Katapult appears under /dev/serial/by-id/ as usb-katapult_stm32h750xx-*

# 2) install mainline Katapult by flashing the deployer through the stock bootloader
flashtool.py -d /dev/serial/by-id/usb-katapult_stm32h750xx-* -f deployer-mainboard.bin   # re-enumerates h750xx → h743xx = success

# 3) flash the Klipper app through the freshly-installed mainline Katapult
flashtool.py -d /dev/serial/by-id/usb-katapult_stm32h743xx-* -f klipper-mainboard.bin   # via the new mainline (H743) Katapult
```

USB-id отражает таргет MCU, под который собран *загрузчик*, так что смена `h750xx` (стоковый вендорский Katapult) на `h743xx` подтверждает, что теперь рулит mainline (H743) Katapult — эта переэнумерация и есть твой сигнал «поехали» между шагами 2 и 3. USB моста переэнумерируется во время этих шагов (вывод SSH/прошивки может пропасть, запись всё равно завершится). **Не трогай питание или USB посреди записи** — чистая прошивка восстанавливается через Katapult, но прерванная запись, которая повредит сам Katapult, — единственный случай, вынуждающий лезть SWD в закопанный мейнборд. После загрузки мейнборд тоже поднимается на **новом реальном UUID** (фейкового `0d1445047cdd` больше нет); `flashtool.py -i can0 -q`, чтобы его прочитать.

Если ты вообще не хочешь бутстрапить тулхед по SWD, тот же трюк с deployer в принципе может пойти по CAN через *работающее* вендорское приложение тулхеда — но у тулхеда нет USB и нет CAN-восстановления, если эта прошивка повредится, так что SWD-один-раз (Этап 2) — безопасный путь.

## Дальше

Когда оба MCU на mainline и их новые UUID записаны, переходи к слою приклада: наведи хост на тот же `master`, переведи конфиг и откалибруй. См. [Конфиг Klipper]({{< relref "/zero/application/klipper-config" >}}) и [калибровку]({{< relref "/zero/application/calibration" >}}).
