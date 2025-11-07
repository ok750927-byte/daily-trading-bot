from __future__ import annotations
"""
주식 자동매매 프로그램 GUI 대시보드
- customtkinter를 사용한 현대적인 UI
- 주요 기능 접근 및 모니터링
"""
import os
import sys
import customtkinter as ctk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from PIL import Image, ImageTk
from pathlib import Path
import threading
import queue
from typing import Optional, Dict
import pandas as pd
import json

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 아이콘 경로 설정
ICON_PATH = project_root / "assets" / "icons"

# 백엔드 모듈 임포트
try:
    from src.analysis.advanced_backtesting import AdvancedBacktester, BacktestResult
    from src.analysis.portfolio_optimization import PortfolioOptimizer, OptimizationResult
    from scripts.live_trading_orchestrator import LiveTradingOrchestrator
    from src.trading.approval import manager as approval_manager
except ImportError as e:
    print(f"백엔드 모듈 임포트 실패: {e}")
    AdvancedBacktester = None
    BacktestResult = None
    PortfolioOptimizer = None
    OptimizationResult = None
    PortfolioOptimizer = None
    OptimizationResult = None

class TradingDashboard(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("📈 일일 트레이딩 봇 - 대시보드")
        self.geometry("1200x800")
        
        # 테마 설정
        ctk.set_appearance_mode("Dark")  # Dark, Light, System
        ctk.set_default_color_theme("blue")  # blue, green, dark-blue

        # 메인 레이아웃 설정 (2x1 그리드)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 1. 사이드바 프레임
        self.sidebar_frame = self.create_sidebar()
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")

        # 2. 메인 컨텐츠 프레임
        self.main_frame = ctk.CTkFrame(self, corner_radius=0)
        self.main_frame.grid(row=0, column=1, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)

        # 각 기능별 프레임 딕셔너리
        self.frames = {}
        for F in (DashboardFrame, BacktestingFrame, OptimizationFrame, LiveTradingFrame, SettingsFrame):
            frame = F(self.main_frame, self)
            self.frames[F.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        # 초기 화면 설정
        self.show_frame("DashboardFrame")

    def create_sidebar(self):
        """사이드바 메뉴 생성"""
        sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        
        # 로고
        logo_label = ctk.CTkLabel(sidebar_frame, text="일일 트레이딩 봇", font=ctk.CTkFont(size=20, weight="bold"))
        logo_label.pack(pady=20)

        # 메뉴 버튼
        menu_items = {
            "대시보드": "DashboardFrame",
            "백테스팅": "BacktestingFrame",
            "최적화": "OptimizationFrame",
            "실시간 트레이딩": "LiveTradingFrame",
            "설정": "SettingsFrame"
        }

        for display_name, frame_name in menu_items.items():
            button = ctk.CTkButton(
                sidebar_frame,
                text=display_name,
                command=lambda fn=frame_name: self.show_frame(fn),
                anchor="w",
                height=40,
                corner_radius=0,
                font=ctk.CTkFont(size=14)
            )
            button.pack(fill="x", pady=2)
        
        # 하단 테마 변경
        appearance_mode_label = ctk.CTkLabel(sidebar_frame, text="테마 설정:", anchor="w")
        appearance_mode_label.pack(side="bottom", padx=20, pady=(10, 0))
        
        appearance_mode_optionemenu = ctk.CTkOptionMenu(
            sidebar_frame,
            values=["Light", "Dark", "System"],
            command=self.change_appearance_mode_event
        )
        appearance_mode_optionemenu.pack(side="bottom", padx=20, pady=10)
        appearance_mode_optionemenu.set("Dark")

        return sidebar_frame

    def show_frame(self, frame_name):
        """선택된 프레임 표시"""
        frame = self.frames[frame_name]
        frame.tkraise()

    def change_appearance_mode_event(self, new_appearance_mode: str):
        """테마 변경"""
        ctk.set_appearance_mode(new_appearance_mode)

# --- 각 기능별 프레임 ---

class DashboardFrame(ctk.CTkFrame):
    """대시보드 프레임"""
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        self.grid_columnconfigure((0, 1), weight=1)
        self.grid_rowconfigure((0, 1, 2), weight=1)

        # 1. 포트폴리오 요약
        summary_frame = ctk.CTkFrame(self)
        summary_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        summary_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        ctk.CTkLabel(summary_frame, text="포트폴리오 요약", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, columnspan=3, pady=10)
        
        ctk.CTkLabel(summary_frame, text="총 자산").grid(row=1, column=0)
        ctk.CTkLabel(summary_frame, text="10,520,000 KRW", font=ctk.CTkFont(size=20, weight="bold")).grid(row=2, column=0)
        
        ctk.CTkLabel(summary_frame, text="오늘의 손익").grid(row=1, column=1)
        ctk.CTkLabel(summary_frame, text="+52,000 (0.50%)", font=ctk.CTkFont(size=20, weight="bold"), text_color="green").grid(row=2, column=1)
        
        ctk.CTkLabel(summary_frame, text="총 수익률").grid(row=1, column=2)
        ctk.CTkLabel(summary_frame, text="+5.20%", font=ctk.CTkFont(size=20, weight="bold"), text_color="green").grid(row=2, column=2)

        # 2. 시스템 상태
        status_frame = ctk.CTkFrame(self)
        status_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        status_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(status_frame, text="시스템 상태", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        
        ctk.CTkLabel(status_frame, text="트레이딩 엔진: 동작 중", text_color="green", anchor="w").pack(fill="x", padx=20)
        ctk.CTkLabel(status_frame, text="데이터 수신: 연결됨", text_color="green", anchor="w").pack(fill="x", padx=20)
        ctk.CTkLabel(status_frame, text="API 연결: 안정적", text_color="green", anchor="w").pack(fill="x", padx=20)

        # 3. 성과 그래프
        chart_frame = ctk.CTkFrame(self)
        chart_frame.grid(row=1, column=0, columnspan=2, padx=20, pady=20, sticky="nsew")
        
        self.create_performance_chart(chart_frame)

        # 4. 로그
        log_frame = ctk.CTkFrame(self)
        log_frame.grid(row=2, column=0, columnspan=2, padx=20, pady=20, sticky="nsew")
        
        ctk.CTkLabel(log_frame, text="시스템 로그", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=5)
        
        log_textbox = ctk.CTkTextbox(log_frame, width=400, height=150)
        log_textbox.pack(fill="both", expand=True, padx=10, pady=10)
        log_textbox.insert("0.0", "11:30:15 [INFO] - 005930 10주 매수 주문 실행\n")
        log_textbox.insert("0.0", "10:45:02 [INFO] - 005930에 대한 강력 매수 신호 감지\n")
        log_textbox.insert("0.0", "09:00:00 [INFO] - 트레이딩 세션 시작.\n")
        log_textbox.configure(state="disabled")

    def create_performance_chart(self, parent_frame):
        """성과 그래프 생성"""
        fig, ax = plt.subplots(facecolor="#2B2B2B")
        ax.set_facecolor("#2B2B2B")
        
        # 데이터
        try:
            import pandas as pd
            x = pd.to_datetime(['2025-10-01', '2025-10-08', '2025-10-15', '2025-10-22', '2025-10-29', '2025-11-05'])
            y = [100, 102, 101.5, 103, 104, 105.2]
        except ImportError:
            x = [1, 2, 3, 4, 5, 6]
            y = [100, 102, 101.5, 103, 104, 105.2]
        
        ax.plot(x, y, color='cyan', marker='o')
        
        # 스타일
        ax.set_title("포트폴리오 성과", color='white')
        ax.set_xlabel("날짜", color='white')
        ax.set_ylabel("가치 (정규화)", color='white')
        ax.tick_params(axis='x', colors='white', rotation=30)
        ax.tick_params(axis='y', colors='white')
        ax.grid(True, color='gray', linestyle='--', linewidth=0.5)
        
        # 테두리 색상
        for spine in ax.spines.values():
            spine.set_edgecolor('white')
            
        fig.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, master=parent_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(side="top", fill="both", expand=True)

class BacktestingFrame(ctk.CTkFrame):
    """백테스팅 프레임"""
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.backtest_thread: Optional[threading.Thread] = None
        self.result_queue = queue.Queue()
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=2)

        # 1. 설정 프레임 (좌측)
        settings_frame = ctk.CTkFrame(self, width=300)
        settings_frame.grid(row=0, column=0, rowspan=2, padx=20, pady=20, sticky="nsew")
        settings_frame.grid_propagate(False)
        settings_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(settings_frame, text="백테스트 설정", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(15, 10))

        # 전략 선택
        ctk.CTkLabel(settings_frame, text="전략").pack(anchor="w", padx=15, pady=(10, 0))
        self.strategy_var = ctk.StringVar(value="random_forest")
        strategy_menu = ctk.CTkOptionMenu(settings_frame, variable=self.strategy_var, values=["random_forest", "logistic_regression"])
        strategy_menu.pack(fill="x", padx=15, pady=5)

        # 종목 코드
        ctk.CTkLabel(settings_frame, text="종목 검색 및 추가").pack(anchor="w", padx=15, pady=(10, 0))
        
        symbols_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        symbols_frame.pack(fill="x", padx=15, pady=5)
        symbols_frame.grid_columnconfigure(0, weight=1)

        self.symbols_combobox = ctk.CTkComboBox(symbols_frame, values=[], command=self.add_stock_callback)
        self.symbols_combobox.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        
        add_button = ctk.CTkButton(symbols_frame, text="추가", width=50, command=self.add_stock_callback)
        add_button.grid(row=0, column=1, sticky="e")


        self.selected_stocks_frame = ctk.CTkScrollableFrame(settings_frame, label_text="선택된 종목")
        self.selected_stocks_frame.pack(fill="x", expand=True, padx=15, pady=5)
        self.selected_stocks = {} # {code: widget}

        # 기간 설정
        ctk.CTkLabel(settings_frame, text="기간").pack(anchor="w", padx=15, pady=(10, 0))
        date_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        date_frame.pack(fill="x", padx=15, pady=5)
        date_frame.grid_columnconfigure((0, 1), weight=1)
        
        self.start_date_entry = ctk.CTkEntry(date_frame)
        self.start_date_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.start_date_entry.insert(0, "2023-01-01")
        
        self.end_date_entry = ctk.CTkEntry(date_frame)
        self.end_date_entry.grid(row=0, column=1, sticky="ew", padx=(5, 0))
        self.end_date_entry.insert(0, "2023-12-31")

        # 초기 자본
        ctk.CTkLabel(settings_frame, text="초기 자본 (KRW)").pack(anchor="w", padx=15, pady=(10, 0))
        self.capital_entry = ctk.CTkEntry(settings_frame)
        self.capital_entry.pack(fill="x", padx=15, pady=5)
        self.capital_entry.insert(0, "10000000")

        # 실행 버튼
        self.run_button = ctk.CTkButton(settings_frame, text="백테스트 실행", command=self.run_backtest_callback, height=40)
        self.run_button.pack(fill="x", padx=15, pady=20)
        
        # 2. 결과 표시 프레임 (우측 상단) - 그래프
        self.chart_frame = ctk.CTkFrame(self)
        self.chart_frame.grid(row=0, column=1, padx=(0, 20), pady=20, sticky="nsew")
        ctk.CTkLabel(self.chart_frame, text="성과 차트", font=ctk.CTkFont(size=16)).pack(pady=10)

        # 3. 결과 표시 프레임 (우측 하단) - 통계 및 로그
        results_frame = ctk.CTkFrame(self)
        results_frame.grid(row=1, column=1, padx=(0, 20), pady=(0, 20), sticky="nsew")
        results_frame.grid_columnconfigure(0, weight=1)
        results_frame.grid_rowconfigure(1, weight=1)

        tab_view = ctk.CTkTabview(results_frame, anchor="w")
        tab_view.pack(fill="both", expand=True, padx=10, pady=10)
        tab_view.add("요약")
        tab_view.add("로그")

        # 통계 탭
        summary_tab = tab_view.tab("요약")
        self.summary_tree = ttk.Treeview(summary_tab, columns=("Metric", "Value"), show="headings")
        self.summary_tree.heading("Metric", text="지표")
        self.summary_tree.heading("Value", text="값")
        self.summary_tree.pack(fill="both", expand=True, padx=5, pady=5)

        # 로그 탭
        log_tab = tab_view.tab("로그")
        self.log_textbox = ctk.CTkTextbox(log_tab)
        self.log_textbox.pack(fill="both", expand=True, padx=5, pady=5)
        self.log_textbox.insert("0.0", "백테스트 실행 준비 완료.\n")
        self.log_textbox.configure(state="disabled")

        # 초기화
        self.load_stock_codes()
        self.add_stock("005930") # 기본값으로 삼성전자 추가

        # 큐 처리 시작
        self.process_queue()

    def load_stock_codes(self):
        """data/stock_codes.json 파일에서 종목 목록 로드"""
        try:
            stock_codes_path = project_root / "data" / "stock_codes.json"
            if stock_codes_path.exists():
                with open(stock_codes_path, 'r', encoding='utf-8') as f:
                    self.stock_data = json.load(f)
                
                self.stock_map = {f"{item['code']} - {item['name']}": item['code'] for item in self.stock_data}
                self.stock_name_map = {item['code']: item['name'] for item in self.stock_data}
                
                self.symbols_combobox.configure(values=list(self.stock_map.keys()))
            else:
                self.log_message("stock_codes.json 파일을 찾을 수 없습니다.", "error")
                self.stock_data = []
                self.stock_map = {}
                self.stock_name_map = {}
        except Exception as e:
            self.log_message(f"종목 코드 로딩 실패: {e}", "error")
            self.stock_data = []
            self.stock_map = {}
            self.stock_name_map = {}

    def add_stock_callback(self):
        """종목 추가 버튼 콜백"""
        selected = self.symbols_combobox.get()
        if selected in self.stock_map:
            stock_code = self.stock_map[selected]
            self.add_stock(stock_code)
        else:
            self.log_message(f"'{selected}'는 유효한 종목이 아닙니다.", "warning")

    def add_stock(self, stock_code: str):
        """선택된 종목 목록에 종목 추가"""
        if stock_code in self.selected_stocks:
            self.log_message(f"{stock_code}는 이미 추가된 종목입니다.", "warning")
            return
        
        stock_name = self.stock_name_map.get(stock_code, "알 수 없음")
        
        item_frame = ctk.CTkFrame(self.selected_stocks_frame, fg_color="transparent")
        item_frame.pack(fill="x", pady=2)
        
        label = ctk.CTkLabel(item_frame, text=f"{stock_code} - {stock_name}")
        label.pack(side="left", padx=(5, 0))
        
        remove_button = ctk.CTkButton(
            item_frame, text="X", width=20, height=20,
            command=lambda sc=stock_code: self.remove_stock(sc)
        )
        remove_button.pack(side="right", padx=(0, 5))
        
        self.selected_stocks[stock_code] = item_frame
        self.log_message(f"{stock_name}({stock_code}) 추가됨.", "info")

    def remove_stock(self, stock_code: str):
        """선택된 종목 목록에서 종목 제거"""
        if stock_code in self.selected_stocks:
            widget = self.selected_stocks[stock_code]
            widget.destroy()
            del self.selected_stocks[stock_code]
            stock_name = self.stock_name_map.get(stock_code, "")
            self.log_message(f"{stock_name}({stock_code}) 제거됨.", "info")

    def run_backtest_callback(self):
        """백테스트 실행 버튼 콜백"""
        if self.backtest_thread and self.backtest_thread.is_alive():
            self.log_message("백테스트가 이미 실행 중입니다.", "warning")
            return

        # UI 초기화
        self.log_message("백테스트 시작...", "info", clear=True)
        self.update_summary_results({})
        self.clear_performance_chart()
        
        self.run_button.configure(state="disabled", text="실행 중...")

        # 백테스트 스레드 생성 및 시작
        self.backtest_thread = threading.Thread(
            target=self._run_backtest_thread,
            daemon=True
        )
        self.backtest_thread.start()

    def _run_backtest_thread(self):
        """백그라운드에서 백테스트를 실행하는 내부 함수"""
        try:
            if not AdvancedBacktester:
                raise RuntimeError("AdvancedBacktester 모듈이 로드되지 않았습니다.")

            # 설정값 가져오기
            strategy = self.strategy_var.get()
            symbols = [s.strip() for s in self.symbols_entry.get().split(',') if s.strip()]
            start_date = self.start_date_entry.get()
            end_date = self.end_date_entry.get()
            initial_capital = int(self.capital_entry.get())

            if not symbols:
                raise ValueError("종목 코드를 입력해야 합니다.")

            # 백테스터 실행
            backtester = AdvancedBacktester()
            backtester.initial_capital = initial_capital
            
            result = backtester.run_backtest(
                symbols=symbols,
                start_date=start_date,
                end_date=end_date,
                strategy_name=strategy
            )
            
            # 결과를 큐에 넣기
            self.result_queue.put(result)

        except Exception as e:
            self.result_queue.put(e)

    def process_queue(self):
        """결과 큐를 주기적으로 확인하고 UI를 업데이트"""
        try:
            result = self.result_queue.get_nowait()

            if isinstance(result, BacktestResult):
                self.log_message("백테스트가 성공적으로 완료되었습니다.", "info")
                self.update_summary_results(result.to_dict())
                self.update_performance_chart(result.portfolio_history)
                self.update_trade_log(result.trades)
            elif isinstance(result, Exception):
                self.log_message(f"백테스트 실패: {result}", "error")
        
        except queue.Empty:
            pass # 큐가 비어있으면 아무것도 하지 않음

        finally:
            # 스레드가 종료되었으면 버튼 활성화
            if self.backtest_thread and not self.backtest_thread.is_alive():
                 self.run_button.configure(state="normal", text="백테스트 실행")

            self.after(100, self.process_queue) # 100ms 마다 다시 확인

    def log_message(self, msg: str, level: str = "info", clear: bool = False):
        """로그 텍스트박스에 메시지 추가"""
        self.log_textbox.configure(state="normal")
        if clear:
            self.log_textbox.delete("0.0", "end")
        
        timestamp = pd.Timestamp.now().strftime('%H:%M:%S')
        log_entry = f"[{timestamp}] [{level.upper()}] {msg}\n"
        
        self.log_textbox.insert("end", log_entry)
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    def update_summary_results(self, results: dict):
        """통계 결과 업데이트"""
        # 기존 데이터 삭제
        for item in self.summary_tree.get_children():
            self.summary_tree.delete(item)
        # 새 데이터 추가
        for metric, value in results.items():
            # 포맷팅
            if isinstance(value, float):
                if "pct" in metric or "return" in metric or "rate" in metric or "수익률" in metric or "율" in metric:
                    value_str = f"{value:.2%}"
                else:
                    value_str = f"{value:,.2f}"
            else:
                value_str = str(value)
            self.summary_tree.insert("", "end", values=(metric, value_str))

    def clear_performance_chart(self):
        """성과 그래프 초기화"""
        for widget in self.chart_frame.winfo_children():
            widget.destroy()
        ctk.CTkLabel(self.chart_frame, text="성과 차트", font=ctk.CTkFont(size=16)).pack(pady=10)

    def update_performance_chart(self, portfolio_history: pd.DataFrame):
        """성과 그래프 업데이트"""
        self.clear_performance_chart()

        if portfolio_history.empty:
            self.log_message("플롯할 포트폴리오 기록이 없습니다.", "warning")
            return

        fig, ax = plt.subplots(facecolor="#2B2B2B")
        ax.set_facecolor("#2B2B2B")
        
        ax.plot(portfolio_history.index, portfolio_history['total_value'], color='cyan')
        
        ax.set_title("백테스트 성과", color='white')
        ax.set_xlabel("날짜", color='white')
        ax.set_ylabel("포트폴리오 가치 (KRW)", color='white')
        ax.tick_params(axis='x', colors='white', rotation=30)
        ax.tick_params(axis='y', colors='white')
        ax.grid(True, color='gray', linestyle='--', linewidth=0.5)
        
        for spine in ax.spines.values():
            spine.set_edgecolor('white')
            
        fig.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(side="top", fill="both", expand=True, padx=10, pady=10)

    def update_trade_log(self, trades: list):
        """거래 로그 탭 업데이트 (구현 필요)"""
        # TODO: 거래 로그를 별도 탭에 테이블 형태로 표시
        pass

class OptimizationFrame(ctk.CTkFrame):
    """포트폴리오 최적화 프레임"""
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.optimization_thread: Optional[threading.Thread] = None
        self.result_queue = queue.Queue()

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(0, weight=1)

        # 1. 설정 프레임 (좌측)
        settings_frame = ctk.CTkFrame(self, width=300)
        settings_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        settings_frame.grid_propagate(False)
        settings_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(settings_frame, text="최적화 설정", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(15, 10))

        # 최적화 방법 선택
        ctk.CTkLabel(settings_frame, text="최적화 방법").pack(anchor="w", padx=15, pady=(10, 0))
        self.method_var = ctk.StringVar(value="max_sharpe")
        method_menu = ctk.CTkOptionMenu(settings_frame, variable=self.method_var, values=["max_sharpe", "min_vol", "risk_parity"])
        method_menu.pack(fill="x", padx=15, pady=5)

        # 종목 코드
        ctk.CTkLabel(settings_frame, text="종목코드 (쉼표로 구분)").pack(anchor="w", padx=15, pady=(10, 0))
        self.symbols_entry = ctk.CTkEntry(settings_frame, placeholder_text="예: 005930,035720,000660")
        self.symbols_entry.pack(fill="x", padx=15, pady=5)
        self.symbols_entry.insert(0, "005930,035720,000660,068270")

        # 기간 설정
        ctk.CTkLabel(settings_frame, text="분석 기간").pack(anchor="w", padx=15, pady=(10, 0))
        date_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        date_frame.pack(fill="x", padx=15, pady=5)
        date_frame.grid_columnconfigure((0, 1), weight=1)
        
        self.start_date_entry = ctk.CTkEntry(date_frame)
        self.start_date_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.start_date_entry.insert(0, "2023-01-01")
        
        self.end_date_entry = ctk.CTkEntry(date_frame)
        self.end_date_entry.grid(row=0, column=1, sticky="ew", padx=(5, 0))
        self.end_date_entry.insert(0, "2023-12-31")

        # 실행 버튼
        self.run_button = ctk.CTkButton(settings_frame, text="최적화 실행", command=self.run_optimization_callback, height=40)
        self.run_button.pack(fill="x", padx=15, pady=20)

        # 2. 결과 표시 프레임 (우측)
        results_frame = ctk.CTkFrame(self)
        results_frame.grid(row=0, column=1, padx=(0, 20), pady=20, sticky="nsew")
        results_frame.grid_rowconfigure(0, weight=1)
        results_frame.grid_rowconfigure(1, weight=1)
        results_frame.grid_columnconfigure(0, weight=1)

        # 파이 차트 프레임
        self.pie_chart_frame = ctk.CTkFrame(results_frame)
        self.pie_chart_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        ctk.CTkLabel(self.pie_chart_frame, text="최적 비중", font=ctk.CTkFont(size=16)).pack(pady=10)

        # 결과 테이블 프레임
        self.table_frame = ctk.CTkFrame(results_frame)
        self.table_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        
        self.summary_tree = ttk.Treeview(self.table_frame, columns=("Symbol", "Weight", "Return", "Volatility"), show="headings")
        self.summary_tree.heading("Symbol", text="종목")
        self.summary_tree.heading("Weight", text="비중")
        self.summary_tree.heading("Return", text="기대수익률")
        self.summary_tree.heading("Volatility", text="변동성")
        self.summary_tree.pack(fill="both", expand=True, padx=5, pady=5)

        # 큐 처리 시작
        self.process_queue()

    def run_optimization_callback(self):
        """최적화 실행 버튼 콜백"""
        if self.optimization_thread and self.optimization_thread.is_alive():
            print("최적화가 이미 실행 중입니다.")
            return

        self.run_button.configure(state="disabled", text="실행 중...")
        self.clear_results()

        self.optimization_thread = threading.Thread(
            target=self._run_optimization_thread,
            daemon=True
        )
        self.optimization_thread.start()

    def _run_optimization_thread(self):
        """백그라운드에서 최적화를 실행하는 내부 함수"""
        try:
            if not PortfolioOptimizer:
                raise RuntimeError("PortfolioOptimizer 모듈이 로드되지 않았습니다.")

            # 설정값 가져오기
            method = self.method_var.get()
            symbols = [s.strip() for s in self.symbols_entry.get().split(',') if s.strip()]
            start_date = self.start_date_entry.get()
            end_date = self.end_date_entry.get()

            if not symbols:
                raise ValueError("종목 코드를 입력해야 합니다.")

            # 최적화 실행
            optimizer = PortfolioOptimizer()
            result = optimizer.run_optimization(
                symbols=symbols,
                start_date=start_date,
                end_date=end_date,
                opt_method=method
            )
            self.result_queue.put(result)

        except Exception as e:
            self.result_queue.put(e)

    def process_queue(self):
        """결과 큐를 주기적으로 확인하고 UI를 업데이트"""
        try:
            result = self.result_queue.get_nowait()

            if isinstance(result, OptimizationResult):
                print("최적화가 성공적으로 완료되었습니다.")
                self.update_pie_chart(result.weights)
                self.update_table(result)
            elif isinstance(result, Exception):
                print(f"최적화 실패: {result}")
            elif result is None:
                print("최적화 결과가 없습니다.")

        except queue.Empty:
            pass

        finally:
            if self.optimization_thread and not self.optimization_thread.is_alive():
                self.run_button.configure(state="normal", text="최적화 실행")
            self.after(100, self.process_queue)

    def clear_results(self):
        """결과 표시 영역 초기화"""
        for widget in self.pie_chart_frame.winfo_children():
            if isinstance(widget, FigureCanvasTkAgg):
                widget.get_tk_widget().destroy()
        
        for item in self.summary_tree.get_children():
            self.summary_tree.delete(item)

    def update_pie_chart(self, weights: Dict[str, float]):
        """파이 차트 업데이트"""
        # self.clear_results() # clear_results는 콜백 시작 시 한 번만 호출

        for widget in self.pie_chart_frame.winfo_children():
            if isinstance(widget, FigureCanvasTkAgg):
                widget.get_tk_widget().destroy()

        labels = list(weights.keys())
        sizes = list(weights.values())
        
        fig, ax = plt.subplots(facecolor="#2B2B2B")
        ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90,
               textprops={'color':"w"}, wedgeprops={'edgecolor': 'white'})
        ax.axis('equal')
        ax.set_title("최적 포트폴리오 비중", color='white')
        
        fig.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, master=self.pie_chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(side="top", fill="both", expand=True, padx=10, pady=10)

    def update_table(self, result: "OptimizationResult"):
        """결과 테이블 업데이트"""
        for symbol, weight in result.weights.items():
            # TODO: 개별 종목의 기대수익률/변동성 표시 기능 추가 필요
            self.summary_tree.insert("", "end", values=(symbol, f"{weight:.2%}", "N/A", "N/A"))
        
        self.summary_tree.insert("", "end", values=("---", "---", "---", "---"))
        self.summary_tree.insert("", "end", values=("합계", "100.00%", f"{result.expected_return:.2%}", f"{result.expected_volatility:.2%}"))


class LiveTradingFrame(ctk.CTkFrame):
    """실시간 트레이딩 프레임"""
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.orchestrator: Optional[LiveTradingOrchestrator] = None
        self.orchestrator_thread: Optional[threading.Thread] = None
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # 1. 제어 및 상태 프레임 (상단)
        top_frame = ctk.CTkFrame(self)
        top_frame.grid(row=0, column=0, columnspan=2, padx=20, pady=20, sticky="ew")
        top_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        ctk.CTkLabel(top_frame, text="실시간 트레이딩 상태:", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, padx=10, pady=10)
        self.status_label = ctk.CTkLabel(top_frame, text="중지됨", text_color="red", font=ctk.CTkFont(size=16))
        self.status_label.grid(row=0, column=1, padx=10, pady=10)

        self.start_button = ctk.CTkButton(top_frame, text="트레이딩 시작", command=self.start_trading)
        self.start_button.grid(row=0, column=2, padx=10, pady=10)
        self.stop_button = ctk.CTkButton(top_frame, text="트레이딩 중지", command=self.stop_trading, state="disabled")
        self.stop_button.grid(row=0, column=3, padx=10, pady=10)
        # Operator approval UI (pending approvals)
        try:
            self.approval_button = ctk.CTkButton(top_frame, text="승인 대기", command=self.open_approval_window)
            self.approval_button.grid(row=0, column=4, padx=10, pady=10)
        except Exception:
            # If customtkinter layout differs, ignore optional button
            pass

        # 2. 포지션 프레임 (좌측)
        positions_frame = ctk.CTkFrame(self)
        positions_frame.grid(row=1, column=0, padx=(20, 10), pady=(0, 20), sticky="nsew")
        positions_frame.grid_rowconfigure(1, weight=1)
        positions_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(positions_frame, text="현재 포지션", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, padx=10, pady=10)
        
        self.positions_tree = ttk.Treeview(positions_frame, columns=("Symbol", "Qty", "Avg Price", "P&L", "Value"), show="headings")
        self.positions_tree.heading("Symbol", text="종목")
        self.positions_tree.heading("Qty", text="수량")
        self.positions_tree.heading("Avg Price", text="평균 단가")
        self.positions_tree.heading("P&L", text="평가손익")
        self.positions_tree.heading("Value", text="평가금액")
        self.positions_tree.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

        # 3. 로그 프레임 (우측)
        log_frame = ctk.CTkFrame(self)
        log_frame.grid(row=1, column=1, padx=(10, 20), pady=(0, 20), sticky="nsew")
        log_frame.grid_rowconfigure(1, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(log_frame, text="거래 로그", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, padx=10, pady=10)
        
        self.log_textbox = ctk.CTkTextbox(log_frame)
        self.log_textbox.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.log_textbox.insert("0.0", "실시간 트레이딩 엔진이 중지되었습니다.\n")
        self.log_textbox.configure(state="disabled")

    def start_trading(self):
        """트레이딩 시작 버튼 콜백"""
        if self.orchestrator_thread and self.orchestrator_thread.is_alive():
            self.log_message("이미 트레이딩이 실행 중입니다.", "warning")
            return

        self.log_message("실시간 트레이딩 시스템을 시작합니다...", "info", clear=True)
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")

        # 오케스트레이터 인스턴스 생성 (GUI 콜백 전달)
        self.orchestrator = LiveTradingOrchestrator(
            gui_log_callback=self.log_message,
            gui_status_callback=self.update_status,
            gui_position_callback=self.update_positions
        )

        # 백그라운드 스레드에서 오케스트레이터 실행
        self.orchestrator_thread = threading.Thread(
            target=self.orchestrator.run,
            daemon=True
        )
        self.orchestrator_thread.start()

    def stop_trading(self):
        """트레이딩 중지 버튼 콜백"""
        if self.orchestrator:
            self.log_message("트레이딩 중지를 요청합니다...", "info")
            self.orchestrator.stop()
            self.stop_button.configure(state="disabled", text="중지 중...")
        else:
            self.log_message("실행 중인 트레이딩 세션이 없습니다.", "warning")

    def update_status(self, status: str):
        """오케스트레이터로부터 상태 업데이트를 받음"""
        if status == "RUNNING":
            self.status_label.configure(text="실행 중", text_color="green")
            self.start_button.configure(state="disabled")
            self.stop_button.configure(state="normal", text="트레이딩 중지")
        elif status == "STOPPED":
            self.status_label.configure(text="중지됨", text_color="red")
            self.start_button.configure(state="normal")
            self.stop_button.configure(state="disabled")
            self.orchestrator = None
            self.orchestrator_thread = None
        elif status == "ERROR":
            self.status_label.configure(text="오류", text_color="red")
            self.start_button.configure(state="normal")
            self.stop_button.configure(state="disabled")

    def update_positions(self, positions: list):
        """오케스트레이터로부터 포지션 정보를 받아 테이블 업데이트"""
        self.after(0, self._update_positions_table, positions)

    def _update_positions_table(self, positions: list):
        """스레드 안전하게 포지션 테이블을 업데이트하는 내부 함수"""
        # 기존 데이터 삭제
        for item in self.positions_tree.get_children():
            self.positions_tree.delete(item)
        
        # 새 데이터 추가
        for pos in positions:
            try:
                symbol = pos.get('pdno', '')
                quantity = int(pos.get('hldg_qty', 0))
                avg_price = float(pos.get('pchs_avg_prc', 0))
                pnl = float(pos.get('evlu_pfls_amt', 0))
                value = float(pos.get('evlu_amt', 0))
                
                pnl_str = f"{pnl:,.0f}"
                text_color = "red" if pnl < 0 else ("green" if pnl > 0 else "white")

                # Treeview 아이템 추가 (태그 사용)
                self.positions_tree.insert("", "end", values=(
                    symbol,
                    f"{quantity:,}",
                    f"{avg_price:,.0f}",
                    pnl_str,
                    f"{value:,.0f}"
                ), tags=(text_color,))

            except (ValueError, TypeError) as e:
                self.log_message(f"포지션 데이터 처리 오류: {pos} - {e}", "error")

        # 태그별 색상 설정
        self.positions_tree.tag_configure("green", foreground="green")
        self.positions_tree.tag_configure("red", foreground="red")
        self.positions_tree.tag_configure("white", foreground="white")


    def log_message(self, msg: str, level: str = "info", clear: bool = False):
        """GUI 로그 박스에 메시지 추가 (스레드 안전)"""
        # `after`를 사용해 메인 스레드에서 UI 업데이트를 예약
        self.after(0, self._update_log_text, msg, level, clear)

    def _update_log_text(self, msg: str, level: str, clear: bool):
        """실제 로그 텍스트를 업데이트하는 내부 함수"""
        self.log_textbox.configure(state="normal")
        if clear:
            self.log_textbox.delete("0.0", "end")
        
        timestamp = pd.Timestamp.now().strftime('%H:%M:%S')
        log_entry = f"[{timestamp}] {msg}\n"
        
        self.log_textbox.insert("end", log_entry)
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    # --- Operator approval window ---
    def open_approval_window(self):
        # Enhanced approval window: auto-refresh, double-click detail, confirm dialogs
        try:
            win = ctk.CTkToplevel(self)
            win.title("승인 대기 목록")
            win.geometry("800x450")

            listbox = ttk.Treeview(win, columns=("id", "symbol", "type", "qty", "price", "requested_at"), show='headings')
            listbox.heading('id', text='Approval ID')
            listbox.heading('symbol', text='종목')
            listbox.heading('type', text='타입')
            listbox.heading('qty', text='수량')
            listbox.heading('price', text='가격')
            listbox.heading('requested_at', text='요청시간')
            listbox.column('id', width=160)
            listbox.column('symbol', width=100)
            listbox.column('type', width=80)
            listbox.column('qty', width=80)
            listbox.column('price', width=120)
            listbox.column('requested_at', width=160)
            listbox.pack(fill='both', expand=True, padx=10, pady=10)

            # Detail pane on the right
            right_frame = ctk.CTkFrame(win)
            right_frame.pack(fill='y', side='right', padx=(0,10), pady=10)
            detail_text = ScrolledText(right_frame, width=40, height=20)
            detail_text.pack(fill='both', expand=True)
            detail_text.configure(state='disabled')

            btn_frame = ctk.CTkFrame(win)
            btn_frame.pack(fill='x', padx=10, pady=(0,10))

            auto_refresh_ms = 5000
            refresh_job = {'id': None}

            def load_pending():
                try:
                    items = approval_manager.list_pending()
                except Exception as e:
                    self.log_message(f"승인 목록 로드 실패: {e}", 'error')
                    return []
                rows = []
                for rec in items:
                    aid = rec.get('approval_id')
                    o = rec.get('order', {})
                    rows.append((aid, o.get('symbol'), o.get('order_type'), o.get('quantity'), o.get('price'), o.get('requested_at'), rec))
                return rows

            def refresh():
                for it in listbox.get_children():
                    listbox.delete(it)
                for aid, symbol, otype, qty, price, req_at, rec in load_pending():
                    listbox.insert('', 'end', iid=aid, values=(aid, symbol, otype, qty, price, req_at))

            def schedule_refresh():
                refresh()
                refresh_job['id'] = win.after(auto_refresh_ms, schedule_refresh)

            def cancel_refresh():
                try:
                    if refresh_job['id'] is not None:
                        win.after_cancel(refresh_job['id'])
                except Exception:
                    pass

            def show_detail(event=None):
                sel = listbox.selection()
                if not sel:
                    return
                aid = sel[0]
                # find record
                rec = None
                for _aid, _symbol, _otype, _qty, _price, _req, r in load_pending():
                    if _aid == aid:
                        rec = r
                        break
                if rec is None:
                    detail_text.configure(state='normal')
                    detail_text.delete('1.0', 'end')
                    detail_text.insert('1.0', '레코드를 찾을 수 없습니다.')
                    detail_text.configure(state='disabled')
                    return
                detail_text.configure(state='normal')
                detail_text.delete('1.0', 'end')
                detail_text.insert('1.0', json.dumps(rec, ensure_ascii=False, indent=2))
                detail_text.configure(state='disabled')

            def confirm_and_act(action: str):
                sel = listbox.selection()
                if not sel:
                    messagebox.showinfo('알림', '하나 이상의 항목을 선택하세요')
                    return
                if not messagebox.askyesno('확인', f"선택된 {len(sel)}개 항목을 '{action}' 하시겠습니까?"):
                    return
                operator = os.environ.get('USER') or os.environ.get('USERNAME') or 'operator'
                errors = []
                for aid in sel:
                    try:
                        if action == '승인':
                            approval_manager.approve(aid, operator=operator)
                        else:
                            approval_manager.reject(aid, operator=operator)
                    except Exception as e:
                        errors.append(f"{aid}: {e}")
                if errors:
                    self.log_message('승인/거부 중 오류: ' + '; '.join(errors), 'error')
                    messagebox.showwarning('경고', '일부 항목 처리 중 오류가 발생했습니다. 로그를 확인하세요.')
                refresh()

            def approve():
                confirm_and_act('승인')

            def reject():
                confirm_and_act('거부')

            approve_btn = ctk.CTkButton(btn_frame, text='승인', command=approve)
            approve_btn.pack(side='left', padx=6)
            reject_btn = ctk.CTkButton(btn_frame, text='거부', command=reject)
            reject_btn.pack(side='left', padx=6)
            refresh_btn = ctk.CTkButton(btn_frame, text='새로고침', command=refresh)
            refresh_btn.pack(side='right', padx=6)

            # bind double-click to show detail
            listbox.bind('<Double-1>', show_detail)

            # on close, cancel scheduled refresh
            def on_close():
                cancel_refresh()
                win.destroy()

            win.protocol('WM_DELETE_WINDOW', on_close)

            # initial load and schedule
            refresh()
            schedule_refresh()

        except Exception as e:
            self.log_message(f"승인 대기 창 열기 실패: {e}", 'error')


class SettingsFrame(ctk.CTkFrame):
    """설정 프레임"""
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        self.grid_columnconfigure(0, weight=1)
        
        settings_container = ctk.CTkFrame(self, width=600)
        settings_container.grid(row=0, column=0, pady=50, padx=100)
        settings_container.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(settings_container, text="API 설정", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(15, 10), anchor="w", padx=20)

        # KIS APP Key
        ctk.CTkLabel(settings_container, text="KIS App Key").pack(anchor="w", padx=20, pady=(10, 0))
        self.app_key_entry = ctk.CTkEntry(settings_container, placeholder_text="KIS App Key를 입력하세요", show="*")
        self.app_key_entry.pack(fill="x", padx=20, pady=5)

        # KIS APP Secret
        ctk.CTkLabel(settings_container, text="KIS App Secret").pack(anchor="w", padx=20, pady=(10, 0))
        self.app_secret_entry = ctk.CTkEntry(settings_container, placeholder_text="KIS App Secret을 입력하세요", show="*")
        self.app_secret_entry.pack(fill="x", padx=20, pady=5)
        
        # KIS Account
        ctk.CTkLabel(settings_container, text="KIS 계좌번호").pack(anchor="w", padx=20, pady=(10, 0))
        self.account_entry = ctk.CTkEntry(settings_container, placeholder_text="계좌번호를 입력하세요 (예: 12345678-01)")
        self.account_entry.pack(fill="x", padx=20, pady=5)

        # 저장 버튼
        save_button = ctk.CTkButton(settings_container, text="설정 저장", command=self.save_settings)
        save_button.pack(fill="x", padx=20, pady=(15,10))

        # 상태 메시지 레이블
        self.status_label = ctk.CTkLabel(settings_container, text="", text_color="green")
        self.status_label.pack(fill="x", padx=20, pady=(0, 10))

        self.load_settings()

    def load_settings(self):
        """secrets.json 파일에서 설정을 로드하여 UI에 표시"""
        try:
            secrets_path = project_root / "secrets.json"
            if secrets_path.exists():
                with open(secrets_path, 'r', encoding='utf-8') as f:
                    secrets = json.load(f)
                
                self.app_key_entry.insert(0, secrets.get("KIS_APP_KEY", ""))
                self.app_secret_entry.insert(0, secrets.get("KIS_APP_SECRET", ""))
                
                account_no = secrets.get("KOREA_ACCOUNT_NO", "")
                account_prdt = secrets.get("KOREA_ACCOUNT_PRDT", "")
                if account_no and account_prdt:
                    self.account_entry.insert(0, f"{account_no}-{account_prdt}")
                elif account_no:
                     self.account_entry.insert(0, account_no)

                self.status_label.configure(text="설정을 성공적으로 불러왔습니다.", text_color="gray")
            else:
                self.status_label.configure(text="secrets.json 파일을 찾을 수 없습니다.", text_color="orange")

        except Exception as e:
            self.status_label.configure(text=f"설정 로드 오류: {e}", text_color="red")

    def save_settings(self):
        """UI의 설정을 secrets.json 파일에 저장"""
        try:
            secrets_path = project_root / "secrets.json"
            
            # 기존 파일 읽기
            if secrets_path.exists():
                with open(secrets_path, 'r', encoding='utf-8') as f:
                    secrets = json.load(f)
            else:
                secrets = {}

            # 값 업데이트
            app_key = self.app_key_entry.get()
            app_secret = self.app_secret_entry.get()
            account_full = self.account_entry.get()
            
            secrets["KIS_APP_KEY"] = app_key
            secrets["KOREA_APP_KEY"] = app_key
            secrets["KIS_APP_SECRET"] = app_secret
            secrets["KOREA_APP_SECRET"] = app_secret
            
            if '-' in account_full:
                account_no, account_prdt = account_full.split('-', 1)
                secrets["KOREA_ACCOUNT_NO"] = account_no
                secrets["KOREA_ACCOUNT_PRDT"] = account_prdt
            else:
                secrets["KOREA_ACCOUNT_NO"] = account_full
                secrets["KOREA_ACCOUNT_PRDT"] = "01" # 기본값

            # 파일에 쓰기
            with open(secrets_path, 'w', encoding='utf-8') as f:
                json.dump(secrets, f, indent=2)

            self.status_label.configure(text="설정을 성공적으로 저장했습니다!", text_color="green")

        except Exception as e:
            self.status_label.configure(text=f"설정 저장 오류: {e}", text_color="red")


if __name__ == "__main__":
    # Pandas 임포트 (그래프용)
    try:
        import pandas as pd
    except ImportError:
        print("Pandas is not installed. Please install it using: pip install pandas")
        # sys.exit(1) # GUI 테스트를 위해 일단 주석 처리
        
    app = TradingDashboard()
    app.mainloop()