# main.py
from slack_notifier import send_slack_message
from upbit_api import get_account_info
import time

def format_slack_message(account_info):
    if not account_info:
        return "Upbit 계좌 정보를 가져오는 데 실패했습니다."
    
    balance_krw = next((item for item in account_info if item['currency'] == 'KRW'), {'balance': '0'})['balance']
    stock_list = ", ".join([item['currency'] for item in account_info if item['currency'] != 'KRW'])
    
    message = f"""
    ※ 주식 시장이 개장하기 10분 전에 보내드리는 메시지입니다. ※
    
    - 계좌번호: 69703743-01
    - 현재 나의 잔고: {balance_krw} KRW
    - 현재 보유 중인 주식: {stock_list if stock_list else "0 종목"}
    - 수익률: 0.00%
    """
    return message

def main():
    # 매일 아침 9시 전에 메시지를 전송하도록 설정 (예: 08:50)
    send_time = "08:50"

    while True:
        current_time = time.strftime("%H:%M")
        
        if current_time == send_time:
            account_info = get_account_info()
            slack_message = format_slack_message(account_info)
            send_slack_message("#general", slack_message)
            print("Slack 메시지를 전송했습니다.")
            
            # 다음날을 기다리도록 설정
            time.sleep(60 * 60 * 24)
        else:
            time.sleep(30)  # 30초 간격으로 확인

if __name__ == "__main__":
    main()
