"""Đọc camera + nhận diện tay ở LUỒNG RIÊNG.

Bản cũ gọi ``cap.read()`` và MediaPipe ngay trong vòng lặp game, nên game bị
khóa theo tốc độ webcam (~30 khung/giây → mọi thứ chạy chậm một nửa). Ở đây
luồng camera chạy độc lập; vòng lặp game chỉ lấy kết quả mới nhất, không chờ.
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np

from spaceship import config
from spaceship.input.backends import BackendUnavailable, create_backend
from spaceship.input.filters import OneEuroFilter
from spaceship.input.gestures import (
    HAND_CONNECTIONS,
    Gesture,
    GestureDebouncer,
    classify,
    map_to_zone,
    palm_center,
    zone_around,
)

log = logging.getLogger(__name__)

PREVIEW_SIZE = (240, 180)


@dataclass(frozen=True)
class HandReading:
    detected: bool = False
    x: float = 0.5            # 0..1 theo chiều ngang màn hình game
    y: float = 0.5
    gesture: Gesture = Gesture.NONE
    raw_x: float = 0.5        # tâm lòng bàn tay trong khung camera (chưa lọc) - dùng để hiệu chỉnh
    raw_y: float = 0.5


class TrackerState:
    STARTING = "starting"
    RUNNING = "running"
    UNAVAILABLE = "unavailable"
    STOPPED = "stopped"


class HandTracker:
    def __init__(
        self,
        camera_index: int = config.CAMERA_INDEX,
        backend_factory: Callable = create_backend,
    ) -> None:
        self.camera_index = camera_index
        self._backend_factory = backend_factory
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._reading = HandReading()
        self._preview: Optional[np.ndarray] = None
        self.state = TrackerState.STARTING
        self.message = "Đang mở camera..."
        self.backend_name = ""
        self.fps = 0.0
        self._fx = OneEuroFilter(config.ONE_EURO_MIN_CUTOFF, config.ONE_EURO_BETA)
        self._fy = OneEuroFilter(config.ONE_EURO_MIN_CUTOFF, config.ONE_EURO_BETA)
        self._debouncer = GestureDebouncer(config.GESTURE_STABLE_FRAMES)
        self._last_seen = 0.0
        #: vùng điều khiển trong khung camera; ControlHub cập nhật khi hiệu chỉnh / đổi độ nhạy
        self.zone = zone_around(config.HAND_DEFAULT_CENTER, config.HAND_SENSITIVITY["medium"], config.HAND_ZONE_ASPECT)

    # --- API cho vòng lặp game (không bao giờ chặn) ----------------------------------
    def start(self) -> "HandTracker":
        self._thread = threading.Thread(target=self._run, name="hand-tracker", daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)

    @property
    def reading(self) -> HandReading:
        with self._lock:
            return self._reading

    def preview(self) -> Optional[np.ndarray]:
        with self._lock:
            return self._preview

    # --- Luồng camera -----------------------------------------------------------------
    def _fail(self, message: str) -> None:
        log.warning("Điều khiển bằng tay không khả dụng: %s", message)
        self.state, self.message = TrackerState.UNAVAILABLE, message

    def _run(self) -> None:
        try:
            import cv2
        except ImportError:
            self._fail("Chưa cài opencv-python")
            return
        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            self._fail(f"Không mở được camera số {self.camera_index}")
            return
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_SIZE[0])
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_SIZE[1])
        try:
            backend = self._backend_factory()
        except BackendUnavailable as exc:
            cap.release()
            self._fail(str(exc))
            return
        self.backend_name = backend.name
        self.state, self.message = TrackerState.RUNNING, "Đang theo dõi tay"
        failures, frames, fps_t0 = 0, 0, time.monotonic()
        try:
            while not self._stop.is_set():
                ok, frame = cap.read()
                if not ok:
                    failures += 1
                    if failures > 60:
                        self._fail("Camera ngừng gửi hình")
                        break
                    time.sleep(0.01)
                    continue
                failures = 0
                frame = cv2.flip(frame, 1)                    # soi gương cho dễ điều khiển
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                now = time.monotonic()
                points = backend.process(rgb, int(now * 1000))
                reading = self._interpret(points, now)
                preview = self._make_preview(cv2, rgb, points, self.zone)
                with self._lock:
                    self._reading, self._preview = reading, preview
                frames += 1
                if now - fps_t0 >= 1.0:
                    self.fps, frames, fps_t0 = frames / (now - fps_t0), 0, now
        finally:
            backend.close()
            cap.release()
            if self.state == TrackerState.RUNNING:
                self.state = TrackerState.STOPPED

    def _interpret(self, points, now: float) -> HandReading:
        if points:
            self._last_seen = now
            palm = palm_center(points)
            pos = map_to_zone(palm, self.zone)
            return HandReading(
                detected=True,
                x=self._fx(pos.x, now),
                y=self._fy(pos.y, now),
                gesture=self._debouncer.update(classify(points)),
                raw_x=palm.x,
                raw_y=palm.y,
            )
        if now - self._last_seen <= config.HAND_LOST_TIMEOUT:
            return self._reading           # mất tay thoáng qua: giữ vị trí cũ, không giật
        self._fx.reset()
        self._fy.reset()
        self._debouncer.reset()
        return HandReading()

    @staticmethod
    def _make_preview(cv2, rgb: np.ndarray, points, zone) -> np.ndarray:
        w, h = PREVIEW_SIZE
        small = cv2.resize(rgb, (w, h))
        x0, y0, x1, y1 = zone
        cv2.rectangle(small, (int(x0 * w), int(y0 * h)), (int(x1 * w), int(y1 * h)), (0, 255, 255), 1)
        if points:
            pts = [(int(p.x * w), int(p.y * h)) for p in points]
            for a, b in HAND_CONNECTIONS:
                cv2.line(small, pts[a], pts[b], (0, 255, 120), 1)
            for p in pts:
                cv2.circle(small, p, 2, (255, 60, 60), -1)
        return small

