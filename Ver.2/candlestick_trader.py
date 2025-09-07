# candlestick_trader.py
import pandas as pd
import numpy as np

class CandlestickTrader:
    def __init__(self, candles_df):
        """캔들스틱 데이터프레임으로 초기화"""
        if candles_df is None or candles_df.empty:
            raise ValueError("캔들 데이터가 비어있습니다.")
        self.df = candles_df
        self.prev_candle = self.df.iloc[-2] # 이전 캔들
        self.last_candle = self.df.iloc[-1] # 마지막(현재) 캔들

    def find_support_resistance(self, window=20):
        """최근 N개 캔들에서 간단한 지지/저항선을 찾습니다."""
        recent_candles = self.df.iloc[-window:-1] # 최근 N개 (마지막 캔들 제외)
        support = recent_candles['low'].min()
        resistance = recent_candles['high'].max()
        return support, resistance

    # --- 캔들 패턴 감지 함수들 ---
    def is_bullish_engulfing(self):
        """상승 장악형 패턴인지 확인"""
        # 이전: 음봉, 현재: 양봉
        if self.prev_candle['open'] < self.prev_candle['close'] or self.last_candle['open'] > self.last_candle['close']:
            return False
        # 현재 캔들이 이전 캔들을 완전히 감싸는지 확인
        return self.last_candle['close'] > self.prev_candle['open'] and self.last_candle['open'] < self.prev_candle['close']

    def is_bearish_engulfing(self):
        """하락 장악형 패턴인지 확인"""
        # 이전: 양봉, 현재: 음봉
        if self.prev_candle['open'] > self.prev_candle['close'] or self.last_candle['open'] < self.last_candle['close']:
            return False
        return self.last_candle['open'] > self.prev_candle['close'] and self.last_candle['close'] < self.prev_candle['open']

    def is_hammer(self):
        """망치형 패턴인지 확인 (상승 반전)"""
        body_size = abs(self.last_candle['close'] - self.last_candle['open'])
        lower_wick = self.last_candle['open'] - self.last_candle['low']
        upper_wick = self.last_candle['high'] - self.last_candle['close']
        # 조건: 몸통이 아래 꼬리의 절반보다 작고, 윗 꼬리는 매우 짧음
        return lower_wick > body_size * 2 and upper_wick < body_size * 0.5

    def is_shooting_star(self):
        """유성형 패턴인지 확인 (하락 반전)"""
        body_size = abs(self.last_candle['close'] - self.last_candle['open'])
        upper_wick = self.last_candle['high'] - self.last_candle['open']
        lower_wick = self.last_candle['close'] - self.last_candle['low']
        # 조건: 몸통이 위 꼬리의 절반보다 작고, 아래 꼬리는 매우 짧음
        return upper_wick > body_size * 2 and lower_wick < body_size * 0.5

    def get_decision(self):
        """종합적인 매매 결정을 반환"""
        support, resistance = self.find_support_resistance()
        current_price = self.last_candle['close']

        # 가격이 지지선 근처에 있는지 확인 (오차 범위 0.5%)
        is_near_support = abs(current_price - support) / support < 0.005
        # 가격이 저항선 근처에 있는지 확인
        is_near_resistance = abs(current_price - resistance) / resistance < 0.005

        # --- 매수 결정 로직 ---
        if is_near_support:
            if self.is_bullish_engulfing():
                print("[신호] 지지선에서 '상승 장악형' 패턴 발생!")
                return "buy"
            if self.is_hammer():
                print("[신호] 지지선에서 '망치형' 패턴 발생!")
                return "buy"

        # --- 매도 결정 로직 ---
        if is_near_resistance:
            if self.is_bearish_engulfing():
                print("[신호] 저항선에서 '하락 장악형' 패턴 발생!")
                return "sell"
            if self.is_shooting_star():
                print("[신호] 저항선에서 '유성형' 패턴 발생!")
                return "sell"

        return "hold"