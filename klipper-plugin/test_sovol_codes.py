#!/usr/bin/env python3
# Tests for the sovol_codes Klipper plugin.
#
# The mapping from a Klipper status/error string to the numeric code Sovol's
# knob screen shows is a pure function (lookup_code) pinned here against the
# official "SOVOL ZERO Screen code list". The runtime glue (output handler,
# shutdown event, deferred M117) is covered with small fakes standing in for
# the Klipper objects, so no live printer is needed.
#
# Pure stdlib (unittest); runs under any Python 3 with no Klipper present.
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sovol_codes import SovolCodes, load_config, lookup_code  # noqa: E402


class TestPromptCodes(unittest.TestCase):
    def test_no_trigger_passes_endstop_name_verbatim(self):
        # Upstream emits the SHORT name (get_name(short=True) strips "stepper_"),
        # so the real string is "No trigger on x ...", shown as "101 x".
        self.assertEqual(
            lookup_code("No trigger on x after full movement"), "101 x")
        self.assertEqual(
            lookup_code("No trigger on z after full movement"), "101 z")

    def test_axis_name_is_not_transformed(self):
        # A custom rail name must be shown as-is, mirroring the vendor's
        # `M117 Tip code: 101 {name}` — no stripping, no lowercasing.
        self.assertEqual(
            lookup_code("No trigger on my_rail after full movement"),
            "101 my_rail")

    def test_endstop_still_triggered_carries_name(self):
        self.assertEqual(
            lookup_code("Endstop y still triggered after retract"), "103 y")

    def test_probe_triggered_prior_to_movement(self):
        self.assertEqual(
            lookup_code("Probe triggered prior to movement"), "102")

    def test_must_home_axis_first_has_no_recoverable_axis(self):
        # move_error() wraps it as "Must home axis first: <coords>"; the axis
        # letter is gone before the string exists, so only "104" is recoverable.
        self.assertEqual(
            lookup_code("Must home axis first: 1.000 2.000 3.000 [4.000]"),
            "104")

    def test_move_out_of_range_has_no_recoverable_axis(self):
        # Same: coordinates only, never an axis letter. Bare "105".
        self.assertEqual(
            lookup_code("Move out of range: 200.0 0.0 0.0 [0.0]"), "105")

    def test_extrude_below_minimum_temp(self):
        self.assertEqual(lookup_code("Extrude below minimum temp"), "106")

    def test_eddy_current_family(self):
        self.assertEqual(lookup_code("Invalid ldc1612 id"), "114")
        self.assertEqual(
            lookup_code("Must calibrate probe_eddy_current first"), "118")
        self.assertEqual(
            lookup_code("Failed calibration - incomplete sensor data"), "116")

    def test_chamber_and_exhaust_fan_exceptions(self):
        self.assertEqual(lookup_code("Exception in chamber_fan"), "110")
        self.assertEqual(lookup_code("Exception in exhaust_fan"), "125")

    def test_codes_112_113_are_not_matched(self):
        # Deliberately omitted — those LDC1612 I2C strings do not exist in the
        # Klipper Python tree, so there is no host-side string to anchor.
        self.assertIsNone(lookup_code("LDC1612 I2C bus busy or timeout error"))
        self.assertIsNone(lookup_code("LDC1612 I2C bus error"))


class TestVendorOnlyStrings(unittest.TestCase):
    # These anchors exist only in the Sovol vendor source (custom fan.py,
    # vendor probe_eddy_current strings, vendor z_offset add-on). Pinned to the
    # REAL emitted wording, not the PDF's screen text.
    def test_109_uses_real_vendor_wording_not_pdf_text(self):
        # PDF screen text is "Pressure probe more than five times"; the vendor
        # add-on actually raises "Toolhead probe more than ten times".
        self.assertEqual(
            lookup_code("ZoffsetCalibration: Toolhead probe more than ten times."),
            "109")
        self.assertIsNone(lookup_code("Pressure probe more than five times"))

    def test_vendor_fan_exceptions(self):
        self.assertEqual(lookup_code("Exception in chamber_fan"), "110")
        self.assertEqual(lookup_code("Exception in exhaust_fan"), "125")
        self.assertEqual(lookup_code("Exception in Hotend_fan"), "73")

    def test_vendor_eddy_strings(self):
        self.assertEqual(
            lookup_code("Failed calibration - frequency not increasing each step"),
            "117")
        self.assertEqual(lookup_code("Eddy current sensor error"), "123")


