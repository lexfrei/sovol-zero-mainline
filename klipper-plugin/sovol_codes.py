# Sovol Zero knob-screen prompt/error codes as an opt-in Klipper plugin.
#
# Sovol's vendor firmware shows numeric codes (101, 103, 60+, ...) on the knob
# screen by editing upstream core files in place — injecting `M117 Tip code: N`
# into klippy/extras/homing.py and growing a message->code table in
# klippy/klippy.py. That couples product UI to the core and blocks tracking
# upstream Klipper.
#
# The same behaviour needs no core edits. Klipper already exposes the hooks:
#   - gcode.register_output_handler(cb): cb sees every message Klipper emits,
#     so the descriptive text ("No trigger on stepper_x after full movement")
#     can be mapped to a code without touching the code path that produced it.
#   - register_event_handler("klippy:notify_mcu_shutdown", ...): fires on every
#     shutdown; printer.get_state_message() yields the reason text.
#
# Drop this file in klippy/extras/ on a STOCK Klipper checkout and enable it
# with `[sovol_codes]` in printer.cfg. Stock Klipper + this plugin == the
# vendor screen codes, minus the fork.
#
# The message->code table is the official "SOVOL ZERO Screen code list".
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import logging
import re

# Prompt codes whose text embeds an endstop name (Klipper's %s). Upstream
# already emits the SHORT name: MCU_stepper.get_name(short=True) returns
# self._name[8:] for a "stepper_x" rail, so homing.py emits
# "No trigger on x after full movement", not "... on stepper_x ...". The screen
# shows that name verbatim — the vendor patch does `M117 Tip code: 101 {name}`,
# so we pass the captured group through unchanged rather than re-deriving an
# axis letter (a custom rail name is shown as-is, exactly like the vendor).
_AXIS_RULES = [
    (re.compile(r"No trigger on (\S+) after full movement"), "101"),
    (re.compile(r"Endstop (\S+) still triggered after retract"), "103"),
]

# Plain message->code rules, matched as substrings (Klipper often appends
# detail or a "!! " / "// " prefix to the canonical text). Ordered so that a
# more specific anchor is tried before any looser one that could shadow it.
#
# Strings were verified against stock upstream Klipper (Klipper3d/klipper) AND
# the Sovol vendor source on the printer. Rules are grouped by origin so it is
# explicit which codes fire on a plain upstream checkout and which need a
# vendor-specific message — see README "Fidelity limits".

# Codes whose anchor string exists in STOCK upstream Klipper — these fire on a
# plain Klipper3d/klipper checkout.
_STOCK_TEXT_RULES = [
    ("Probe triggered prior to movement", "102"),
    # 104/105 are per-axis on the screen (104 x/y/z, 105 x/y/z) but the upstream
    # messages carry only coordinates: move_error() wraps the static string as
    # "Must home axis first: <x> <y> <z> [<e>]" — the axis index is gone before
    # the string exists, so only the bare code is recoverable here. See README.
    ("Must home axis first", "104"),
    ("Move out of range", "105"),
    ("Extrude below minimum temp", "106"),
    ("Extrude only move too long", "107"),
    ("Move exceeds maximum extrusion", "108"),
    ("Invalid lis2dw id", "111"),
    # Codes 112/113 (LDC1612 I2C bus busy/error) are intentionally omitted: no
    # such host-side string exists in either stock or vendor Klipper. The
    # LDC1612 reports faults as numeric enumerations from the MCU, not as a
    # stable text reason, so there is nothing reliable to anchor. (Note: many
    # other MCU faults DO arrive as verbatim text — e.g. 62/69/70 below — so
    # the omission is specific to LDC1612, not a general C-layer limitation.)
    ("Invalid ldc1612 id", "114"),
    ("Invalid probe_eddy_current height", "115"),
    ("Failed calibration - incomplete sensor data", "116"),
    ("Must calibrate probe_eddy_current first", "118"),
    ("probe_eddy_current sensor outage", "119"),
    ("Unable to obtain probe_eddy_current sensor readings", "120"),
    ("probe_eddy_current sensor not in valid range", "121"),
    ("Communication timeout during homing", "122"),
    ("Must home before probe", "124"),
    # --- shutdown reasons; these arrive verbatim from the MCU/host (60+) ---
    ("Lost communication with MCU", "60"),
    ("Shutdown due to webhooks request", "61"),
    ("ADC out of range", "62"),
    ("Heater extruder not heating at expected rate", "63"),
    ("Heater heater_bed not heating at expected rate", "64"),
    ("TMC 'stepper_x' reports error", "65"),
    ("TMC 'stepper_y' reports error", "66"),
    ("TMC 'stepper_z' reports error", "67"),
    ("TMC 'extruder' reports error", "68"),
    ("Move queue overflow", "69"),
    ("Missed scheduling of next digital out event", "70"),
    ("Unable to write tmc spi 'stepper_x' register", "71"),
    # PDF lists 71 AND 72 both as "...stepper_x..." (a vendor copy-paste typo);
    # the klippy.py vendor patch distinguishes x/y, so 72 is the stepper_y case.
    ("Unable to write tmc spi 'stepper_y' register", "72"),
]

