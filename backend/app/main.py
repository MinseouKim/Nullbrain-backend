# backend/app/main.py
from dotenv import load_dotenv
load_dotenv() # <-- FastAPI 앱이 시작되기 전에 .env 파일을 먼저 읽습니다.
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware  # [!code ++]
from app.api import rest, ws



app = FastAPI(title="Motion Backend")

# --- CORS 미들웨어 추가 --- # [!code focus]
origins = [
    "http://localhost:3000",  # React 앱의 기본 주소
    # 만약 다른 프론트엔드 주소가 있다면 여기에 추가
]

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
app.include_router(rest.router, prefix="/api")
app.include_router(ws.router)

# --- 이 부분은 이제 React에서 처리하므로 삭제하거나 주석 처리해도 됩니다 --- #
@app.get("/{exercise_name}", response_class=HTMLResponse)
async def serve_exercise_app(exercise_name: str):
    with open("app/static/index.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    html_with_exercise = html_content.replace("EXERCISE_PLACEHOLDER", exercise_name)
    return HTMLResponse(content=html_with_exercise, status_code=200)