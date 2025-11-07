"""
Discord 웹훅을 이용한 알림 시스템
- 거래 체결 알림
- 수익률 리포트
- 시스템 상태 알림
- 예측 결과 알림
"""
import os
import json
import requests
from datetime import datetime
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class DiscordBot:
    """디스코드 웹훅 알림 봇"""

    def __init__(self):
        self.webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')

        if not self.webhook_url:
            logger.warning("디스코드 웹훅 URL이 설정되지 않았습니다. 알림 기능이 비활성화됩니다.")
            self.enabled = False
        else:
            self.enabled = True

        # 봇 정보
        self.bot_name = "AI Trading Bot"
        self.bot_avatar_url = "https://cdn.discordapp.com/attachments/example/trading-bot-avatar.png"

    def send_message(self, content: str = "", embeds: list = None) -> bool:
        """디스코드 메시지 전송"""
        if not self.enabled:
            logger.info(f"[알림] {content}")  # 콘솔에 출력
            return True

        try:
            payload = {
                "username": self.bot_name,
                "avatar_url": self.bot_avatar_url,
                "content": content,
                "embeds": embeds or []
            }

            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )
            response.raise_for_status()

            logger.info("디스코드 메시지 전송 완료")
            return True

        except Exception as e:
            logger.error(f"디스코드 메시지 전송 실패: {e}")
            return False

    def send_trade_alert(self, trade_data: Dict[str, Any]):
        """거래 체결 알림"""
        stock_code = trade_data.get('stock_code', 'Unknown')
        side = trade_data.get('side', 'unknown')
        quantity = trade_data.get('quantity', 0)
        price = trade_data.get('price', 0)
        pnl = trade_data.get('pnl', 0)

        # 색상 설정 (매수: 초록, 매도: 빨강)
        color = 0x00ff00 if side == "buy" else 0xff0000

        # 이모지 선택
        side_emoji = "🟢" if side == "buy" else "🔴"
        pnl_emoji = "💰" if pnl > 0 else "📉" if pnl < 0 else "⚪"

        embed = {
            "title": f"{side_emoji} 거래 체결 알림",
            "color": color,
            "fields": [
                {
                    "name": "📊 종목코드",
                    "value": f"`{stock_code}`",
                    "inline": True
                },
                {
                    "name": "📈 수량",
                    "value": f"`{quantity:,}주`",
                    "inline": True
                },
                {
                    "name": "💎 가격",
                    "value": f"`{price:,}원`",
                    "inline": True
                }
            ],
            "timestamp": datetime.now().isoformat(),
            "footer": {
                "text": "AI 자동매매 봇"
            }
        }

        if pnl != 0:
            pnl_rate = (pnl / (price * quantity)) * 100
            embed["fields"].append({
                "name": f"{pnl_emoji} 손익",
                "value": f"`{pnl:+,.0f}원` ({pnl_rate:+.2f}%)",
                "inline": False
            })

        self.send_message(embeds=[embed])

    def send_daily_report(self, summary: Dict[str, Any]):
        """일일 리포트 전송"""
        total_trades = summary.get('total_trades', 0)
        win_rate = summary.get('win_rate', 0)
        total_profit = summary.get('total_profit', 0)
        max_drawdown = summary.get('max_drawdown', 0)
        sharpe_ratio = summary.get('sharpe_ratio', 0)

        # 색상 설정 (수익: 초록, 손실: 빨강)
        color = 0x00ff00 if total_profit > 0 else 0xff0000 if total_profit < 0 else 0xffaa00

        embed = {
            "title": "📊 일일 거래 리포트",
            "color": color,
            "fields": [
                {
                    "name": "💰 총 손익",
                    "value": f"`{total_profit:+,.0f}원`",
                    "inline": True
                },
                {
                    "name": "🎯 승률",
                    "value": f"`{win_rate:.1f}%`",
                    "inline": True
                },
                {
                    "name": "📋 거래 횟수",
                    "value": f"`{total_trades}회`",
                    "inline": True
                },
                {
                    "name": "📉 최대 낙폭",
                    "value": f"`{max_drawdown:,.0f}원`",
                    "inline": True
                },
                {
                    "name": "⚡ 샤프 비율",
                    "value": f"`{sharpe_ratio:.2f}`",
                    "inline": True
                }
            ],
            "timestamp": datetime.now().isoformat(),
            "footer": {
                "text": f"리포트 일자: {datetime.now().strftime('%Y년 %m월 %d일')}"
            }
        }

        self.send_message(embeds=[embed])

    def send_system_alert(self, alert_type: str, message: str):
        """시스템 상태 알림"""
        color_map = {
            "error": 0xff0000,    # 빨강
            "warning": 0xffaa00,  # 주황
            "info": 0x0099ff,     # 파랑
            "success": 0x00ff00   # 초록
        }

        emoji_map = {
            "error": "🚨",
            "warning": "⚠️",
            "info": "ℹ️",
            "success": "✅"
        }

        color = color_map.get(alert_type, 0x808080)
        emoji = emoji_map.get(alert_type, "📢")

        embed = {
            "title": f"{emoji} 시스템 알림",
            "description": message,
            "color": color,
            "timestamp": datetime.now().isoformat(),
            "footer": {
                "text": "시스템 모니터링"
            }
        }

        self.send_message(embeds=[embed])

    def send_prediction_alert(self, predictions: Dict[str, Any]):
        """예측 결과 알림"""
        if not predictions or 'recommendations' not in predictions:
            return

        prediction_date = predictions.get('prediction_date', 'Unknown')
        recommendations = predictions['recommendations'][:3]  # 상위 3개

        embed = {
            "title": "🤖 AI 예측 결과",
            "description": f"📅 예측일: **{prediction_date}**",
            "color": 0x9932cc,  # 보라색
            "fields": [],
            "timestamp": datetime.now().isoformat(),
            "footer": {
                "text": "AI 예측 엔진"
            }
        }

        for i, rec in enumerate(recommendations):
            stock_code = rec.get('code', 'Unknown')
            probability = rec.get('up_probability', 0)
            gain_rate = rec.get('estimated_gain_rate', 0)
            last_price = rec.get('last_close_price', 0)

            # 신호 강도에 따른 이모지
            if probability >= 70:
                signal_emoji = "🔥"
            elif probability >= 60:
                signal_emoji = "⭐"
            else:
                signal_emoji = "💡"

            embed["fields"].append({
                "name": f"{signal_emoji} 추천 #{i+1}: {stock_code}",
                "value": f"상승확률: `{probability}%`\n예상수익: `+{gain_rate:.1f}%`\n현재가: `{last_price:,}원`",
                "inline": True
            })

        self.send_message(embeds=[embed])

    def send_rich_message(self, title: str, description: str, fields: list = None, color: int = 0x0099ff):
        """풍부한 임베드 메시지 전송"""
        embed = {
            "title": title,
            "description": description,
            "color": color,
            "fields": fields or [],
            "timestamp": datetime.now().isoformat(),
            "footer": {
                "text": "AI Trading Bot"
            }
        }

        self.send_message(embeds=[embed])