# Codes whose anchor string exists ONLY in the Sovol vendor source (custom
# fan.py shutdowns, vendor probe_eddy_current strings, and the vendor-only
# z_offset_calibration add-on). These never fire on a plain upstream checkout;
# they are kept so the plugin is faithful on the vendor/community firmware that
# actually emits them. 109's PDF text ("Pressure probe more than five times")
# does not match the real wording — the vendor add-on raises "Toolhead probe
# more than ten times", so the real string is anchored here.
_VENDOR_TEXT_RULES = [
    ("Toolhead probe more than", "109"),
    ("Exception in chamber_fan", "110"),
    ("Failed calibration - frequency not increasing", "117"),
    ("Eddy current sensor error", "123"),
    ("Exception in exhaust_fan", "125"),
    ("Exception in Hotend_fan", "73"),
]

_TEXT_RULES = _STOCK_TEXT_RULES + _VENDOR_TEXT_RULES


def lookup_code(message):
    """Map a Klipper status/error string to its Sovol screen code.

    Returns the code as a string (e.g. "101 x" or "60"), or None when the
    message is not one Sovol enumerated. Pure function — no Klipper runtime.

    For the axis-bearing prompts (101/103) the captured name is passed through
    verbatim — upstream already emits the short form and the vendor screen shows
    it unchanged. Codes 104/105 yield only the bare code (the axis letter is not
    present in the upstream message; see _TEXT_RULES).
    """
    if not message:
        return None
    for regex, code in _AXIS_RULES:
        match = regex.search(message)
        if match:
            return "%s %s" % (code, match.group(1))
    for text, code in _TEXT_RULES:
        if text in message:
            return code
    return None


class SovolCodes:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.reactor = self.printer.get_reactor()
        self.gcode = self.printer.lookup_object('gcode')
        self.enabled = config.getboolean('enable', True)
        self.last_code = None
        if self.enabled:
            self.gcode.register_output_handler(self._on_output)
            # Stock upstream broadcasts a shutdown by calling the
            # "klippy:shutdown" handlers directly from invoke_shutdown (after
            # _set_state, so get_state_message() already holds the reason).
            # The Sovol vendor fork instead sends "klippy:notify_mcu_shutdown"
            # with (msg, details). Register both so the plugin works on stock
            # Klipper and on the vendor firmware; the handler takes *args to
            # absorb the differing signatures.
            for event in ("klippy:shutdown", "klippy:notify_mcu_shutdown"):
                self.printer.register_event_handler(event, self._on_shutdown)
        self.gcode.register_command(
            "SOVOL_LAST_CODE", self.cmd_SOVOL_LAST_CODE,
            desc="Report the last matched Sovol knob-screen code")

    def _emit(self, code):
        if code is None:
            return
        self.last_code = code
        logging.info("sovol_codes: matched screen code %s", code)
        text = "Tip code: %s" % (code,)
        # Set the display message field directly — the same field M117 writes
        # (display_status.cmd_M117 just does `self.message = msg`). This is
        # essential for the shutdown codes (60+): after a shutdown M117 lives
        # only in ready_gcode_handlers, so routing "M117 ..." through gcode
        # would hit cmd_default's not-ready branch and raise instead of
        # displaying. Writing the attribute bypasses gcode dispatch, works in
        # both ready and shutdown states, and never takes the gcode mutex (so
        # no reactor deferral is needed even from inside the output callback).
        display_status = self.printer.lookup_object('display_status', None)
        if display_status is not None:
            display_status.message = text
            return
        # No display_status configured (unusual). Fall back to a deferred M117,
        # which reaches the screen on the prompt-code path (printer ready) but
        # is skipped post-shutdown. Defer so we never run gcode under the mutex
        # held during the output callback.
        self.reactor.register_callback(
            lambda eventtime: self.gcode.run_script("M117 " + text))

    def _on_output(self, msg):
        # Our own "M117 Tip code: N" feeds back through here. It matches no rule
        # today, but guard explicitly so a future rule can never make us recurse.
        if not msg or msg.startswith("M117") or "Tip code:" in msg:
            return
        self._emit(lookup_code(msg))

    def _on_shutdown(self, *args):
        # Fired by klippy:shutdown (no args) or klippy:notify_mcu_shutdown
        # (msg, details). Either way the reason is in the printer state.
        state_message, _state = self.printer.get_state_message()
        self._emit(lookup_code(state_message))

    def cmd_SOVOL_LAST_CODE(self, gcmd):
        if not self.enabled:
            gcmd.respond_info("sovol_codes is disabled (enable: False)")
        elif self.last_code is None:
            gcmd.respond_info("No Sovol screen code matched yet")
        else:
            gcmd.respond_info("Last Sovol screen code: %s" % (self.last_code,))


def load_config(config):
    return SovolCodes(config)
