# main.py
import time
import os
from dotenv import load_dotenv
import python_bithumb
from slack_bot import SlackNotifier
from trade_manager import TradeManager
from candlestick_trader import CandlestickTrader
from market_scanner import MarketScanner
from datetime import datetime, time as dt_time

load_dotenv()

# --- 봇 설정 ---
TIMEFRAME = "minute15"
STOP_LOSS_PERCENT = 1.5
TIME_INTERVAL_SECONDS = 900 # 15분

def main():
    # 1. 모듈 초기화
    try:
        notifier = SlackNotifier()
        manager = TradeManager()
        scanner = MarketScanner()
        bithumb_api = python_bithumb.Bithumb(
            access_key=os.getenv("BITHUMB_API_KEY"),
            secret_key=os.getenv("BITHUMB_SECRET_KEY")
        )
    except Exception as e:
        print(f"모듈 초기화 실패: {e}")
        return

    # --- 두 종목의 상태를 독립적으로 관리 ---
    positions = {
        "primary": {"ticker": None, "in_position": False, "purchase_price": 0, "capital_alloc": 0.7}, # 주종목 자금 70%
        "secondary": {"ticker": None, "in_position": False, "purchase_price": 0, "capital_alloc": 0.3} # 부종목 자금 30%
    }
    last_scan_date = None
    
    notifier.send_message(f"📈 최종 결합 전략 자동매매 봇을 시작합니다. (TIMEFRAME: {TIMEFRAME})")

    while True:
        try:
            now = datetime.now()
            
            # --- 매일 오전 9시 5분, 오늘의 주/부종목 선정 ---
            if last_scan_date != now.date() and now.time() >= dt_time(9, 5):
                primary, secondary = scanner.select_daily_tickers()
                
                positions["primary"].update({"ticker": primary, "in_position": False, "purchase_price": 0})
                positions["secondary"].update({"ticker": secondary, "in_position": False, "purchase_price": 0})
                last_scan_date = now.date()

                if primary:
                    notifier.send_message(f"🎯 *금일 공략 종목 선정*\n∙ *주종목:* `{primary}`\n∙ *부종목:* `{secondary if secondary else '없음'}`")
                else:
                    notifier.send_message(f"🐻 시장 상황이 좋지 않아 금일 거래 종목을 선정하지 않았습니다.")
            
            # --- 각 포지션을 개별적으로 순회하며 매매 판단 ---
            for key, pos in positions.items():
                if not pos["ticker"]: # 선정된 종목이 없으면 건너뛰기
                    continue

                # 1. 데이터 가져오기
                df = python_bithumb.get_ohlcv(pos["ticker"], TIMEFRAME, count=30)
                if df is None or len(df) < 3:
                    continue
                
                current_price = df.iloc[-1]['close']

                # 2. 매수/매도/손절 로직
                if pos["in_position"]:
                    # --- 포지션 보유 시: 손절 또는 이익실현 매도 확인 ---
                    coin_total, _, _ = bithumb_api.get_balance(pos["ticker"].split('-')[1])

                    # 2-A. 손절매 로직
                    if manager.check_stop_loss(current_price, pos["purchase_price"], STOP_LOSS_PERCENT):
                        if coin_total > 0:
                            bithumb_api.sell_market_order(pos["ticker"], coin_total)
                            pnl = (current_price - pos["purchase_price"]) * coin_total
                            pnl_percent = ((current_price - pos["purchase_price"]) / pos["purchase_price"]) * 100
                            
                            notifier.report_trade(pos["ticker"], "sell", current_price, coin_total, pnl, pnl_percent)
                            manager.log_trade(pos["ticker"], "sell", current_price, coin_total, pnl, pnl_percent)
                            
                            pos["in_position"] = False
                        continue 

                    # 2-B. 이익실현 매도 로직
                    trader = CandlestickTrader(df)
                    decision = trader.get_decision()
                    manager.log_trade(pos["ticker"], decision, current_price) # 판단 기록

                    if decision == "sell":
                        if coin_total > 0:
                            bithumb_api.sell_market_order(pos["ticker"], coin_total)
                            pnl = (current_price - pos["purchase_price"]) * coin_total
                            pnl_percent = ((current_price - pos["purchase_price"]) / pos["purchase_price"]) * 100

                            notifier.report_trade(pos["ticker"], "sell", current_price, coin_total, pnl, pnl_percent)
                            manager.log_trade(pos["ticker"], "sell", current_price, coin_total, pnl, pnl_percent)

                            pos["in_position"] = False

                else: 
                    # --- 포지션 미보유 시: 매수 확인 ---
                    trader = CandlestickTrader(df)
                    decision = trader.get_decision()
                    manager.log_trade(pos["ticker"], decision, current_price) # 판단 기록

                    if decision == "buy":
                        total_krw = bithumb_api.get_balance("KRW")
                        investment_amount = total_krw * pos["capital_alloc"] # 할당된 자금 비율만큼만 투자
                        
                        if investment_amount > 5000:
                            bithumb_api.buy_market_order(pos["ticker"], investment_amount)
                            
                            pos["in_position"] = True
                            pos["purchase_price"] = current_price
                            volume = investment_amount / current_price
                            notifier.report_trade(pos["ticker"], "buy", current_price, volume)
                            manager.log_trade(pos["ticker"], "buy", current_price, volume)

            print(f"--- [{now.strftime('%H:%M:%S')}] 사이클 완료. 다음 캔들을 기다립니다. ---")
            time.sleep(TIME_INTERVAL_SECONDS)

        except Exception as e:
            print(f"[CRITICAL ERROR] 메인 루프 오류: {e}")
            notifier.send_message(f"🚨 봇 실행 중 심각한 오류가 발생했습니다: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()