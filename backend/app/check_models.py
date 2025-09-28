# backend/check_models.py

import os
import requests
from dotenv import load_dotenv

# .env 파일에서 API 키를 불러옵니다.
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")

if not API_KEY:
    print("오류: .env 파일에서 GOOGLE_API_KEY를 찾을 수 없습니다.")
else:
    # 모델 목록을 요청하는 API 엔드포인트
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={API_KEY}"
    
    print("사용 가능한 모델 목록을 요청합니다...")
    
    try:
        response = requests.get(url)
        response.raise_for_status() # HTTP 오류가 있으면 예외 발생
        
        data = response.json()
        
        print("\n--- ✅ 사용 가능한 모델 목록 ---")
        if 'models' in data:
            for model in data['models']:
                # generateContent를 지원하는 모델만 필터링
                if 'generateContent' in model.get('supportedGenerationMethods', []):
                    print(f"- {model['name']}")
        else:
            print("사용 가능한 모델이 없습니다.")
        print("----------------------------\n")

    except requests.exceptions.RequestException as e:
        print("\n--- ❌ 요청 실패 ---")
        print(f"오류: {e}")
        if e.response:
            print(f"상태 코드: {e.response.status_code}")
            print(f"응답 내용: {e.response.text}")
        print("---------------------\n")