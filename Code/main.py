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
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import google.generativeai as genai
from PIL import Image
import python_bithumb

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

    def save_and_plot_ohlcv(self, 
    ticker: str = "KRW-BTC",
    interval: str = "minute5",
    count: int = 100,
    csv_filename: str ="",
    img_filename: str = "img/scalping_plot.png"
    ):
        # OHLCV 데이터 가져오기
        df = python_bithumb.get_ohlcv(ticker, interval=interval, count=count)
        if df is None or df.empty:
            print(f"[WARNING] {ticker} {interval} 데이터가 비어 있습니다. 작업을 중단합니다.")
            return
        
        csv_filename = "csv/" + csv_filename + ".csv"

        # CSV 저장
        csv_dir = os.path.dirname(csv_filename)
        if csv_dir and not os.path.exists(csv_dir):
            os.makedirs(csv_dir, exist_ok=True)
        
        df.to_csv(csv_filename, encoding='utf-8-sig', index=True)
        print(f"[INFO] 데이터 {count}개를 '{csv_filename}'에 저장했습니다.")

        img_filename = "img/" + img_filename + ".png"
        # 이미지 저장
        img_dir = os.path.dirname(img_filename)
        if img_dir and not os.path.exists(img_dir):
            os.makedirs(img_dir, exist_ok=True)

        plt.figure(figsize=(10, 6))
        plt.plot(df.index, df['open'], label='Open Price', color='blue')

        # 그래프 꾸미기
        plt.title(f"{ticker} Open Price ({interval})")
        plt.xlabel("DateTime")
        plt.ylabel("Price (KRW)")
        plt.legend()

        # x축 눈금 설정
        ax = plt.gca()
        ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=5))
        ax.xaxis.set_minor_locator(mdates.MinuteLocator(interval=1))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        plt.xticks(rotation=45)

        # Grid 설정
        plt.grid(which='both', linestyle='--', linewidth=0.5, alpha=0.7)
        plt.minorticks_on()

        plt.savefig(img_filename, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"[INFO] 그래프를 '{img_filename}'에 저장했습니다.")

    # Google Generative AI를 사용한 분석
    def analyze_with_google_ai(self, prompt: str) -> str:
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_text(prompt=prompt)
            return response.text
        except Exception as e:
            print(f"[ERROR] Google Generative AI 오류: {e}")
            return ""

    def run_autoupdate(self, interval=300, channel_name: str = "#money"):
        news_folder = "NEWS"
        os.makedirs(news_folder, exist_ok=True)
        csv_path = os.path.join(news_folder, "my_news.csv")
        print(f"[INFO] 자동 업데이트 시작 ({int(interval / 60)}분 간격)")
        last_date = datetime.date.today()

        try:
            while True:
                now = datetime.datetime.now()
                today_date = now.date()

                # (A) 날짜가 바뀌었으면 CSV 초기화
                if today_date != last_date:
                    if os.path.exists(csv_path):
                        os.remove(csv_path)
                        print(f"[INFO] 날짜 변경으로 CSV({csv_path})를 초기화했습니다.")
                    last_date = today_date

                print(f"\n[INFO] 뉴스 확인 중... ({now.strftime('%Y-%m-%d %H:%M:%S')})")

                # (B) 뉴스 크롤링
                driver = webdriver.Chrome()
                try:
                    driver.get("https://coinness.com/article")
                    time.sleep(5)  # JS 로딩 대기

                    css = "#root > div > div.Wrap-sc-v065lx-0.hwmGSB > div > main > div.ContentContainer-sc-91rcal-0.jJHYjq > div.ArticleListContainer-sc-cj3rkv-0.fkxjqP"
                    container = driver.find_element(By.CSS_SELECTOR, css)
                    raw_text = container.text
                except Exception as e:
                    print(f"[ERROR] 크롤링 실패: {e}")
                    raw_text = ""
                finally:
                    driver.quit()

                if not raw_text:
                    print("[WARNING] 크롤링 결과가 비어 있습니다.")
                    time.sleep(interval)
                    continue

                # (C) 뉴스 텍스트 파싱
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
                new_df = pd.DataFrame(articles, columns=["time", "date", "title", "content"])
                if new_df.empty:
                    print("[INFO] 새로 추출된 기사가 없습니다.")
                    time.sleep(interval)
                    continue

                # (D) CSV 저장 및 Slack 메시지 전송
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

                print(f"[INFO] {int(interval / 60)}분 뒤 다음 업데이트 진행...")
                time.sleep(interval)

        except KeyboardInterrupt:
            print("[INFO] 자동 업데이트 종료 (KeyboardInterrupt).")

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