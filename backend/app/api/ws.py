# backend/app/api/ws.py

import cv2
from fastapi import APIRouter, WebSocket
import asyncio
from app.ml.pipeline import PoseEstimator
from app.ml.feedback import get_squat_feedback
import numpy as np # [!code ++]
from PIL import ImageFont, ImageDraw, Image # [!code ++]

router = APIRouter()
camera = None
pose_estimator = PoseEstimator()

# --- 한글 폰트 경로 설정 --- # [!code focus]
font_path = "app/static/NanumGothic.ttf" # [!code ++]
font = ImageFont.truetype(font_path, 35) # [!code ++]

def get_camera():
    global camera
    if camera is None or not camera.isOpened():
        camera = cv2.VideoCapture(0)
    return camera

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    camera = get_camera()
    try:
        while True:
            success, frame = camera.read()
            if not success: break
            
            processed_frame, landmarks = pose_estimator.process_frame(frame)

            if landmarks:
                feedback, angle = get_squat_feedback(landmarks)
                
                # --- Pillow를 사용해 한글 텍스트 그리기 (수정된 부분) --- # [!code focus]
                # 1. OpenCV 프레임(BGR)을 Pillow 이미지(RGB)로 변환
                img_pil = Image.fromarray(cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)) # [!code ++]
                draw = ImageDraw.Draw(img_pil) # [!code ++]

                # 2. 텍스트 그리기
                angle_text = f"무릎 각도: {int(angle)}" if angle else "각도 측정 불가" # [!code ++]
                feedback_text = f"피드백: {feedback}" # [!code ++]
                draw.text((10, 20), angle_text, font=font, fill=(0, 255, 0)) # [!code ++]
                draw.text((10, 60), feedback_text, font=font, fill=(0, 255, 0)) # [!code ++]

                # 3. 다시 OpenCV 프레임으로 변환
                processed_frame = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR) # [!code ++]
                # ------------------------------------------------------------------ #

            ret, buffer = cv2.imencode('.jpg', processed_frame)
            frame_bytes = buffer.tobytes()
            await websocket.send_bytes(frame_bytes)
            await asyncio.sleep(0.03)

    except Exception as e:
        print(f"WebSocket 오류 발생: {e}")
    finally:
        if camera and camera.isOpened():
            camera.release()
            print("웹캠 자원이 해제되었습니다.")