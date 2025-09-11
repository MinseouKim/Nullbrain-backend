# backend/app/api/ws.py

import cv2
from fastapi import APIRouter, WebSocket
import asyncio
from app.ml.pipeline import PoseEstimator      # [!code ++]
from app.ml.feedback import get_squat_feedback # [!code ++]

router = APIRouter()
camera = None
# face_cascade = cv2.CascadeClassifier(...) # [!code --] # 얼굴 인식 코드 삭제

# PoseEstimator 클래스의 인스턴스를 생성합니다.
pose_estimator = PoseEstimator() # [!code ++]

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
            
            # --- AI 분석 및 시각화 (새 코드로 교체) ---
            # 1. pipeline.py의 PoseEstimator로 관절 탐지
            processed_frame, landmarks = pose_estimator.process_frame(frame) # [!code ++]

            # 2. 관절이 탐지되었을 경우 feedback.py로 자세 분석
            if landmarks: # [!code ++]
                feedback, angle = get_squat_feedback(landmarks) # [!code ++]
                
                # 3. 화면에 피드백과 각도 텍스트 추가
                cv2.putText(processed_frame, f"Knee Angle: {int(angle)}" if angle else "No Angle",
                            (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA) # [!code ++]
                cv2.putText(processed_frame, f"Feedback: {feedback}",
                            (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA) # [!code ++]
            # ---------------------------------------------

            # 관절과 피드백이 그려진 이미지를 JPEG로 인코딩
            ret, buffer = cv2.imencode('.jpg', processed_frame) # [!code focus]
            frame_bytes = buffer.tobytes()

            # 웹소켓을 통해 브라우저로 전송
            await websocket.send_bytes(frame_bytes)
            await asyncio.sleep(0.03) # 프레임 속도 조절

    except Exception as e:
        print(f"WebSocket 오류 발생: {e}")
    finally:
        if camera and camera.isOpened():
            camera.release()
            print("웹캠 자원이 해제되었습니다.")