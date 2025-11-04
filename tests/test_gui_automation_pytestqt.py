import os
import json
import sys
import time

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication


def test_gui_pipeline_runs_and_creates_report(qtbot, tmp_path):
    """Start the GUI, click Start, wait for mock pipeline finish, and check report."""
    # Import the recovered GUI implementation
    from gui_app_recovered import TradingBotGUI

    # Ensure a single QApplication
    app = QApplication.instance() or QApplication(sys.argv)

    gui = TradingBotGUI()
    qtbot.addWidget(gui)
    gui.show()

    # Point pipeline to a non-existent script inside tmp_path to force mock run
    gui.pipeline_thread.script_path = str(tmp_path / "no_such_script.py")

    finished = {"ok": False}

    def _on_finished(s):
        finished["ok"] = True

    gui.pipeline_thread.finished_signal.connect(_on_finished)

    # Click start
    qtbot.mouseClick(gui.start_button, Qt.MouseButton.LeftButton)

    # Wait until finished or timeout
    qtbot.waitUntil(lambda: finished["ok"], timeout=8000)

    # After finish, GUI should have created a dummy report file under results/
    report_path = os.path.join(os.path.dirname(__file__), os.pardir, "results", "performance_summary.json")
    report_path = os.path.abspath(report_path)
    assert os.path.exists(report_path), f"Expected report at {report_path}"

    # Validate JSON structure
    with open(report_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    assert "total_trades" in data
    assert "win_rate" in data

    # Also ensure the runtime log contains evidence the GUI started
    log_path = os.path.join(os.path.dirname(__file__), os.pardir, "results", "gui_runtime.log")
    log_path = os.path.abspath(log_path)
    assert os.path.exists(log_path), f"Expected runtime log at {log_path}"
    with open(log_path, 'r', encoding='utf-8') as lf:
        log_text = lf.read()
    assert ("TradingBotGUI initialized" in log_text) or ("MODULE STARTED" in log_text)

    # Close GUI
    gui.close()
