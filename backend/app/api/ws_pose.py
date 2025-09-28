# backend/app/api/ws_pose.py
import asyncio, json, os
from typing import Optional, Tuple

import cv2
import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from .camera_hub import hub  # ← 상대 임포트

# ---------- 유틸 --------------------------------------------------------------
def to_dict(keypoints):
    d = {}
    for k in keypoints:
        name = k.get("name") or k.get("part")
        if name:
            d[name] = k
    return d

def _angle(a, b, c):
    if a is None or b is None or c is None:
        return None
    ax, ay = a["x"], a["y"]; bx, by = b["x"], b["y"]; cx, cy = c["x"], c["y"]
    v1 = np.array([ax - bx, ay - by], dtype=float)
    v2 = np.array([cx - bx, cy - by], dtype=float)
    n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
    if n1 == 0 or n2 == 0: return None
    cos = np.clip(np.dot(v1, v2) / (n1 * n2), -1.0, 1.0)
    return float(np.degrees(np.arccos(cos)))

def angle(d, a, b, c): return _angle(d.get(a), d.get(b), d.get(c))

def seg_len(d, a, b):
    A, B = d.get(a), d.get(b)
    if not A or not B: return None
    return float(np.hypot(A["x"] - B["x"], A["y"] - B["y"]))

def pixel_to_cm_factor(d, height_cm):
    nose = d.get("nose")
    lf, rf = d.get("left_foot_index"), d.get("right_foot_index")
    if not nose or not (lf or rf): return None
    fy = (lf["y"] if lf else rf["y"])
    px = abs(fy - nose["y"])
    return (height_cm / px) if px > 0 else None

# 고정 입력 크기(세그 스무딩 오류 방지)
T_W, T_H = 640, 384
def letterbox(img, target=(T_W, T_H), color=(0, 0, 0)):
    h, w = img.shape[:2]
    tw, th = target
    scale = min(tw / w, th / h)
    nw, nh = int(w * scale), int(h * scale)
    resized = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA)
    out = np.zeros((th, tw, 3), dtype=img.dtype)
    px, py = (tw - nw) // 2, (th - nh) // 2
    out[py:py + nh, px:px + nw] = resized
    return out, scale, px, py, (w, h)

# ----- "정교 윤곽선" 도우미 ---------------------------------------------------
def uniform_sample_closed(poly_xy, n=160):
    """닫힌 다각형 좌표를 호길이 균등 샘플링"""
    pts = np.asarray(poly_xy, dtype=np.float32)
    if len(pts) < 3: return pts
    if not np.allclose(pts[0], pts[-1]):
        pts = np.vstack([pts, pts[:1]])
    seg = np.linalg.norm(pts[1:] - pts[:-1], axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    total = cum[-1]
    if total < 1e-3:
        return pts[:-1][:n]
    targets = np.linspace(0, total, n + 1)[:-1]
    res = []
    j = 1
    for t in targets:
        while j < len(cum) and cum[j] < t:
            j += 1
        t0, t1 = cum[j - 1], cum[j]
        r = 0.0 if t1 == t0 else (t - t0) / (t1 - t0)
        p = pts[j - 1] * (1 - r) + pts[j] * r
        res.append(p)
    return np.asarray(res, dtype=np.float32)

def chaikin_curve(pts):
    """Chaikin 곡선(닫힌) 1회 적용 → 부드러운 곡선"""
    P = np.asarray(pts, dtype=np.float32)
    if not np.allclose(P[0], P[-1]):
        P = np.vstack([P, P[:1]])
    Q = []
    for i in range(len(P) - 1):
        p0, p1 = P[i], P[i + 1]
        Q.append(0.75 * p0 + 0.25 * p1)
        Q.append(0.25 * p0 + 0.75 * p1)
    Q = np.asarray(Q, dtype=np.float32)
    return Q

def make_outline(mask_full, shrink_px=1, n_points=192, smooth_iter=3, min_area=1000):
    """
    마스크 → (erosion) → 외곽선 → 균등샘플 → Chaikin 스무딩 → n점 반환
    """
    m = mask_full
    # 조금만 깎아내 타이트하게
    if shrink_px > 0:
        ksz = int(max(3, shrink_px * 2 + 1))
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (ksz, ksz))
        m = cv2.erode(m, kernel, iterations=1)
    # 가장 큰 컨투어
    cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not cnts: return None
    c = max(cnts, key=cv2.contourArea)
    if cv2.contourArea(c) < min_area: return None
    poly = c[:, 0, :]  # (N,2)
    poly = uniform_sample_closed(poly, n_points)
    for _ in range(smooth_iter):
        poly = chaikin_curve(poly)
    poly = uniform_sample_closed(poly, n_points)
    poly = np.round(poly).astype(int)
    return [(int(x), int(y)) for x, y in poly]
