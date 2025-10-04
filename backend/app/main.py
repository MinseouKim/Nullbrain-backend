# backend/app/main.py
from dotenv import load_dotenv
load_dotenv() # <-- FastAPI 앱이 시작되기 전에 .env 파일을 먼저 읽습니다.
import os
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware  # [!code ++]
from app.api import ws
from app.api.api_profile import router as profile_router
from app.db import engine
from app import models



app = FastAPI(title="Motion Backend")

@app.on_event("startup")
def on_startup():
    # 테이블 생성 (Alembic 쓰면 이 부분 대체)
    models.Profile.metadata.create_all(bind=engine)

@app.middleware("http")
async def add_coop_coep_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
    return response


# --- CORS 미들웨어 추가 --- # [!code focus]
env_origins = os.getenv("CORS_ORIGINS", "")
origins = [o.strip() for o in env_origins.split(",") if o.strip()] or ["http://localhost:3000", "http://localhost:5173"]


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # 모든 HTTP 메소드 허용
    allow_headers=["*"],  # 모든 HTTP 헤더 허용
)
# ------------------------- #

# --- 기존 코드는 그대로 둡니다 --- #
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(ws.router)
app.include_router(profile_router)

# --- 이 부분은 이제 React에서 처리하므로 삭제하거나 주석 처리해도 됩니다 --- #
# @app.get("/{exercise_name}", response_class=HTMLResponse)
# async def serve_exercise_app(exercise_name: str):
#     with open("app/static/index.html", "r", encoding="utf-8") as f:
#         html_content = f.read()
#     html_with_exercise = html_content.replace("EXERCISE_PLACEHOLDER", exercise_name)
#     return HTMLResponse(content=html_with_exercise, status_code=200)