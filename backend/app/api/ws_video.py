# app/ws_video.py
import asyncio, cv2
from fastapi import APIRouter, WebSocket
from app.api.camera_hub import hub

router = APIRouter()

@router.websocket("/ws")
async def websocket_video(ws: WebSocket):
    await ws.accept()
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 65]  # 60~70 권장
    try:
        while True:
            frame = hub.get_latest()
            if frame is None:
                await asyncio.sleep(0.01); continue
            # 전송 해상도 축소
            frame_small = cv2.resize(frame, (960, 540), interpolation=cv2.INTER_AREA)
            ok, buf = cv2.imencode(".jpg", frame_small, encode_param)
            if ok:
                await ws.send_bytes(buf.tobytes())
            await asyncio.sleep(1/15)  # 15 FPS
    finally:
        pass
