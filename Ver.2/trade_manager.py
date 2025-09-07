# trade_manager.py
import pandas as pd
import os
from datetime import datetime
import schedule
import time
from slack_bot import SlackNotifier # 위에서 작성한 슬랙 봇 임포트

class TradeManager:
    # def __init__(self, log_dir="logs"):
    #     """거래 관리자 초기화 (로깅 및 손절)"""
    #     self.log_dir = log_dir
    #     os.makedirs(self.log_dir, exist_ok=True)
    #     self.log_file_path = self.get_log_path()
    #     self.notifier = SlackNotifier()
    #     self.initialize_log_file()

    def __init__(self, log_dir="logs"):
        """거래 관리자 초기화 (로깅 및 손절)"""
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)
        # 단일 로그 파일을 사용하도록 경로 고정
        self.log_file_path = os.path.join(self.log_dir, "trade_log_all.csv")
        self.notifier = SlackNotifier()
        self.initialize_log_file()
        
    def get_log_path(self):
        """오늘 날짜에 맞는 로그 파일 경로 생성"""
        return os.path.join(self.log_dir, f"trade_log_{datetime.now().strftime('%Y-%m-%d')}.csv")

    def initialize_log_file(self):
        """로그 파일이 없으면 새로 생성하고 한글 헤더를 추가"""
        if not os.path.exists(self.log_file_path):
            # --- ✨ 헤더를 한글로 변경 ---
            df = pd.DataFrame(columns=[
                "시간", "종목", "판단", 
                "가격", "수량", "실현손익", "수익률(%)"
            ])
            # --------------------------
            df.to_csv(self.log_file_path, index=False, encoding='utf-8-sig')
            print(f"[INFO] 새로운 통합 로그 파일 생성: {self.log_file_path}")

    def log_trade(self, ticker: str, side: str, price: float, volume: float = 0.0, pnl: float = 0.0, pnl_percent: float = 0.0):
        """거래 내역 및 AI 판단을 CSV 파일에 기록"""
        try:
            # --- ✨ 데이터의 키(Key)를 한글 헤더에 맞춤 ---
            new_log = pd.DataFrame([{
                "시간": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "종목": ticker,
                "판단": side,
                "가격": price,
                "수량": volume,
                "실현손익": pnl,
                "수익률(%)": pnl_percent
            }])
            # ----------------------------------------
            new_log.to_csv(self.log_file_path, mode='a', header=False, index=False, encoding='utf-8-sig')
            
            if side in ["buy", "sell"]:
                print(f"[LOG] 거래 기록 완료: {side} {ticker} @ {price}")
            else:
                print(f"[LOG] AI 판단 기록 완료: {side}")
        except Exception as e:
            print(f"[ERROR] 로그 기록 중 오류 발생: {e}")
            
    def check_stop_loss(self, current_price: float, purchase_price: float, stop_loss_percent: float) -> bool:
        """손절매 조건을 확인"""
        if purchase_price <= 0:
            return False
        loss_percent = ((current_price - purchase_price) / purchase_price) * 100
        if loss_percent <= -abs(stop_loss_percent):
            print(f"🚨 [손절매 발동] 현재가: {current_price:,.0f} | 매수가: {purchase_price:,.0f} | 손실률: {loss_percent:.2f}%")
            return True
        return False
        
    def reset_log_daily(self):
        """매일 자정에 로그 파일을 백업하고 새로 시작"""
        print("[INFO] 일일 로그 리셋 작업을 시작합니다.")
        
        # 1. 어제 로그 파일 경로 확인
        yesterday_log_path = self.log_file_path
        if not os.path.exists(yesterday_log_path):
            print("[INFO] 어제 거래 로그가 없어 리셋을 건너뜁니다.")
            # 새 로그 파일 초기화만 진행
            self.log_file_path = self.get_log_path()
            self.initialize_log_file()
            return

        # 2. 어제 로그 파일 슬랙으로 전송
        try:
            df = pd.read_csv(yesterday_log_path)
            total_pnl = df['pnl'].sum()
            message = f"*{datetime.now().strftime('%Y-%m-%d')}* 어제자 거래 로그 파일입니다.\n총 실현 손익: `{total_pnl:,.2f}` KRW"
            self.notifier.send_message(message, file_path=yesterday_log_path)
        except Exception as e:
            self.notifier.send_message(f"어제자 로그 파일 공유에 실패했습니다: {e}")

        # 3. 새 로그 파일 경로 설정 및 초기화
        self.log_file_path = self.get_log_path()
        self.initialize_log_file()
        print("[INFO] 새로운 오늘자 로그 파일을 준비했습니다.")
        
# --- 스케줄링 및 테스트 ---
def run_daily_reset_job():
    """매일 자정에 실행될 작업"""
    manager = TradeManager()
    manager.reset_log_daily()

def start_scheduler():
    """스케줄러 시작"""
    # 매일 00:00에 run_daily_reset_job 함수 실행
    schedule.every().day.at("00:00").do(run_daily_reset_job)
    print("[SCHEDULER] 일일 로그 리셋 스케줄러가 시작되었습니다.")
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    # TradeManager 기능 테스트
    manager = TradeManager()
    manager.log_trade("KRW-ETH", "buy", 4500000, 0.01)
    time.sleep(1)
    manager.log_trade("KRW-ETH", "sell", 4550000, 0.01, pnl=4500, pnl_percent=1.0)
    
    # 손절매 로직 테스트
    is_stop_loss_triggered = manager.check_stop_loss(
        current_price=88000000, 
        purchase_price=90000000, 
        stop_loss_percent=2.0
    )
    print(f"손절매 필요 여부: {is_stop_loss_triggered}") # True 출력 예상
    
    # 일일 리셋 기능 직접 실행 테스트
    # manager.reset_log_daily() 
    
    # 스케줄러 실행 (실제 봇 운영 시 백그라운드에서 실행)
    # print("실제 봇에서는 아래 함수를 실행하여 매일 자정 로그 리셋을 자동화합니다.")
    # start_scheduler()