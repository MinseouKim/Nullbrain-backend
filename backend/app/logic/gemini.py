# backend/app/logic/gemini.py
import os
import json
from typing import Optional, List
from dotenv import load_dotenv
import google.generativeai as genai

# --- 1. 환경 설정 ---
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# --- 2. Gemini 모델 설정 ---
model = None
if API_KEY:
    genai.configure(api_key=API_KEY)

    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]

    generation_config = {
        "temperature": 0.7,
        "response_mime_type": "application/json",
    }

    model = genai.GenerativeModel(
        MODEL_NAME,
        safety_settings=safety_settings,
        generation_config=generation_config,
    )


# --- 3. AI 피드백 생성 함수 ---
async def get_conversational_feedback(
    exercise_name: str,
    rep_counter: int,
    stage: str,
    body_profile: Optional[dict] = None,
    real_time_analysis: Optional[dict] = None,
    angle: Optional[float] = None,
    history: Optional[List[str]] = None,
) -> dict:
    """
    체형 및 실시간 분석 정보를 바탕으로 '정확도'와 '피드백'을 JSON으로 요청합니다.
    """
    if not model:
        return {"accuracy": 0, "feedback": "⚠️ Gemini API Key가 설정되지 않았습니다."}

    profile_section = f"* 사용자의 체형 분석 정보 (정적 데이터):\n{body_profile}\n" if body_profile else ""
    analysis_section = f"* 이번 세트의 실시간 움직임 분석 결과 (동적 데이터):\n{real_time_analysis}\n" if real_time_analysis else ""

    prompt = f"""
당신은 사용자의 정적 체형 데이터와 실시간 움직임 데이터를 종합적으로 분석하는 전문 AI 퍼스널 트레이너입니다. 
아래에 제공된 분석 결과들은 참고용 데이터입니다.
이 내용을 그대로 반복하거나 인용하지 말고, 당신의 판단으로 최종 종합 피드백을 만들어야 합니다.

다음 두 가지 데이터를 바탕으로 분석하세요:

{profile_section}
{analysis_section}

* 현재 운동 정보 (참고용):
- 운동 종류: {exercise_name}
- 단계: {stage}
- 반복 횟수: {rep_counter}

* JSON 출력 규칙:
1. "accuracy": 0~100 범위의 정수로 전체 동작 정확도를 평가하세요.
2. "feedback": 위의 데이터를 참고하되, 단순 복붙이 아닌 당신의 종합 판단으로 **70자 이내의 자연스러운 한국어 문장**을 만드세요.
3. 피드백에는 "좌우", "깊이" 등 세부 지표 단어를 직접 인용하지 말고, 종합적인 느낌을 전달하세요.

예시 출력:
{{
  "accuracy": 85,
  "feedback": "자세가 불안정합니다. 좌우 불균형 데이터를 볼 때 왼쪽으로 쏠리는 경향이 있으니 중앙에 무게를 두세요."
}}
"""

    try:
        resp = await model.generate_content_async(prompt)
        try:
            result = json.loads(resp.text)
        except Exception:
            print(f"[WARN] Gemini 응답이 JSON 형식이 아님: {resp.text}")
            result = {"accuracy": 0, "feedback": "⚠️ AI 응답 파싱 실패"}

        return result
    
    except Exception as e:
        print(f"--- GEMINI API ERROR ---")
        print(f"Error: {e}")
        if "resp" in locals() and hasattr(resp, "prompt_feedback"):
            print(f"Prompt Feedback: {resp.prompt_feedback}")
        print(f"--------------------------")
        return {"accuracy": 0, "feedback": "⚠️ AI 피드백 생성에 실패했습니다."}
