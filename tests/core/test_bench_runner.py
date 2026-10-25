# SPDX-License-Identifier: GPL-3.0-or-later
"""Batas waktu per kasus benchmark (scripts/bench_runner.py): kasus macet berakhir sebagai error, tidak menggantung."""

import math
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts import bench_runner  # noqa: E402


def test_slow_case_becomes_a_timeout_and_the_next_case_still_runs(capsys):
    def on_timeout(message, seconds):
        return {"status": "timeout", "message": message, "seconds": seconds}

    with bench_runner.CaseRunner(0.5, 3, lambda r: r["status"] if isinstance(r, dict) else "ok") as runner:
        slow = runner.run("lambat", time.sleep, (30,), on_timeout)
        fast = runner.run("cepat", math.sqrt, (16.0,), on_timeout)
        again = runner.run("lambat lagi", time.sleep, (30,), on_timeout)
    assert slow["status"] == "timeout" and "0.5 s" in slow["message"] and slow["seconds"] < 5
    assert fast == 4.0
    assert again["status"] == "timeout"
    assert runner.timeouts == 2
    log = capsys.readouterr().err.splitlines()
    assert log[0].startswith("[1/3] lambat: timeout") and log[1].startswith("[2/3] cepat: ok")


def test_keep_awake_is_held_on_windows_and_released_after():
    runner = bench_runner.CaseRunner(1.0, 0, str)
    with runner:
        assert runner.awake == (sys.platform == "win32")
    assert bench_runner.keep_awake(False) == (sys.platform == "win32")
