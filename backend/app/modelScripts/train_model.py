# backend/app/modelScripts/train_model.py

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
import joblib
import os

# --- 경로 설정 (수정된 부분) ---
# 이 스크립트 파일의 위치를 기준으로 경로를 설정하여 안정성을 높입니다.
script_dir = os.path.dirname(__file__)
project_root = os.path.dirname(os.path.dirname(script_dir)) # backend 폴더

# 1. 읽어올 데이터셋(CSV) 파일 경로
csv_path = os.path.join(project_root, 'app', 'dataSet', 'squat_landmarks.csv')

# 2. 훈련된 모델을 저장할 경로와 파일명
model_save_path = os.path.join(script_dir, 'squat_model.joblib')
# -----------------------------


# 데이터 로드
df = pd.read_csv(csv_path)

# 특징(X)과 레이블(y) 분리
X = df.drop('class', axis=1)
y = df['class']

# 훈련 데이터와 테스트 데이터 분리
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, stratify=y, random_state=42
)

# 모델 생성 및 훈련
model = RandomForestClassifier(n_estimators=100, random_state=42)
print("AI 모델 훈련을 시작합니다...")
model.fit(X_train, y_train)
print("훈련 완료!")
# 모델 성능 평가
print("모델 성능을 평가합니다...")
y_pred = model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)
print(f"모델 정확도: {accuracy * 100:.2f}%")

# 훈련된 모델 저장
joblib.dump(model, model_save_path)
print(f"훈련된 모델을 '{model_save_path}' 경로에 저장했습니다.")