class AlertManager:
    """통합 알림 관리자 (디스코드 버전)"""

    def __init__(self):
        self.discord_bot = DiscordBot()
        self.last_daily_report = None

    def notify_trade(self, trade_data: Dict[str, Any]):
        """거래 체결 알림"""
        self.discord_bot.send_trade_alert(trade_data)
        self._save_alert_log("trade", trade_data)

    def notify_daily_report(self, summary: Dict[str, Any], force: bool = False):
        """일일 리포트 알림"""
        today = datetime.now().date()

        # 하루에 한 번만 전송
        if self.last_daily_report == today and not force:
            return

        self.discord_bot.send_daily_report(summary)
        self.last_daily_report = today
        self._save_alert_log("daily_report", summary)

    def notify_system(self, alert_type: str, message: str):
        """시스템 알림"""
        self.discord_bot.send_system_alert(alert_type, message)
        self._save_alert_log("system", {"type": alert_type, "message": message})

    def notify_prediction(self, predictions: Dict[str, Any]):
        """예측 결과 알림"""
        self.discord_bot.send_prediction_alert(predictions)
        self._save_alert_log("prediction", predictions)

    def notify_performance_milestone(self, milestone_data: Dict[str, Any]):
        """성과 이정표 알림 (새로운 기능)"""
        milestone_type = milestone_data.get('type', 'unknown')
        value = milestone_data.get('value', 0)

        title_map = {
            'profit_milestone': '💰 수익 이정표 달성!',
            'loss_limit': '⚠️ 손실 한도 경고',
            'win_streak': '🔥 연승 기록!',
            'trade_volume': '📈 거래량 이정표'
        }

        title = title_map.get(milestone_type, '📊 성과 알림')

        if milestone_type == 'profit_milestone':
            description = f"축하합니다! 총 수익이 **{value:,.0f}원**을 달성했습니다!"
            color = 0x00ff00
        elif milestone_type == 'loss_limit':
            description = f"주의! 일일 손실이 **{value:,.0f}원**에 도달했습니다."
            color = 0xff0000
        elif milestone_type == 'win_streak':
            description = f"연속 **{value}회** 수익 거래를 달성했습니다!"
            color = 0xffd700
        else:
            description = f"성과 지표: {value}"
            color = 0x0099ff

        self.discord_bot.send_rich_message(title, description, color=color)

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
    alert_manager.notify_system("success", "🚀 AI 자동매매 봇이 성공적으로 시작되었습니다!")

    # 거래 체결 알림 테스트
    test_trade = {
        "stock_code": "005930",
        "side": "buy",
        "quantity": 10,
        "price": 70000,
        "pnl": 0
    }
    alert_manager.notify_trade(test_trade)

    # 수익 거래 알림 테스트
    profit_trade = {
        "stock_code": "000660",
        "side": "sell",
        "quantity": 5,
        "price": 580000,
        "pnl": 15000
    }
    alert_manager.notify_trade(profit_trade)

    # 예측 결과 알림 테스트
    test_predictions = {
        "prediction_date": "2025-11-05",
        "recommendations": [
            {
                "code": "005930",
                "up_probability": 75,
                "estimated_gain_rate": 3.2,
                "last_close_price": 105200
            },
            {
                "code": "000660",
                "up_probability": 68,
                "estimated_gain_rate": 2.8,
                "last_close_price": 586000
            }
        ]
    }
    alert_manager.notify_prediction(test_predictions)

    # 수익 이정표 알림 테스트
    milestone = {
        "type": "profit_milestone",
        "value": 1000000
    }
    alert_manager.notify_performance_milestone(milestone)

    print("✅ 디스코드 알림 테스트 완료!")
