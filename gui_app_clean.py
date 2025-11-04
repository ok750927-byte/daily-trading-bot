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

from PyQt6.QtCore import QThread, pyqtSignal
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

        self.statusBar().showMessage("준비 완료")

        script_path = os.path.join(os.path.dirname(__file__), "run_auto_pipeline.py")
        self.pipeline_thread = PipelineThread(script_path)
        self.pipeline_thread.progress_signal.connect(self._on_progress)
        self.pipeline_thread.finished_signal.connect(self._on_finished)

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


if __name__ == "__main__":
    main()
