import asyncio, json, time
from typing import Optional

import cv2
import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from ultralytics import YOLO
import torch

from app.pose.utils import to_dict, angle, seg_len, pixel_to_cm_factor

router = APIRouter()

# ---- Camera ----
_cam = None
def get_cam():
    global _cam
    if _cam is None or not _cam.isOpened():
        _cam = cv2.VideoCapture(0, cv2.CAP_V4L2)
        _cam.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        _cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        _cam.set(cv2.CAP_PROP_FPS, 30)
        _cam.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
    return _cam

# ---- YOLOv8 Pose ----
_device = 0 if torch.cuda.is_available() else "cpu"
_model = YOLO("yolov8n-pose.pt")   # n/s/m 선택 가능 (n이 가볍고 견고)
# COCO 17 keypoints 이름
COCO17 = ['nose','left_eye','right_eye','left_ear','right_ear',
          'left_shoulder','right_shoulder','left_elbow','right_elbow',
          'left_wrist','right_wrist','left_hip','right_hip',
          'left_knee','right_knee','left_ankle','right_ankle']

@router.websocket("/ws/pose")
async def ws_pose(
    ws: WebSocket,
    height_cm: Optional[float] = Query(None, description="전신 프레임에서 키(cm)로 cm/px 보정"),
):
    await ws.accept()
    cam = get_cam()
    cm_per_px: Optional[float] = None

    # 누적 측정치
    accum = {
        "minKneeL": float("inf"),
        "minKneeR": float("inf"),
        "maxTrunk": 0.0,
        "maxValgus": 0.0,
        "overheadOK": False,
        "L": {"thighL": None, "thighR": None, "shankL": None, "shankR": None,
              "uarmL": None, "uarmR": None, "farmL": None, "farmR": None},
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
            h, w = frame.shape[:2]

            # ---- YOLO Pose 추론 (사람 검출+포즈 동시) ----
            res = _model(frame, imgsz=640, conf=0.5, device=_device, verbose=False)[0]
            keypoints = None
            if res.keypoints is not None and len(res.keypoints) > 0:
                # 가장 큰 사람 하나 고르기(화면에 가장 크게 잡힌 사람)
                areas = []
                for b in (res.boxes.xyxy if res.boxes is not None else []):
                    x1,y1,x2,y2 = b.tolist()
                    areas.append(max(0,(x2-x1)) * max(0,(y2-y1)))
                person_idx = int(np.argmax(areas)) if areas else 0

                kxy = res.keypoints.xy[person_idx].tolist()       # [[x,y], ...]
                ksc = res.keypoints.conf[person_idx].tolist()     # [score, ...]
                keypoints = []
                for (x,y), s, name in zip(kxy, ksc, COCO17):
                    keypoints.append({"name": name, "x": float(x), "y": float(y), "z": 0.0, "score": float(s or 0)})

            # 페이로드 기본
            payload = {
                "ok": True,
                "size": {"w": w, "h": h},
                "keypoints": keypoints,
                "cm_per_px": cm_per_px,
                "advice": None,
                "metrics": {},
            }

            if keypoints:
                d = to_dict(keypoints)

                # 전신 프레이밍 체크 + 안내
                head_y_candidates = [d.get(k,{}).get("y") for k in ["nose","left_eye","right_eye","left_ear","right_ear"] if d.get(k)]
                foot_y_candidates = [d.get(k,{}).get("y") for k in ["left_ankle","right_ankle","left_foot_index","right_foot_index"] if d.get(k)]
                if head_y_candidates and foot_y_candidates:
                    pxH = max(foot_y_candidates) - min(head_y_candidates)
                    fill = pxH / h
                    if   fill > 0.90: payload["advice"] = "카메라에서 한 걸음 뒤로 가세요"
                    elif fill < 0.45: payload["advice"] = "조금 더 가까이 오세요"
                    else:             payload["advice"] = "좋아요! 측정 중…"

                # 키(cm) 기반 cm/px 보정(최초 1회)
                if height_cm and cm_per_px is None:
                    cm_per_px = pixel_to_cm_factor(d, height_cm)
                    payload["cm_per_px"] = cm_per_px

                # 각도/지표
                kL = angle(d, "left_hip", "left_knee", "left_ankle")
                kR = angle(d, "right_hip", "right_knee", "right_ankle")
                if kL is not None: accum["minKneeL"] = min(accum["minKneeL"], kL)
                if kR is not None: accum["minKneeR"] = min(accum["minKneeR"], kR)

                tL = angle(d, "left_shoulder", "left_hip", "left_ankle")
                tR = angle(d, "right_shoulder", "right_hip", "right_ankle")
                if tL or tR:
                    tr = max(t for t in [tL or 0, tR or 0])
                    accum["maxTrunk"] = max(accum["maxTrunk"], tr)

                for side in ("left", "right"):
                    hip, knee, ank = d.get(f"{side}_hip"), d.get(f"{side}_knee"), d.get(f"{side}_ankle")
                    if hip and knee and ank:
                        valg = (knee["x"] - hip["x"]) - (ank["x"] - hip["x"])
                        accum["maxValgus"] = max(accum["maxValgus"], valg)

                for side in ("left", "right"):
                    wst, sh = d.get(f"{side}_wrist"), d.get(f"{side}_shoulder")
                    if wst and sh and wst["y"] < sh["y"]:
                        accum["overheadOK"] = True

                # 길이(px) EMA
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

                # 임계치/요약
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
