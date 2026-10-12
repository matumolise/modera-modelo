"""Reserva exclusiva del escritor; el archivo de reserva nunca se elimina."""

import errno
import os
import time


def _acquire_windows(stream, msvcrt, timeout=2.0):
    """La liberación por terminación puede demorarse; nunca sustituir la reserva.

    Cada intento pide al sistema operativo el mismo byte. Un escritor vivo
    conserva la exclusión y el arranque falla al vencer el plazo técnico.
    """
    deadline = time.monotonic() + timeout
    while True:
        stream.seek(0)
        try:
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            return
        except OSError as exc:
            if exc.errno not in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                raise
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise
            time.sleep(min(0.025, remaining))


class WriterLease:
    def __init__(self, path):
        self._stream = None
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        # msvcrt opera sobre el descriptor: seek debe mover su posición real.
        stream = path.open("a+b", buffering=0)
        try:
            if os.name == "nt":
                import msvcrt
                if os.fstat(stream.fileno()).st_size == 0:
                    stream.write(b"\0")
                    stream.flush()
                _acquire_windows(stream, msvcrt)
            elif os.name == "posix":
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            else:
                raise RuntimeError("Plataforma sin reserva de escritor implementada")
        except BaseException:
            stream.close()
            raise
        self._stream = stream

    def valid(self):
        if self._stream is None:
            return False
        try:
            opened = os.fstat(self._stream.fileno())
            current = self.path.stat()
            return (opened.st_dev, opened.st_ino) == (current.st_dev, current.st_ino)
        except OSError:
            return False

    def close(self):
        stream, self._stream = self._stream, None
        if stream is None:
            return
        try:
            if os.name == "nt":
                import msvcrt
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        finally:
            stream.close()
