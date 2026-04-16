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
    kst = datetime.timezone(datetime.timedelta(hours=9))
    base_datetime = datetime.datetime.now(kst)
    
    error_logs = []
    for i in range(10):
        target_date = (base_datetime - datetime.timedelta(days=i)).strftime("%Y%m%d")
        try:
            tickers = stock.get_etf_ticker_list(target_date)
            if tickers and len(tickers) > 0:
                return set(tickers), target_date
        except Exception as e:
            error_logs.append(f"{target_date}: {str(e)}")
            continue
            
    return None, "\n".join(error_logs[-3:]) # 최근 3건의 에러만 반환

async def check_new_etfs():
    """
    KRX ETF 상장 리스트를 모니터링하여 신규 상장 종목을 텔레그램으로 알림.
    """
    if not TOKEN or not CHAT_ID:
        print("에러: TELEGRAM_TOKEN 또는 TELEGRAM_CHAT_ID가 설정되지 않았습니다.")
        return

    bot = Bot(token=TOKEN)
    kst = datetime.timezone(datetime.timedelta(hours=9))
    today_kst = datetime.datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"[{today_kst}] KRX ETF 상장 모니터링 시작...")

    # [즉시 확인용] 시스템 시작 보고
    try:
        startup_msg = f"🔔 [{today_kst}] ETF 모니터링을 시작합니다.\n(텔레그램 연결 상태: 정상 ✅)"
        await bot.send_message(chat_id=CHAT_ID, text=startup_msg)
    except Exception as e:
        print(f"텔레그램 전송 실패: {e}")
        return # 텔레그램이 안되면 의미가 없으므로 종료

    try:
        # 1. 현재 상장된 가장 최신 ETF 티커 리스트 가져오기
        current_tickers, result_info = get_latest_etf_tickers()
        
        if not current_tickers:
            error_msg = f"⚠️ 데이터 조회 실패 보고\n\n최근 10일간 KRX에서 데이터를 가져오지 못했습니다.\n\n[최근 에러 로그]\n{result_info}"
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
        
        # 3. 신규 상장 종목 식별
        new_tickers = current_tickers - previous_tickers
        
        # 4. 알림 발송 로직
        if new_tickers:
            message = f"🆕 신규 상장 ETF 발견!\n(데이터 기준일: {result_info})\n\n"
            for ticker in sorted(list(new_tickers)):
                try:
                    name = stock.get_etf_ticker_name(ticker)
                    message += f"• [{ticker}] {name}\n"
                except:
                    message += f"• [{ticker}] (이름 조회 실패)\n"
            
            await bot.send_message(chat_id=CHAT_ID, text=message)
        else:
            # 변동 사항이 없을 때도 1회성 확인 메시지가 필요하다면 아래 주석 해제
            # await bot.send_message(chat_id=CHAT_ID, text="🔍 현재 신규 상장 종목이 없습니다.")
            pass

        # 5. 현재 리스트 저장
        df_current = pd.DataFrame({'ticker': sorted(list(current_tickers))})
        df_current.to_csv(DATA_FILE, index=False)
        print("상태 업데이트 완료.")

    except Exception as e:
        await bot.send_message(chat_id=CHAT_ID, text=f"❌ 시스템 내부 오류 발생:\n{str(e)}")

if __name__ == "__main__":
    asyncio.run(check_new_etfs())
