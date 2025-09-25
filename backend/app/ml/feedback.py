# backend/app/ml/feedback.py
import numpy as np
# MediaPipe 라이브러리는 백엔드에서 더 이상 직접 사용하지 않지만,
# 랜드마크 인덱스 번호를 참조하기 위해 남겨둘 수 있습니다.
import mediapipe as mp

def calculate_angle(a, b, c):
    # a, b, c는 이제 {'x': 0.5, 'y': 0.4, ...} 형태의 딕셔너리입니다.
    a = np.array([a['x'], a['y']])
    b = np.array([b['x'], b['y']])
    c = np.array([c['x'], c['y']])

    radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
    angle = np.abs(radians * 180.0 / np.pi)

    if angle > 180.0:
        angle = 360 - angle

    return angle

def get_squat_feedback(landmarks):
    # landmarks는 이제 33개의 딕셔너리가 담긴 리스트입니다.
    mp_pose = mp.solutions.pose.PoseLandmark
    feedback, angle = "자세를 분석할 수 없습니다.", None
    try:
        hip = landmarks[mp_pose.LEFT_HIP.value]
        knee = landmarks[mp_pose.LEFT_KNEE.value]
        ankle = landmarks[mp_pose.LEFT_ANKLE.value]
        angle = calculate_angle(hip, knee, ankle)

        # y 좌표는 hip['y'] > knee['y'] 형태로 접근
        if angle < 95 and hip['y'] > knee['y']:
            feedback = "자세 좋습니다!"
        elif angle > 160:
            feedback = "준비"
        else:
            feedback = "더 내려가세요!"
    except Exception as e:
        feedback = "카메라에 전신이 나오게 해주세요"
    return feedback, angle

# (푸시업 함수도 동일한 원리로 수정 가능, 여기서는 생략)