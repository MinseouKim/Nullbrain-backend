# app/ml/pipeline.py

import cv2
import mediapipe as mp
import numpy as np

class PoseEstimator:
    def __init__(self):
        """MediaPipe Pose 모델을 초기화합니다."""
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose()
        self.mp_drawing = mp.solutions.drawing_utils

    def process_frame(self, frame):
        """
        OpenCV 프레임을 입력받아 자세를 추정하고,
        관절이 그려진 이미지와 랜드마크 데이터를 반환합니다.
        """
        # MediaPipe는 RGB 이미지를 사용하므로, OpenCV의 BGR 이미지를 RGB로 변환합니다.
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image.flags.writeable = False

        # 이미지에서 자세 추정을 수행합니다.
        results = self.pose.process(image)

        # 다시 BGR로 변환하여 화면에 표시할 수 있도록 합니다.
        image.flags.writeable = True
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        # 랜드마크(관절 좌표) 데이터 추출 및 시각화
        landmarks = None
        if results.pose_landmarks:
            landmarks = results.pose_landmarks.landmark
            self.mp_drawing.draw_landmarks(
                image,
                results.pose_landmarks,
                self.mp_pose.POSE_CONNECTIONS,
                landmark_drawing_spec=self.mp_drawing.DrawingSpec(color=(245, 117, 66), thickness=2, circle_radius=2),
                connection_drawing_spec=self.mp_drawing.DrawingSpec(color=(245, 66, 230), thickness=2, circle_radius=2)
            )

        return image, landmarks