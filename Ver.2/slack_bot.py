# slack_bot.py
import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv

# .env 파일에서 환경 변수 로드
load_dotenv()

class SlackNotifier:
    def __init__(self):
        """슬랙 알림 봇 초기화"""
        self.slack_token = os.getenv("SLACK_BOT_TOKEN")
        if not self.slack_token:
            raise ValueError("SLACK_BOT_TOKEN이 .env 파일에 설정되지 않았습니다.")
            
        self.client = WebClient(token=self.slack_token)
        self.channel = os.getenv("SLACK_CHANNEL_NAME", "#trading-bot") # 기본 채널명 설정

    def send_message(self, message: str, file_path: str = None):
        """기본 메시지 및 파일 전송"""
        try:
            # 파일이 있는 경우 파일 업로드
            if file_path:
                self.client.files_upload_v2(
                    channel=self.channel,
                    file=file_path,
                    initial_comment=message,
                    title=os.path.basename(file_path)
                )
                print(f"✅ 슬랙으로 메시지 및 파일 전송 성공: {os.path.basename(file_path)}")
            else:
                self.client.chat_postMessage(channel=self.channel, text=message)
                print(f"✅ 슬랙으로 메시지 전송 성공.")
        except SlackApiError as e:
            print(f"❌ 슬랙 API 오류 발생: {e.response['error']}")

    def report_trade(self, ticker: str, side: str, price: float, volume: float, pnl: float = 0.0, pnl_percent: float = 0.0):
        """거래 체결 내역 보고"""
        icon = "🟢" if side.lower() == "buy" else "🔴"
        action = "매수" if side.lower() == "buy" else "매도"
        
        message = (
            f"{icon} *[{ticker}] {action} 체결*\n\n"
            f"∙ *체결 가격:* `{price:,.0f}` KRW\n"
            f"∙ *체결 수량:* `{volume}` {ticker.split('-')[1]}\n"
        )
        
        # 매도 시 수익률 정보 추가
        if side.lower() == "sell":
            pnl_icon = "📈" if pnl >= 0 else "📉"
            message += f"∙ *실현 손익:* `{pnl:,.2f}` KRW ({pnl_icon} `{pnl_percent:.2f}` %)\n"
            
        self.send_message(message)

    def report_daily_summary(self, total_pnl: float, total_trades: int, win_rate: float, daily_goal: float):
        """일일 거래 마감 보고"""
        pnl_icon = "🎉" if total_pnl >= 0 else "😭"
        
        # 목표 달성률 계산
        achievement_rate = (total_pnl / daily_goal) * 100 if daily_goal > 0 else 0
        
        message = (
            f"*{datetime.now().strftime('%Y-%m-%d')} 거래 마감 브리핑*\n\n"
            f"∙ *총 거래 횟수:* `{total_trades}` 회\n"
            f"∙ *승률:* `{win_rate:.2f}` %\n"
            f"∙ *총 실현 손익:* `{total_pnl:,.2f}` KRW {pnl_icon}\n"
            f"∙ *일일 목표 달성률:* `{achievement_rate:.2f}` % (목표: `{daily_goal:,.0f}` KRW)\n\n"
            "오늘 하루도 수고하셨습니다! 내일도 성공적인 투자를 기원합니다."
        )
        self.send_message(message)

# 테스트용 코드
if __name__ == "__main__":
    from datetime import datetime
    
    notifier = SlackNotifier()
    # 기본 메시지 테스트
    notifier.send_message("🤖 자동매매 봇이 시작되었습니다.")
    
    # 매수/매도 보고 테스트
    notifier.report_trade(ticker="KRW-BTC", side="buy", price=90000000, volume=0.0001)
    time.sleep(1) # 슬랙 메시지 순서 보장을 위한 딜레이
    notifier.report_trade(ticker="KRW-BTC", side="sell", price=90500000, volume=0.0001, pnl=4500, pnl_percent=5.0)
    
    # 일일 마감 보고 테스트
    notifier.report_daily_summary(total_pnl=125000, total_trades=20, win_rate=65.0, daily_goal=100000)