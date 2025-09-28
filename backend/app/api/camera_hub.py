# app/camera_hub.py
import cv2, threading, time

class CameraHub:
    def __init__(self, index=0, width=1280, height=720,mirror=True, fps=30):
        self.cap = cv2.VideoCapture(index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,  width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_FPS, fps)
        self.lock = threading.Lock()
        self.mirror = mirror
        self.latest = None
        self.running = False
        self.thread = None
        self.target_interval = 1.0 / fps

    def start(self):
        if self.running: return
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def _loop(self):
        while self.running:
            ok, frame = self.cap.read()
            if ok:
                if self.mirror:
                    frame = cv2.flip(frame, 1)  # ★ 좌우 반전
                with self.lock:
                    self.latest = frame
            time.sleep(self.target_interval * 0.5)

    def get_latest(self):
        with self.lock:
            return None if self.latest is None else self.latest.copy()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        if self.cap and self.cap.isOpened():
            self.cap.release()

# 글로벌 싱글턴 인스턴스 시작
hub = CameraHub()
hub.start()
