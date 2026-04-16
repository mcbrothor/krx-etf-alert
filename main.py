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
    """
    # KST (UTC+9) 기준 현재 시간 계산
    kst = datetime.timezone(datetime.timedelta(hours=9))
    base_datetime = datetime.datetime.now(kst)
    
    # 최근 10일간의 데이터를 시도하여 가장 최신 영업일 데이터를 찾음
    for i in range(10):
        target_date = (base_datetime - datetime.timedelta(days=i)).strftime("%Y%m%d")
        try:
            # get_etf_ticker_list()는 데이터가 없으면 빈 리스트를 반환하거나 IndexError를 낼 수 있음
            tickers = stock.get_etf_ticker_list(target_date)
            if tickers and len(tickers) > 0:
                print(f"✅ {target_date} 기준 데이터를 성공적으로 가져왔습니다. (종목 수: {len(tickers)})")
                return set(tickers), target_date
        except (IndexError, Exception) as e:
            print(f"DEBUG: {target_date} 조회 시도 중 오류/데이터 없음: {str(e)}")
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
        # 1. 현재 상장된 가장 최신 ETF 티커 리스트 가져오기
        current_tickers, data_date = get_latest_etf_tickers()
        
        # 데이터 조회 실패 시에도 알림 (디버깅용)
        if not current_tickers:
            error_msg = f"⚠️ [{today_kst}] KRX 데이터 조회 실패\n최근 10일간의 ETF 리스트를 가져오지 못했습니다. pykrx 라이브러리 상태를 확인해 주세요."
            print(error_msg)
            await bot.send_message(chat_id=CHAT_ID, text=error_msg)
            return

        # 2. 이전 상장 리스트 로드
        is_first_run = not os.path.exists(DATA_FILE)
        previous_tickers = set()
        
        if not is_first_run:
            try:
                df_prev = pd.read_csv(DATA_FILE, dtype={'ticker': str})
                previous_tickers = set(df_prev['ticker'].tolist())
            except Exception as e:
                print(f"이전 데이터 로드 오류: {e}")
        else:
            print("이전 기록 파일이 없습니다. (최초 실행 모드)")

        # 3. 신규 상장 종목 식별
        new_tickers = current_tickers - previous_tickers
        
        # [임시 테스트] 이번에는 시스템 생존 확인을 위해 무조건 샘플을 추가합니다.
        if not new_tickers:
            print("🔔 작동 확인을 위해 샘플 종목을 추가합니다.")
            new_tickers.add("SAMPLE_OK")

        # 4. 알림 발송 로직
        if new_tickers:
            message = f"🆕 {today_kst} KRX ETF 모니터링 알림\n(데이터 기준일: {data_date})\n\n"
            for ticker in sorted(list(new_tickers)):
                try:
                    if ticker == "SAMPLE_OK":
                        name = "✅ 알림 시스템 안정화 완료(생존 보고)"
                    else:
                        name = stock.get_etf_ticker_name(ticker)
                    message += f"• [{ticker}] {name}\n"
                except Exception:
                    message += f"• [{ticker}] (이름 조회 실패)\n"
            
            await bot.send_message(chat_id=CHAT_ID, text=message)
            print(f"알림 전송 완료 (종목 수: {len(new_tickers)})")

        # 5. 현재 리스트 저장
        df_current = pd.DataFrame({'ticker': sorted(list(current_tickers))})
        df_current.to_csv(DATA_FILE, index=False)
        print("상태 업데이트 완료.")

    except Exception as e:
        error_report = f"❌ [{today_kst}] 모니터링 오류 발생:\n{str(e)}"
        print(error_report)
        try:
            await bot.send_message(chat_id=CHAT_ID, text=error_report)
        except:
            pass

if __name__ == "__main__":
    asyncio.run(check_new_etfs())
