import os
import time
import re
import json
import datetime
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv
import google.generativeai as genai
from PIL import Image


class Coin_Bot:
    def __init__(self, slack_token: str, google_api_key: str, channel_name: str="#money"):
        self.slack_client = WebClient(token=slack_token)
        genai.configure(api_key=google_api_key)
        self.channel_name = channel_name
        self.news_folder = "NEWS"
        os.makedirs(self.news_folder, exist_ok=True)

    # Slack 메시지 전송
    def send_message(self, message: str):
        try:
            self.slack_client.chat_postMessage(channel=self.channel_name, text=message)
            print(f"[INFO] Slack 메시지가 전송되었습니다.")
        except SlackApiError as e:
            print(f"[ERROR] Slack API 오류: {e.response['error']}")

    # Selenium을 사용한 뉴스 크롤링
    def crawl_with_selenium(self, url: str, css_selector: str) -> str:
        driver = webdriver.Chrome()
        driver.get(url)
        time.sleep(5)  # JS 로딩 대기

        try:
            container = driver.find_element(By.CSS_SELECTOR, css_selector)
            return container.text
        except Exception as e:
            print(f"[ERROR] 요소 찾기 실패: {e}")
            return ""
        finally:
            driver.quit()

    # 뉴스 텍스트 파싱
    def parse_news_text(self, raw_text: str) -> pd.DataFrame:
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        time_pattern = re.compile(r"^\d{2}:\d{2}$")

        articles = []
        current_time, current_date, current_title = None, None, None
        content_lines = []

        def save_article():
            if current_time and current_date and current_title:
                articles.append(
                    {
                        "time": current_time,
                        "date": current_date,
                        "title": current_title,
                        "content": "\n".join(content_lines).strip(),
                    }
                )

        state = "idle"
        for line in lines:
            if time_pattern.match(line):  # 시간 감지
                save_article()
                current_time = line
                current_date, current_title = None, None
                content_lines = []
                state = "got_time"
                continue

            if state == "got_time":
                current_date = line
                state = "got_date"
                continue

            if state == "got_date":
                current_title = line
                state = "got_title"
                continue

            content_lines.append(line)
            state = "collecting_content"

        save_article()
        return pd.DataFrame(articles, columns=["time", "date", "title", "content"])

    # Google Generative AI를 사용한 분석
    def analyze_with_google_ai(self, prompt: str) -> str:
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_text(prompt=prompt)
            return response.text
        except Exception as e:
            print(f"[ERROR] Google Generative AI 오류: {e}")
            return ""

    # 뉴스 저장 및 Slack 메시지 전송
    def process_and_send(self, new_df: pd.DataFrame, csv_path: str):
        if new_df.empty:
            print("[INFO] 새로 추출된 기사가 없습니다.")
            return

        if os.path.exists(csv_path):
            try:
                existing_df = pd.read_csv(csv_path)
            except pd.errors.EmptyDataError:
                existing_df = pd.DataFrame(columns=["time", "date", "title", "content"])
        else:
            existing_df = pd.DataFrame(columns=["time", "date", "title", "content"])

        existing_signatures = {
            (row["time"], row["date"], row["title"], row["content"])
            for _, row in existing_df.iterrows()
        }

        new_articles = []
        for _, row in new_df.iterrows():
            sig = (row["time"], row["date"], row["title"], row["content"])
            if sig not in existing_signatures:
                new_articles.append(row)
                existing_signatures.add(sig)

        if new_articles:
            message_parts = []
            for row in new_articles:
                part = f"[{row['time']}][{row['date']}]\n{row['title']}\n{row['content']}\n"
                message_parts.append(part)
            self.send_message("\n".join(message_parts))

        new_articles_df = pd.DataFrame(new_articles, columns=["time", "date", "title", "content"])
        final_df = pd.concat([existing_df, new_articles_df], ignore_index=True).drop_duplicates()
        final_df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    # 자동 업데이트 실행
    def run_autoupdate(self, interval: int = 300, url: str = "", css_selector: str = ""):
        csv_path = os.path.join(self.news_folder, "my_news.csv")
        last_date = datetime.date.today()

        try:
            while True:
                now = datetime.datetime.now()
                if now.date() != last_date:
                    if os.path.exists(csv_path):
                        os.remove(csv_path)
                    last_date = now.date()

                raw_text = self.crawl_with_selenium(url, css_selector)
                parsed_news = self.parse_news_text(raw_text)
                self.process_and_send(parsed_news, csv_path)

                time.sleep(interval)
        except KeyboardInterrupt:
            print("[INFO] 자동 업데이트가 종료되었습니다.")

    # 이미지를 포함한 프롬프트 생성
    def create_openai_prompt(self, role_description: str, tasks: str, image_file_paths: list) -> str:
        image_descriptions = []
        for image_path in image_file_paths:
            if not os.path.exists(image_path):
                image_descriptions.append(f"[Error: {image_path} not found]")
            else:
                with open(image_path, "rb") as image_file:
                    encoded_image = base64.b64encode(image_file.read()).decode("utf-8")
                    image_descriptions.append(f"Image: {os.path.basename(image_path)} - {encoded_image[:50]}...")

        return f"Role: {role_description}\nTodo: {tasks}\nImages: {' & '.join(image_descriptions)}"

# # 실행 예제
# if __name__ == "__main__":
#     load_dotenv()
#     SLACK_TOKEN = os.getenv("SLACK_BOT_TOKEN")
#     GOOGLE_API_KEY = os.getenv("GEMINI_API_KEY")

#     bot = CoinNewsBot(slack_token=SLACK_TOKEN, google_api_key=GOOGLE_API_KEY, channel_name="#general")
#     bot.run_autoupdate(interval=300, url="https://coinness.com/article", css_selector="CSS_SELECTOR")
