# backend/app/logic/squat.py
import numpy as np
import mediapipe as mp

def calculate_angle(a, b, c):
    """세 점(랜드마크) 사이의 각도를 계산하는 함수"""
    # a, b, c는 {'x': 0.5, 'y': 0.4, ...} 형태의 딕셔너리입니다.
    a = np.array([a['x'], a['y']])
    b = np.array([b['x'], b['y']])
    c = np.array([c['x'], c['y']])
    
    radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
    angle = np.abs(radians * 180.0 / np.pi)
    
    if angle > 180.0:
        angle = 360 - angle
        
    return angle

def get_squat_angle(landmarks):
    """
    스쿼트 자세의 왼쪽 무릎 각도를 '계산만' 해서 반환합니다.
    """
    mp_pose = mp.solutions.pose.PoseLandmark
    angle = None
    
    try:
        hip = landmarks[mp_pose.LEFT_HIP.value]
        knee = landmarks[mp_pose.LEFT_KNEE.value]
        ankle = landmarks[mp_pose.LEFT_ANKLE.value]
        angle = calculate_angle(hip, knee, ankle)
    except Exception as e:
        print(f"스쿼트 각도 계산 오류: {e}")
        
    return angle