# -----------------------------------------------------------------------------

# === NEW: 상세 모드 유틸 ===
def bbox_from_points(pts, w, h, margin=24):
    xs, ys = [], []
    for p in pts:
        if not p: continue
        xs.append(p["x"]); ys.append(p["y"])
    if not xs: return (0,0,w,h)
    x1, x2 = max(0, int(min(xs) - margin)), min(w, int(max(xs) + margin))
    y1, y2 = max(0, int(min(ys) - margin)), min(h, int(max(ys) + margin))
    if x2 <= x1 or y2 <= y1:
        return (0,0,w,h)
    return (x1, y1, x2, y2)

def horiz_angle_deg(ax, ay, bx, by):
    # 수평선과 AB 벡터 사이 각도(도). 오른쪽이 +x, 아래가 +y.
    dx, dy = (bx-ax), (by-ay)
    return float(np.degrees(np.arctan2(dy, dx)))

def dist(a, b):
    return float(np.hypot(a["x"]-b["x"], a["y"]-b["y"]))


# YOLO ROI (옵션)
YOLO_OK = False
YOLO = None
MODEL_PATH = "yolov8n-pose.pt"
try:
    from ultralytics import YOLO as _YOLO
    if os.path.exists(MODEL_PATH):
        YOLO = _YOLO(MODEL_PATH); YOLO_OK = True
    else:
        YOLO = _YOLO("yolov8n-pose.pt"); YOLO_OK = True
except Exception:
    YOLO_OK = False

router = APIRouter()
_mp_pose = None
_pose = None

def ensure_pose(model_complexity: int = 1):
    global _mp_pose, _pose
    if _pose is None:
        import mediapipe as mp
        _mp_pose = mp.solutions.pose
        _pose = _mp_pose.Pose(
            static_image_mode=False,
            model_complexity=model_complexity,
            enable_segmentation=True,
            smooth_segmentation=False,  # 입력크기 변동시 크래시 방지
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
            smooth_landmarks=True,
        )

def clamp_box(xyxy, w, h, margin=0):
    x1, y1, x2, y2 = map(int, xyxy)
    x1 = max(0, x1 - margin); y1 = max(0, y1 - margin)
    x2 = min(w, x2 + margin); y2 = min(h, y2 + margin)
    if x2 <= x1 or y2 <= y1:
        return 0, 0, w, h
    return x1, y1, x2, y2

def detect_person_roi(frame, prev_roi=None, every_n=10, idx=0):
    h, w = frame.shape[:2]
    if not YOLO_OK: return (0, 0, w, h)
    if idx % every_n != 0 and prev_roi is not None:
        return prev_roi
    try:
        scale = 480 / max(h, w)
        small = cv2.resize(frame, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA) if scale < 1.0 else frame
        res = YOLO.predict(small, imgsz=min(small.shape[1], small.shape[0]), conf=0.35, verbose=False)[0]
        best, best_area = None, 0
        for b in res.boxes:
            if int(b.cls[0].item()) != 0: continue
            sx1, sy1, sx2, sy2 = b.xyxy[0].tolist()
            x1, y1, x2, y2 = (sx1/scale, sy1/scale, sx2/scale, sy2/scale) if scale < 1.0 else (sx1, sy1, sx2, sy2)
            area = (x2 - x1) * (y2 - y1)
            if area > best_area:
                best_area, best = area, (x1, y1, x2, y2)
        return clamp_box(best, w, h, margin=20) if best else (0, 0, w, h)
    except Exception:
        return (0, 0, w, h)

