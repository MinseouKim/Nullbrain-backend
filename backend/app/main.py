from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.ws_video import router as video_router
from app.api.ws_pose import router as pose_router
from app.api.ws_face import router as face_router            # 옵션
from app.api.profile import router as profile_router     # 옵션

app = FastAPI(title="Posture Capture Demo")

# 라우터 등록
app.include_router(video_router)
app.include_router(pose_router)
app.include_router(face_router)      # 얼굴 박스 스트림이 필요 없으면 제거해도 됨
app.include_router(profile_router)   # 프로필 REST가 필요 없으면 제거

# 정적 프론트 엔드(데모)
app.mount("/", StaticFiles(directory="app/static", html=True), name="static")
