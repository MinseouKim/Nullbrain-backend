# backend/app/api/ws.py
import cv2
from fastapi import APIRouter, WebSocket
import asyncio

router = APIRouter()
camera = None
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

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
            if not camera.isOpened():
                break

            success, frame = camera.read()
            if not success:
                break
            
            # --- AI 분석 및 시각화 ---
            gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray_frame, 1.1, 4)

            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
            # ------------------------

            ret, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()

            await websocket.send_bytes(frame_bytes)
            await asyncio.sleep(0.03)

    except asyncio.CancelledError:
        print("WebSocket 연결이 종료되었습니다.")
    finally:
        if camera and camera.isOpened():
            camera.release()
            print("웹캠 자원이 해제되었습니다.")