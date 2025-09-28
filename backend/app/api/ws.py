# backend/app/api/ws.py

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.logic.squat import get_squat_angle
from app.logic.pushup import get_pushup_angle
from app.logic.gemini import get_conversational_feedback
import time
import mediapipe as mp # 관절 인덱스 번호를 위해 import 합니다.

router = APIRouter()

@router.websocket("/ws/{exercise_name}")
async def websocket_endpoint(websocket: WebSocket, exercise_name: str):
    await websocket.accept()
    
    rep_counter = 0
    stage = "up"
    feedback = "운동을 시작하세요."
    conversation_history = []
    last_api_call_time = 0
    
    # MediaPipe의 관절 인덱스를 쉽게 사용하기 위해 변수 선언
    mp_pose = mp.solutions.pose.PoseLandmark

    try:
        while True:
            landmarks_data = await websocket.receive_json()
            
            # --- 👇 1. 스쿼트 관절 가시성 사전 검사 ---
            if exercise_name == 'squat':
                visibility_threshold = 0.6 # 가시성 기준값 (0.0 ~ 1.0)
                try:
                    # 왼쪽 하체 관절들의 가시성 점수를 확인합니다.
                    hip_visible = landmarks_data[mp_pose.LEFT_HIP.value]['visibility'] > visibility_threshold
                    knee_visible = landmarks_data[mp_pose.LEFT_KNEE.value]['visibility'] > visibility_threshold
                    ankle_visible = landmarks_data[mp_pose.LEFT_ANKLE.value]['visibility'] > visibility_threshold

                    # 세 관절 중 하나라도 잘 보이지 않으면, 안내 메시지를 보내고 이번 프레임 처리를 건너뜁니다.
                    if not (hip_visible and knee_visible and ankle_visible):
                        payload = { 
                            "feedback": "하체 전체가 잘 보이도록 뒤로 물러나세요.", 
                            "angle": None,
                            "rep_count": rep_counter
                        }
                        await websocket.send_json(payload)
                        continue # 다음 프레임으로 넘어감
                except (IndexError, KeyError):
                    # 프론트에서 불완전한 랜드마크 데이터가 올 경우를 대비한 예외 처리
                    continue
            # ------------------------------------

            angle = None
            if exercise_name == 'squat':
                angle = get_squat_angle(landmarks_data)
            elif exercise_name == 'pushup':
                angle = get_pushup_angle(landmarks_data)
            
            previous_stage = stage 

            if angle is not None:
                if exercise_name == 'squat':
                    if angle < 100 and stage == 'up':
                        stage = 'down'
                        rep_counter += 1
                    elif angle > 160 and stage == 'down':
                        stage = 'up'
                
                elif exercise_name == 'pushup':
                    if angle < 90 and stage == 'up':
                        stage = 'down'
                        rep_counter += 1
                    elif angle > 160 and stage == 'down':
                        stage = 'up'

            current_time = time.time()
            if (stage != previous_stage or (current_time - last_api_call_time) > 3) and angle is not None:
                feedback = await get_conversational_feedback(
                    exercise_name, angle, rep_counter, stage, conversation_history
                )
                
                user_action = f"({exercise_name} 자세, 각도: {int(angle)}, 상태: {stage})"
                conversation_history.append(f"사용자: {user_action}")
                conversation_history.append(f"AI 코치: {feedback}") 
                if len(conversation_history) > 10:
                    conversation_history = conversation_history[-10:]
                
                last_api_call_time = current_time
            
            payload = { 
                "feedback": feedback, 
                "angle": int(angle) if angle is not None else None,
                "rep_count": rep_counter
            }
            await websocket.send_json(payload)

    except WebSocketDisconnect:
        print("클라이언트 연결이 끊어졌습니다.")
    except Exception as e:
        print(f"오류 발생: {e}")
