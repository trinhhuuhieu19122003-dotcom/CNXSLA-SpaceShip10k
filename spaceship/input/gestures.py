"""Nhận diện cử chỉ từ 21 điểm mốc bàn tay của MediaPipe — hàm thuần, dễ test.

Khác bản cũ:
- Xét ngón "duỗi" theo KHOẢNG CÁCH tới cổ tay thay vì so tọa độ y, nên vẫn
  đúng khi nghiêng/xoay bàn tay.
- Lấy vị trí theo TÂM BÀN TAY (trung bình cổ tay + 4 gốc ngón), ổn định hơn cổ tay.
- Chỉ dùng một VÙNG ĐIỀU KHIỂN nhỏ quanh tư thế nghỉ của tay (xem ``zone_around``).
- Cử chỉ phải giữ ổn định vài khung mới được nhận (chống nhấp nháy).
"""
from __future__ import annotations

import math
from enum import Enum
from typing import NamedTuple, Sequence, Tuple

from spaceship.config import PINCH_RATIO


class Point(NamedTuple):
    x: float
    y: float


# Chỉ số điểm mốc theo tài liệu MediaPipe Hands
WRIST = 0
FINGERS = {  # (gốc MCP, khớp giữa PIP, đầu ngón TIP)
    "index": (5, 6, 8),
    "middle": (9, 10, 12),
    "ring": (13, 14, 16),
    "pinky": (17, 18, 20),
}
PALM_POINTS = (0, 5, 9, 13, 17)
HAND_CONNECTIONS: Tuple[Tuple[int, int], ...] = (
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20), (0, 17),
)
EXTENDED_RATIO = 1.1  # đầu ngón phải xa cổ tay hơn khớp giữa ít nhất 10%


THUMB_TIP, INDEX_TIP, MIDDLE_MCP = 4, 8, 9


class Gesture(Enum):
    NONE = "none"      # không thấy tay
    OPEN = "open"      # xòe tay: lái tàu
    PINCH = "pinch"    # chụm đầu ngón cái + trỏ: kỹ năng Nộ
    FIST = "fist"      # nắm tay: né chậm
    POINT = "point"    # chỉ ngón trỏ: bắn (khi tắt tự động bắn)
    THREE = "three"    # trỏ + giữa + áp út (giữ để tương thích, không còn dùng)
    OTHER = "other"    # tư thế khác: vẫn lái bình thường


def _dist(a: Point, b: Point) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


def finger_extended(landmarks: Sequence[Point], finger: str, ratio: float = EXTENDED_RATIO) -> bool:
    _mcp, pip, tip = FINGERS[finger]
    wrist = landmarks[WRIST]
    return _dist(wrist, landmarks[tip]) > _dist(wrist, landmarks[pip]) * ratio


def palm_size(landmarks: Sequence[Point]) -> float:
    """Cỡ bàn tay (cổ tay -> gốc ngón giữa): dùng làm thước đo, không phụ thuộc tay gần/xa camera."""
    return max(1e-6, _dist(landmarks[WRIST], landmarks[MIDDLE_MCP]))


def is_pinch(landmarks: Sequence[Point], ratio: float = PINCH_RATIO) -> bool:
    return _dist(landmarks[THUMB_TIP], landmarks[INDEX_TIP]) < ratio * palm_size(landmarks)


def classify(landmarks: Sequence[Point]) -> Gesture:
    if len(landmarks) < 21:
        return Gesture.NONE
    up = {name: finger_extended(landmarks, name) for name in FINGERS}
    pattern = (up["index"], up["middle"], up["ring"], up["pinky"])
    if not any(pattern):                  # xét nắm tay TRƯỚC: khi nắm, ngón cái cũng nằm sát ngón trỏ
        return Gesture.FIST
    if is_pinch(landmarks):
        return Gesture.PINCH
    if pattern == (True, False, False, False):
        return Gesture.POINT
    if pattern == (True, True, True, False):
        return Gesture.THREE
    if all(pattern):
        return Gesture.OPEN
    return Gesture.OTHER


def palm_center(landmarks: Sequence[Point]) -> Point:
    xs = [landmarks[i].x for i in PALM_POINTS]
    ys = [landmarks[i].y for i in PALM_POINTS]
    return Point(sum(xs) / len(xs), sum(ys) / len(ys))


def map_to_zone(point: Point, zone: Tuple[float, float, float, float]) -> Point:
    """Đổi tọa độ trong vùng điều khiển thành 0..1 (kẹp lại nếu ra ngoài vùng)."""
    x0, y0, x1, y1 = zone
    nx = (point.x - x0) / (x1 - x0)
    ny = (point.y - y0) / (y1 - y0)
    return Point(min(1.0, max(0.0, nx)), min(1.0, max(0.0, ny)))


def zone_around(center: Tuple[float, float], half_width: float, aspect: float) -> Tuple[float, float, float, float]:
    """Vùng điều khiển (x0, y0, x1, y1) quanh tư thế nghỉ, tự dịch vào trong nếu chạm mép khung."""
    hw = min(0.5, half_width)
    hh = min(0.5, half_width * aspect)
    cx = min(1 - hw, max(hw, center[0]))
    cy = min(1 - hh, max(hh, center[1]))
    return (cx - hw, cy - hh, cx + hw, cy + hh)


class GestureDebouncer:
    """Chỉ đổi cử chỉ khi cử chỉ mới xuất hiện liên tiếp ``frames`` lần."""

    def __init__(self, frames: int = 3) -> None:
        self.frames = frames
        self.reset()

    def reset(self) -> None:
        self.stable = Gesture.NONE
        self._candidate = Gesture.NONE
        self._count = 0

    def update(self, gesture: Gesture) -> Gesture:
        if gesture == self._candidate:
            self._count += 1
        else:
            self._candidate, self._count = gesture, 1
        if self._count >= self.frames:
            self.stable = gesture
        return self.stable
