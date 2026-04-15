import os
import asyncio
import datetime
import pandas as pd
from pykrx import stock
from telegram import Bot
from dotenv import load_dotenv

# .env 파일 로드 (로컬 테스트용)
load_dotenv()

# 환경 변수 로드
TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
DATA_FILE = "last_etf_tickers.csv"

async def check_new_etfs():
    """
    KRX ETF 상장 리스트를 주기적으로 확인하여 신규 상장 종목을 텔레그램으로 알림.
    """
    if not TOKEN or not CHAT_ID:
        print("에러: TELEGRAM_TOKEN 또는 TELEGRAM_CHAT_ID가 설정되지 않았습니다.")
        return

    bot = Bot(token=TOKEN)
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    print(f"[{today}] KRX ETF 상장 모니터링 시작...")
    
    try:
        # 1. 현재 상장된 모든 ETF 티커 리스트 가져오기
        # pykrx.stock.get_etf_ticker_list()는 현재 날짜 기준의 ETF 리스트를 반환합니다.
        current_tickers = set(stock.get_etf_ticker_list())
        print(f"현재 총 {len(current_tickers)}개 종목 상장 중.")
        
        # 2. 이전 상장 리스트 로드
        is_first_run = not os.path.exists(DATA_FILE)
        previous_tickers = set()
        
        if not is_first_run:
            df_prev = pd.read_csv(DATA_FILE, dtype={'ticker': str})
            previous_tickers = set(df_prev['ticker'].tolist())
        else:
            print("이전 기록 파일이 없습니다. 초기화를 진행합니다.")

        # 3. 신규 상장 종목 식별 (현재 리스트 - 이전 리스트)
        new_tickers = current_tickers - previous_tickers
        
        # [임시 테스트] 알림 작동 확인을 위해 가상 종목을 하나 추가합니다.
        if not is_first_run and not new_tickers:
            new_tickers.add("TEST999")

        # 4. 알림 발송 로직
        if not is_first_run and new_tickers:
            # 신규 상장 종목이 있는 경우
            message = f"🆕 {today} 신규 상장 ETF 알림\n\n"
            for ticker in sorted(list(new_tickers)):
                if ticker == "TEST999":
                    name = "알림 시스템 작동 테스트용 종목"
                else:
                    name = stock.get_etf_ticker_name(ticker)
                message += f"• [{ticker}] {name}\n"
            
            await bot.send_message(chat_id=CHAT_ID, text=message)
            print(f"신규 상장(테스트 포함) {len(new_tickers)}건 알림 전송 완료.")
        
        elif is_first_run or ("test" in os.environ.get("GITHUB_WORKFLOW", "").lower()):
            # 테스트 또는 첫 실행 시에도 확인 메시지 발송
            test_msg = f"🔔 {today} ETF 모니터링 시스템 작동 확인\n\n현재 정상적으로 KRX 데이터를 감시하고 있습니다. 신규 상장 발생 시 알림이 발송됩니다."
            await bot.send_message(chat_id=CHAT_ID, text=test_msg)
            print("테스트/초기화 알림 전송 완료.")
        
        else:
            # 변동 사항 없는 경우 (로컬 테스트 시 확인을 위해 로그만 출력)
            print("신규 상장 종목이 없습니다.")

        # 5. 현재 리스트 저장 (상태 업데이트)
        # 파일을 Push하여 지속성을 유지하기 위해 CSV로 저장합니다.
        df_current = pd.DataFrame({'ticker': sorted(list(current_tickers))})
        df_current.to_csv(DATA_FILE, index=False)
        print("상태 파일(last_etf_tickers.csv) 업데이트 완료.")

    except Exception as e:
        error_msg = f"❌ ETF 모니터링 중 에러 발생:\n{str(e)}"
        print(error_msg)
        # 에러 발생 시에도 텔레그램으로 알림 (설정된 경우)
        try:
            await bot.send_message(chat_id=CHAT_ID, text=error_msg)
        except:
            pass

if __name__ == "__main__":
    asyncio.run(check_new_etfs())
