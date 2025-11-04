import sys
import subprocess
import os
import json
import time
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTextEdit,
    QTabWidget,
    QLabel,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
)
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QFont


class PipelineThread(QThread):
    """백그라운드에서 파이프라인(스크립트)을 실행하고 stdout을 GUI로 전달합니다."""
    progress_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool)

    def __init__(self, script_path):
        super().__init__()
        self.script_path = script_path
        self.process = None
        self.is_running = False

    def run(self):
        self.is_running = True
        try:
            # 실제 스크립트 실행
            if not os.path.exists(self.script_path):
                # 파일이 없으면 모의 로그를 출력
                self.progress_signal.emit(f"스크립트를 찾을 수 없음: {self.script_path}")
                steps = [
                    "(모의) 데이터 수집...",
                    "(모의) 전처리...",
                    "(모의) 모델 학습...",
                    "(모의) 리포트 생성...",
                ]
                for s in steps:
                    if not self.is_running:
                        self.progress_signal.emit("작업 중단됨")
                        self.finished_signal.emit(False)
                        return
                    self.progress_signal.emit(s)
                    time.sleep(1.0)
                self.progress_signal.emit("모의 파이프라인 완료")
                self.finished_signal.emit(True)
                return

            # 실행 가능한 스크립트가 있으면 파이프라인 실행
            self.process = subprocess.Popen(
                [sys.executable, '-u', self.script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
            )

            for line in iter(self.process.stdout.readline, ''):
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

        except Exception as e:
            self.progress_signal.emit(f"파이프라인 실행 중 오류: {e}")
            self.finished_signal.emit(False)
        finally:
            self.is_running = False

    def stop(self):
        self.is_running = False
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
            except Exception:
                pass


class TradingBotGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("일일 자동매매 봇 대시보드")
        self.setGeometry(100, 100, 1000, 700)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        self.tabs = QTabWidget()
        self.main_layout.addWidget(self.tabs)

        self.create_dashboard_tab()
        self.create_log_tab()
        self.create_report_tab()

        self.statusBar().showMessage("준비 완료")

    def create_dashboard_tab(self):
        dashboard_tab = QWidget()
        self.tabs.addTab(dashboard_tab, "대시보드")
        layout = QVBoxLayout(dashboard_tab)

        control_panel = QHBoxLayout()
        self.start_button = QPushButton("자동매매 파이프라인 시작")
        self.stop_button = QPushButton("중지")
        self.stop_button.setEnabled(False)
        control_panel.addWidget(self.start_button)
        control_panel.addWidget(self.stop_button)
        layout.addLayout(control_panel)

        status_group = QVBoxLayout()
        status_group.addWidget(QLabel("진행 상태:"))
        self.status_label = QLabel("대기 중...")
        status_group.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        status_group.addWidget(self.progress_bar)
        layout.addLayout(status_group)

        self.start_button.clicked.connect(self.run_pipeline)
        self.stop_button.clicked.connect(self.stop_pipeline)

        script_path = os.path.join(os.path.dirname(__file__), 'run_auto_pipeline.py')
        self.pipeline_thread = PipelineThread(script_path)
        self.pipeline_thread.progress_signal.connect(self.update_log_and_status)
        self.pipeline_thread.finished_signal.connect(self.pipeline_finished)

    def create_log_tab(self):
        log_tab = QWidget()
        self.tabs.addTab(log_tab, "실행 로그")
        layout = QVBoxLayout(log_tab)
        self.log_viewer = QTextEdit()
        self.log_viewer.setReadOnly(True)
        self.log_viewer.setFont(QFont("Courier New", 10))
        layout.addWidget(self.log_viewer)

    def create_report_tab(self):
        report_tab = QWidget()
        self.tabs.addTab(report_tab, "성과 리포트")
        layout = QVBoxLayout(report_tab)

        self.report_table = QTableWidget()
        self.report_table.setColumnCount(2)
        self.report_table.setHorizontalHeaderLabels(["항목", "값"])
        self.report_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.report_table.verticalHeader().setVisible(False)
        layout.addWidget(self.report_table)

    def run_pipeline(self):
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.statusBar().showMessage("파이프라인 실행 중...")
        self.log_viewer.clear()
        self.report_table.setRowCount(0)
        self.pipeline_thread.start()

    def stop_pipeline(self):
        self.stop_button.setEnabled(False)
        self.pipeline_thread.stop()

    def update_log_and_status(self, message):
        self.log_viewer.append(message)
        self.status_label.setText(message)

    def pipeline_finished(self, success):
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.progress_bar.setVisible(False)
        if success:
            self.statusBar().showMessage("파이프라인 성공적으로 완료됨.", 5000)
            self.load_report()
        else:
            self.statusBar().showMessage("파이프라인 중단 또는 오류 발생.", 5000)

    def load_report(self):
        report_path = os.path.join(os.path.dirname(__file__), 'results', 'performance_summary.json')
        try:
            if not os.path.exists(report_path):
                # 테스트용 더미 리포트 생성
                os.makedirs(os.path.dirname(report_path), exist_ok=True)
                dummy_report = {
                    "total_trades": 120,
                    "win_rate": 62.5,
                    "total_profit": 18500.75,
                    "max_drawdown": -550.20,
                    "avg_profit_per_trade": 154.17,
                    "sharpe_ratio": 1.25,
                }
                with open(report_path, 'w', encoding='utf-8') as f:
                    json.dump(dummy_report, f, indent=2)

            with open(report_path, 'r', encoding='utf-8') as f:
                report_data = json.load(f)

            self.report_table.setRowCount(0)
            row = 0
            for key, value in report_data.items():
                # 리스트(예: strategy_stats) 처리
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

        except FileNotFoundError:
            self.statusBar().showMessage(f"리포트 파일을 찾을 수 없습니다: {report_path}", 5000)
        except Exception as e:
            self.statusBar().showMessage(f"리포트 로딩 오류: {e}", 5000)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    gui = TradingBotGUI()
    gui.show()
    sys.exit(app.exec())
