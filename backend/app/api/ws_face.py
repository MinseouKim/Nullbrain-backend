# app/ws_face.py
import asyncio, cv2
from fastapi import APIRouter, WebSocket
from app.api.camera_hub import hub

router = APIRouter()
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

@router.websocket("/ws/face")
async def websocket_face(ws: WebSocket):
    await ws.accept()
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 65]
    try:
        while True:
            frame = hub.get_latest()
            if frame is None:
                await asyncio.sleep(0.01); continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)

            frame_small = cv2.resize(frame, (960, 540), interpolation=cv2.INTER_AREA)
            ok, buf = cv2.imencode(".jpg", frame_small, encode_param)
            if ok:
                await ws.send_bytes(buf.tobytes())
            await asyncio.sleep(1/15)
    finally:
        pass
