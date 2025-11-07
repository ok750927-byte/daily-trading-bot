"""
Discord 웹훅 자동 설정 스크립트
- 웹훅 URL 검증
- 테스트 메시지 전송
- 설정 파일 자동 생성
"""
import os
import requests
import json
import time
from typing import Optional, Dict, Any

def create_discord_setup_guide():
    """디스코드 웹훅 생성 가이드"""
    guide = """
🎮 Discord 웹훅 알림 설정 가이드

1️⃣ Discord 서버 및 채널 준비:
   - Discord 서버 생성 또는 기존 서버 사용
   - 알림을 받을 채널 선택 (예: #trading-alerts)

2️⃣ 웹훅 생성:
   - 채널 설정 → 연동 → 웹훅 → '새 웹훅'
   - 웹훅 이름: AI Trading Bot
   - 아바타 설정 (선택사항)
   - '웹훅 URL 복사' 클릭

3️⃣ 웹훅 URL 형식:
   - https://discord.com/api/webhooks/[WEBHOOK_ID]/[WEBHOOK_TOKEN]
   - 예: https://discord.com/api/webhooks/123456789/abcdefg-hijklmn

4️⃣ 자동 설정:
   - 아래 스크립트 실행하여 웹훅 테스트 및 설정 저장
"""
    print(guide)

