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

def get_latest_etf_tickers():
    """
    KST 기준 오늘부터 과거로 가며 데이터가 있는 가장 최근 날짜의 ETF 리스트를 반환합니다.
    장 시작 전 '오늘' 데이터가 없을 때 발생하는 IndexError를 방지합니다.
    """
    # KST (UTC+9) 기준 현재 시간 계산
    kst = datetime.timezone(datetime.timedelta(hours=9))
    base_datetime = datetime.datetime.now(kst)
    
    # 최근 7일간의 데이터를 시도하여 가장 최신 영업일 데이터를 찾음
    for i in range(7):
        target_date = (base_datetime - datetime.timedelta(days=i)).strftime("%Y%m%d")
        try:
            tickers = stock.get_etf_ticker_list(target_date)
            if tickers and len(tickers) > 0:
                print(f"✅ {target_date} 기준 데이터를 성공적으로 가져왔습니다.")
                return set(tickers), target_date
        except (IndexError, Exception):
            # IndexError는 주로 해당 일자에 데이터가 없을 때 pykrx 내부에서 발생함
            continue
            
    return None, None

async def check_new_etfs():
    """
    KRX ETF 상장 리스트를 모니터링하여 신규 상장 종목을 텔레그램으로 알림.
    """
    if not TOKEN or not CHAT_ID:
        print("에러: TELEGRAM_TOKEN 또는 TELEGRAM_CHAT_ID가 설정되지 않았습니다.")
        return

    bot = Bot(token=TOKEN)
    kst = datetime.timezone(datetime.timedelta(hours=9))
    today_kst = datetime.datetime.now(kst).strftime("%Y-%m-%d")
    
    print(f"[{today_kst}] KRX ETF 상장 모니터링 시작...")
    
    try:
        # 1. 현재 상장된 가장 최신 ETF 티커 리스트 가져오기 (재시도 로직 포함)
        current_tickers, data_date = get_latest_etf_tickers()
        
        if not current_tickers:
            print("⚠️ KRX에서 ETF 리스트를 가져오지 못했습니다. (최근 7일간 데이터 부재)")
            return

        print(f"조회 기준일: {data_date}, 상장 종목 수: {len(current_tickers)}개")
        
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
            message = f"🆕 {today_kst} 신규 상장 ETF 알림\n(데이터 기준일: {data_date})\n\n"
            for ticker in sorted(list(new_tickers)):
                try:
                    name = stock.get_etf_ticker_name(ticker)
                    message += f"• [{ticker}] {name}\n"
                except Exception:
                    message += f"• [{ticker}] (이름 조회 실패)\n"
            
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
        error_msg = f"❌ ETF 모니터링 중 에러 발생:\n{str(e)}"
        print(error_msg)
        # 사용자에게 에러 알림 전송
        try:
            await bot.send_message(chat_id=CHAT_ID, text=error_msg)
        except:
            pass

if __name__ == "__main__":
    asyncio.run(check_new_etfs())
