"""Orquestación ADB con respuestas ficticias; no prueba un teléfono."""

import argparse
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools.validation.capture_f12_phone import capture, PACKAGE
from tools.validation.smoke_f12_prepared_payload import run as run_prepared_smoke


class PhoneCaptureProtocolTests(unittest.TestCase):
    def args(self, directory):
        return argparse.Namespace(adb="adb", serial="synthetic-serial", query_begin=1, query_end=2,
                                  local_date="2026-09-01", time_zone="America/Argentina/Buenos_Aires",
                                  output_dir=Path(directory) / "new-evidence")

    def test_device_selection_permission_and_failed_harness_are_not_hidden(self):
        for response, message in (("unauthorized", "no accesible"), ("offline", "no accesible")):
            with TemporaryDirectory() as directory, patch("tools.validation.capture_f12_phone.subprocess.run") as run:
                run.return_value = argparse.Namespace(returncode=0, stdout=response, stderr="")
                with self.assertRaisesRegex(RuntimeError, message):
                    capture(self.args(directory))
                self.assertFalse(self.args(directory).output_dir.exists())

    def test_emulator_refused_and_no_permission_mutation_issued(self):
        with TemporaryDirectory() as directory, patch("tools.validation.capture_f12_phone.subprocess.run") as run:
            run.side_effect = [argparse.Namespace(returncode=0, stdout="device", stderr=""),
                               argparse.Namespace(returncode=0, stdout="1", stderr="")]
            with self.assertRaisesRegex(RuntimeError, "fisico"):
                capture(self.args(directory))
            self.assertEqual(run.call_count, 2)

    def test_failed_instrumentation_retains_log_and_does_not_pull_fabricated_files(self):
        with TemporaryDirectory() as directory, patch("tools.validation.capture_f12_phone.subprocess.run") as run:
            def respond(argv, **kwargs):
                if "get-state" in argv: output = "device"
                elif "instrument" in argv: output = "FAILURES!!!\nINSTRUMENTATION_FAILED"
                else: output = ""
                return argparse.Namespace(returncode=0, stdout=output, stderr="")
            run.side_effect = respond
            args = self.args(directory)
            with self.assertRaisesRegex(RuntimeError, "no aprobo"):
                capture(args)
            self.assertTrue((args.output_dir / "instrumentation.log").is_file())
            self.assertFalse(any("pull" in call.args[0] for call in run.call_args_list))

    def test_failed_parity_still_recovers_exported_originals_when_marker_exists(self):
        with TemporaryDirectory() as directory, patch("tools.validation.capture_f12_phone.subprocess.run") as run:
            run_id = "00000000-0000-4000-8000-000000000001"
            remote = "/storage/emulated/0/Android/data/" + PACKAGE + "/files/f12-diagnostic"
            def respond(argv, **kwargs):
                if "get-state" in argv: output = "device"
                elif "instrument" in argv:
                    output = "F12_EXPORT_RUN=" + run_id + "\nF12_EXPORT_DIRECTORY=" + remote + "\nFAILURES!!!"
                elif "pull" in argv:
                    Path(argv[-1]).write_bytes(b"SYNTHETIC-NOT-AN-ANDROID-EXPORT")
                    output = ""
                else: output = ""
                return argparse.Namespace(returncode=0, stdout=output, stderr="")
            run.side_effect = respond
            args = self.args(directory)
            with self.assertRaisesRegex(RuntimeError, "originales recuperados"):
                capture(args)
            self.assertTrue((args.output_dir / "summary.json").is_file())
            self.assertTrue((args.output_dir / "events.jsonl").is_file())
            self.assertFalse((args.output_dir / "parity.json").exists())

    def test_prepared_smoke_refuses_external_backend_before_any_io(self):
        args = argparse.Namespace(base_url="https://backend.example.invalid", packet=Path("missing"),
                                  receipt_file=Path("missing"), phase="seed")
        with patch("tools.validation.smoke_f12_prepared_payload.request") as request:
            with self.assertRaisesRegex(RuntimeError, "127.0.0.1"):
                run_prepared_smoke(args)
            request.assert_not_called()

    def test_prepared_smoke_refuses_product_configuration(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "request.json").write_text("{}")
            args = argparse.Namespace(base_url="http://127.0.0.1:8769", packet=root,
                                      receipt_file=root / "receipt.json", phase="seed")
            health = {"capabilities": {"historical": {"state": "READY", "configuration_id": "product"}}}
            with patch("tools.validation.smoke_f12_prepared_payload.load_packet", return_value=({}, {}, {})), \
                    patch("tools.validation.smoke_f12_prepared_payload.os.environ", {"ANALYTICS_SERVICE_TOKEN": "test-only"}), \
                    patch("tools.validation.smoke_f12_prepared_payload.request", return_value=(200, health)) as request:
                with self.assertRaisesRegex(RuntimeError, "producto"):
                    run_prepared_smoke(args)
                self.assertEqual(request.call_count, 1)
