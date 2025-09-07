# market_scanner.py
import pandas as pd
import pandas_ta as ta
import python_bithumb
import time

class MarketScanner:
    def select_daily_tickers(self) -> (str or None, str or None):
        """
        매일 아침 실행되어 그날 거래할 가장 유망한 2개 종목을 선정합니다.
        시장 국면에 따라 다른 전략을 사용하며, 수수료가 과도한 종목은 제외합니다.
        (주종목, 부종목) 형태의 튜플로 반환합니다.
        """
        try:
            # 1. 비트코인 일봉으로 시장 국면 판단 (5일 이평선 > 20일 이평선)
            df_btc = python_bithumb.get_ohlcv("KRW-BTC", "day", count=30)
            df_btc.ta.ema(length=5, append=True)
            df_btc.ta.ema(length=20, append=True)
            latest_btc = df_btc.iloc[-1]

            all_tickers = python_bithumb.get_market_all()
            krw_tickers = [t['market'] for t in all_tickers if t['market'].startswith("KRW-")]
            scored_tickers = []

            # 수수료 필터링을 위한 기준값 설정
            HYPOTHETICAL_TRADE_AMOUNT = 100000  # 10만원
            BITHUMB_FEE_RATE = 0.0025  # 0.25%
            FEE_THRESHOLD = HYPOTHETICAL_TRADE_AMOUNT * BITHUMB_FEE_RATE # 기준 거래 수수료 (250원)

            # 2. 시장 국면에 따라 스캐닝 전략 변경
            if latest_btc['EMA_5'] >= latest_btc['EMA_20']:
                # 2-A. 상승장 전략: 전날의 상승 모멘텀이 가장 강한 종목 Top 2 선정
                print("[스캐너] 상승장 감지. 모멘텀 스캐닝을 시작합니다.")
                for ticker in krw_tickers:
                    if ticker == "KRW-BTC": continue
                    
                    # --- 수수료 검증 로직 ---
                    if self._is_fee_too_high(ticker, FEE_THRESHOLD):
                        continue # 수수료가 비싸면 건너뛰기

                    df_ticker = python_bithumb.get_ohlcv(ticker, "day", count=2)
                    if df_ticker is None or len(df_ticker) < 2: continue
                    
                    yesterday = df_ticker.iloc[-2]
                    price_change_ratio = (yesterday['close'] - yesterday['open']) / yesterday['open']
                    if price_change_ratio > 0.03: # 최소 3% 이상 상승
                        score = price_change_ratio * yesterday['value']
                        scored_tickers.append((score, ticker))
            else:
                # 2-B. 하락장 전략: 하락 속에서도 반등 시도(양봉+아래꼬리)를 한 종목 Top 2 선정
                print("[스캐너] 하락장 감지. 반등 시도 종목 스캐닝을 시작합니다.")
                for ticker in krw_tickers:
                    if ticker == "KRW-BTC": continue

                    # --- 수수료 검증 로직 ---
                    if self._is_fee_too_high(ticker, FEE_THRESHOLD):
                        continue

                    df_ticker = python_bithumb.get_ohlcv(ticker, "day", count=2)
                    if df_ticker is None or len(df_ticker) < 2: continue

                    yesterday = df_ticker.iloc[-2]
                    is_positive_candle = yesterday['close'] > yesterday['open']
                    is_enough_volume = yesterday['value'] > 1_000_000_000
                    
                    if is_positive_candle and is_enough_volume:
                        lower_tail = min(yesterday['open'], yesterday['close']) - yesterday['low']
                        score = lower_tail * yesterday['value']
                        scored_tickers.append((score, ticker))

            # 3. 점수 순으로 정렬하여 최종 2개 종목 선정
            scored_tickers.sort(key=lambda x: x[0], reverse=True)
            
            primary_ticker = scored_tickers[0][1] if len(scored_tickers) > 0 else None
            secondary_ticker = scored_tickers[1][1] if len(scored_tickers) > 1 else None
            
            return primary_ticker, secondary_ticker

        except Exception as e:
            print(f"[스캐너 오류] 유망 종목 선정 중 오류 발생: {e}")
            return None, None

    def _is_fee_too_high(self, ticker: str, threshold: float) -> bool:
        """
        출금 수수료의 원화 가치가 기준치(threshold)보다 높은지 확인하는 헬퍼 함수
        """
        try:
            coin_symbol = ticker.split('-')[1]
            asset_info = python_bithumb.get_asset_status(coin_symbol)
            time.sleep(0.1) # API 요청 간격

            if asset_info:
                withdrawal_fee = float(asset_info.get('withdrawal_fee', 0))
                current_price = python_bithumb.get_current_price(ticker)
                
                if withdrawal_fee > 0 and current_price:
                    withdrawal_fee_krw = withdrawal_fee * current_price
                    if withdrawal_fee_krw > threshold:
                        print(f"[필터링] {ticker}: 출금 수수료({withdrawal_fee_krw:,.0f}원)가 과도하여 제외합니다.")
                        return True
            return False
        except Exception as e:
            print(f"[수수료 조회 오류] {ticker}: {e}")
            return False # 오류 발생 시 일단 통과