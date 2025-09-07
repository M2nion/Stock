# diagnosis.py
import os
from dotenv import load_dotenv
import python_bithumb
import json # 보기 편하게 출력하기 위한 라이브러리

load_dotenv()

try:
    bithumb_api = python_bithumb.Bithumb(
        access_key=os.getenv("BITHUMB_API_KEY"),
        secret_key=os.getenv("BITHUMB_SECRET_KEY")
    )

    print("="*50)
    print("빗썸 API로부터 받은 '전체 자산 데이터 원본'을 출력합니다.")
    print("="*50)

    # get_balance가 아닌, 그 이전 단계인 get_balances()를 호출합니다.
    all_balances_raw = bithumb_api.get_balances()

    # 결과를 보기 편한 JSON 형태로 출력합니다.
    print(json.dumps(all_balances_raw, indent=2, ensure_ascii=False))

except Exception as e:
    print(f"오류가 발생했습니다: {e}")