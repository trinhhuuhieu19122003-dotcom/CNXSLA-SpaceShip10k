"""Gộp điều khiển bàn phím và cử chỉ tay thành một ``ControlState`` cho mỗi tick.

Bàn phím luôn hoạt động, nên máy không có webcam vẫn chơi được (bản cũ thì
con tàu đứng im mãi).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import pygame

from spaceship.config import HEIGHT, WIDTH
from spaceship.input.gestures import Gesture
from spaceship.input.hand_tracker import HandTracker

KEYS_LEFT = (pygame.K_LEFT, pygame.K_a)
KEYS_RIGHT = (pygame.K_RIGHT, pygame.K_d)
KEYS_UP = (pygame.K_UP, pygame.K_w)
KEYS_DOWN = (pygame.K_DOWN, pygame.K_s)
KEYS_FIRE = (pygame.K_SPACE, pygame.K_j)
KEYS_NUKE = (pygame.K_n, pygame.K_k)


@dataclass
class ControlState:
    move_x: float = 0.0                              # trục bàn phím -1..1
    move_y: float = 0.0
    target: Optional[Tuple[float, float]] = None     # vị trí tay trên màn hình (px)
    fire: bool = False
    nuke: bool = False
    source: str = "keyboard"                         # "keyboard" | "hand"


def _any(keys, group) -> bool:
    return any(keys[k] for k in group)


class ControlHub:
    def __init__(self, tracker: Optional[HandTracker] = None) -> None:
        self.tracker = tracker

    def poll(self, keys=None) -> ControlState:
        keys = keys if keys is not None else pygame.key.get_pressed()
        state = ControlState(
            move_x=float(_any(keys, KEYS_RIGHT)) - float(_any(keys, KEYS_LEFT)),
            move_y=float(_any(keys, KEYS_DOWN)) - float(_any(keys, KEYS_UP)),
            fire=_any(keys, KEYS_FIRE),
            nuke=_any(keys, KEYS_NUKE),
        )
        hand = self.tracker.reading if self.tracker else None
        if hand is not None and hand.detected:
            state.fire = state.fire or hand.gesture == Gesture.POINT
            state.nuke = state.nuke or hand.gesture == Gesture.THREE
            if state.move_x == 0 and state.move_y == 0:   # đang bấm phím thì ưu tiên phím
                state.target = (hand.x * WIDTH, hand.y * HEIGHT)
                state.source = "hand"
        return state
