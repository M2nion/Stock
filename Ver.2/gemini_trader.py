# gemini_trader.py
import os
import google.generativeai as genai
from dotenv import load_dotenv
import pandas as pd
import python_bithumb # 사용자가 제공한 public_api 모듈

load_dotenv()

class GeminiTrader:
    def __init__(self, ticker="KRW-BTC"):
        """Gemini AI를 이용한 트레이딩 결정 봇"""
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY가 .env 파일에 설정되지 않았습니다.")
        
        genai.configure(api_key=self.gemini_api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.ticker = ticker
        
    def get_market_data_for_prompt(self, interval="minute15", count=50):
        """AI 프롬프트에 사용할 시장 데이터(OHLCV, 기술 지표)를 가져옵니다."""
        try:
            # 1. 빗썸에서 캔들 데이터(OHLCV) 가져오기
            df = python_bithumb.get_ohlcv(self.ticker, interval=interval, count=count)
            if df is None or df.empty:
                print("[WARNING] 빗썸에서 시장 데이터를 가져오지 못했습니다.")
                return None
            
            # 2. 간단한 기술 지표 추가 (이동평균, RSI) - pandas_ta 라이브러리 필요
            try:
                import pandas_ta as ta
                df.ta.sma(length=20, append=True) # 20 이평선
                df.ta.rsi(length=14, append=True) # 14 RSI
                # 불필요한 컬럼 제거
                df = df[['open', 'high', 'low', 'close', 'volume', 'SMA_20', 'RSI_14']]
            except ImportError:
                print("[WARNING] 'pandas_ta' 라이브러리가 없어 기술 지표를 추가하지 못했습니다.")
                df = df[['open', 'high', 'low', 'close', 'volume']]
                
            # AI에게 텍스트로 쉽게 이해시키기 위해 최신 10개 데이터만 문자열로 변환
            return df.tail(10).to_string()
        except Exception as e:
            print(f"[ERROR] 시장 데이터 준비 중 오류: {e}")
            return None

    def get_decision(self) -> str:
        """시장 데이터를 기반으로 Gemini AI에게 매매 결정을 요청합니다."""
        market_data_str = self.get_market_data_for_prompt()
        if not market_data_str:
            return "hold" # 데이터가 없으면 관망

        # --- AI에게 전달할 프롬프트 ---
        prompt = f"""
        당신은 암호화폐 단타 트레이딩 전문가입니다. 당신의 목표는 제공된 시장 데이터를 분석하여 오직 'buy', 'sell', 'hold' 중 하나의 결정만 내리는 것입니다. 다른 설명은 절대 하지 마세요.

        [분석 대상]
        - 코인: {self.ticker}
        - 현재 상황: 변동성이 큰 단기 트레이딩

        [최신 시장 데이터]
        {market_data_str}

        [규칙]
        1. 상승 추세가 명확하고 RSI가 과매수(70 이상) 상태가 아닐 때 'buy'를 고려하세요.
        2. 하락 추세가 명확하고 RSI가 과매도(30 이하) 상태가 아닐 때 'sell'을 고려하세요.
        3. 추세가 불분명하거나, 이미 너무 많이 오르거나 내렸을 때는 'hold'를 선택하여 위험을 관리하세요.
        4. 당신의 답변은 반드시 'buy', 'sell', 'hold' 중 하나여야 합니다.

        [결정]
        """
        
        try:
            print("[INFO] Gemini AI에게 매매 결정을 요청합니다...")
            response = self.model.generate_content(prompt)
            decision = response.text.strip().lower()
            
            if decision not in ["buy", "sell", "hold"]:
                print(f"[WARNING] AI가 유효하지 않은 답변을 했습니다: {decision}. 안전을 위해 'hold'로 처리합니다.")
                return "hold"
                
            print(f"🧠 [AI 결정] {decision.upper()}")
            return decision
            
        except Exception as e:
            print(f"[ERROR] Gemini AI 요청 중 오류 발생: {e}")
            return "hold" # 오류 발생 시 안전하게 관망


if __name__ == "__main__":
    trader = GeminiTrader(ticker="KRW-BTC")
    
    # AI 매매 결정 테스트
    final_decision = trader.get_decision()
    
    # (참고) 실제 봇이라면 이 결정에 따라 Bithumb 주문을 실행합니다.
    # if final_decision == "buy":
    #     bithumb_private_client.buy_market_order(...)
    # elif final_decision == "sell":
    #     bithumb_private_client.sell_market_order(...)