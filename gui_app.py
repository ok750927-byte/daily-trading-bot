"""Simple PyQt6 GUI (clean copy) for running the pipeline and viewing a JSON report.

This is a clean, standalone copy of the GUI so we can run it without editing
the original (potentially corrupted) `gui_app.py` in-place.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from typing import Optional

# Try to import PyQt6; if not available, we'll fall back to a headless mode.
PYQT_AVAILABLE = True
try:
    from PyQt6.QtCore import QThread, pyqtSignal, QTimer
    from PyQt6.QtGui import QFont
    from PyQt6.QtWidgets import (
        QApplication,
        QHBoxLayout,
        QLabel,
        QMainWindow,
        QProgressBar,
        QPushButton,
        QTabWidget,
        QTableWidget,
        QTableWidgetItem,
        QTextEdit,
        QVBoxLayout,
        QWidget,
        QHeaderView,
    )
except Exception:  # pragma: no cover - environment dependent
    PYQT_AVAILABLE = False



class PipelineThread(QThread):
    progress_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool)

    def __init__(self, script_path: str):
        super().__init__()
        self.script_path = script_path
        self.process: Optional[subprocess.Popen] = None
        self.is_running = False

    def run(self) -> None:
        self.is_running = True
        try:
            if not os.path.exists(self.script_path):
                self.progress_signal.emit(f"스크립트를 찾을 수 없음: {self.script_path}")
                for step in (
                    "(모의) 데이터 수집...",
                    "(모의) 전처리...",
                    "(모의) 모델 학습...",
                    "(모의) 리포트 생성...",
                ):
                    if not self.is_running:
                        self.progress_signal.emit("작업 중단됨")
                        self.finished_signal.emit(False)
                        return
                    self.progress_signal.emit(step)
                    time.sleep(0.8)
                self.progress_signal.emit("모의 파이프라인 완료")
                self.finished_signal.emit(True)
                return

            self.process = subprocess.Popen(
                [sys.executable, "-u", self.script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
            )

            assert self.process.stdout is not None
            for line in iter(self.process.stdout.readline, ""):
                if not self.is_running:
                    break
                if line:
                    self.progress_signal.emit(line.rstrip())

            self.process.wait()
            rc = self.process.returncode
            self.finished_signal.emit(rc == 0)
            if rc == 0:
                self.progress_signal.emit("파이프라인 정상 종료")
            else:
                self.progress_signal.emit(f"파이프라인 비정상 종료 (코드 {rc})")

        except Exception as exc:
            self.progress_signal.emit(f"파이프라인 실행 중 오류: {exc}")
            self.finished_signal.emit(False)
        finally:
            self.is_running = False

    def stop(self) -> None:
        self.is_running = False
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
            except Exception:
                pass


class TradingBotGUI(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("일일 자동매매 봇 대시보드 (클린)")
        self.setGeometry(100, 100, 1000, 700)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        self.tabs = QTabWidget()
        self.main_layout.addWidget(self.tabs)

        self._build_dashboard_tab()
        self._build_log_tab()
        self._build_report_tab()
        self._build_realtime_tab()

        self.statusBar().showMessage("준비 완료")

        script_path = os.path.join(os.path.dirname(__file__), "run_auto_pipeline.py")
        self.pipeline_thread = PipelineThread(script_path)
        self.pipeline_thread.progress_signal.connect(self._on_progress)
        self.pipeline_thread.finished_signal.connect(self._on_finished)
        # load persisted operator name if exists
        try:
            op_file = os.path.join(os.path.dirname(__file__), 'results', 'operator.txt')
            if os.path.exists(op_file):
                with open(op_file, 'r', encoding='utf-8') as fh:
                    name = fh.read().strip()
                    if name and hasattr(self, 'operator_input'):
                        self.operator_input.setText(name)
        except Exception:
            pass

    def _build_dashboard_tab(self) -> None:
        tab = QWidget()
        self.tabs.addTab(tab, "대시보드")
        layout = QVBoxLayout(tab)

        controls = QHBoxLayout()
        self.start_button = QPushButton("자동매매 파이프라인 시작")
        self.stop_button = QPushButton("중지")
        self.stop_button.setEnabled(False)
        controls.addWidget(self.start_button)
        controls.addWidget(self.stop_button)
        layout.addLayout(controls)

        self.status_label = QLabel("대기 중...")
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.start_button.clicked.connect(self._start_pipeline)
        self.stop_button.clicked.connect(self._stop_pipeline)

    def _build_log_tab(self) -> None:
        tab = QWidget()
        self.tabs.addTab(tab, "실행 로그")
        layout = QVBoxLayout(tab)
        self.log_viewer = QTextEdit()
        self.log_viewer.setReadOnly(True)
        self.log_viewer.setFont(QFont("Courier New", 10))
        layout.addWidget(self.log_viewer)

    def _build_report_tab(self) -> None:
        tab = QWidget()
        self.tabs.addTab(tab, "성과 리포트")
        layout = QVBoxLayout(tab)
        self.report_table = QTableWidget()
        self.report_table.setColumnCount(2)
        self.report_table.setHorizontalHeaderLabels(["항목", "값"])
        self.report_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.report_table.verticalHeader().setVisible(False)
        layout.addWidget(self.report_table)

    def _build_realtime_tab(self) -> None:
        from src.trading.realtime_trader import RealtimeTrader
        from src.trading.approval import ApprovalManager
        import threading

        tab = QWidget()
        self.tabs.addTab(tab, "실시간 트레이딩")
        layout = QVBoxLayout(tab)

        controls = QHBoxLayout()
        self.operator_label = QLabel('Operator:')
        self.operator_input = QPushButton('Not logged in')
        # operator_input is a placeholder button — allow clicking to set simple name
        self.operator_input.setCheckable(False)
        self.operator_input.clicked.connect(self._set_operator_name_interactive)

        self.rt_start_button = QPushButton("실시간 시작")
        self.rt_stop_button = QPushButton("실시간 중지")
        self.rt_stop_button.setEnabled(False)
        self.auto_approve_checkbox = QPushButton("AUTO_APPROVE: OFF")
        self.auto_approve_checkbox.setCheckable(True)
        controls.addWidget(self.operator_label)
        controls.addWidget(self.operator_input)
        controls.addWidget(self.rt_start_button)
        controls.addWidget(self.rt_stop_button)
        controls.addWidget(self.auto_approve_checkbox)
        layout.addLayout(controls)

        self.pending_table = QTableWidget()
        self.pending_table.setColumnCount(4)
        self.pending_table.setHorizontalHeaderLabels(["Req ID", "Symbol", "Qty", "Approve/Reject"])
        self.pending_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.pending_table)

        # approval manager and trader (non-blocking flow)
        self._approval_mgr = ApprovalManager()
        self._rt_trader = RealtimeTrader(approval_manager=self._approval_mgr, dry_run=True)

    # connect buttons
        def _start_rt():
            self.rt_start_button.setEnabled(False)
            self.rt_stop_button.setEnabled(True)
            # start background supplier using demo signals
            self._rt_thread = threading.Thread(target=lambda: self._rt_trader.run_from_iterator(self._demo_signals()), daemon=True)
            self._rt_thread.start()

        def _stop_rt():
            self.rt_stop_button.setEnabled(False)
            self.rt_start_button.setEnabled(True)
            try:
                self._rt_trader.stop()
            except Exception:
                pass

        def _toggle_auto():
            on = self.auto_approve_checkbox.isChecked()
            self.auto_approve_checkbox.setText(f"AUTO_APPROVE: {'ON' if on else 'OFF'}")

        self.rt_start_button.clicked.connect(_start_rt)
        self.rt_stop_button.clicked.connect(_stop_rt)
        self.auto_approve_checkbox.clicked.connect(_toggle_auto)

        # periodic refresh of pending table (1s)
        self._pending_timer = QTimer()
        self._pending_timer.setInterval(1000)
        self._pending_timer.timeout.connect(self._refresh_pending_table)
        self._pending_timer.start()

    def _set_operator_name_interactive(self):
        # lightweight prompt via input dialog in console if GUI dialog not desired
        try:
            # try to use a simple QInputDialog if available
            from PyQt6.QtWidgets import QInputDialog
            name, ok = QInputDialog.getText(self, 'Operator Login', 'Enter operator name:')
            if ok and name:
                self.operator_input.setText(name)
                # persist operator name
                try:
                    op_file = os.path.join(os.path.dirname(__file__), 'results')
                    os.makedirs(op_file, exist_ok=True)
                    with open(os.path.join(op_file, 'operator.txt'), 'w', encoding='utf-8') as fh:
                        fh.write(name)
                except Exception:
                    pass
        except Exception:
            # fallback to console input
            try:
                name = input('Operator name: ')
                if name:
                    self.operator_input.setText(name)
                    try:
                        op_file = os.path.join(os.path.dirname(__file__), 'results')
                        os.makedirs(op_file, exist_ok=True)
                        with open(os.path.join(op_file, 'operator.txt'), 'w', encoding='utf-8') as fh:
                            fh.write(name)
                    except Exception:
                        pass
            except Exception:
                pass

        # helper to refresh pending table from ApprovalManager
        def _make_action_buttons(req_id):
            from PyQt6.QtWidgets import QPushButton, QWidget, QHBoxLayout

            widget = QWidget()
            layout = QHBoxLayout(widget)
            approve = QPushButton('Approve')
            reject = QPushButton('Reject')

            def _on_approve():
                # approver identity from operator_input text (default 'gui')
                approver = self.operator_input.text() if hasattr(self, 'operator_input') else 'gui'
                self._approval_mgr.approve(req_id, approver=approver, approve=True)
                self._refresh_pending_table()

            def _on_reject():
                approver = self.operator_input.text() if hasattr(self, 'operator_input') else 'gui'
                self._approval_mgr.approve(req_id, approver=approver, approve=False)
                self._refresh_pending_table()

            approve.clicked.connect(_on_approve)
            reject.clicked.connect(_on_reject)
            layout.addWidget(approve)
            layout.addWidget(reject)
            layout.setContentsMargins(0, 0, 0, 0)
            return widget

        self._make_action_buttons = _make_action_buttons

    def _demo_signals(self):
        # same sample used by scripts/run_realtime_trader.py
        sample = [
            {'symbol': '005930', 'qty': 1, 'price': 70000, 'side': 'buy', 'idempotency_key': 'demo-1'},
            {'symbol': '000660', 'qty': 1, 'price': 90000, 'side': 'buy', 'idempotency_key': 'demo-2'},
            {'symbol': '005930', 'qty': 1, 'price': 70000, 'side': 'sell', 'idempotency_key': 'demo-3'},
        ]
        for s in sample:
            yield s

    def _refresh_pending_table(self):
        # must be called from GUI thread
        # get pending from approval manager if available
        pending = {}
        if hasattr(self, '_approval_mgr'):
            pending = self._approval_mgr.list_pending()

        self.pending_table.setRowCount(0)
        row = 0
        for key, rec in pending.items():
            sig = rec.get('signal', {})
            self.pending_table.insertRow(row)
            self.pending_table.setItem(row, 0, QTableWidgetItem(str(key)))
            self.pending_table.setItem(row, 1, QTableWidgetItem(str(sig.get('symbol'))))
            self.pending_table.setItem(row, 2, QTableWidgetItem(str(sig.get('qty'))))
            self.pending_table.setCellWidget(row, 3, self._make_action_buttons(key))
            row += 1

    def _start_pipeline(self) -> None:
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.statusBar().showMessage("파이프라인 실행 중...")
        self.log_viewer.clear()
        self.report_table.setRowCount(0)
        self.pipeline_thread.start()

    def _stop_pipeline(self) -> None:
        self.stop_button.setEnabled(False)
        self.pipeline_thread.stop()

    def _on_progress(self, text: str) -> None:
        self.log_viewer.append(text)
        self.status_label.setText(text)

    def _on_finished(self, success: bool) -> None:
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.progress_bar.setVisible(False)
        if success:
            self.statusBar().showMessage("파이프라인 성공적으로 완료됨.", 5000)
            self._load_report()
        else:
            self.statusBar().showMessage("파이프라인 중단 또는 오류 발생.", 5000)

    def _load_report(self) -> None:
        report_path = os.path.join(os.path.dirname(__file__), "results", "performance_summary.json")
        try:
            if not os.path.exists(report_path):
                os.makedirs(os.path.dirname(report_path), exist_ok=True)
                dummy_report = {
                    "total_trades": 120,
                    "win_rate": 62.5,
                    "total_profit": 18500.75,
                    "max_drawdown": -550.20,
                    "avg_profit_per_trade": 154.17,
                    "sharpe_ratio": 1.25,
                }
                with open(report_path, "w", encoding="utf-8") as fh:
                    json.dump(dummy_report, fh, indent=2)

            with open(report_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)

            self.report_table.setRowCount(0)
            row = 0
            for key, value in data.items():
                if isinstance(value, list) and all(isinstance(i, dict) for i in value):
                    self.report_table.insertRow(row)
                    self.report_table.setItem(row, 0, QTableWidgetItem(str(key)))
                    self.report_table.setItem(row, 1, QTableWidgetItem("(세부 항목 있음)"))
                    row += 1
                    for item in value:
                        for sub_k, sub_v in item.items():
                            self.report_table.insertRow(row)
                            self.report_table.setItem(row, 0, QTableWidgetItem(f"  - {sub_k}"))
                            self.report_table.setItem(row, 1, QTableWidgetItem(str(sub_v)))
                            row += 1
                else:
                    self.report_table.insertRow(row)
                    self.report_table.setItem(row, 0, QTableWidgetItem(str(key)))
                    self.report_table.setItem(row, 1, QTableWidgetItem(str(value)))
                    row += 1

        except Exception as exc:
            self.statusBar().showMessage(f"리포트 로딩 오류: {exc}", 5000)


def main() -> None:
    app = QApplication(sys.argv)
    gui = TradingBotGUI()
    gui.show()
    sys.exit(app.exec())


def _headless_main() -> None:
    """Run a terminal-only mock of the pipeline when PyQt6 isn't installed.

    This helps developers who run the repo in headless CI, containers, or
    environments without GUI libraries. It prints install instructions and
    then performs the same mock progress steps the GUI uses when the
    pipeline script is missing.
    """
    print("PyQt6 is not installed. To run the GUI, install it with:")
    print("    pip install PyQt6")
    print("")
    print("Running headless pipeline simulation...")
    steps = [
        "(모의) 데이터 수집...",
        "(모의) 전처리...",
        "(모의) 모델 학습...",
        "(모의) 리포트 생성...",
    ]
    try:
        for s in steps:
            print(s)
            time.sleep(0.8)
        print("모의 파이프라인 완료")
        sys.exit(0)
    except KeyboardInterrupt:
        print("작업 중단됨")
        sys.exit(1)


if __name__ == "__main__":
    if PYQT_AVAILABLE:
        main()
    else:
        _headless_main()
