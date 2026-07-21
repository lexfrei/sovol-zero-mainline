---
title: Прошивка по SWD
weight: 2
---

# Прошивка по SWD через Flipper Zero (DAP Link)

Katapult тулхеда работает только по запросу и не восстанавливается по CAN, если приложение сломалось, так что SWD-пробник — это страховка. Подойдёт любой CMSIS-DAP-пробник — клон ST-Link V2 или Flipper Zero с приложением **DAP Link**.

> [!WARNING]
> **Проверенный охват.** Всё здесь тестировалось только на **тулхеде F103** и только с **Flipper Zero** (приложение DAP Link). ST-Link должен вести себя так же (это стандартный SWD), а раздел про H750 ниже — рассуждение, а не проверка. Правки и дополнения приветствуются — открой PR.

## Пробник (Flipper Zero)

- Используй приложение **DAP Link** — *не* «SWD Probe» (то только читает, прошивать не умеет). DAP Link представляется хосту как CMSIS-DAP-пробник (`Combined VCP and CMSIS-DAP Adapter`).
- GPIO DAP Link по умолчанию: SWC (SWCLK) = пин 10, SWD (SWDIO) = пин 12, GND = пин 11, 3V3 = пин 9. Сверься в приложении в *Config → Help and Pinout*.
- openocd рулит им через `adapter driver cmsis-dap` + `transport select swd`.

## Тулхед F103 — проверено

Таргет `stm32f1x`. Хедер: 4-пиновый `5V3 IO CK G` рядом с F103 (см. [распиновку тулхеда]({{< relref "/zero/hardware/toolhead" >}})). Отключи голову от принтера — 3.3 В с пробника питают MCU (синий светодиод подтверждает питание).

```bash
# sanity: read the chip (expect Cortex-M3, device id 0x...410)
openocd -c "adapter driver cmsis-dap" -c "transport select swd" -c "adapter speed 1000" \
  -f target/stm32f1x.cfg -c "init" -c "dap info" -c "shutdown"

# dump the factory firmware first (the only exact rollback for the toolhead)
openocd -c "adapter driver cmsis-dap" -c "transport select swd" -c "adapter speed 1000" \
  -f target/stm32f1x.cfg -c "init" -c "halt" \
  -c "dump_image factory.bin 0x08000000 0x10000" -c "shutdown"

# erase + write Katapult (0x08000000) + Klipper (0x08002000) + run
openocd -c "adapter driver cmsis-dap" -c "transport select swd" -c "adapter speed 1000" \
  -f target/stm32f1x.cfg -c "init" -c "reset halt" \
  -c "stm32f1x mass_erase 0" \
  -c "flash write_image katapult.bin 0x08000000" \
  -c "flash write_image klipper.bin 0x08002000" \
  -c "reset run" -c "shutdown"
```

Валидный дамп начинается с вменяемой таблицы векторов (начальный SP в RAM `0x2000xxxx`, reset-вектор во флеши `0x0800xxxx`), а не сплошными `0xFF`/`0x00`.

## Мейнборд H750 — тут не тестировалось

Таргет `stm32h7x`. SWD-пины — PA13 (SWDIO) / PA14 (SWCLK); хедер на мейнборде, добраться труднее, чем до тулхеда. SWD — это путь чтения / восстановления для H750, с одной оговоркой:

- Приложение Klipper лежит по `0x8020000` — за пределами 128 KiB внутренней флеши, в дополнительной (QSPI) флеши платы. openocd пишет внутреннюю флешь из коробки; для записи этого внешнего региона нужен настроенный драйвер внешней флеши, а это нетривиально. Внутренний регион (Katapult) можно писать по SWD, а приложение — без этой настройки нет.
- На практике H750 прошивают через **USB-Katapult** (см. [Миграцию MCU]({{< relref "mcu-migration" >}})), а не по SWD. Держи SWD на случай, когда приложение повреждено и в USB-Katapult уже не войти.
- Даже *замена* самого Katapult строго не требует SWD: Katapult **deployer** (собери из исходников — см. [Сборку прошивки]({{< relref "build" >}})), прошитый через стоковый загрузчик по USB, ставит mainline Katapult на место. SWD остаётся путём восстановления для уже повреждённого загрузчика.
- Для точного возврата к стоку откат — это **твой собственный SWD-дамп** (снятый до того, как ты что-то стёр). Если ты его не снял и застрял, [asnajder/zero-config](https://github.com/asnajder/zero-config) публикует прошиваемые через ST-LINK вендорские recovery-образы для мейнборда (включая его Katapult), тулхеда и MCU термокамеры — но это сторонние готовые бинарники непроверяемого происхождения, так что относись к ним как к аварийному запасному варианту, а не рутинному источнику.

Если ты прошивал H750 по SWD (с конфигом внешней флеши) или использовал ST-Link на любом из чипов — PR, уточняющий это, приветствуется.
