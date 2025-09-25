# backend/app/api/ws.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.ml.feedback import get_squat_feedback #, get_pushup_feedback...

router = APIRouter()

@router.websocket("/ws/{exercise_name}")
async def websocket_endpoint(websocket: WebSocket, exercise_name: str):
    await websocket.accept()
    try:
        while True:
            # 1. 프론트엔드로부터 관절 좌표 데이터(JSON)를 받습니다.
            landmarks_data = await websocket.receive_json()

            feedback, angle = (None, None)
            if exercise_name == 'squat':
                feedback, angle = get_squat_feedback(landmarks_data)
            # elif exercise_name == 'pushup':
            #     feedback, angle = get_pushup_feedback(landmarks_data)
            else:
                feedback = "알 수 없는 운동입니다."

            # 3. 생성된 피드백 텍스트와 각도만 프론트엔드로 다시 보냅니다.
            payload = { "feedback": feedback, "angle": angle }
            await websocket.send_json(payload)

    except WebSocketDisconnect:
        print("클라이언트 연결이 끊어졌습니다.")
    except Exception as e:
        print(f"오류 발생: {e}")