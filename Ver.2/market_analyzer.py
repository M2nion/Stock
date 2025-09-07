# market_analyzer.py
import os
import pandas as pd
import pandas_ta as ta
import python_bithumb
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

class MarketAnalyzer:
    def __init__(self):
        """Gemini AI를 이용한 시장 분석기"""
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY가 .env 파일에 설정되지 않았습니다.")

        genai.configure(api_key=self.gemini_api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def _get_chart_summary(self, ticker: str, interval: str) -> str:
        """차트 데이터를 가져와 요약 텍스트를 생성합니다."""
        try:
            df = python_bithumb.get_ohlcv(ticker, interval, count=100)
            if df is None or df.empty:
                return "데이터 없음"

            # 주요 지표 계산
            df.ta.sma(length=20, append=True) # 20 이평선
            df.ta.sma(length=60, append=True) # 60 이평선
            df.ta.rsi(length=14, append=True) # 14 RSI

            latest = df.iloc[-1]
            summary = (
                f"현재가: {latest['close']:,.0f}, "
                f"20-MA: {latest['SMA_20']:,.0f}, "
                f"60-MA: {latest['SMA_60']:,.0f}, "
                f"RSI: {latest['RSI_14']:.2f}"
            )
            return summary
        except Exception:
            return "분석 오류"

    def get_market_regime(self, ticker="KRW-BTC") -> str:
        """
        여러 시간대 차트를 분석하여 현재 시장 국면을 판단합니다.
        'bullish', 'bearish', 'neutral' 중 하나를 반환합니다.
        """
        print("[분석가] 5분, 15분, 1시간봉 데이터 종합 분석 중...")
        summary_5m = self._get_chart_summary(ticker, "minute5")
        summary_15m = self._get_chart_summary(ticker, "minute15")
        summary_1h = self._get_chart_summary(ticker, "hour") # 빗썸은 1시간봉을 'hour'로 요청

        prompt = f"""
        당신은 최고의 암호화폐 시장 분석가입니다. 아래 제공된 여러 시간대의 차트 데이터를 종합하여, 현재 시장의 전반적인 국면이 'bullish'(상승 우세), 'bearish'(하락 우세), 'neutral'(중립/횡보) 중 무엇인지 판단해주세요. 오직 세 단어 중 하나로만 답변해야 합니다.

        [분석 데이터]
        - 1시간봉 (장기 추세): {summary_1h}
        - 15분봉 (중기 추세): {summary_15m}
        - 5분봉 (단기 추세): {summary_5m}

        [판단 기준]
        - 장기 추세(1시간봉)를 가장 중요하게 고려하세요.
        - 이동평균선이 정배열(20-MA > 60-MA)이고 RSI가 50 이상이면 'bullish' 경향이 강합니다.
        - 이동평균선이 역배열(20-MA < 60-MA)이고 RSI가 50 이하면 'bearish' 경향이 강합니다.
        - 신호가 엇갈리거나 방향성이 없으면 'neutral'로 판단하세요.

        [시장 국면 판단]
        """

        try:
            response = self.model.generate_content(prompt)
            decision = response.text.strip().lower()

            if decision in ["bullish", "bearish", "neutral"]:
                print(f"🧠 [분석가 판단] 현재 시장 국면: {decision.upper()}")
                return decision
            else:
                print(f"[분석가 경고] AI가 유효하지 않은 답변을 했습니다: {decision}")
                return "neutral" # 오류 시 안전하게 중립으로 처리
        except Exception as e:
            print(f"[분석가 오류] Gemini AI 요청 중 오류 발생: {e}")
            return "neutral"