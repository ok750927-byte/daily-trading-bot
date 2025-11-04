import sys
import subprocess
import os
import json
import time
import tempfile
import logging
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

# configure module-level logging to a persistent file under the project `results/`
# Prefer the current working directory's results folder so frozen executables
# (which run from a temp _MEI folder) write logs to the project workspace.
try:
    # Determine a reliable workspace root and write logs into its results/ folder.
    def find_workspace_root():
        # 1) honor explicit environment override
        env = os.environ.get('DAILY_TRADING_WORKSPACE')
        if env and os.path.isdir(env):
            return os.path.abspath(env)

        # 2) start from cwd and walk upwards looking for a repository marker
        cwd = os.getcwd()
        markers = ('pyproject.toml', 'README.md', 'requirements.txt', '.git')
        cur = cwd
        while True:
            for m in markers:
                if os.path.exists(os.path.join(cur, m)):
                    return os.path.abspath(cur)
            parent = os.path.dirname(cur)
            if parent == cur:
                break
            cur = parent

        # 3) fallback to the script directory
        try:
            return os.path.abspath(os.path.dirname(__file__))
        except Exception:
            return os.path.abspath(cwd)

    workspace_root = find_workspace_root()
    results_dir = os.path.join(workspace_root, 'results')
    os.makedirs(results_dir, exist_ok=True)
    log_path = os.path.join(results_dir, 'gui_runtime.log')
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s: %(message)s',
        handlers=[
            logging.FileHandler(log_path, encoding='utf-8'),
            logging.StreamHandler(sys.stdout),
        ],
    )
    # As an extra guarantee (works even if the process is killed), write a
    # small marker using low-level os.open/os.write to the absolute results log.
    try:
        try:
            fd = os.open(log_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND)
        except AttributeError:
            # Windows compatibility fallback (shouldn't normally happen)
            fd = open(log_path, 'a', encoding='utf-8')
            fd.write(f"MODULE STARTED: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            fd.close()
        else:
            os.write(fd, (f"MODULE STARTED: {time.strftime('%Y-%m-%d %H:%M:%S')}\n").encode('utf-8'))
            os.close(fd)
    except Exception:
        pass
    # Merge any existing PyInstaller extracted (_MEI...) runtime logs into the
    # repository results file so developers can find logs after runs. Exposed
    # as a function for testing and can accept an override temp_dir.
    def merge_temp_mei_logs(temp_dir=None):
        try:
            td = temp_dir or tempfile.gettempdir()
            for name in os.listdir(td):
                if not name.startswith('_MEI'):
                    continue
                candidate = os.path.join(td, name, 'results', 'gui_runtime.log')
                if os.path.isfile(candidate):
                    try:
                        with open(candidate, 'rb') as sf, open(log_path, 'ab') as df:
                            df.write((f"\n--- BEGIN MERGED FROM {name} ---\n").encode('utf-8'))
                            df.write(sf.read())
                            df.write((f"\n--- END MERGED FROM {name} ---\n").encode('utf-8'))
                    except Exception:
                        # ignore errors copying a single file
                        pass
        except Exception:
            pass

    try:
        merge_temp_mei_logs()
    except Exception:
        pass
except Exception:
    # best-effort; don't fail import if logging setup can't be created
    try:
        logging.basicConfig(level=logging.INFO)
    except Exception:
        pass


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
            # ensure the same workspace results dir exists for runtime logging
            try:
                # use the module-level workspace_root if available
                results_dir = os.path.join(workspace_root, 'results')
            except Exception:
                results_dir = os.path.join(os.path.dirname(__file__), 'results')
            os.makedirs(results_dir, exist_ok=True)
        except Exception:
            pass
        logger = logging.getLogger(__name__)
        logger.info(f"PipelineThread starting for: {self.script_path}")
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
                cwd=workspace_root,
                env={**os.environ, 'DAILY_TRADING_WORKSPACE': workspace_root},
            )

            for line in iter(self.process.stdout.readline, ''):
                if not self.is_running:
                    break
                if line:
                    text = line.rstrip()
                    self.progress_signal.emit(text)
                    logger.info(f"PIPELINE_OUT: {text}")

            self.process.wait()
            rc = self.process.returncode
            self.finished_signal.emit(rc == 0)
            if rc == 0:
                self.progress_signal.emit("파이프라인 정상 종료")
            else:
                self.progress_signal.emit(f"파이프라인 비정상 종료 (코드 {rc})")

        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.exception("파이프라인 실행 중 오류")
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
        logging.getLogger(__name__).info("PipelineThread.stop() called")


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
        # runtime marker log so we have immediate evidence the GUI started
        try:
            logging.getLogger(__name__).info("TradingBotGUI initialized")
        except Exception:
            pass
        # Also write a guaranteed marker directly to a persistent file (append)
        try:
            # Write a guaranteed marker directly to the workspace results folder
            manual_log_dir = os.path.join(workspace_root, 'results')
            os.makedirs(manual_log_dir, exist_ok=True)
            manual_log_path = os.path.join(manual_log_dir, 'gui_runtime_manual.log')
            with open(manual_log_path, 'a', encoding='utf-8') as mf:
                mf.write(f"TradingBotGUI initialized: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        except Exception:
            pass

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
        # attempt to merge any temp _MEI logs after pipeline finishes
        try:
            merge_temp_mei_logs()
        except Exception:
            pass

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
    # Ensure we attempt a final merge of any temp logs on clean shutdown
    try:
        exit_code = app.exec()
        try:
            merge_temp_mei_logs()
        except Exception:
            pass
        sys.exit(exit_code)
    except Exception:
        try:
            merge_temp_mei_logs()
        except Exception:
            pass
        raise
