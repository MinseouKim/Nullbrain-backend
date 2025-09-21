import asyncio
import cv2
from fastapi import APIRouter, WebSocket

router = APIRouter()
_cam = None

def get_cam():
    global _cam
    if _cam is None or not _cam.isOpened():
        _cam = cv2.VideoCapture(0, cv2.CAP_V4L2)
        _cam.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        _cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        _cam.set(cv2.CAP_PROP_FPS, 30)
        _cam.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
    return _cam

@router.websocket("/ws")
async def ws_jpeg(websocket: WebSocket):
    await websocket.accept()
    cam = get_cam()
    try:
        while True:
            if not cam.isOpened():
                break
            ok, frame = cam.read()
            if not ok:
                break
            # 원한다면 여기서 가이드라인(중앙선/프레이밍 박스)도 그릴 수 있음
            ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            if not ok:
                continue
            await websocket.send_bytes(buf.tobytes())
            await asyncio.sleep(0.03)  # ~33fps
    except Exception:
        pass
