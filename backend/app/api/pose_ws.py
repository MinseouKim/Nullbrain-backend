import asyncio
import json
from typing import Optional

import cv2
import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.pose.utils import to_dict, angle, seg_len, pixel_to_cm_factor

router = APIRouter()
_camera: Optional[cv2.VideoCapture] = None

def get_camera() -> cv2.VideoCapture:
    global _camera
    if _camera is None or not _camera.isOpened():
        _camera = cv2.VideoCapture(0)  # 필요시 v4l2 파라미터 조정
    return _camera

# MediaPipe Pose 로더
_mp_pose = None
_pose = None
def ensure_pose(model_complexity: int = 1):
    global _mp_pose, _pose
    if _pose is None:
        import mediapipe as mp
        _mp_pose = mp.solutions.pose
        _pose = _mp_pose.Pose(
            static_image_mode=False,
            model_complexity=model_complexity,  # 0/1/2
            enable_segmentation=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
            smooth_landmarks=True,
        )

@router.websocket("/ws/pose")
async def ws_pose(
    ws: WebSocket,
    height_cm: Optional[float] = Query(None, description="사용자 키(cm), 전신 프레임에서 cm/px 보정용"),
):
    await ws.accept()
    ensure_pose(model_complexity=1)
    cam = get_camera()
    cm_per_px: Optional[float] = None

    # 누적값(캘리브레이션/개인세팅)
    accum = {
        "minKneeL": float("inf"),
        "minKneeR": float("inf"),
        "maxTrunk": 0.0,
        "maxValgus": 0.0,
        "overheadOK": False,
        "L": {"thighL": None, "thighR": None, "shankL": None, "shankR": None,
              "uarmL": None, "uarmR": None, "farmL": None, "farmR": None}
    }
    def ema(prev, cur, a=0.2): 
        return cur if prev is None else prev*(1-a)+cur*a

    try:
        while True:
            if not cam.isOpened():
                break
            ok, frame = cam.read()
            if not ok:
                break

            # BGR->RGB
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            res = _pose.process(rgb)

            payload = {"ok": True, "keypoints": None, "metrics": {}, "cm_per_px": cm_per_px}
            if res and res.pose_landmarks:
                # MediaPipe는 0~1 정규화 좌표 -> 픽셀로 변환
                h, w = frame.shape[:2]
                kps = []
                for i, lm in enumerate(res.pose_landmarks.landmark):
                    kps.append({
                        "name": _mp_pose.PoseLandmark(i).name.lower(),
                        "x": lm.x * w, "y": lm.y * h, "z": lm.z * w, 
                        "score": lm.visibility
                    })
                d = to_dict(kps)
                payload["keypoints"] = kps

                # 키(cm) 받았고 아직 보정 전이면 cm/px 계산
                if height_cm and cm_per_px is None:
                    cm_per_px = pixel_to_cm_factor(d, height_cm)
                    payload["cm_per_px"] = cm_per_px

                # 각도/지표 업데이트
                kL = angle(d, "left_hip", "left_knee", "left_ankle")
                kR = angle(d, "right_hip", "right_knee", "right_ankle")
                if kL is not None: accum["minKneeL"] = min(accum["minKneeL"], kL)
                if kR is not None: accum["minKneeR"] = min(accum["minKneeR"], kR)

                tL = angle(d, "left_shoulder", "left_hip", "left_ankle")
                tR = angle(d, "right_shoulder", "right_hip", "right_ankle")
                tr = max(t for t in [tL or 0, tR or 0])
                accum["maxTrunk"] = max(accum["maxTrunk"], tr)

                for side in ("left", "right"):
                    hip, knee, ank = d.get(f"{side}_hip"), d.get(f"{side}_knee"), d.get(f"{side}_ankle")
                    if hip and knee and ank:
                        valg = (knee["x"]-hip["x"]) - (ank["x"]-hip["x"])
                        accum["maxValgus"] = max(accum["maxValgus"], valg)

                # 오버헤드 체크
                for side in ("left", "right"):
                    wst, sh = d.get(f"{side}_wrist"), d.get(f"{side}_shoulder")
                    if wst and sh and wst["y"] < sh["y"]:
                        accum["overheadOK"] = True

                # 길이(px) EMA -> cm 변환(보정 완료 시)
                def upd_len(key, a, b):
                    Lpx = seg_len(d, a, b)
                    if Lpx: accum["L"][key] = ema(accum["L"][key], Lpx)

                upd_len("thighL", "left_hip", "left_knee")
                upd_len("thighR", "right_hip", "right_knee")
                upd_len("shankL", "left_knee", "left_ankle")
                upd_len("shankR", "right_knee", "right_ankle")
                upd_len("uarmL", "left_shoulder", "left_elbow")
                upd_len("uarmR", "right_shoulder", "right_elbow")
                upd_len("farmL", "left_elbow", "left_wrist")
                upd_len("farmR", "right_elbow", "right_wrist")

                # 결과 패키징
                minKnee = min(accum["minKneeL"], accum["minKneeR"])
                kneeThr = int(min(max((minKnee if minKnee != float("inf") else 90) + 8, 75), 110))
                trunkThr = int(min(accum["maxTrunk"] + 5, 45)) if accum["maxTrunk"] else None
                valgThr = round(max(0.12, min(0.25, accum["maxValgus"] + 0.02)), 2)

                def to_cm(v):
                    return round(v * cm_per_px, 1) if (v and cm_per_px) else None

                payload["metrics"] = {
                    "knee_min_angle_deg": None if minKnee == float("inf") else round(minKnee),
                    "trunk_max_flexion_deg": round(accum["maxTrunk"], 1) if accum["maxTrunk"] else None,
                    "valgus_index_max": round(accum["maxValgus"], 3),
                    "overhead_ok": accum["overheadOK"],
                    "lengths_cm": {
                        "thighL": to_cm(accum["L"]["thighL"]),
                        "thighR": to_cm(accum["L"]["thighR"]),
                        "shankL": to_cm(accum["L"]["shankL"]),
                        "shankR": to_cm(accum["L"]["shankR"]),
                        "upperArmL": to_cm(accum["L"]["uarmL"]),
                        "upperArmR": to_cm(accum["L"]["uarmR"]),
                        "forearmL": to_cm(accum["L"]["farmL"]),
                        "forearmR": to_cm(accum["L"]["farmR"]),
                    },
                    "thresholds": {
                        "knee_depth_angle_le": kneeThr,
                        "trunk_flexion_max_deg": trunkThr,
                        "valgus_index_max": valgThr,
                        "shoulder_flexion_goal_deg": 160,
                    },
                }

            await ws.send_text(json.dumps(payload))
            await asyncio.sleep(0.03)

    except WebSocketDisconnect:
        pass
    finally:
        # 카메라를 여기서 닫지 않는 게 여러 WS에서 공유할 때 안전
        pass
