from pykrx import stock
import pandas as pd

# 현재 상장된 모든 ETF 티커 가져오기
tickers = stock.get_etf_ticker_list()

if tickers:
    # 마지막 종목 하나를 제외 (테스트용)
    test_tickers = tickers[:-1]
    removed_ticker = tickers[-1]
    removed_name = stock.get_etf_ticker_name(removed_ticker)
    
    df = pd.DataFrame({'ticker': test_tickers})
    df.to_csv("last_etf_tickers.csv", index=False)
    
    print(f"테스트 준비 완료: '{removed_name}({removed_ticker})' 종목을 리스트에서 제외했습니다.")
    print("이제 이 파일을 Push하고 워크플로우를 실행하면 위 종목에 대한 신규 상장 알림이 올 것입니다.")
else:
    print("ETF 리스트를 가져오지 못했습니다.")