class TestShutdownCodes(unittest.TestCase):
    def test_lost_communication(self):
        self.assertEqual(lookup_code("Lost communication with MCU"), "60")

    def test_heater_not_heating(self):
        self.assertEqual(
            lookup_code("Heater extruder not heating at expected rate"), "63")
        self.assertEqual(
            lookup_code("Heater heater_bed not heating at expected rate"), "64")

    def test_tmc_reports_error_per_stepper(self):
        self.assertEqual(lookup_code("TMC 'stepper_x' reports error"), "65")
        self.assertEqual(lookup_code("TMC 'stepper_y' reports error"), "66")
        self.assertEqual(lookup_code("TMC 'extruder' reports error"), "68")

    def test_tmc_spi_write_per_stepper(self):
        # PDF prints both 71 and 72 as stepper_x (vendor typo); 72 is stepper_y.
        self.assertEqual(
            lookup_code("Unable to write tmc spi 'stepper_x' register"), "71")
        self.assertEqual(
            lookup_code("Unable to write tmc spi 'stepper_y' register"), "72")


class TestMatchingRobustness(unittest.TestCase):
    def test_prefixed_error_line_still_matches(self):
        # Klipper prefixes errors with "!! " and info with "// " — substring
        # matching must see through both.
        self.assertEqual(
            lookup_code("!! Move out of range: 200.0 0.0 0.0 [0.0]"), "105")
        self.assertEqual(
            lookup_code("// Lost communication with MCU"), "60")

    def test_specific_wins_over_generic(self):
        # "Move queue overflow" (69) must not be shadowed by "Move out of
        # range" (105) — different strings, but pin it.
        self.assertEqual(lookup_code("Move queue overflow"), "69")

    def test_our_own_m117_echo_matches_nothing(self):
        # Pin the no-loop invariant at the mapping level: our emitted line and a
        # prefixed echo of it map to no code.
        self.assertIsNone(lookup_code("M117 Tip code: 101 x"))
        self.assertIsNone(lookup_code("// Tip code: 60"))

    def test_unknown_message_returns_none(self):
        self.assertIsNone(lookup_code("Some message Sovol never enumerated"))
        self.assertIsNone(lookup_code(""))
        self.assertIsNone(lookup_code(None))


# --- Runtime glue, exercised with fakes (no Klipper required) ---

class FakeReactor:
    def __init__(self):
        self.callbacks = []

    def register_callback(self, cb):
        self.callbacks.append(cb)

    def run_pending(self):
        for cb in list(self.callbacks):
            cb(0.)
        self.callbacks = []


class FakeGCode:
    # Models the relevant slice of Klipper's gcode dispatch: M117 is only in
    # the ready handler set, so once the printer is not ready, routing "M117 …"
    # through run_script hits cmd_default's not-ready branch and raises (just
    # like the real gcode.py:292). This is what makes the post-shutdown bug
    # reproducible in tests rather than papered over by a permissive fake.
    def __init__(self):
        self.output_handlers = []
        self.commands = {}
        self.scripts = []
        self.is_printer_ready = True

    def register_output_handler(self, cb):
        self.output_handlers.append(cb)

    def register_command(self, name, cb, desc=None):
        self.commands[name] = cb

    def run_script(self, script):
        if not self.is_printer_ready and script.startswith("M117"):
            raise RuntimeError(
                "cmd_default: printer is not ready (M117 not in base handlers)")
        self.scripts.append(script)


class FakeDisplayStatus:
    def __init__(self):
        self.message = None


class FakeGCmd:
    def __init__(self):
        self.responses = []

    def respond_info(self, msg):
        self.responses.append(msg)


_SENTINEL = object()


class FakePrinter:
    def __init__(self, state_message="Ready", with_display=True):
        self.reactor = FakeReactor()
        self.gcode = FakeGCode()
        self.display_status = FakeDisplayStatus() if with_display else None
        self.event_handlers = {}
        self._state_message = state_message

    def get_reactor(self):
        return self.reactor

    def lookup_object(self, name, default=_SENTINEL):
        if name == "gcode":
            return self.gcode
        if name == "display_status":
            if self.display_status is not None:
                return self.display_status
            if default is not _SENTINEL:
                return default
            raise KeyError(name)
        raise KeyError(name)

    def register_event_handler(self, event, cb):
        self.event_handlers[event] = cb

    def get_state_message(self):
        return (self._state_message, "shutdown")


class FakeConfig:
    def __init__(self, printer, enable=True):
        self._printer = printer
        self._enable = enable

    def get_printer(self):
        return self._printer

    def getboolean(self, name, default):
        assert name == "enable"
        return self._enable


