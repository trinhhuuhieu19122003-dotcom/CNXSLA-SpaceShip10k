"""Điều hướng menu bằng phím, chuột và tay trong hệ tọa độ màn hình ảo."""
from __future__ import annotations

import pygame

from spaceship.input.gestures import Gesture
from spaceship.ui.widgets import draw_progress_ring

MOVE_KEYS = (pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT)
CONFIRM_KEYS = (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)
HAND_DEADBAND = 8


class MenuList:
    def __init__(self, game, rects, activate) -> None:
        self.game = game
        self._on_activate = activate
        self.progress = 0.0
        self._pinching = False
        self._hand_position = None
        self.set_rects(rects)

    def set_rects(self, rects, *, selected: int = 0) -> None:
        """Cập nhật bố cục mà vẫn giữ trạng thái tay đang điều khiển."""
        self.rects = tuple(rects)
        self.selected = selected
        rows: dict[int, list[int]] = {}
        for i, rect in enumerate(self.rects):
            rows.setdefault(rect.centery, []).append(i)
        self._rows = [sorted(rows[y], key=lambda i: self.rects[i].centerx) for y in sorted(rows)]

    @classmethod
    def for_buttons(cls, game, buttons, activate) -> MenuList:
        return cls(game, (b.rect for b in buttons), lambda i: activate(buttons[i].action))

    def activate(self, index: int) -> None:
        self.game.audio.play("ui_select")
        self._on_activate(index)

    def select(self, index: int) -> None:
        if index != self.selected:
            self.selected = index
            self.game.audio.play("ui_move")

    def _nearest_column(self, row, x):
        return min(row, key=lambda i: abs(self.rects[i].centerx - x))

    def _move(self, key) -> None:
        row_index = next(i for i, row in enumerate(self._rows) if self.selected in row)
        row = self._rows[row_index]
        if key in (pygame.K_UP, pygame.K_DOWN):
            step = 1 if key == pygame.K_DOWN else -1
            target = self._rows[(row_index + step) % len(self._rows)]
            self.select(self._nearest_column(target, self.rects[self.selected].centerx))
        else:
            step = 1 if key == pygame.K_RIGHT else -1
            self.select(row[(row.index(self.selected) + step) % len(row)])

    def handle_event(self, event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in MOVE_KEYS:
                self._move(event.key)
            elif event.key in CONFIRM_KEYS:
                self.activate(self.selected)
        elif event.type == pygame.MOUSEMOTION or (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1):
            if event.pos is None:
                return
            for index, rect in enumerate(self.rects):
                if rect.collidepoint(event.pos):
                    self.select(index)
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        self.activate(index)
                    return

    def update(self, controls, *, enabled: bool = True) -> None:
        pinching = controls.gesture is Gesture.PINCH
        if controls.gesture not in (Gesture.NONE, Gesture.PINCH):
            self.game.menu_pinch_consumed = False
        target = controls.target
        if target is None and controls.gesture is Gesture.NONE:
            self._hand_position = None
        # Khóa mục trong khi chụm. Tay đứng yên không đổi mục vừa chọn bằng phím hoặc chuột.
        can_aim = not pinching or not (self._pinching or self.game.menu_pinch_consumed)
        if enabled and target is not None and can_aim:
            previous = self._hand_position
            if previous is None or max(abs(target[0] - previous[0]), abs(target[1] - previous[1])) >= HAND_DEADBAND:
                self._hand_position = target
                row = min(self._rows, key=lambda indices: abs(self.rects[indices[0]].centery - target[1]))
                self.select(self._nearest_column(row, target[0]))
        self._pinching = pinching
        self.progress = 0.0
        if enabled and pinching and target is not None:
            self.progress = 1.0 if self.game.menu_pinch_consumed else controls.skill_progress
        if pinching and controls.skill_progress >= 1.0 and not self.game.menu_pinch_consumed:
            self.game.menu_pinch_consumed = True
            if enabled and target is not None:
                self.activate(self.selected)

    def draw_progress(self, surface: pygame.Surface, center=None) -> None:
        if self.progress > 0:
            rect = self.rects[self.selected]
            draw_progress_ring(surface, center or (rect.right + 13, rect.centery), 8, self.progress)
