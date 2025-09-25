# backend/app/api/ws.py

import cv2
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
from app.ml.pipeline import PoseEstimator
from app.ml.feedback import get_squat_feedback, get_pushup_feedback, get_conversational_feedback
import numpy as np
from PIL import ImageFont, ImageDraw, Image
import time
import base64

router = APIRouter()
pose_estimator = PoseEstimator()
font_path = "app/static/NanumGothic.ttf"
font = ImageFont.truetype(font_path, 35)

@router.websocket("/ws/{exercise_name}")
async def websocket_endpoint(websocket: WebSocket, exercise_name: str):
    await websocket.accept()
    camera = cv2.VideoCapture(0)
    
    if not camera.isOpened():
        print("카메라를 열 수 없습니다.")
        await websocket.close(code=1011)
        return

    shared_state = {
        "latest_landmarks": None,
        "latest_angle": None,
        "current_feedback": "자세를 잡아주세요.",
        "feedback_active": False
    }

    # ---  3개의 작업 함수를 먼저 모두 정의합니다. ---
    async def stream_video(websocket: WebSocket):
        """(작업 1) 웹캠 영상을 프론트엔드로 전송하는 역할"""
        while True:
            success, frame = camera.read()
            if not success: 
                break

            processed_frame, landmarks = pose_estimator.process_frame(frame)
            shared_state["latest_landmarks"] = landmarks

            angle_text = f"각도: {int(shared_state['latest_angle'])}도" if shared_state['latest_angle'] is not None else "각도 측정 불가"
            
            img_pil = Image.fromarray(cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB))
            draw = ImageDraw.Draw(img_pil)
            draw.text((10, 20), angle_text, font=font, fill=(0, 255, 0))
            draw.text((10, 60), shared_state['current_feedback'], font=font, fill=(255, 255, 0))
            final_frame = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

            ret, buffer = cv2.imencode('.jpg', final_frame)
            
            jpg_as_text = base64.b64encode(buffer).decode('utf-8')
            payload = { "image": jpg_as_text }
            
            # --- 👇 전송 부분을 try...except로 감싸 안정성 확보 ---
            try:
                await websocket.send_json(payload)
            except WebSocketDisconnect:
                print("[INFO] Video stream: Client disconnected, stopping send.")
                break # 클라이언트 연결이 끊어지면 루프를 탈출합니다.
            except Exception as e:
                print(f"[ERROR] Video stream send failed: {e}")
                break # 다른 에러 발생 시에도 루프를 탈출합니다.
            # ----------------------------------------------------
            
            await asyncio.sleep(0.03)

    async def update_feedback_with_gemini(exercise_name: str):
        """(작업 2) 운동 상태를 관리하고, 피드백을 업데이트하는 역할"""
        conversation_history = []
        
        rep_counter = 0
        stage = "up"

        while True:
            await asyncio.sleep(1)

            if not shared_state["feedback_active"]:
                shared_state["current_feedback"] = "AI 코칭 대기 중..."
                rep_counter = 0
                stage = "up"
                continue

            landmarks = shared_state["latest_landmarks"]
            if landmarks:
                _, angle = (None, None)
                
                if exercise_name == "squat":
                    _, angle = get_squat_feedback(landmarks)
                elif exercise_name == "pushup":
                    _, angle = get_pushup_feedback(landmarks)
                
                shared_state["latest_angle"] = angle

                if exercise_name == "squat" and angle is not None:
                    feedback = shared_state["current_feedback"]

                    # --- 👇 스쿼트 피드백 세분화 로직 ---
                    if stage == 'up':
                        if angle < 100: # 목표 지점 도달
                            stage = 'down'
                            rep_counter += 1
                            feedback = f"{rep_counter}회! 좋습니다. 올라오세요."
                        elif angle < 130: # 중간 지점 통과
                            feedback = "거의 다 왔어요! 조금만 더!"
                        elif angle < 160: # 내려가기 시작
                            feedback = "좋습니다, 계속 내려가세요."
                    
                    elif stage == 'down':
                        if angle > 160: # 시작 지점 복귀
                            stage = 'up'
                            feedback = f"{rep_counter}회 완료! 다음 자세 준비하세요."
                        elif angle > 100: # 올라오는 중
                            feedback = "좋습니다! 끝까지 올라오세요."
                    # ------------------------------------
                    
                    shared_state["current_feedback"] = feedback
                
                elif exercise_name == "pushup" and angle is not None:
                    # (푸시업 로직은 기존대로 유지)
                    if angle > 160:
                        shared_state["current_feedback"] = "내려가세요"
                    elif angle < 90:
                        shared_state["current_feedback"] = "자세 좋습니다!"

    async def handle_client_messages(websocket: WebSocket):
        """(작업 3) 프론트엔드로부터 메시지를 수신하고 처리하는 역할"""
        try:
            while True:
                data = await websocket.receive_json()
                action = data.get("action")
                if action == "start_feedback":
                    shared_state["feedback_active"] = True
                    print("[INFO] AI 피드백 시작")
                elif action == "stop_feedback":
                    shared_state["feedback_active"] = False
                    print("[INFO] AI 피드백 중지")
        except WebSocketDisconnect:
            pass
    # --------------------------------------------------------

    # --- 3개의 작업을 생성하고 동시에 실행합니다. ---
    video_task = asyncio.create_task(stream_video(websocket))
    feedback_task = asyncio.create_task(update_feedback_with_gemini(exercise_name))
    message_handler_task = asyncio.create_task(handle_client_messages(websocket))
    
    try:
        # 3개의 작업이 모두 함께 실행되도록 gather에 포함시킵니다.
        await asyncio.gather(video_task, feedback_task, message_handler_task)
    except Exception as e:
        print(f"오류 발생: {e}")
    finally:
        # 모든 작업을 안전하게 취소합니다.
        video_task.cancel()
        feedback_task.cancel()
        message_handler_task.cancel()
        if camera and camera.isOpened():
            camera.release()
            print("웹캠 자원이 해제되었습니다.")