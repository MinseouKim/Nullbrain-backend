# app/api/api_feedback.py
from fastapi import APIRouter
from app.logic.gemini import get_conversational_feedback, get_overall_feedback

router = APIRouter(prefix="/api/feedback", tags=["Feedback"])

@router.post("/set")
async def feedback_per_set(data: dict):
    """
    세트별 AI 피드백 생성
    """
    exercise = data.get("exercise", "unknown")
    rep_count = data.get("rep_count", 0)
    stage = data.get("stage", "N/A")
    body_profile = data.get("body_profile")
    analysis_data = data.get("analysis_data")

    result = await get_conversational_feedback(
        exercise_name=exercise,
        rep_counter=rep_count,
        stage=stage,
        body_profile=body_profile,
        real_time_analysis=analysis_data,
    )

    return {
        "feedback": result.get("feedback", "AI 피드백 생성 실패"),
        "accuracy": result.get("accuracy", 0),
        "tips": result.get("tips", []),
        "risk_level": result.get("risk_level", "unknown"),
    }

@router.post("/overall")
async def feedback_overall(data: dict):
    """
    전체 세트 완료 후 종합 피드백
    """
    set_results = data.get("set_results", [])
    result = await get_overall_feedback(set_results)
    return result
