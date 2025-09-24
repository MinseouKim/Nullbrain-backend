# backend/app/dataSet/create_dataset.py

import cv2
import os
import csv
import sys

# --- 경로 설정 (가장 중요!) ---
# 이 스크립트 파일의 현재 위치를 기준으로 프로젝트 루트(backend) 경로를 계산합니다.
# 이렇게 하면 어떤 위치에서 실행해도 경로가 꼬이지 않습니다.
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)
# --------------------------------

from app.ml.pipeline import PoseEstimator # 이제 app 모듈을 확실히 찾을 수 있습니다.

# --- 설정 (수정된 부분) ---
# 1. 영상 파일이 있는 폴더 경로 (프로젝트 루트 기준)
VIDEO_FOLDER = os.path.join(project_root, 'app', 'videos')
# 2. 저장할 CSV 파일 경로 (프로젝트 루트 기준)
CSV_FILE_NAME = os.path.join(project_root, 'app', 'dataSet', 'squat_landmarks.csv')
# 3. 처리할 영상과 부여할 정답(레이블) 목록
VIDEO_FILES_AND_LABELS = [
    ('squat_good.mp4', 'good'),
    ('squat_bad_high.mp4', 'bad_high')
]
# -------------------------

# PoseEstimator 인스턴스 생성
pose_estimator = PoseEstimator()

# CSV 파일 생성을 위한 헤더 준비
landmarks_header = [f'lm_{i}_{axis}' for i in range(33) for axis in ['x', 'y', 'z', 'v']]
landmarks_header.append('class')

# CSV 파일 열기
with open(CSV_FILE_NAME, 'w', newline='') as f:
    csv_writer = csv.writer(f)
    csv_writer.writerow(landmarks_header) # 헤더 작성

    # 각 비디오 파일을 순서대로 처리
    for video_file, label in VIDEO_FILES_AND_LABELS:
        video_path = os.path.join(VIDEO_FOLDER, video_file)
        
        if not os.path.exists(video_path):
            print(f"[경고] 파일을 찾을 수 없습니다: {video_path}")
            continue

        cap = cv2.VideoCapture(video_path)
        frame_count = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            _, landmarks = pose_estimator.process_frame(frame)
            
            if landmarks:
                row = [coord for lm in landmarks for coord in [lm.x, lm.y, lm.z, lm.visibility]]
                row.append(label)
                csv_writer.writerow(row)
                frame_count += 1
        
        cap.release()
        print(f"[완료] 영상 '{video_file}' 처리 완료. 총 {frame_count}개 프레임에서 랜드마크를 추출했습니다.")

print(f"\n모든 작업 완료! 데이터가 '{os.path.basename(CSV_FILE_NAME)}' 파일에 저장되었습니다.")