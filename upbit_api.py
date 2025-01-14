# upbit_api.py
import requests
import jwt
import uuid
import hashlib
from urllib.parse import urlencode
from upbit_keys import get_upbit_keys

UPBIT_API_URL = "https://api.upbit.com/v1"

def get_account_info():
    keys = get_upbit_keys()
    access_key = keys["access_key"]
    secret_key = keys["secret_key"]
    
    payload = {
        'access_key': access_key,
        'nonce': str(uuid.uuid4()),
    }
    jwt_token = jwt.encode(payload, secret_key)
    authorize_token = f'Bearer {jwt_token}'

    headers = {"Authorization": authorize_token}
    res = requests.get(f"{UPBIT_API_URL}/accounts", headers=headers)
    
    if res.status_code == 200:
        return res.json()
    else:
        print(f"Upbit 계좌 정보 요청 실패: {res.status_code}, {res.text}")
        return None
