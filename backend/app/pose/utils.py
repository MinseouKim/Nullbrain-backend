import math

def to_dict(kps):
    d = {}
    for k in kps or []:
        n = k.get("name") or k.get("part")
        if n:
            d[n] = {"x": k.get("x"), "y": k.get("y"), "z": k.get("z", 0), "score": k.get("score")}
    return d

def angle(d, a, b, c):
    A, B, C = d.get(a), d.get(b), d.get(c)
    if not (A and B and C): 
        return None
    ab = (A["x"] - B["x"], A["y"] - B["y"])
    cb = (C["x"] - B["x"], C["y"] - B["y"])
    dot = ab[0]*cb[0] + ab[1]*cb[1]
    mag = (math.hypot(*ab) * math.hypot(*cb)) + 1e-9
    cosv = max(-1.0, min(1.0, dot/mag))
    return math.degrees(math.acos(cosv))

def seg_len(d, a, b):
    A, B = d.get(a), d.get(b)
    if not (A and B):
        return None
    return math.hypot(A["x"] - B["x"], A["y"] - B["y"])

def pixel_to_cm_factor(d, Hcm):
    tops = [d.get(k, {}).get("y") for k in ["nose","left_eye","right_eye","left_ear","right_ear"] if d.get(k)]
    bots = [d.get(k, {}).get("y") for k in ["left_ankle","right_ankle","left_foot_index","right_foot_index"] if d.get(k)]
    if not tops or not bots:
        return None
    pxH = max(bots) - min(tops)
    if pxH < 120:
        return None
    return Hcm / pxH
