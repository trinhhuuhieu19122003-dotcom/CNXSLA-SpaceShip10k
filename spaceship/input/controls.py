"""Gộp bàn phím và cử chỉ tay thành một ``ControlState`` cho mỗi tick.

Thiết kế cho ĐỠ MỎI TAY:
- Tự động bắn (mặc định): tay chỉ còn việc lái.
- Lòng bàn tay thả lỏng = lái; NẮM TAY = né chậm; CHỤM ngón cái + trỏ, giữ 0.5 giây = kỹ năng Nộ.
- Vùng điều khiển nhỏ quanh tư thế nghỉ (hiệu chỉnh được), độ nhạy chỉnh được.
- Mất tay lâu -> báo ``hand_lost`` để màn chơi tự tạm dừng.
Bàn phím luôn hoạt động song song (máy không có webcam vẫn chơi được).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import pygame

from spaceship import config
from spaceship.config import HEIGHT, TICK, WIDTH
from spaceship.input.gestures import Gesture, zone_around

KEYS_LEFT = (pygame.K_LEFT, pygame.K_a)
KEYS_RIGHT = (pygame.K_RIGHT, pygame.K_d)
KEYS_UP = (pygame.K_UP, pygame.K_w)
KEYS_DOWN = (pygame.K_DOWN, pygame.K_s)
KEYS_FIRE = (pygame.K_SPACE, pygame.K_j)
KEYS_NUKE = (pygame.K_n, pygame.K_k)
KEYS_FOCUS = (pygame.K_LSHIFT, pygame.K_RSHIFT)


@dataclass
class ControlState:
    move_x: float = 0.0                              # trục bàn phím -1..1
    move_y: float = 0.0
    target: Optional[Tuple[float, float]] = None     # vị trí tay trên màn hình (px)
    fire: bool = False
    nuke: bool = False
    focus: bool = False                              # né chậm
    source: str = "keyboard"                         # "keyboard" | "hand"
    gesture: Gesture = Gesture.NONE
    skill_progress: float = 0.0                      # 0..1 khi đang giữ chụm ngón
    hand_lost: bool = False                          # đang chơi bằng tay mà mất tay quá lâu
    hand_absent: float = 0.0                         # số giây đã mất tay


def _any(keys, group) -> bool:
    return any(keys[k] for k in group)


class ControlHub:
    def __init__(self, tracker=None, settings=None) -> None:
        self.tracker = tracker
        self.settings = settings
        self.hand_mode = False          # người chơi đang lái bằng tay?
        self.hand_absent = 0.0
        self._pinch_ticks = 0
        self.apply_settings()

    # --- Cài đặt ------------------------------------------------------------------------
    @property
    def auto_fire(self) -> bool:
        return True if self.settings is None else self.settings.auto_fire

    def zone(self) -> Tuple[float, float, float, float]:
        if self.settings is None:
            return zone_around(config.HAND_DEFAULT_CENTER, config.HAND_SENSITIVITY["medium"], config.HAND_ZONE_ASPECT)
        return zone_around(self.settings.center, self.settings.half_width, config.HAND_ZONE_ASPECT)

    def apply_settings(self) -> None:
        """Gửi vùng điều khiển mới cho luồng camera (gọi sau khi hiệu chỉnh / đổi độ nhạy)."""
        if self.tracker is not None:
            self.tracker.zone = self.zone()

    def reset_hand_mode(self) -> None:
        """Gọi khi bắt đầu ván mới: chỉ tự dừng nếu người chơi THỰC SỰ lái bằng tay trong ván này."""
        self.hand_mode = False
        self.hand_absent = 0.0
        self._pinch_ticks = 0

    def hand_reading(self):
        if self.tracker is None or getattr(self.tracker, "state", None) != "running":
            return None
        return self.tracker.reading

    # --- Mỗi tick -----------------------------------------------------------------------
    def poll(self, keys=None, *, allow_pinch_skill: bool = True) -> ControlState:
        keys = keys if keys is not None else pygame.key.get_pressed()
        move_x = float(_any(keys, KEYS_RIGHT)) - float(_any(keys, KEYS_LEFT))
        move_y = float(_any(keys, KEYS_DOWN)) - float(_any(keys, KEYS_UP))
        keyboard_moving = bool(move_x or move_y)
        state = ControlState(
            move_x=move_x,
            move_y=move_y,
            fire=self.auto_fire or _any(keys, KEYS_FIRE),
            nuke=_any(keys, KEYS_NUKE),
            focus=_any(keys, KEYS_FOCUS),
        )

        hand = self.hand_reading()
        if hand is not None and hand.detected:
            self.hand_absent = 0.0
            state.gesture = hand.gesture
            if not keyboard_moving:
                self.hand_mode = True
                state.target = (hand.x * WIDTH, hand.y * HEIGHT)
                state.source = "hand"
            if hand.gesture == Gesture.FIST:
                state.focus = True
            if not self.auto_fire and hand.gesture == Gesture.POINT:
                state.fire = True
            self._pinch_ticks = self._pinch_ticks + 1 if hand.gesture == Gesture.PINCH else 0
        else:
            self._pinch_ticks = 0
            if self.hand_mode:
                self.hand_absent += TICK

        if keyboard_moving:
            self.hand_mode = False
            self.hand_absent = 0.0

        hold_ticks = config.PINCH_HOLD_SECONDS * config.TICK_RATE
        state.skill_progress = min(1.0, self._pinch_ticks / hold_ticks)
        if allow_pinch_skill and state.skill_progress >= 1.0:
            state.nuke = True
        state.hand_absent = self.hand_absent
        state.hand_lost = self.hand_mode and self.hand_absent >= config.HAND_PAUSE_SECONDS
        return state
