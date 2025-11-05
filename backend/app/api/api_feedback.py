from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from app.logic.gemini import get_conversational_feedback, get_overall_feedback
from app.logic.analysis_utils import get_latest_profile
from app.db import get_db

import json
from typing import Any, Dict

router = APIRouter(prefix="/api/feedback", tags=["Feedback"])

def _normalize_feedback(res: Any) -> Dict[str, Any]:
    """
    Gemini 응답을 dict로 강제 정규화.
    - dict 그대로면 반환
    - list면 첫 dict를 선택 (없으면 빈 dict/tips 감싸기)
    - str이면 JSON 파싱 후 재귀 처리, 실패하면 {"feedback": str}
    - 그 외는 빈 dict
    """
    if res is None:
        return {}
    if isinstance(res, dict):
        return res
    if isinstance(res, list):
        for item in res:
            if isinstance(item, dict):
                return item
        return {"feedback": "AI 피드백 생성 실패", "tips": res}
    if isinstance(res, str):
        try:
            obj = json.loads(res)
            return _normalize_feedback(obj)
        except Exception:
            return {"feedback": res}
    return {}

@router.post("/set")
async def feedback_per_set(data: dict = Body(...), db: Session = Depends(get_db)):
    """
    Body 예시:
    {
      "userId": "admin",
      "exerciseId": "squat",
      "exerciseName": "스쿼트",
      "rep_count": 12,
      "set_index": 2,          # 1-based
      "total_sets": 3,
      "target_reps": 12,
      "analysis_data": [... landmarks ...]
    }
    """
    user_id      = data.get("userId")
    exercise_id  = data.get("exerciseId", "unknown")
    exercise_ko  = data.get("exerciseName") or exercise_id       # 한글명 우선
    rep_count    = data.get("rep_count", 0)
    stage        = data.get("stage", "completed")
    history      = data.get("analysis_data", [])

    set_index    = int(data.get("set_index", 1))
    total_sets   = int(data.get("total_sets", 1))
    target_reps  = int(data.get("target_reps", rep_count))

    # DB에서 최신 프로필(체형분석) 조회
    body_profile = get_latest_profile(db, user_id)

    # 추가 컨텍스트(세트/타깃/표시명) 함께 전달
    extra = {
        "exercise_display_name": exercise_ko,
        "exercise_id": exercise_id,
        "set_index": set_index,
        "total_sets": total_sets,
        "target_reps": target_reps,
    }

    raw = await get_conversational_feedback(
        exercise_name=exercise_id,
        rep_counter=rep_count,
        stage=stage,
        body_profile=body_profile,
        real_time_analysis=history,
        extra_context=extra,   # 👈 추가
    )

    result = _normalize_feedback(raw)

    # 타입 가드
    feedback    = result.get("feedback", "AI 피드백 생성 실패")
    accuracy    = result.get("accuracy", 0)
    tips        = result.get("tips", [])
    if isinstance(tips, str):
        tips = [tips]
    risk_level  = result.get("risk_level", "unknown")

    return {
        "feedback": feedback,
        "accuracy": accuracy,
        "tips": tips,
        "risk_level": risk_level,
    }

@router.post("/overall")
async def feedback_overall(data: dict = Body(...)):
    set_results = data.get("set_results", [])
    # gemini.py에서 이미 dict 강제/기본값 설정
    return await get_overall_feedback(set_results)
