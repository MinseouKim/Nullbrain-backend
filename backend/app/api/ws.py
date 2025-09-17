# backend/app/api/ws.py

import cv2
from fastapi import APIRouter, WebSocket, WebSocketDisconnect # [!code ++]
import asyncio
from app.ml.pipeline import PoseEstimator
from app.ml.feedback import get_squat_feedback, get_pushup_feedback # [!code focus]
import numpy as np
from PIL import ImageFont, ImageDraw, Image

router = APIRouter()
camera = None
pose_estimator = PoseEstimator()
font_path = "app/static/NanumGothic.ttf"
font = ImageFont.truetype(font_path, 35)

def get_camera():
    global camera
    if camera is None or not camera.isOpened():
        camera = cv2.VideoCapture(0)
    return camera

@router.websocket("/ws/{exercise_name}") # [!code focus]
async def websocket_endpoint(websocket: WebSocket, exercise_name: str): # [!code focus]
    await websocket.accept()
    camera = get_camera()
    try:
        while True:
            success, frame = camera.read()
            if not success: break
            
            processed_frame, landmarks = pose_estimator.process_frame(frame)

            if landmarks:
                feedback = "알 수 없는 운동입니다." # [!code ++]
                angle = None # [!code ++]
                
                # URL로 받은 운동 이름에 따라 다른 함수 호출
                if exercise_name == "squat": # [!code ++]
                    feedback, angle = get_squat_feedback(landmarks) # [!code ++]
                elif exercise_name == "pushup": # [!code ++]
                    feedback, angle = get_pushup_feedback(landmarks) # [!code ++]
                
                # Pillow를 사용해 한글 텍스트 그리기
                img_pil = Image.fromarray(cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB))
                draw = ImageDraw.Draw(img_pil)

                angle_text = f"각도: {int(angle)}" if angle else "각도 측정 불가" # [!code focus]
                feedback_text = f"피드백: {feedback}"
                draw.text((10, 20), angle_text, font=font, fill=(0, 255, 0))
                draw.text((10, 60), feedback_text, font=font, fill=(0, 255, 0))

                processed_frame = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

            ret, buffer = cv2.imencode('.jpg', processed_frame)
            frame_bytes = buffer.tobytes()
            await websocket.send_bytes(frame_bytes)
            await asyncio.sleep(0.03)

    except WebSocketDisconnect: # [!code ++]
        print("클라이언트 연결이 끊어졌습니다.") # [!code ++]
    except Exception as e:
        print(f"WebSocket 오류 발생: {e}")
    finally:
        if camera and camera.isOpened():
            camera.release()
            print("웹캠 자원이 해제되었습니다.")