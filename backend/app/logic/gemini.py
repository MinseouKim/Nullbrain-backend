import os
import json
import asyncio
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
        generation_config=generation_config
    )

# --- 3. AI 피드백 생성 함수 ---
async def get_conversational_feedback(
    exercise_name: str,
    rep_counter: int,
    stage: str,
    body_profile: dict | None = None,
    real_time_analysis: dict | None = None,
    angle: float | None = None,
    history: list | None = None,
) -> dict:
    """
    체형 및 실시간 분석 정보를 바탕으로 '정확도'와 '피드백'을 JSON으로 요청합니다.
    """
    if not model:
        return {"accuracy": 0, "feedback": "⚠️ Gemini API Key가 설정되지 않았습니다."}

    profile_section = f"* 사용자의 체형 분석 정보 (정적 데이터):\n{body_profile}\n" if body_profile else ""
    analysis_section = f"* 이번 세트의 실시간 움직임 분석 결과 (동적 데이터):\n{real_time_analysis}\n" if real_time_analysis else ""
    
    prompt = f"""
당신은 사용자의 정적 체형 데이터와 실시간 움직임 데이터를 종합적으로 분석하는 전문 AI 퍼스널 트레이너입니다. 주어진 정보를 바탕으로, 반드시 JSON 형식으로 'accuracy'와 'feedback' 두 가지 키를 포함하여 답변하세요.

{profile_section}
{analysis_section}

* 현재 운동 정보 (참고용):
- 운동 종류: {exercise_name}
- 단계: {stage}

* JSON 출력 규칙:
1. 'accuracy' 키에는 0부터 100까지의 정수로 전체적인 운동 정확도를 평가하여 숫자로만 제공하세요.
2. 'feedback' 키에는 평가에 대한 종합적인 피드백을 70자 이내의 한국어 한 문장으로 제공하세요. 이 피드백은 '자세가 좋습니다/불안정합니다' 등으로 시작할 수 있습니다. 꼭 이러한 단어가 아니여도 됩니다.
3. 피드백에는 '반복수'나 '각도'를 언급하지 마세요.

예시 출력:
{{
  "accuracy": 85,
  "feedback": "자세가 불안정합니다. 좌우 불균형 데이터를 볼 때 왼쪽으로 쏠리는 경향이 있으니 중앙에 무게를 두세요."
}}
"""
    try:
        # 모델 API를 직접 호출
        resp = await model.generate_content_async(prompt)
        # Gemini가 생성한 텍스트를 JSON 객체로 파싱
        return json.loads(resp.text)
    except Exception as e:
        print(f"--- GEMINI API ERROR ---")
        print(f"Error: {e}")
        # Gemini API 자체 에러인 경우, 원본 응답을 확인하는 것이 매우 중요합니다.
        if 'resp' in locals() and hasattr(resp, 'prompt_feedback'):
             print(f"Prompt Feedback: {resp.prompt_feedback}")
        print(f"--------------------------")
        # 실패하더라도 항상 동일한 JSON 구조로 반환하여 프론트엔드 에러 방지
        return {"accuracy": 0, "feedback": f"⚠️ AI 피드백 생성에 실패했습니다."}