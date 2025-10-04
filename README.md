# 가상환경 명령어

[생성]
```cmd
py -3.11 -m venv .venv
```

[가상환경 활성화]
```cmd
cd Nullbrain-backend/backend
source .venv/Scripts/activate

bash
source .venv/Scripts/activate
```
```bash
source .venv/Scripts/activate
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
- fastapi[all] : FastAPI의 모든 부가 기능을 한 번에 설치
- uvicorn : 웹프레임워크 => 앱 실행하게끔

```cmd
pip install opencv-python
```
opencv

```cmd
pip install mediapipe opencv-python
```


한번에 설치 : 
```
pip install -r requirements.txt
```


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




### postgreSQL (docker)

1) 백그라운드 실행
docker compose up -d

2) 상태 확인
docker ps

3) 로그 보기
docker logs -f pg docker ps -a | grep pg # pg 관련 컨테이너 확인 docker inspect pg | grep -A3 Mounts # 기존 컨테이너 볼륨 경로 확인

컨테이너 내부 접속(psql)
docker exec -it pg psql -U synctogether -d synctogether

백업/복원
docker exec -t pg pg_dump -U synctogether synctogether > backup.sql cat backup.sql | docker exec -i pg psql -U synctogether -d synctogether

컨테이너/볼륨 제거 (주의: 데이터 삭제)
docker compose down -v

스쿼트 확인 : http://127.0.0.1:8000/squat

푸시업 확인 : http://127.0.0.1:8000/pushup
