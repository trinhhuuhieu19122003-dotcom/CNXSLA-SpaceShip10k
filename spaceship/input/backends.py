"""Hai "động cơ" nhận diện tay của MediaPipe.

- ``LegacyHandsBackend``: API cũ ``mp.solutions.hands`` (mediapipe <= 0.10.21).
- ``TasksHandBackend``: API mới ``HandLandmarker`` (bắt buộc từ 0.10.31 vì
  ``mp.solutions`` đã bị xóa). Cần file model ``hand_landmarker.task`` — tự tải
  về thư mục dữ liệu người dùng ở lần chạy đầu.

Cả hai trả về cùng một dạng: danh sách 21 ``Point`` (tọa độ 0..1) hoặc None.
"""
from __future__ import annotations

import logging
import os
import urllib.request
from pathlib import Path
from typing import List, Optional

import numpy as np

from spaceship.config import HAND_LANDMARKER_URL
from spaceship.core.storage import default_save_path
from spaceship.input.gestures import Point

log = logging.getLogger(__name__)


class BackendUnavailable(RuntimeError):
    """Không dùng được nhận diện tay (thiếu thư viện, thiếu model...)."""


class LegacyHandsBackend:
    name = "MediaPipe Hands (legacy)"

    def __init__(self, mp) -> None:
        self._hands = mp.solutions.hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            model_complexity=0,          # model nhẹ: nhanh hơn, đủ chính xác cho game
            min_detection_confidence=0.7,
            min_tracking_confidence=0.6,
        )

    def process(self, rgb: np.ndarray, timestamp_ms: int) -> Optional[List[Point]]:
        result = self._hands.process(rgb)
        if not result.multi_hand_landmarks:
            return None
        return [Point(lm.x, lm.y) for lm in result.multi_hand_landmarks[0].landmark]

    def close(self) -> None:
        self._hands.close()


class TasksHandBackend:
    name = "MediaPipe HandLandmarker (tasks)"

    def __init__(self, mp, model_path: Path) -> None:
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision

        options = vision.HandLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=str(model_path)),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=1,
            min_hand_detection_confidence=0.6,
            min_hand_presence_confidence=0.6,
            min_tracking_confidence=0.6,
        )
        self._mp = mp
        self._landmarker = vision.HandLandmarker.create_from_options(options)
        self._last_ts = -1

    def process(self, rgb: np.ndarray, timestamp_ms: int) -> Optional[List[Point]]:
        timestamp_ms = max(int(timestamp_ms), self._last_ts + 1)   # API yêu cầu số nguyên tăng dần
        self._last_ts = timestamp_ms
        image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb))
        result = self._landmarker.detect_for_video(image, timestamp_ms)
        if not result.hand_landmarks:
            return None
        return [Point(lm.x, lm.y) for lm in result.hand_landmarks[0]]

    def close(self) -> None:
        self._landmarker.close()


def default_model_path() -> Path:
    return default_save_path().parent / "hand_landmarker.task"


def ensure_model(path: Path) -> Path:
    if path.exists():
        return path
    log.info("Đang tải model nhận diện tay về %s ...", path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".download")
        urllib.request.urlretrieve(HAND_LANDMARKER_URL, tmp)
        os.replace(tmp, path)
    except OSError as exc:
        raise BackendUnavailable(
            "Không tải được model hand_landmarker.task. Tải thủ công từ "
            f"{HAND_LANDMARKER_URL} và đặt vào {path}"
        ) from exc
    return path


def create_backend():
    try:
        import mediapipe as mp
    except ImportError as exc:
        raise BackendUnavailable("Chưa cài mediapipe (pip install -r requirements.txt)") from exc

    solutions = getattr(mp, "solutions", None)
    if solutions is not None and hasattr(solutions, "hands"):
        return LegacyHandsBackend(mp)
    return TasksHandBackend(mp, ensure_model(default_model_path()))
