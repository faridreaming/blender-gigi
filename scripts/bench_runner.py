# SPDX-License-Identifier: GPL-3.0-or-later
"""Menjalankan kasus benchmark di proses pekerja dengan batas waktu per kasus dan log progres per baris (stderr).

Kasus yang melewati batas waktu tidak menggantung seluruh benchmark: pekerja dihentikan, kasus dicatat sebagai
error "timeout" lewat on_timeout, lalu pekerja baru dimulai untuk kasus berikutnya. Exception biasa di kasus tetap
diteruskan (benchmark berhenti dengan traceback, seperti sebelumnya).

Fungsi kasus wajib fungsi tingkat modul (dikirim ke proses pekerja dengan pickle, metode spawn).

Selama CaseRunner aktif, Windows ditahan agar tidak tidur karena idle (SetThreadExecutionState dengan
ES_CONTINUOUS | ES_SYSTEM_REQUIRED, dilepas di akhir; no-op di OS lain). Ini tidak mencegah tidur karena laptop
ditutup atau Sleep manual: dua run di §5.4 tercatat berjam-jam karena laptop tidur di tengah run.
"""

from __future__ import annotations

import ctypes
import multiprocessing
import sys
import time
from typing import Callable

DEFAULT_TIMEOUT_S = 300.0
STARTUP_TIMEOUT_S = 300.0  # start proses pekerja (import numpy dan skrip), tidak dihitung ke batas waktu kasus
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001


def keep_awake(active: bool) -> bool:
    """Tahan (active=True) atau lepas tahanan Windows terhadap tidur karena idle. False bila bukan Windows atau
    panggilan gagal."""
    if sys.platform != "win32":
        return False
    flags = ES_CONTINUOUS | ES_SYSTEM_REQUIRED if active else ES_CONTINUOUS
    return ctypes.windll.kernel32.SetThreadExecutionState(flags) != 0


def _ready() -> bool:
    return True


def add_arguments(parser) -> None:
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_S,
                        help=f"batas waktu per kasus dalam detik (default {DEFAULT_TIMEOUT_S:g})")


class CaseRunner:
    """Satu proses pekerja; run() menunggu paling lama timeout_s per kasus."""

    def __init__(self, timeout_s: float, total: int, status: Callable[[dict], str]):
        self.timeout_s = timeout_s
        self.total = total
        self.status = status
        self.done = 0
        self.timeouts = 0
        self._pool = None

    def __enter__(self) -> "CaseRunner":
        self.awake = keep_awake(True)
        return self

    def __exit__(self, *exc) -> None:
        self._stop()
        keep_awake(False)

    def _stop(self) -> None:
        if self._pool is not None:
            self._pool.terminate()
            self._pool.join()
            self._pool = None

    def run(self, label: str, func: Callable, args: tuple, on_timeout: Callable[[str, float], dict]) -> dict:
        if self._pool is None:
            self._pool = multiprocessing.get_context("spawn").Pool(1)
            self._pool.apply_async(_ready).get(STARTUP_TIMEOUT_S)
        start = time.perf_counter()
        job = self._pool.apply_async(func, args)
        try:
            result = job.get(self.timeout_s)
        except multiprocessing.TimeoutError:
            self._stop()
            self.timeouts += 1
            result = on_timeout(f"timeout: case exceeded {self.timeout_s:g} s", time.perf_counter() - start)
        self.done += 1
        print(f"[{self.done}/{self.total}] {label}: {self.status(result)} ({time.perf_counter() - start:.1f} s)",
              file=sys.stderr, flush=True)
        return result
