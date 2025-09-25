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


import numpy as np
import mediapipe as mp
import os
import google.generativeai as genai

# --- Gemini API 설정 ---

# API 키 설정
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Gemini 모델 초기화 (한 번만 실행)
gemini_model = genai.GenerativeModel('gemini-1.5-flash-latest')
# -------------------------


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

# --- 기존 규칙 기반 함수들은 그대로 둡니다 ---
def get_squat_feedback(landmarks):
    """
    스쿼트 자세의 왼쪽 무릎 각도를 계산하여 반환합니다.
    """
    mp_pose = mp.solutions.pose.PoseLandmark
    angle = None
    try:
        hip = [landmarks[mp_pose.LEFT_HIP.value].x, landmarks[mp_pose.LEFT_HIP.value].y]
        knee = [landmarks[mp_pose.LEFT_KNEE.value].x, landmarks[mp_pose.LEFT_KNEE.value].y]
        ankle = [landmarks[mp_pose.LEFT_ANKLE.value].x, landmarks[mp_pose.LEFT_ANKLE.value].y]
        angle = calculate_angle(hip, knee, ankle)
    except Exception as e:
        print(f"스쿼트 각도 계산 오류: {e}")
    return None, angle # 피드백은 항상 None, 각도만 반환

def get_pushup_feedback(landmarks):
    mp_pose = mp.solutions.pose.PoseLandmark
    feedback = "자세를 분석할 수 없습니다."
    elbow_angle = None
    
    try:
        # 어깨, 팔꿈치, 손목, 엉덩이의 2D 좌표 추출
        shoulder = [landmarks[mp_pose.RIGHT_SHOULDER.value].x, landmarks[mp_pose.RIGHT_SHOULDER.value].y]
        elbow = [landmarks[mp_pose.RIGHT_ELBOW.value].x, landmarks[mp_pose.RIGHT_ELBOW.value].y]
        wrist = [landmarks[mp_pose.RIGHT_WRIST.value].x, landmarks[mp_pose.RIGHT_WRIST.value].y]
        hip = [landmarks[mp_pose.RIGHT_HIP.value].x, landmarks[mp_pose.RIGHT_HIP.value].y]

        # 1. 사용자가 엎드려 있는지 (몸이 수평에 가까운지) 먼저 확인
        # y좌표는 화면 위쪽이 0, 아래쪽이 1이므로, 어깨와 엉덩이의 y좌표 차이가 작으면 수평 자세임
        vertical_dist = abs(shoulder[1] - hip[1])

        if vertical_dist < 0.15:  # 몸이 충분히 수평일 때 (엎드린 자세)
            # 2. 엎드린 자세일 경우에만 팔꿈치 각도를 계산하여 피드백
            elbow_angle = calculate_angle(shoulder, elbow, wrist)
            
            if elbow_angle > 160:
                feedback = "내려가세요"
            elif elbow_angle < 90:
                feedback = "자세 좋습니다!"
            else:
                feedback = "올라오세요" # 중간 상태 추가

        else: # 몸이 수평이 아닐 때 (서 있는 자세)
            feedback = "푸시업 준비 자세를 취해주세요"
            
    except Exception as e:
        # 관절이 감지되지 않으면 기본 피드백 유지
        feedback = "카메라에 전신이 나오게 해주세요"
        print(f"푸시업 피드백 생성 오류: {e}")
        
    return feedback, elbow_angle

# ---  새로 추가된 Gemini 대화형 피드백 함수 ---
async def get_conversational_feedback(exercise_name: str, angle: float, history: list) -> str:
    """
    대화 히스토리를 포함하여 Gemini API를 호출하고, 대화형 피드백을 생성합니다.
    """
    if angle is None:
        return "자세를 분석하고 있습니다..."

    current_state_summary = f"사용자는 {exercise_name} 운동 중이며, 현재 주요 각도는 {int(angle)}도 입니다."
    prompt = f"""
    당신은 사용자의 자세를 교정해주는 AI 퍼스널 트레이너입니다.
    아래는 지금까지 사용자와 나눈 대화 내용(히스토리)과 현재 사용자의 자세 정보입니다.
    
    <대화 히스토리>
    {history}
    
    <현재 자세 정보>
    {current_state_summary}

    위 대화 히스토리와 현재 자세 정보를 바탕으로, 다음 피드백을 한 문장의 자연스러운 한국어 대화체로 생성해주세요.
    - 이전보다 자세가 좋아졌다면 칭찬해주세요.
    - 같은 실수를 반복한다면 부드럽게 다시 지적해주세요.
    - 긍정적이고 격려하는 말투를 사용해주세요.
    """

    try:
        response = await gemini_model.generate_content_async(prompt)
        if not response.parts:
            return "적절한 피드백을 생성할 수 없습니다. 자세를 조금 바꿔보세요."
        return response.text.strip()
    except Exception as e:
        print(f"Gemini API 호출 오류: {e}")
        return "피드백 생성 중 오류가 발생했습니다."