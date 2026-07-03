#!/usr/bin/env python3
import json

import requests


req_url = ""


if not req_url.strip():
    raise SystemExit("req_url 값을 입력한 뒤 다시 실행하세요.")

with open("input_example.json", "r", encoding="utf-8") as f:
    data = json.load(f)

req_msg = json.dumps(data)
headers = {}

resp = requests.post(req_url, headers=headers, data=req_msg)

print("status_code:", resp.status_code)
try:
    print(json.dumps(resp.json(), ensure_ascii=False, indent=2))
except ValueError:
    print(resp.text)
