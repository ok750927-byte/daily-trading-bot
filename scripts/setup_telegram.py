"""
텔레그램 봇 자동 설정 스크립트
- 봇 토큰 검증
- 채팅방 ID 자동 확인
- 설정 파일 자동 생성
"""
import os
import requests
import json
import time
from typing import Optional, Dict, Any

def create_telegram_bot_guide():
    """텔레그램 봇 생성 가이드"""
    guide = """
🤖 텔레그램 알림 봇 설정 가이드

1️⃣ 텔레그램 봇 생성:
   - 텔레그램에서 @BotFather 검색
   - /newbot 명령어 입력
   - 봇 이름 입력 (예: AI Trading Alert)
   - 봇 사용자명 입력 (예: ai_trading_alert_bot)
   - 봇 토큰 복사 (예: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz)

2️⃣ 채팅방 ID 확인:
   - 생성된 봇에게 /start 메시지 전송
   - 아래 스크립트 실행하여 자동으로 채팅방 ID 확인

3️⃣ 환경변수 설정:
   - .env 파일에 토큰과 채팅방 ID 추가
   - 또는 아래 스크립트로 자동 설정
"""
    print(guide)

class TelegramSetupManager:
    """텔레그램 봇 설정 관리자"""

    def __init__(self):
        self.bot_token = None
        self.chat_id = None

    def validate_bot_token(self, token: str) -> bool:
        """봇 토큰 유효성 검사"""
        try:
            url = f"https://api.telegram.org/bot{token}/getMe"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                bot_info = response.json()
                if bot_info.get('ok'):
                    print(f"✅ 봇 연결 성공: {bot_info['result']['first_name']}")
                    return True

            print("❌ 유효하지 않은 봇 토큰입니다.")
            return False

        except Exception as e:
            print(f"❌ 봇 토큰 검증 실패: {e}")
            return False

    def get_chat_updates(self, token: str) -> Optional[list]:
        """최근 메시지 업데이트 조회"""
        try:
            url = f"https://api.telegram.org/bot{token}/getUpdates"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    return data.get('result', [])

            return None

        except Exception as e:
            print(f"❌ 업데이트 조회 실패: {e}")
            return None

    def find_chat_id(self, token: str) -> Optional[str]:
        """채팅방 ID 자동 탐지"""
        print("\n📱 채팅방 ID를 찾는 중...")
        print("💡 봇에게 메시지를 보내주세요 (예: /start)")

        for i in range(30):  # 30초 동안 시도
            updates = self.get_chat_updates(token)

            if updates:
                for update in updates:
                    if 'message' in update:
                        chat_id = update['message']['chat']['id']
                        chat_type = update['message']['chat']['type']

                        if chat_type == 'private':
                            print(f"✅ 개인 채팅방 ID 발견: {chat_id}")
                            return str(chat_id)

            print(f"⏳ 대기 중... ({i+1}/30초)")
            time.sleep(1)

        print("❌ 채팅방 ID를 찾을 수 없습니다. 봇에게 메시지를 보냈는지 확인하세요.")
        return None

    def test_message_sending(self, token: str, chat_id: str) -> bool:
        """메시지 전송 테스트"""
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": "🤖 AI 자동매매 봇 연결 테스트\n\n✅ 텔레그램 알림이 정상적으로 설정되었습니다!",
                "parse_mode": "Markdown"
            }

            response = requests.post(url, json=payload, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    print("✅ 테스트 메시지 전송 성공!")
                    return True

            print(f"❌ 메시지 전송 실패: {response.text}")
            return False

        except Exception as e:
            print(f"❌ 메시지 전송 오류: {e}")
            return False

    def save_to_env_file(self, token: str, chat_id: str):
        """환경변수 파일에 저장"""
        try:
            env_file_path = ".env"

            # 기존 .env 파일 읽기
            env_content = ""
            if os.path.exists(env_file_path):
                with open(env_file_path, 'r', encoding='utf-8') as f:
                    env_content = f.read()

            # 텔레그램 설정 추가/수정
            lines = env_content.split('\n')
            updated_lines = []

            token_updated = False
            chat_id_updated = False

            for line in lines:
                if line.startswith('TELEGRAM_BOT_TOKEN='):
                    updated_lines.append(f'TELEGRAM_BOT_TOKEN={token}')
                    token_updated = True
                elif line.startswith('TELEGRAM_CHAT_ID='):
                    updated_lines.append(f'TELEGRAM_CHAT_ID={chat_id}')
                    chat_id_updated = True
                else:
                    updated_lines.append(line)

            # 새로운 설정 추가 (없는 경우)
            if not token_updated:
                updated_lines.append(f'TELEGRAM_BOT_TOKEN={token}')
            if not chat_id_updated:
                updated_lines.append(f'TELEGRAM_CHAT_ID={chat_id}')

            # 파일 저장
            with open(env_file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(updated_lines))

            print(f"✅ 설정이 {env_file_path}에 저장되었습니다.")

        except Exception as e:
            print(f"❌ 설정 파일 저장 실패: {e}")

    def interactive_setup(self):
        """대화형 설정"""
        print("🚀 텔레그램 봇 자동 설정을 시작합니다.\n")

        # 1. 봇 토큰 입력
        while True:
            token = input("📝 봇 토큰을 입력하세요: ").strip()

            if not token:
                print("❌ 봇 토큰을 입력해주세요.")
                continue

            if self.validate_bot_token(token):
                self.bot_token = token
                break

        # 2. 채팅방 ID 자동 탐지
        chat_id = self.find_chat_id(token)

        if not chat_id:
            # 수동 입력
            chat_id = input("📝 채팅방 ID를 수동으로 입력하세요: ").strip()

        if chat_id:
            self.chat_id = chat_id

            # 3. 메시지 전송 테스트
            if self.test_message_sending(token, chat_id):
                # 4. 설정 파일 저장
                self.save_to_env_file(token, chat_id)

                print("\n🎉 텔레그램 봇 설정이 완료되었습니다!")
                print(f"📱 봇 토큰: {token[:10]}...")
                print(f"💬 채팅방 ID: {chat_id}")

                return True

        print("❌ 설정에 실패했습니다.")
        return False

def main():
    """메인 실행 함수"""
    create_telegram_bot_guide()

    setup_manager = TelegramSetupManager()

    choice = input("\n자동 설정을 시작하시겠습니까? (y/n): ").lower().strip()

    if choice in ['y', 'yes', 'ㅇ']:
        setup_manager.interactive_setup()
    else:
        print("설정을 건너뛰었습니다. 나중에 수동으로 설정할 수 있습니다.")

if __name__ == "__main__":
    main()
