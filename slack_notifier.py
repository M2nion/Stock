# slack_notifier.py
import requests
from slack_keys import get_slack_key

def send_slack_message(channel, message):
    slack_key = get_slack_key()
    url = "https://slack.com/api/chat.postMessage"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {slack_key['api_token']}"
    }
    payload = {
        "channel": channel,
        "text": message
    }
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code != 200:
        print(f"Slack 메시지 전송 실패: {response.status_code}, {response.text}")
    else:
        print("Slack 메시지 전송 성공")
