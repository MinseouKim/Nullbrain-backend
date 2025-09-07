# backend/app/api/ws.py
import cv2
import asyncio
from fastapi import APIRouter, WebSocket
import subprocess
import threading

router = APIRouter()
camera = None
stream_process = None

def get_camera():
    global camera
    if camera is None or not camera.isOpened():
        camera = cv2.VideoCapture(0)
    return camera

def run_ffmpeg_stream(websocket):
    global stream_process
    camera = get_camera()

    command = ['ffmpeg',
               '-y',  # 파일이 존재하면 덮어쓰기
               '-f', 'rawvideo',
               '-vcodec', 'rawvideo',
               '-pix_fmt', 'bgr24',
               '-s', '640x480',
               '-i', '-',  # 파이프를 통해 입력받음
               '-c:v', 'libx264',
               '-pix_fmt', 'yuv420p',
               '-preset', 'ultrafast',
               '-f', 'mp4',
               '-movflags', 'frag_keyframe+empty_moov',
               'pipe:1']

    stream_process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE)

    try:
        while True:
            success, frame = camera.read()
            if not success:
                break

            # 프레임을 FFmpeg 프로세스로 전달
            stream_process.stdin.write(frame.tobytes())
            
            # FFmpeg의 출력 데이터를 WebSocket으로 전송
            output_data = stream_process.stdout.read(4096)
            if output_data:
                asyncio.run(websocket.send_bytes(output_data))
                
    except asyncio.CancelledError:
        print("스트리밍이 종료되었습니다.")
    finally:
        if stream_process:
            stream_process.stdin.close()
            stream_process.terminate()
            stream_process = None
        if camera and camera.isOpened():
            camera.release()
            
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    # FFmpeg 스트리밍을 별도 스레드에서 실행
    thread = threading.Thread(target=run_ffmpeg_stream, args=(websocket,))
    thread.start()
    
    # 웹소켓이 닫힐 때까지 대기
    await asyncio.sleep(60 * 60) # 무한대기