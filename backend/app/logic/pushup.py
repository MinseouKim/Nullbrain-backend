# backend/app/logic/pushup.py
import numpy as np
import mediapipe as mp

def calculate_angle(a, b, c):
    a = np.array([a['x'], a['y']])
    b = np.array([b['x'], b['y']])
    c = np.array([c['x'], c['y']])
    radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
    angle = np.abs(radians * 180.0 / np.pi)
    if angle > 180.0:
        angle = 360 - angle
    return angle

def get_pushup_angle(landmarks):
    mp_pose = mp.solutions.pose.PoseLandmark
    elbow_angle = None
    try:
        shoulder = landmarks[mp_pose.RIGHT_SHOULDER.value]
        elbow = landmarks[mp_pose.RIGHT_ELBOW.value]
        wrist = landmarks[mp_pose.RIGHT_WRIST.value]
        elbow_angle = calculate_angle(shoulder, elbow, wrist)
    except Exception as e:
        print(f"푸시업 각도 계산 오류: {e}")
    return elbow_angle