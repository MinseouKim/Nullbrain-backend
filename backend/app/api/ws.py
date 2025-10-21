# backend/app/api/ws.py
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from app.db import SessionLocal
from app.logic.gemini import get_conversational_feedback
from app.models import Profile

router = APIRouter()

def get_latest_profile() -> dict | None:
    """DB에서 가장 최근 체형 분석(Profile) 데이터 로드"""
    db: Session = SessionLocal()
    try:
        profile = db.query(Profile).order_by(Profile.created_at.desc()).first()
        if profile:
            return {
                "id": str(profile.id),
                "version": profile.version,
                "body": profile.body,
                "measures": profile.measures,
            }
        return None
    finally:
        db.close()

@router.websocket("/ws/feedback")
async def websocket_feedback(websocket: WebSocket):
    await websocket.accept()
    print("[WS] 클라이언트 연결됨 (AI 피드백 채널)")

    # --- 체형 데이터 DB에서 로드 ---
    body_profile = None
    try:
        body_profile = get_latest_profile()
        if body_profile:
            print("[INFO] 최신 체형 데이터 로드 성공")
        else:
            print("[WARN] DB에 체형 데이터가 없습니다.")
    except Exception as e:
        print(f"[ERROR] 체형 데이터 로드 실패: {e}")

    try:
        while True:
            # 프론트에서 이미 계산된 결과를 받음
            data = await websocket.receive_json()
            exercise_name = data.get("exerciseName")
            rep_count = data.get("repCount")
            landmark_history = data.get("landmarkHistory", [])
            analysis_data = data.get("analysis", {})
            stage = data.get("stage", "completed")

            # --- Gemini 호출 ---
            ai_result = await get_conversational_feedback(
                exercise_name=exercise_name,
                rep_counter=rep_count,
                stage=stage,
                real_time_analysis=analysis_data,
                body_profile=body_profile,
                history=[],
            )

            # --- 응답 정리 ---
            payload = {
                "exerciseName": exercise_name,
                "repCount": rep_count,
                "feedback": ai_result.get("feedback", "AI 피드백 생성 실패"),
                "accuracy": ai_result.get("accuracy", 0),
            }
            await websocket.send_json(payload)

    except WebSocketDisconnect:
        print("[WS] 클라이언트 연결 종료")
    except Exception as e:
        print(f"[WS ERROR] {e}")
