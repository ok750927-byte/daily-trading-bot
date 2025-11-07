"""
텔레그램 알림 봇
- 거래 체결 알림
- 수익률 리포트
- 시스템 상태 알림
"""
import os
import asyncio
import json
from datetime import datetime
from typing import Dict, Any
import requests
import logging

logger = logging.getLogger(__name__)

class TelegramBot:
    """텔레그램 알림 봇"""

    def __init__(self):
        self.bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.environ.get('TELEGRAM_CHAT_ID')

        if not self.bot_token or not self.chat_id:
            logger.warning("텔레그램 설정이 없습니다. 알림 기능이 비활성화됩니다.")
            self.enabled = False
        else:
            self.enabled = True

        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"

    def send_message(self, text: str, parse_mode: str = "Markdown") -> bool:
        """메시지 전송"""
        if not self.enabled:
            logger.info(f"[알림] {text}")  # 콘솔에 출력
            return True

        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": parse_mode
            }

            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()

            logger.info("텔레그램 메시지 전송 완료")
            return True

        except Exception as e:
            logger.error(f"텔레그램 메시지 전송 실패: {e}")
            return False

    def send_trade_alert(self, trade_data: Dict[str, Any]):
        """거래 체결 알림"""
        stock_code = trade_data.get('stock_code', 'Unknown')
        side = trade_data.get('side', 'unknown')
        quantity = trade_data.get('quantity', 0)
        price = trade_data.get('price', 0)
        pnl = trade_data.get('pnl', 0)

        # 이모지 선택
        side_emoji = "🟢 매수" if side == "buy" else "🔴 매도"
        pnl_emoji = "💰" if pnl > 0 else "📉" if pnl < 0 else "⚪"

        message = f"""
{side_emoji} *거래 체결 알림*

📊 종목: `{stock_code}`
📈 수량: `{quantity:,}주`
💎 가격: `{price:,}원`
"""

        if pnl != 0:
            message += f"{pnl_emoji} 손익: `{pnl:+,.0f}원` ({(pnl/abs(pnl)*abs(pnl)/price/quantity)*100:+.2f}%)"

        message += f"\n🕐 시간: {datetime.now().strftime('%H:%M:%S')}"

        self.send_message(message)

    def send_daily_report(self, summary: Dict[str, Any]):
        """일일 리포트 전송"""
        total_trades = summary.get('total_trades', 0)
        win_rate = summary.get('win_rate', 0)
        total_profit = summary.get('total_profit', 0)
        max_drawdown = summary.get('max_drawdown', 0)

        profit_emoji = "📈" if total_profit > 0 else "📉" if total_profit < 0 else "⚪"

        message = f"""
📊 *일일 거래 리포트*

{profit_emoji} 총 손익: `{total_profit:+,.0f}원`
🎯 승률: `{win_rate:.1f}%`
📋 거래 횟수: `{total_trades}회`
📉 최대 낙폭: `{max_drawdown:,.0f}원`

📅 {datetime.now().strftime('%Y년 %m월 %d일')}
"""

        self.send_message(message)

    def send_system_alert(self, alert_type: str, message: str):
        """시스템 상태 알림"""
        emoji_map = {
            "error": "🚨",
            "warning": "⚠️",
            "info": "ℹ️",
            "success": "✅"
        }

        emoji = emoji_map.get(alert_type, "📢")

        alert_message = f"""
{emoji} *시스템 알림*

{message}

🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

        self.send_message(alert_message)

    def send_prediction_alert(self, predictions: Dict[str, Any]):
        """예측 결과 알림"""
        if not predictions or 'recommendations' not in predictions:
            return

        prediction_date = predictions.get('prediction_date', 'Unknown')
        recommendations = predictions['recommendations'][:3]  # 상위 3개

        message = f"""
🤖 *AI 예측 결과*

📅 예측일: `{prediction_date}`

"""

        for i, rec in enumerate(recommendations):
            stock_code = rec.get('code', 'Unknown')
            probability = rec.get('up_probability', 0)
            gain_rate = rec.get('estimated_gain_rate', 0)

            # 신호 강도에 따른 이모지
            if probability >= 70:
                signal_emoji = "🔥"
            elif probability >= 60:
                signal_emoji = "⭐"
            else:
                signal_emoji = "💡"

            message += f"{signal_emoji} `{stock_code}`: {probability}% (예상수익 +{gain_rate:.1f}%)\n"

        self.send_message(message)


class AlertManager:
    """통합 알림 관리자"""

    def __init__(self):
        self.telegram_bot = TelegramBot()
        self.last_daily_report = None

    def notify_trade(self, trade_data: Dict[str, Any]):
        """거래 체결 알림"""
        self.telegram_bot.send_trade_alert(trade_data)

        # 거래 로그에 저장
        self._save_alert_log("trade", trade_data)

    def notify_daily_report(self, summary: Dict[str, Any], force: bool = False):
        """일일 리포트 알림"""
        today = datetime.now().date()

        # 하루에 한 번만 전송
        if self.last_daily_report == today and not force:
            return

        self.telegram_bot.send_daily_report(summary)
        self.last_daily_report = today

        # 알림 로그에 저장
        self._save_alert_log("daily_report", summary)

    def notify_system(self, alert_type: str, message: str):
        """시스템 알림"""
        self.telegram_bot.send_system_alert(alert_type, message)

        # 알림 로그에 저장
        self._save_alert_log("system", {"type": alert_type, "message": message})

    def notify_prediction(self, predictions: Dict[str, Any]):
        """예측 결과 알림"""
        self.telegram_bot.send_prediction_alert(predictions)

        # 알림 로그에 저장
        self._save_alert_log("prediction", predictions)

    def _save_alert_log(self, alert_type: str, data: Dict[str, Any]):
        """알림 로그 저장"""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "type": alert_type,
                "data": data
            }

            log_file = "results/alert_log.jsonl"
            os.makedirs(os.path.dirname(log_file), exist_ok=True)

            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')

        except Exception as e:
            logger.error(f"알림 로그 저장 실패: {e}")


# 사용 예제
if __name__ == "__main__":
    # 알림 매니저 초기화
    alert_manager = AlertManager()

    # 시스템 시작 알림
    alert_manager.notify_system("info", "자동매매 봇이 시작되었습니다.")

    # 거래 체결 알림 테스트
    test_trade = {
        "stock_code": "005930",
        "side": "buy",
        "quantity": 10,
        "price": 70000,
        "pnl": 0
    }
    alert_manager.notify_trade(test_trade)

    # 예측 결과 알림 테스트
    test_predictions = {
        "prediction_date": "2025-11-05",
        "recommendations": [
            {
                "code": "005930",
                "up_probability": 75,
                "estimated_gain_rate": 3.2
            },
            {
                "code": "000660",
                "up_probability": 68,
                "estimated_gain_rate": 2.8
            }
        ]
    }
    alert_manager.notify_prediction(test_predictions)

    print("알림 테스트 완료!")
