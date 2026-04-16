import os
import asyncio
import datetime
import pandas as pd
import requests
import FinanceDataReader as fdr
from telegram import Bot
from dotenv import load_dotenv

# .env 파일 로드 (로컬 테스트용)
load_dotenv()

# 환경 변수 로드
TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
DATA_FILE = "last_etf_tickers.csv"

def get_fdr_etfs():
    """
    FinanceDataReader를 사용하여 현재 상장된 모든 ETF 리스트를 가져옵니다.
    """
    try:
        df = fdr.StockListing('ETF/KR')
        if not df.empty:
            # 'Symbol' 컬럼이 티커 코드입니다.
            tickers = df['Symbol'].tolist()
            # 종목명 매핑 정보 생성 (나중에 이름 찾기용)
            name_map = dict(zip(df['Symbol'], df['Name']))
            return set(tickers), name_map
    except Exception as e:
        print(f"FinanceDataReader 조회 실패: {e}")
    return set(), {}

def get_etfcheck_new_items():
    """
    etfcheck.co.kr API를 호출하여 최근 상장된 ETF 리스트를 가져옵니다. (병행 모니터링)
    """
    url = "https://www.etfcheck.co.kr/user/etp/getIssueNewItem"
    try:
        # API 호출 (POST 방식, 데이터는 기본값 전달)
        response = requests.post(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            new_items = data.get('list', [])
            tickers = [item.get('item_cd') for item in new_items if item.get('item_cd')]
            name_map = {item.get('item_cd'): item.get('item_nm') for item in new_items if item.get('item_cd')}
            return set(tickers), name_map
    except Exception as e:
        print(f"ETFCheck API 조회 실패: {e}")
    return set(), {}

async def check_new_etfs():
    """
    두 가지 소스(FDR, ETFCheck)를 활용하여 ETF 상장을 모니터링합니다.
    """
    if not TOKEN or not CHAT_ID:
        print("에러: TELEGRAM_TOKEN 또는 TELEGRAM_CHAT_ID가 설정되지 않았습니다.")
        return

    bot = Bot(token=TOKEN)
    kst = datetime.timezone(datetime.timedelta(hours=9))
    now_kst = datetime.datetime.now(kst)
    today_str = now_kst.strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"[{today_str}] ETF 이중 모니터링 가동...")

    try:
        # 1. 데이터 수집 (FinanceDataReader + ETFCheck)
        fdr_tickers, fdr_names = get_fdr_etfs()
        check_tickers, check_names = get_etfcheck_new_items()
        
        # 두 소스의 티커 및 이름 데이터 통합
        current_tickers = fdr_tickers | check_tickers
        all_names = {**fdr_names, **check_names}
        
        if not current_tickers:
            error_msg = f"⚠️ [{today_str}] 모든 소스에서 데이터 조회 실패\n시스템 상태를 점검해 주세요."
            print(error_msg)
            await bot.send_message(chat_id=CHAT_ID, text=error_msg)
            return

        print(f"통합 상장 종목 수: {len(current_tickers)}개 (FDR: {len(fdr_tickers)}, ETFCheck: {len(check_tickers)})")

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
            message = f"🆕 {now_kst.strftime('%Y-%m-%d')} 신규 상장 ETF 알림\n(FDR + ETFCheck 통합 감지)\n\n"
            for ticker in sorted(list(new_tickers)):
                name = all_names.get(ticker, "이름 정보 없음")
                message += f"• [{ticker}] {name}\n"
            
            await bot.send_message(chat_id=CHAT_ID, text=message)
            print(f"신규 상장 {len(new_tickers)}건 알림 전송 완료.")
        else:
            print("신규 상장 종목이 없습니다.")

        # 5. 현재 리스트 저장 (상태 업데이트)
        df_current = pd.DataFrame({'ticker': sorted(list(current_tickers))})
        df_current.to_csv(DATA_FILE, index=False)
        print("상태 파일 업데이트 완료.")

    except Exception as e:
        err_msg = f"❌ 시스템 오류 발생:\n{str(e)}"
        print(err_msg)
        try:
            await bot.send_message(chat_id=CHAT_ID, text=err_msg)
        except:
            pass

if __name__ == "__main__":
    asyncio.run(check_new_etfs())
