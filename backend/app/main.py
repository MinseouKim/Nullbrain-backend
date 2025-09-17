# backend/app/main.py

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from app.api import rest, ws

app = FastAPI(title="Motion Backend")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(rest.router, prefix="/api")
app.include_router(ws.router)

# --- 기존 /webcam 라우터를 아래 코드로 변경 --- # [!code focus]
@app.get("/{exercise_name}", response_class=HTMLResponse)
async def serve_exercise_app(exercise_name: str):
    with open("app/static/index.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    
    # HTML 내용에 운동 이름을 동적으로 삽입
    # (Jinja2 같은 템플릿 엔진을 사용하면 더 깔끔하게 처리 가능)
    html_with_exercise = html_content.replace("EXERCISE_PLACEHOLDER", exercise_name)
    
    return HTMLResponse(content=html_with_exercise, status_code=200)