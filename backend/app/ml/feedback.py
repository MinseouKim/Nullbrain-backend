# app/ml/feedback.py

import numpy as np
import mediapipe as mp

def calculate_angle(a, b, c):
    """세 점(랜드마크) 사이의 각도를 계산하는 함수 (예: 어깨-팔꿈치-손목)."""
    # 각 점을 numpy 배열로 변환
    a = np.array(a) # 첫 번째 점
    b = np.array(b) # 중간 점
    c = np.array(c) # 마지막 점
    
    # arctan2를 이용해 라디안 각도를 구하고, 이를 다시 각도로 변환
    radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
    angle = np.abs(radians * 180.0 / np.pi)
    
    # 각도가 180도를 넘으면 360에서 빼서 작은 쪽 각도를 사용
    if angle > 180.0:
        angle = 360 - angle
        
    return angle

def get_squat_feedback(landmarks):
    """
    랜드마크 데이터를 기반으로 스쿼트 자세에 대한 피드백과
    무릎 각도를 반환하는 함수.
    """
    # MediaPipe의 PoseLandmark enum을 사용해 관절 인덱스에 쉽게 접근
    mp_pose = mp.solutions.pose.PoseLandmark

    # 피드백을 위한 변수 초기화
    feedback = "자세를 잡아주세요"
    knee_angle = None
    
    try:
        # 왼쪽 엉덩이, 무릎, 발목의 2D 좌표 추출
        hip = [landmarks[mp_pose.LEFT_HIP.value].x, landmarks[mp_pose.LEFT_HIP.value].y]
        knee = [landmarks[mp_pose.LEFT_KNEE.value].x, landmarks[mp_pose.LEFT_KNEE.value].y]
        ankle = [landmarks[mp_pose.LEFT_ANKLE.value].x, landmarks[mp_pose.LEFT_ANKLE.value].y]

        # 무릎 각도 계산
        knee_angle = calculate_angle(hip, knee, ankle)
        
        # 각도에 따른 피드백 생성
        if knee_angle > 160:
            feedback = "준비"
        elif knee_angle <= 160 and knee_angle > 90:
            feedback = "더 내려가세요"
        elif knee_angle <= 90:
            feedback = "자세 좋습니다!"
            
    except:
        # 관절이 감지되지 않는 등 예외 발생 시
        pass
        
    return feedback, knee_angle

def get_pushup_feedback(landmarks):
    """
    랜드마크 데이터를 기반으로 푸시업 자세에 대한 피드백과
    팔꿈치 각도를 반환하는 함수.
    """
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
            
    except:
        pass
        
    return feedback, elbow_angle