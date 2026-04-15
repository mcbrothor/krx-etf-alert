🚀 [Project] KRX 신규 상장 ETF 텔레그램 알림 자동화
1. 개요 (Overview)
목표: KRX(한국거래소) ETF 정보시스템의 데이터를 모니터링하여 신규 상장 정보를 텔레그램으로 자동 전송.

주요 특징:

공시 기반의 가장 빠르고 정확한 데이터 확보.

서버 유지비 0원 (Github Actions 활용).

매일 장 시작 전(08:30) 자동 체크 및 알림.

2. 사전 준비 사항 (Prerequisites)
[ ] Telegram Bot: @BotFather를 통해 생성한 API Token.

[ ] Telegram ID: 본인의 Chat ID (전송 대상).

[ ] Github: 코드를 관리하고 스케줄러를 실행할 리포지토리.

3. 핵심 파일 구성 (Configuration)
📄 requirements.txt
Plaintext
pykrx
python-telegram-bot
pandas
📄 main.py (파이썬 로직)
Python
import os
import asyncio
import datetime
from pykrx import stock
from telegram import Bot

# 환경 변수 로드
TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

async def check_new_etfs():
    bot = Bot(token=TOKEN)
    today = datetime.datetime.now().strftime("%Y%m%d")
    
    # 1. 현재 상장된 모든 ETF 리스트 가져오기
    tickers = stock.get_etf_ticker_list()
    
    # [참고] 실무에서는 전날 리스트를 파일로 저장해두고 비교(Set 차집합)하는 로직을 권장합니다.
    # 여기서는 실행 여부를 확인하는 기본 메시지를 구성합니다.
    message = f"🔍 {today} KRX ETF 상장 모니터링\n현재 총 {len(tickers)}개 종목 상장 중"
    
    await bot.send_message(chat_id=CHAT_ID, text=message)

if __name__ == "__main__":
    asyncio.run(check_new_etfs())
📄 .github/workflows/etf_alert.yml (자동화 설정)
YAML
name: Daily KRX ETF Alert

on:
  schedule:
    # 한국 시간 기준 오전 08:30 (UTC 23:30)
    - cron: '30 23 * * *'
  workflow_dispatch: # 수동 실행 버튼

jobs:
  run_bot:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'

      - name: Install Dependencies
        run: pip install -r requirements.txt

      - name: Execute Script
        env:
          TELEGRAM_TOKEN: ${{ secrets.TELEGRAM_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
        run: python main.py
4. 구축 단계 (Execution Steps)
Github Secrets 등록:

Repository > Settings > Secrets and variables > Actions 이동.

TELEGRAM_TOKEN과 TELEGRAM_CHAT_ID를 각각 추가.

파일 업로드:

위 코드들을 각 파일명에 맞게 저장소에 push.

작동 확인:

Github 저장소의 Actions 탭에서 Daily KRX ETF Alert 워크플로우를 선택하고 Run workflow 클릭.

본인의 텔레그램으로 알림이 오는지 확인.

5. 향후 확장 (Backlog)
[ ] 신규 상장 감지 로직 고도화: ticker_list를 파일로 저장하여 전날과 비교하는 로직 추가.

[ ] 상세 정보 추가: 신규 종목 발견 시 구성 종목(PDF) 리스트 및 추적 지수 정보 자동 추출.

[ ] 에러 알림: 스크립트 실행 실패 시 개발자에게 별도 알림 발송.