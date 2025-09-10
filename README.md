# 가상환경 명령어

[생성]
```cmd
python -m venv .venv
```

[가상환경 활성화]
```cmd
cd Nullbrain-backend/backend
.venv\Scripts\activate
```

[가상환경 비활성화]
```cmd
deactivate
```

### 패키지 설치
```cmd
pip install "fastapi[all]"
pip install uvicorn
```
fastapi[all] : FastAPI의 모든 부가 기능을 한 번에 설치
uvicorn : 웹프레임워크 => 앱 실행하게끔


### 서버 실행
```cmd
uvicorn app.main:app --reload
```

app.main:app → app 폴더 안 main.py에 있는 app 객체를 가리킵니다.
--reload → 코드 수정 시 자동으로 서버 재시작
기본 포트: 8000


웹브라우저 접속 테스트 : http://localhost:8000/api/ping
결과 : {"message":"pong"}


웹캠 페이지 : http://127.0.0.1:8000/static/index.html
