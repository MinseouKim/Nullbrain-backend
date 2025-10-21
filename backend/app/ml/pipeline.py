# (현재 프론트엔드가 MediaPipe Pose를 처리하므로, 이 파일은 현재 실행 흐름에서 사용되지 않습니다.)
# 향후 서버 사이드 영상 분석 또는 데이터 전처리 파이프라인에 사용할 수 있습니다.


import cv2
import mediapipe as mp
import numpy as np
# import os  <- 더 이상 필요 없습니다.

class PoseEstimator:
    def __init__(self):
        """MediaPipe Pose 모델을 초기화합니다."""
        self.mp_pose = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils

        # 이 한 줄이면 MediaPipe가 알아서 모델을 로드합니다.
        self.pose = self.mp_pose.Pose(
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

    def process_frame(self, frame):
        """
        OpenCV 프레임을 입력받아 자세를 추정하고,
        관절이 그려진 이미지와 랜드마크 데이터를 반환합니다.
        """
        # BGR → RGB 변환
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image.flags.writeable = False

        # Pose 추정
        results = self.pose.process(image)

        # 다시 BGR 변환
        image.flags.writeable = True
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        # 랜드마크 데이터 추출 및 시각화
        landmarks = None
        if results.pose_landmarks:
            landmarks = results.pose_landmarks.landmark
            self.mp_drawing.draw_landmarks(
                image,
                results.pose_landmarks,
                self.mp_pose.POSE_CONNECTIONS,
                landmark_drawing_spec=self.mp_drawing.DrawingSpec(
                    color=(245, 117, 66), thickness=2, circle_radius=2
                ),
                connection_drawing_spec=self.mp_drawing.DrawingSpec(
                    color=(245, 66, 230), thickness=2, circle_radius=2
                )
            )

        return image, landmarks