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
    KRX ETF 상장 리스트를 모니터링하여 신규 상장 종목을 텔레그램으로 알림.
    """
    if not TOKEN or not CHAT_ID:
        print("에러: TELEGRAM_TOKEN 또는 TELEGRAM_CHAT_ID가 설정되지 않았습니다.")
        return

    bot = Bot(token=TOKEN)
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    print(f"[{today}] KRX ETF 상장 모니터링 시작...")
    
    try:
        # 1. 현재 상장된 모든 ETF 티커 리스트 가져오기
        current_tickers_list = stock.get_etf_ticker_list()
        
        # 데이터가 비어있는지 확인 (새벽 점검 시간 등 대응)
        if not current_tickers_list:
            print("⚠️ KRX에서 ETF 리스트를 가져오지 못했습니다. (사이트 점검 중일 수 있습니다.)")
            return

        current_tickers = set(current_tickers_list)
        print(f"현재 총 {len(current_tickers)}개 종목 상장 중.")
        
        # 2. 이전 상장 리스트 로드
        is_first_run = not os.path.exists(DATA_FILE)
        previous_tickers = set()
        
        if not is_first_run:
            try:
                df_prev = pd.read_csv(DATA_FILE, dtype={'ticker': str})
                previous_tickers = set(df_prev['ticker'].tolist())
            except Exception as e:
                print(f"이전 데이터 로드 중 오류(초기화 진행): {e}")
                is_first_run = True
        else:
            print("이전 기록 파일이 없습니다. 초기화를 진행합니다.")

        # 3. 신규 상장 종목 식별 (현재 리스트 - 이전 리스트)
        new_tickers = current_tickers - previous_tickers
        
        # 4. 알림 발송 로직
        if not is_first_run and new_tickers:
            # 신규 상장 종목이 있는 경우
            message = f"🆕 {today} 신규 상장 ETF 알림\n\n"
            for ticker in sorted(list(new_tickers)):
                try:
                    name = stock.get_etf_ticker_name(ticker)
                    message += f"• [{ticker}] {name}\n"
                except Exception as e:
                    message += f"• [{ticker}] (이름 조회 실패: {str(e)})\n"
            
            await bot.send_message(chat_id=CHAT_ID, text=message)
            print(f"신규 상장 {len(new_tickers)}건 알림 전송 완료.")
        
        elif is_first_run:
            print("초기 리스트 저장 완료. 다음 실행부터 신규 상장을 감지합니다.")
        
        else:
            print("신규 상장 종목이 없습니다.")

        # 5. 현재 리스트 저장 (상태 업데이트)
        df_current = pd.DataFrame({'ticker': sorted(list(current_tickers))})
        df_current.to_csv(DATA_FILE, index=False)
        print("상태 파일(last_etf_tickers.csv) 업데이트 완료.")

    except Exception as e:
        error_msg = f"❌ ETF 모니터링 중 치명적 에러 발생:\n{str(e)}"
        print(error_msg)
        try:
            await bot.send_message(chat_id=CHAT_ID, text=error_msg)
        except:
            pass

if __name__ == "__main__":
    asyncio.run(check_new_etfs())