class DiscordSetupManager:
    """디스코드 웹훅 설정 관리자"""

    def __init__(self):
        self.webhook_url = None

    def validate_webhook_url(self, url: str) -> bool:
        """웹훅 URL 유효성 검사"""
        try:
            # URL 형식 검사
            if not url.startswith("https://discord.com/api/webhooks/"):
                print("❌ 올바른 Discord 웹훅 URL 형식이 아닙니다.")
                print("   형식: https://discord.com/api/webhooks/[ID]/[TOKEN]")
                return False

            # 웹훅 정보 조회 테스트
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                webhook_info = response.json()
                webhook_name = webhook_info.get('name', 'Unknown')
                channel_name = webhook_info.get('channel_id', 'Unknown')
                print(f"✅ 웹훅 연결 성공: {webhook_name}")
                print(f"   채널 ID: {channel_name}")
                return True
            else:
                print(f"❌ 웹훅 접근 실패 (상태코드: {response.status_code})")
                return False

        except Exception as e:
            print(f"❌ 웹훅 검증 실패: {e}")
            return False

    def send_test_message(self, webhook_url: str) -> bool:
        """테스트 메시지 전송"""
        try:
            # 간단한 테스트 메시지
            payload = {
                "username": "AI Trading Bot",
                "content": "🧪 **연결 테스트**",
                "embeds": [{
                    "title": "🤖 Discord 알림 설정 완료!",
                    "description": "AI 자동매매 봇의 Discord 알림이 성공적으로 설정되었습니다.",
                    "color": 0x00ff00,
                    "fields": [
                        {
                            "name": "📊 알림 유형",
                            "value": "• 거래 체결 알림\n• 일일 수익률 리포트\n• 시스템 상태 알림\n• AI 예측 결과",
                            "inline": False
                        }
                    ],
                    "footer": {
                        "text": f"테스트 일시: {time.strftime('%Y-%m-%d %H:%M:%S')}"
                    }
                }]
            }

            response = requests.post(webhook_url, json=payload, timeout=10)

            if response.status_code == 204:  # Discord 웹훅 성공 응답
                print("✅ 테스트 메시지 전송 성공!")
                print("   Discord 채널에서 메시지를 확인하세요.")
                return True
            else:
                print(f"❌ 메시지 전송 실패 (상태코드: {response.status_code})")
                return False

        except Exception as e:
            print(f"❌ 메시지 전송 오류: {e}")
            return False

    def save_to_env_file(self, webhook_url: str):
        """환경변수 파일에 저장"""
        try:
            env_file_path = ".env"

            # 기존 .env 파일 읽기
            env_content = ""
            if os.path.exists(env_file_path):
                with open(env_file_path, 'r', encoding='utf-8') as f:
                    env_content = f.read()

            # Discord 설정 추가/수정
            lines = env_content.split('\n')
            updated_lines = []

            webhook_updated = False

            for line in lines:
                if line.startswith('DISCORD_WEBHOOK_URL='):
                    updated_lines.append(f'DISCORD_WEBHOOK_URL={webhook_url}')
                    webhook_updated = True
                else:
                    updated_lines.append(line)

            # 새로운 설정 추가 (없는 경우)
            if not webhook_updated:
                updated_lines.append(f'DISCORD_WEBHOOK_URL={webhook_url}')

            # 파일 저장
            with open(env_file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(updated_lines))

            print(f"✅ 설정이 {env_file_path}에 저장되었습니다.")

        except Exception as e:
            print(f"❌ 설정 파일 저장 실패: {e}")

    def save_to_config_file(self, webhook_url: str):
        """config 파일에도 저장"""
        try:
            config_file = "config_production.json"

            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            else:
                config = {}

            # Discord 설정 추가
            if 'alerts' not in config:
                config['alerts'] = {}

            config['alerts']['discord'] = {
                "enabled": True,
                "webhook_url": webhook_url,
                "daily_report_time": "18:00",
                "error_notifications": True,
                "trade_notifications": True,
                "prediction_notifications": True
            }

            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)

            print(f"✅ 설정이 {config_file}에도 저장되었습니다.")

        except Exception as e:
            print(f"❌ 설정 파일 저장 실패: {e}")

    def interactive_setup(self):
        """대화형 설정"""
        print("🚀 Discord 웹훅 자동 설정을 시작합니다.\n")

        # 웹훅 URL 입력
        while True:
            webhook_url = input("📝 Discord 웹훅 URL을 입력하세요: ").strip()

            if not webhook_url:
                print("❌ 웹훅 URL을 입력해주세요.")
                continue

            if self.validate_webhook_url(webhook_url):
                self.webhook_url = webhook_url
                break

        # 테스트 메시지 전송
        print("\n🧪 테스트 메시지를 전송합니다...")

        if self.send_test_message(webhook_url):
            # 설정 파일 저장
            self.save_to_env_file(webhook_url)
            self.save_to_config_file(webhook_url)

            print("\n🎉 Discord 웹훅 설정이 완료되었습니다!")
            print(f"🔗 웹훅 URL: {webhook_url[:50]}...")

            return True
        else:
            print("❌ 설정에 실패했습니다.")
            return False

    def create_sample_alerts(self):
        """샘플 알림 전송"""
        if not self.webhook_url:
            return

        print("\n📨 샘플 알림을 전송하시겠습니까? (y/n): ", end="")
        choice = input().lower().strip()

        if choice in ['y', 'yes', 'ㅇ']:
            # 거래 알림 샘플
            trade_payload = {
                "username": "AI Trading Bot",
                "embeds": [{
                    "title": "🟢 거래 체결 알림 (샘플)",
                    "color": 0x00ff00,
                    "fields": [
                        {"name": "📊 종목코드", "value": "`005930`", "inline": True},
                        {"name": "📈 수량", "value": "`10주`", "inline": True},
                        {"name": "💎 가격", "value": "`70,000원`", "inline": True}
                    ],
                    "footer": {"text": "샘플 거래 알림"}
                }]
            }

            requests.post(self.webhook_url, json=trade_payload)

            # 예측 결과 샘플
            time.sleep(2)
            prediction_payload = {
                "username": "AI Trading Bot",
                "embeds": [{
                    "title": "🤖 AI 예측 결과 (샘플)",
                    "description": "📅 예측일: **2025-11-05**",
                    "color": 0x9932cc,
                    "fields": [
                        {
                            "name": "🔥 추천 #1: 005930",
                            "value": "상승확률: `75%`\n예상수익: `+3.2%`\n현재가: `105,200원`",
                            "inline": True
                        }
                    ],
                    "footer": {"text": "샘플 예측 알림"}
                }]
            }

            requests.post(self.webhook_url, json=prediction_payload)

            print("✅ 샘플 알림이 전송되었습니다!")

def main():
    """메인 실행 함수"""
    create_discord_setup_guide()

    setup_manager = DiscordSetupManager()

    choice = input("\n자동 설정을 시작하시겠습니까? (y/n): ").lower().strip()

    if choice in ['y', 'yes', 'ㅇ']:
        if setup_manager.interactive_setup():
            setup_manager.create_sample_alerts()
    else:
        print("설정을 건너뛰었습니다. 나중에 수동으로 설정할 수 있습니다.")

if __name__ == "__main__":
    main()
