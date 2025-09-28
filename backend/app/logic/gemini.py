# backend/app/logic/gemini.py

import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# --- 👇 모델 초기화 시, 최대 출력 토큰을 설정합니다 ---
generation_config = genai.GenerationConfig(
    max_output_tokens=50 # 답변을 약 20~30글자 내외로 제한
)
gemini_model = genai.GenerativeModel(
    'gemini-flash-latest',
    generation_config=generation_config
)
# ----------------------------------------------------

async def get_conversational_feedback(exercise_name: str, angle: float, rep_counter: int, stage: str, history: list) -> str:
    if angle is None:
        return "자세를 분석하고 있습니다..."

    current_state_summary = f"사용자는 {exercise_name} 운동 중이며, 현재 {rep_counter}개를 완료했습니다. 현재 자세 단계는 '{stage}'(up/down)이며, 주요 관절 각도는 {int(angle)}도 입니다."
    
    # --- 👇 AI에게 보내는 지시문을 훨씬 더 강력하고 명확하게 수정합니다 ---
    prompt = f"""
    You are an AI personal trainer who gives feedback in a single, short, encouraging sentence in Korean.
    DO NOT use markdown. DO NOT use emojis. DO NOT write multiple paragraphs.
    Analyze the user's current state based on the conversation history.

    ## Conversation History:
    {history}
    
    ## Current User State:
    {current_state_summary}

    Based on all this information, generate ONLY ONE concise sentence of feedback.
    
    Example 1: 좋습니다! 조금만 더 내려가세요.
    Example 2: 5회 완료! 자세가 아주 안정적이네요.
    Example 3: 좋아요, 다시 일어서 볼까요?
    """

    try:
        response = await gemini_model.generate_content_async(prompt)
        if not response.parts:
            return "피드백 생성 중... 자세를 조금 바꿔보세요."
        return response.text.strip()
    except Exception as e:
        print(f"Gemini API 호출 오류: {e}")
        return "피드백 생성 중 오류가 발생했습니다."