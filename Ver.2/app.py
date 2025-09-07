# app.py (Thread 분리 최종 버전)
import os
import pandas as pd
from datetime import datetime, time
from flask import Flask, request
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from dotenv import load_dotenv
import python_bithumb
from threading import Thread # Thread 라이브러리 추가

# --- 초기화 ---
load_dotenv()
flask_app = Flask(__name__)
app = App(
    token=os.getenv("SLACK_BOT_TOKEN"),
    signing_secret=os.getenv("SLACK_SIGNING_SECRET")
)
handler = SlackRequestHandler(app)

try:
    bithumb_api = python_bithumb.Bithumb(
        access_key=os.getenv("BITHUMB_API_KEY"),
        secret_key=os.getenv("BITHUMB_SECRET_KEY")
    )
except Exception as e:
    print(f"Bithumb API 초기화 실패: {e}")
    bithumb_api = None

# --- 시간이 오래 걸리는 실제 작업 함수 ---
def process_report(say):
    """백그라운드에서 실행될 보고서 생성 및 전송 함수"""
    try:
        # 1. 최근 5개 거래 기록 조회
        log_path = os.path.join("logs", "trade_log_all.csv")
        if os.path.exists(log_path):
            df = pd.read_csv(log_path)
            trade_df = df[df['판단'].isin(['buy', 'sell'])]
            last_5_trades = trade_df.tail(5).to_markdown(index=False)
        else:
            last_5_trades = "아직 거래 기록이 없습니다."

        # 2. 현재 잔액 조회
        if bithumb_api:
            krw_balance = bithumb_api.get_balance("KRW")
            btc_balance = bithumb_api.get_balance("BTC")
            balance_text = (
                f"∙ *KRW 잔고:* `{krw_balance:,.0f}` 원\n"
                f"∙ *BTC 잔고:* `{btc_balance}` BTC"
            )
        else:
            balance_text = "API 키 문제로 잔액을 조회할 수 없습니다."

        # 3. 오전 8시 기준 실현 손익 계산
        if os.path.exists(log_path):
            df = pd.read_csv(log_path)
            df['시간'] = pd.to_datetime(df['시간'])
            today_8am = datetime.combine(datetime.today(), time(8, 0))
            today_trades = df[df['시간'] >= today_8am]
            today_pnl = today_trades['실현손익'].sum()
            pnl_icon = "📈" if today_pnl >= 0 else "📉"
            pnl_text = f"{pnl_icon} `{today_pnl:,.2f}` KRW"
        else:
            pnl_text = "거래 기록이 없어 계산할 수 없습니다."

        # 4. 슬랙 메시지 전송
        say(
            blocks=[
                {"type": "header", "text": {"type": "plain_text", "text": f"📊 자동매매 현황 보고 ({datetime.now().strftime('%H:%M:%S')})"}},
                {"type": "divider"},
                {"type": "section", "text": {"type": "mrkdwn", "text": f"*💰 현재 잔액*\n{balance_text}"}},
                {"type": "section", "text": {"type": "mrkdwn", "text": f"*오늘의 실현 손익 (오전 8시 기준)*\n{pnl_text}"}},
                {"type": "divider"},
                {"type": "section", "text": {"type": "mrkdwn", "text": f"*📈 최근 5개 실제 거래 기록*\n```{last_5_trades}```"}}
            ]
        )
    except Exception as e:
        say(f"❌ 보고서 생성 중 오류가 발생했습니다: {e}")

# --- 슬랙 명령어 핸들러 ---
@app.command("/report")
def show_report_command_handler(ack, say, command):
    ack() # 1. 즉시 응답하여 타임아웃 방지

    # 2. 시간이 걸리는 작업은 별도 스레드에서 실행
    thread = Thread(target=process_report, args=(say,))
    thread.start()

# --- Flask 라우터 ---
@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)

# --- 서버 실행 ---
if __name__ == "__main__":
    flask_app.run(host="0.0.0.0", port=3000)