@router.websocket("/ws/pose")
async def ws_pose(
    ws: WebSocket,
    height_cm: Optional[float] = Query(None, description="cm/px 보정용 사용자 키(cm)"),
    detail: Optional[str] = Query(None, description="상세 측정 모드: 'neck' 지원"),  # ★ 추가

):
    await ws.accept()
    ensure_pose(model_complexity=1)

    cm_per_px: Optional[float] = None
    accum = {
        "minKneeL": float("inf"),
        "minKneeR": float("inf"),
        "maxTrunk": 0.0,
        "maxValgus": 0.0,
        "overheadOK": False,
        "stable_full_body_frames": 0,
        "L": {"thighL": None, "thighR": None, "shankL": None, "shankR": None,
              "uarmL": None, "uarmR": None, "farmL": None, "farmR": None}
    }
    def ema(prev, cur, a=0.2): return cur if prev is None else prev * (1 - a) + cur * a

    idx = 0
    last_roi = None
    target_interval = 1.0 / 12.0  # 12 FPS

    try:
        while True:
            frame = hub.get_latest()
            if frame is None:
                await asyncio.sleep(0.01); continue

            H, W = frame.shape[:2]

            # ROI
            x1, y1, x2, y2 = detect_person_roi(frame, prev_roi=last_roi, every_n=10, idx=idx)
            last_roi = (x1, y1, x2, y2)
            crop = frame[y1:y2, x1:x2]
            if crop.size == 0:
                crop = frame; x1 = y1 = 0; x2 = W; y2 = H

            # 고정 크기 입력으로 Pose 실행
            inp, scale, px, py, (cw, ch) = letterbox(crop, target=(T_W, T_H))
            rgb = cv2.cvtColor(inp, cv2.COLOR_BGR2RGB)
            res = _pose.process(rgb)

            payload = {
                "ok": True,
                "keypoints": None,
                "metrics": {},
                "cm_per_px": cm_per_px,
                "size": {"w": W, "h": H},
                "outline": None,
                "coverage": None,
                "roi": [int(x1), int(y1), int(x2), int(y2)],
            }

            if res and res.pose_landmarks:
                # 키포인트 역투영
                kps = []
                tw, th = T_W, T_H
                nw, nh = int(cw * scale), int(ch * scale)
                for i, lm in enumerate(res.pose_landmarks.landmark):
                    xi, yi = lm.x * tw, lm.y * th
                    cx = (xi - px) / scale
                    cy = (yi - py) / scale
                    cx = max(0.0, min(cw - 1.0, cx))
                    cy = max(0.0, min(ch - 1.0, cy))
                    ox = x1 + cx; oy = y1 + cy
                    kps.append({
                        "name": _mp_pose.PoseLandmark(i).name.lower(),
                        "x": float(ox), "y": float(oy),
                        "z": float(lm.z * tw / scale),
                        "score": float(lm.visibility),
                    })
                d = to_dict(kps)
                payload["keypoints"] = kps

                # 윤곽선: 더 타이트하고 부드럽게 (3프레임마다)
                if res.segmentation_mask is not None and (idx % 3 == 0):
                    # threshold를 0.60으로 살짝 올려 과팽창 방지
                    mask_inp = (res.segmentation_mask > 0.60).astype("uint8") * 255  # (th, tw)
                    mask_paste = mask_inp[py:py + nh, px:px + nw]
                    mask_crop = cv2.resize(mask_paste, (cw, ch), interpolation=cv2.INTER_NEAREST)
                    mask_full = np.zeros((H, W), dtype=np.uint8)
                    mask_full[y1:y2, x1:x2] = mask_crop

                    # 모폴로지로 작은 구멍 메움 (close) → 그 뒤 약간 깎아내기(make_outline 내부)
                    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
                    mask_full = cv2.morphologyEx(mask_full, cv2.MORPH_CLOSE, kernel, iterations=1)

                    outline = make_outline(mask_full, shrink_px=2, n_points=160, smooth_iter=2, min_area=1200)
                    if outline is not None:
                        payload["outline"] = outline

                # cm/px
                if height_cm and cm_per_px is None:
                    cm_per_px = pixel_to_cm_factor(d, height_cm)
                    payload["cm_per_px"] = cm_per_px

                # 누적 메트릭 (생략 없이 유지)
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
                        valg = (knee["x"] - hip["x"]) - (ank["x"] - hip["x"])
                        accum["maxValgus"] = max(accum["maxValgus"], valg)
                for side in ("left", "right"):
                    wst, sh = d.get(f"{side}_wrist"), d.get(f"{side}_shoulder")
                    if wst and sh and wst["y"] < sh["y"]:
                        accum["overheadOK"] = True
                def ema(prev, cur, a=0.2): return cur if prev is None else prev * (1 - a) + cur * a
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

                # 커버리지 판정(기존 로직 유지)
                def v(name, thr=0.35):
                    kp = d.get(name); return bool(kp) and (kp["score"] or 0) >= thr
                groups = {
                    "head": ["nose","left_ear","right_ear","left_eye","right_eye"],
                    "shoulders": ["left_shoulder","right_shoulder"],
                    "elbows": ["left_elbow","right_elbow"],
                    "wrists": ["left_wrist","right_wrist"],
                    "hips": ["left_hip","right_hip"],
                    "knees": ["left_knee","right_knee"],
                    "ankles": ["left_ankle","right_ankle"],
                    "feet": ["left_foot_index","right_foot_index","left_heel","right_heel"],
                }
                visible_groups = {}
                for g, names in groups.items():
                    if g in ("shoulders","elbows","wrists","hips","knees","ankles"):
                        ok = v(names[0]) and v(names[1])
                    else:
                        ok = any(v(n) for n in names)
                    visible_groups[g] = ok
                weights = {"head":1,"shoulders":2,"elbows":1,"wrists":1,"hips":2,"knees":2,"ankles":2,"feet":1}
                got = sum(weights[g] for g, ok in visible_groups.items() if ok)
                tot = sum(weights.values())
                coverage_score = round(got / tot, 3)
                is_full_body = (
                    visible_groups["shoulders"] and visible_groups["hips"] and
                    visible_groups["knees"] and visible_groups["ankles"] and
                    (visible_groups["head"] or visible_groups["feet"])
                )
                def inside_y(name, margin=4):
                    kp = d.get(name); return bool(kp) and 0 + margin <= kp["y"] <= H - margin
                ankles_in = inside_y("left_ankle") and inside_y("right_ankle")
                if is_full_body and not ankles_in:
                    is_full_body = False
                if is_full_body:
                    accum["stable_full_body_frames"] += 1
                else:
                    accum["stable_full_body_frames"] = 0
                state = "full" if is_full_body else ("partial" if coverage_score >= 0.2 else "no_person")
                payload["coverage"] = {
                    "score": coverage_score,
                    "visible_groups": visible_groups,
                    "is_full_body": is_full_body,
                    "stable_full_body_frames": accum["stable_full_body_frames"],
                    "state": state,
                }

                # 임계치/메트릭
                minKnee = min(accum["minKneeL"], accum["minKneeR"])
                kneeThr = int(min(max((minKnee if minKnee != float("inf") else 90) + 8, 75), 110))
                trunkThr = int(min(accum["maxTrunk"] + 5, 45)) if accum["maxTrunk"] else None
                valgThr = round(max(0.12, min(0.25, accum["maxValgus"] + 0.02)), 2)
                def to_cm(v): return round(v * cm_per_px, 1) if (v and cm_per_px) else None
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
            idx += 1
            await asyncio.sleep(target_interval)
    except WebSocketDisconnect:
        pass
