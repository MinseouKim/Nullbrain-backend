# backend/app/api/ws.py

import cv2
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
from app.ml.pipeline import PoseEstimator
from app.ml.feedback import get_squat_feedback, get_pushup_feedback
import numpy as np
from PIL import ImageFont, ImageDraw, Image

router = APIRouter()
# camera = None # [!code --] # 전역 변수 camera를 삭제합니다.
pose_estimator = PoseEstimator()
font_path = "app/static/NanumGothic.ttf"
font = ImageFont.truetype(font_path, 35)

# def get_camera(): # [!code --] # get_camera 함수도 더 이상 필요 없습니다.
#     global camera
#     if camera is None or not camera.isOpened():
#         camera = cv2.VideoCapture(0)
#     return camera

@router.websocket("/ws/{exercise_name}")
async def websocket_endpoint(websocket: WebSocket, exercise_name: str):
    await websocket.accept()
    
    camera = cv2.VideoCapture(0) # [!code focus] # 웹소켓 연결 시점에 카메라를 초기화합니다.
    
    if not camera.isOpened(): # [!code ++]
        print("카메라를 열 수 없습니다.") # [!code ++]
        await websocket.close(code=1011) # [!code ++]
        return # [!code ++]
        
    try:
        while True:
            success, frame = camera.read()
            if not success: break
            
            processed_frame, landmarks = pose_estimator.process_frame(frame)

            if landmarks:
                feedback = "알 수 없는 운동입니다."
                angle = None
                
                if exercise_name == "squat":
                    feedback, angle = get_squat_feedback(landmarks)
                elif exercise_name == "pushup":
                    feedback, angle = get_pushup_feedback(landmarks)
                
                img_pil = Image.fromarray(cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB))
                draw = ImageDraw.Draw(img_pil)
                angle_text = f"각도: {int(angle)}" if angle else "각도 측정 불가"
                feedback_text = f"피드백: {feedback}"
                draw.text((10, 20), angle_text, font=font, fill=(0, 255, 0))
                draw.text((10, 60), feedback_text, font=font, fill=(0, 255, 0))
                processed_frame = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB_BGR)

            ret, buffer = cv2.imencode('.jpg', processed_frame)
            frame_bytes = buffer.tobytes()
            await websocket.send_bytes(frame_bytes)
            await asyncio.sleep(0.03)

    except WebSocketDisconnect:
        print("클라이언트 연결이 끊어졌습니다.")
    except Exception as e:
        print(f"WebSocket 오류 발생: {e}")
    finally:
        if camera and camera.isOpened(): # [!code focus]
            camera.release() # [!code focus]
            print("웹캠 자원이 해제되었습니다.") # [!code focus]