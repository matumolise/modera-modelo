"""Reintento técnico Windows simulado y reserva real POSIX/Windows."""

import errno
import io
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from analytics_service.writer_lease import WriterLease, _acquire_windows
from tools.validation.validate_historical_candidate_windows import pinned_requirements


class WriterRecoveryTests(unittest.TestCase):
    def test_delayed_release_requires_successful_native_lock(self):
        with TemporaryDirectory() as directory:
            with (Path(directory) / "lock").open("a+b", buffering=0) as stream:
                stream.write(b"\0")
                positions = []

                def locking(fd, mode, size):
                    import os
                    positions.append(os.lseek(fd, 0, os.SEEK_CUR))
                    if len(positions) < 3:
                        raise PermissionError(errno.EACCES, "still locked")

                native = SimpleNamespace(locking=Mock(side_effect=locking), LK_NBLCK=2)
                with patch("analytics_service.writer_lease.time.monotonic", side_effect=[0, .01, .02]), \
                        patch("analytics_service.writer_lease.time.sleep") as pause:
                    _acquire_windows(stream, native)
                self.assertEqual(positions, [0, 0, 0])
                self.assertEqual(pause.call_count, 2)
                self.assertEqual(native.locking.call_count, 3)

    def test_live_writer_is_never_bypassed(self):
        native = SimpleNamespace(locking=Mock(side_effect=PermissionError(errno.EACCES, "locked")), LK_NBLCK=2)
        stream = Mock()
        with patch("analytics_service.writer_lease.time.monotonic", side_effect=[0, .01, 2.01]), \
                patch("analytics_service.writer_lease.time.sleep") as pause:
            with self.assertRaises(PermissionError):
                _acquire_windows(stream, native)
        self.assertEqual(native.locking.call_count, 2)
        self.assertEqual(pause.call_count, 1)

    def test_non_contention_error_is_not_retried(self):
        native = SimpleNamespace(locking=Mock(side_effect=OSError(errno.EBADF, "invalid fd")), LK_NBLCK=2)
        with patch("analytics_service.writer_lease.time.sleep") as pause:
            with self.assertRaises(OSError) as caught:
                _acquire_windows(Mock(), native)
        self.assertEqual(caught.exception.errno, errno.EBADF)
        pause.assert_not_called()

    def test_native_descriptor_is_unbuffered_and_close_is_idempotent(self):
        with TemporaryDirectory() as directory:
            lease = WriterLease(Path(directory) / "lock")
            try:
                self.assertIsInstance(lease._stream, io.FileIO)
                self.assertTrue(lease.valid())
                with self.assertRaises(OSError):
                    WriterLease(lease.path)
            finally:
                lease.close()
                lease.close()
            replacement = WriterLease(lease.path)
            replacement.close()

    def test_environment_pins_include_recursive_files_and_bom(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "base.txt").write_text("a==1.2\n", encoding="utf-8")
            (root / "test.txt").write_text("-r base.txt\n# comment\nb==3\n", encoding="utf-8-sig")
            self.assertEqual(pinned_requirements(root / "test.txt"), {"a": "1.2", "b": "3"})

    def test_environment_conflicting_pins_are_rejected(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "base.txt").write_text("a==1\n", encoding="utf-8")
            (root / "test.txt").write_text("-r base.txt\na==2\n", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                pinned_requirements(root / "test.txt")


if __name__ == "__main__":
    unittest.main()
