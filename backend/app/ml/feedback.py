# # backend/app/ml/feedback.py

# import numpy as np
# import mediapipe as mp
# import joblib  #  <-- 모델 로드를 위해 추가
# import pandas as pd  # <-- 데이터 프레임 생성을 위해 추가
# import os # <-- 경로 설정을 위해 추가

# # --- 1. 훈련된 AI 모델 불러오기 ---
# # 스크립트의 위치를 기준으로 모델 파일의 절대 경로를 계산합니다.
# script_dir = os.path.dirname(__file__)
# model_path = os.path.join(script_dir, '..', 'modelScripts', 'squat_model.joblib')
# squat_model = joblib.load(model_path)
# # ------------------------------------


# def calculate_angle(a, b, c):
#     """세 점(랜드마크) 사이의 각도를 계산하는 함수 (푸시업에서 계속 사용)"""
#     a = np.array(a)
#     b = np.array(b)
#     c = np.array(c)
    
#     radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
#     angle = np.abs(radians * 180.0 / np.pi)
    
#     if angle > 180.0:
#         angle = 360 - angle
        
#     return angle


# # --- get_squat_feedback 함수 수정 ---
# def get_squat_feedback(landmarks):
#     """
#     AI 모델과 각도 계산을 결합하여 스쿼트 피드백을 생성합니다.
#     """
#     feedback = "자세를 분석할 수 없습니다."
#     angle = None  # [!code ++]
    
#     try:
#         # 1. AI 모델 예측을 위한 데이터 준비
#         row = [coord for lm in landmarks for coord in [lm.x, lm.y, lm.z, lm.visibility]]
#         landmarks_header = [f'lm_{i}_{axis}' for i in range(33) for axis in ['x', 'y', 'z', 'v']]
#         X = pd.DataFrame([row], columns=landmarks_header)
        
#         # 2. AI 모델로 자세 예측
#         prediction = squat_model.predict(X)[0]
        
#         # 3. 예측 결과에 따라 피드백 생성 (AI의 판단)
#         if prediction == 'good':
#             feedback = "자세 좋습니다!"
#         elif prediction == 'bad_high':
#             # 4. 구체적인 수치를 위해 각도 계산 (규칙 기반)
#             mp_pose = mp.solutions.pose.PoseLandmark
#             hip = [landmarks[mp_pose.LEFT_HIP.value].x, landmarks[mp_pose.LEFT_HIP.value].y]
#             knee = [landmarks[mp_pose.LEFT_KNEE.value].x, landmarks[mp_pose.LEFT_KNEE.value].y]
#             ankle = [landmarks[mp_pose.LEFT_ANKLE.value].x, landmarks[mp_pose.LEFT_ANKLE.value].y]
#             angle = calculate_angle(hip, knee, ankle)
            
#             feedback = f"더 내려가세요! (현재 각도: {int(angle)}°)" # [!code focus]
#         else:
#             feedback = prediction

#     except Exception as e:
#         print(f"스쿼트 피드백 생성 오류: {e}")
        
#     return feedback, angle # [!code focus] # 이제 각도 정보도 함께 반환합니다.


# # --- 푸시업 함수는 기존 규칙 기반으로 그대로 둡니다 ---
# def get_pushup_feedback(landmarks):
#     """
#     랜드마크 데이터를 기반으로 푸시업 자세에 대한 피드백과
#     팔꿈치 각도를 반환하는 함수.
#     """
#     # (이전 코드와 동일)
#     mp_pose = mp.solutions.pose.PoseLandmark
#     feedback = "자세를 잡아주세요"
#     elbow_angle = None
    
#     try:
#         shoulder = [landmarks[mp_pose.RIGHT_SHOULDER.value].x, landmarks[mp_pose.RIGHT_SHOULDER.value].y]
#         elbow = [landmarks[mp_pose.RIGHT_ELBOW.value].x, landmarks[mp_pose.RIGHT_ELBOW.value].y]
#         wrist = [landmarks[mp_pose.RIGHT_WRIST.value].x, landmarks[mp_pose.RIGHT_WRIST.value].y]
#         elbow_angle = calculate_angle(shoulder, elbow, wrist)
        
#         if elbow_angle > 160:
#             feedback = "내려가세요"
#         elif elbow_angle < 90:
#             feedback = "자세 좋습니다!"
            
#     except:
#         pass
        
#     return feedback, elbow_angle


# backend/app/ml/feedback.py

# backend/app/ml/feedback.py

import numpy as np
import mediapipe as mp

def calculate_angle(a, b, c):
    """세 점(랜드마크) 사이의 각도를 계산하는 함수"""
    a = np.array(a)
    b = np.array(b)
    c = np.array(c)

    radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
    angle = np.abs(radians * 180.0 / np.pi)

    if angle > 180.0:
        angle = 360 - angle

    return angle

# --- 스쿼트 함수 (완성된 규칙 기반) ---
def get_squat_feedback(landmarks):
    mp_pose = mp.solutions.pose.PoseLandmark
    feedback = "자세를 잡아주세요"
    angle = None

    try:
        hip = [landmarks[mp_pose.LEFT_HIP.value].x, landmarks[mp_pose.LEFT_HIP.value].y]
        knee = [landmarks[mp_pose.LEFT_KNEE.value].x, landmarks[mp_pose.LEFT_KNEE.value].y]
        ankle = [landmarks[mp_pose.LEFT_ANKLE.value].x, landmarks[mp_pose.LEFT_ANKLE.value].y]
        angle = calculate_angle(hip, knee, ankle)

        if angle > 160:
            feedback = "준비"
        elif angle <= 160 and angle > 90:
            feedback = f"더 내려가세요!"
        elif angle <= 90:
            feedback = "자세 좋습니다!"

    except Exception as e:
        print(f"스쿼트 각도 계산 오류: {e}")

    return feedback, angle

# --- 푸시업 함수 (완성된 규칙 기반) ---
def get_pushup_feedback(landmarks):
    mp_pose = mp.solutions.pose.PoseLandmark
    feedback = "자세를 잡아주세요"
    elbow_angle = None

    try:
        # 오른쪽 어깨, 팔꿈치, 손목의 2D 좌표 추출
        shoulder = [landmarks[mp_pose.RIGHT_SHOULDER.value].x, landmarks[mp_pose.RIGHT_SHOULDER.value].y]
        elbow = [landmarks[mp_pose.RIGHT_ELBOW.value].x, landmarks[mp_pose.RIGHT_ELBOW.value].y]
        wrist = [landmarks[mp_pose.RIGHT_WRIST.value].x, landmarks[mp_pose.RIGHT_WRIST.value].y]

        # 팔꿈치 각도 계산
        elbow_angle = calculate_angle(shoulder, elbow, wrist)

        # 각도에 따른 피드백 생성
        if elbow_angle > 160:
            feedback = "내려가세요"
        elif elbow_angle < 90:
            feedback = "자세 좋습니다!"

    except Exception as e:
        print(f"푸시업 각도 계산 오류: {e}")

    return feedback, elbow_angle