class TestRuntimeGlue(unittest.TestCase):
    def _make(self, enable=True, state_message="Ready", with_display=True):
        printer = FakePrinter(
            state_message=state_message, with_display=with_display)
        obj = load_config(FakeConfig(printer, enable=enable))
        return printer, obj

    def test_load_config_returns_plugin_and_registers_command(self):
        printer, obj = self._make()
        self.assertIsInstance(obj, SovolCodes)
        self.assertIn("SOVOL_LAST_CODE", printer.gcode.commands)

    def test_enabled_registers_hooks_on_real_stock_event(self):
        printer, _obj = self._make(enable=True)
        self.assertEqual(len(printer.gcode.output_handlers), 1)
        # The stock-upstream shutdown event is "klippy:shutdown" (invoke_shutdown
        # calls its handlers directly). Pin it so a wrong/vendor-only name fails.
        self.assertIn("klippy:shutdown", printer.event_handlers)
        # Vendor fork compatibility is also registered.
        self.assertIn("klippy:notify_mcu_shutdown", printer.event_handlers)

    def test_disabled_registers_no_hooks(self):
        printer, _obj = self._make(enable=False)
        self.assertEqual(printer.gcode.output_handlers, [])
        self.assertNotIn("klippy:shutdown", printer.event_handlers)
        self.assertNotIn("klippy:notify_mcu_shutdown", printer.event_handlers)

    def test_matched_output_sets_display_message(self):
        printer, obj = self._make()
        handler = printer.gcode.output_handlers[0]
        handler("!! Move out of range: 200.0 0.0 0.0 [0.0]")
        # Emitted via display_status.message directly — no gcode dispatch.
        self.assertEqual(printer.display_status.message, "Tip code: 105")
        self.assertEqual(printer.gcode.scripts, [])
        self.assertEqual(obj.last_code, "105")

    def test_unmatched_output_emits_nothing(self):
        printer, obj = self._make()
        printer.gcode.output_handlers[0]("// echoing some chatter")
        self.assertIsNone(printer.display_status.message)
        self.assertIsNone(obj.last_code)

    def test_own_m117_echo_does_not_loop(self):
        printer, obj = self._make()
        printer.gcode.output_handlers[0]("M117 Tip code: 105")
        self.assertIsNone(printer.display_status.message)
        self.assertIsNone(obj.last_code)

    def test_shutdown_code_displays_without_raising_when_not_ready(self):
        # Regression for the post-shutdown path: after a shutdown the printer is
        # not ready and M117 is gone from the active handlers, so routing M117
        # through gcode would raise. The plugin must still surface the code.
        printer, obj = self._make(
            state_message="Lost communication with MCU\nOnce the underlying...")
        printer.gcode.is_printer_ready = False  # post-shutdown reality
        printer.event_handlers["klippy:shutdown"]()  # stock fires with no args
        printer.reactor.run_pending()
        self.assertEqual(printer.display_status.message, "Tip code: 60")
        self.assertEqual(printer.gcode.scripts, [])  # no M117 routed through gcode
        self.assertEqual(obj.last_code, "60")

    def test_vendor_shutdown_event_signature_is_absorbed(self):
        # Vendor fork fires klippy:notify_mcu_shutdown with (msg, details);
        # the *args handler must accept it without error.
        printer, obj = self._make(state_message="ADC out of range")
        printer.gcode.is_printer_ready = False
        printer.event_handlers["klippy:notify_mcu_shutdown"](
            "ADC out of range", {"error": "x"})
        printer.reactor.run_pending()
        self.assertEqual(printer.display_status.message, "Tip code: 62")
        self.assertEqual(obj.last_code, "62")

    def test_fallback_to_deferred_m117_without_display_status(self):
        # With no display_status configured, the prompt-code path falls back to
        # a deferred M117 (works while ready).
        printer, obj = self._make(with_display=False)
        printer.gcode.output_handlers[0](
            "!! Move out of range: 200.0 0.0 0.0 [0.0]")
        self.assertEqual(printer.gcode.scripts, [])  # deferred, not inline
        printer.reactor.run_pending()
        self.assertEqual(printer.gcode.scripts, ["M117 Tip code: 105"])
        self.assertEqual(obj.last_code, "105")

    def test_last_code_command_reports_state(self):
        printer, obj = self._make()
        cmd = printer.gcode.commands["SOVOL_LAST_CODE"]
        g1 = FakeGCmd()
        cmd(g1)
        self.assertIn("No Sovol screen code", g1.responses[0])
        obj.last_code = "101 x"
        g2 = FakeGCmd()
        cmd(g2)
        self.assertIn("101 x", g2.responses[0])

    def test_last_code_command_reports_disabled(self):
        printer, _obj = self._make(enable=False)
        g = FakeGCmd()
        printer.gcode.commands["SOVOL_LAST_CODE"](g)
        self.assertIn("disabled", g.responses[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
