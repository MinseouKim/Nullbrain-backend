# backend/app/api/analysis.py
from fastapi import APIRouter, Body
from ..logic.gemini import get_conversational_feedback # Gemini 함수 재활용

router = APIRouter()

@router.post("/api/analyze-set")
async def analyze_workout_set(data: dict = Body(...)):
    # 프론트로부터 받은 데이터 추출
    exercise_name = data.get("exerciseName")
    user_profile = data.get("userProfile") # 나중에 체형분석 데이터도 받음 우선 더미데이터로 적용
    rep_count = data.get("repCount") #


    # Gemini에게 보낼 프롬프트 재구성
    # 여기서는 간단히 요약 정보만 보내지만, 나중에는 전체 데이터를 보낼 수 있음
    feedback = await get_conversational_feedback(
        exercise_name, 
        angle=90, # 임시 각도
         rep_counter=rep_count,
        stage="completed", 
        history=[], 
        body_profile=user_profile
    )

    return {"analysis_feedback": feedback}