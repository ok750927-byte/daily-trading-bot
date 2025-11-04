"""Helper script to run the GUI automation test locally.

Usage:
  - On Linux/macOS with Xvfb installed:
      RUN_GUI_LOCAL=1 python scripts/run_gui_automation.py

  - On Windows (have a display):
      set RUN_GUI_LOCAL=1
      python scripts/run_gui_automation.py

The script will invoke pytest for `tests/gui_local_automation.py` and stream logs.
"""
from __future__ import annotations

import os
import shlex
import subprocess
import sys


def main() -> int:
    os.environ.setdefault("RUN_GUI_LOCAL", "1")
    test_target = "tests/gui_local_automation.py::test_operator_persistence_and_gui_start"

    if sys.platform.startswith("linux") or sys.platform.startswith("darwin"):
        # Try to use xvfb-run if available
        cmd = f"xvfb-run -s '-screen 0 1280x720x24' pytest -q {shlex.quote(test_target)}"
    else:
        cmd = f"pytest -q {shlex.quote(test_target)}"

    print("Running:", cmd)
    try:
        rc = subprocess.call(cmd, shell=True)
        return rc
    except KeyboardInterrupt:
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
