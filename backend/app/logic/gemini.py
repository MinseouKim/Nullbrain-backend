# backend/app/logic/gemini.py

import os
from dotenv import load_dotenv
import google.generativeai as genai

# .env 파일에서 환경 변수(API 키) 로드
load_dotenv()
# API 키 설정
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
# Gemini 모델 초기화 (안정적인 최신 버전 사용)
gemini_model = genai.GenerativeModel('gemini-1.5-flash-latest')

async def get_conversational_feedback(exercise_name: str, angle: float, rep_counter: int, stage: str, history: list) -> str:
    """
    대화 히스토리를 포함하여 Gemini API를 호출하고, 대화형 피드백을 생성합니다.
    """
    if angle is None:
        return "자세를 분석하고 있습니다..."

    # 현재 상태를 Gemini가 이해하기 쉽게 문장으로 만듭니다.
    current_state_summary = f"사용자는 {exercise_name} 운동 중이며, 현재 {rep_counter}개를 완료했습니다. 현재 자세 단계는 '{stage}'(up/down)이며, 주요 관절 각도는 {int(angle)}도 입니다."
    
    prompt = f"""
    당신은 사용자의 자세를 교정해주는 최고의 AI 퍼스널 트레이너입니다.
    아래는 지금까지 사용자와 나눈 대화 내용(히스토리)과 현재 사용자의 자세 정보입니다.
    
    <대화 히스토리>
    {history}
    
    <현재 자세 정보>
    {current_state_summary}

    
    """

    try:
        response = await gemini_model.generate_content_async(prompt)
        if not response.parts:
            return "피드백 생성 중... 자세를 조금 바꿔보세요."
        return response.text.strip()
    except Exception as e:
        print(f"Gemini API 호출 오류: {e}")
        return "피드백 생성 중 오류가 발생했습니다."