"""Thanh trượt âm lượng Nhạc nền / Hiệu ứng, dùng chung cho màn Cài đặt và màn Tạm dừng.

Chỉnh bằng: chuột (bấm vào thanh để nhảy tới, giữ rồi kéo), phím trái/phải (±5%), tay (chụm ngón rồi di ngang
như nắm núm kéo - lúc đó không tính là "bấm" mục). Thả chuột/thả tay thì lưu settings.json.
"""
from __future__ import annotations

from typing import Optional, Sequence

import pygame

from spaceship.input.gestures import Gesture
from spaceship.ui.widgets import (
    ACCENT, CORNER, PANEL_FILL, SECONDARY, SELECTED_FILL, TEXT, Button, draw_panel, fit_text,
)

VOLUMES = {"music": "music_volume", "sfx": "sfx_volume"}
STEP = 0.05
LABEL_W, VALUE_W = 170, 64


class VolumeSliders:
    def __init__(self, game, buttons: Sequence[Button]) -> None:
        self.game = game
        self.buttons = buttons
        self.mouse_drag: Optional[str] = None
        self.hand_drag: Optional[str] = None

    # --- Hình học & giá trị --------------------------------------------------------------
    @staticmethod
    def track(button: Button) -> pygame.Rect:
        r = button.rect
        return pygame.Rect(r.x + LABEL_W, r.centery - 3, r.width - LABEL_W - VALUE_W, 6)

    def _slider(self, action: str) -> Button:
        return next(b for b in self.buttons if b.action == action)

    def _at(self, pos) -> Optional[Button]:
        if pos is None:
            return None
        return next((b for b in self.buttons if b.action in VOLUMES and b.rect.collidepoint(pos)), None)

    def set_volume(self, action: str, value: float, *, save: bool) -> None:
        s = self.game.settings
        key = VOLUMES[action]
        value = min(1.0, max(0.0, round(value * 20) / 20))          # bước 5%
        changed = abs(getattr(s, key) - value) > 1e-6
        setattr(s, key, value)
        self.game.audio.set_volumes(s.music_volume, s.sfx_volume)
        if changed and action == "sfx":
            self.game.audio.play("ui_move")                          # nghe thử ngay mức vừa chỉnh
        if save:
            s.save()

    def set_from_x(self, button: Button, x: int, *, save: bool = False) -> None:
        track = self.track(button)
        self.set_volume(button.action, (x - track.x) / track.width, save=save)

    def step(self, action: str, delta: float, wrap: bool = False) -> None:
        value = getattr(self.game.settings, VOLUMES[action]) + delta
        if wrap and value > 1.0 + 1e-6:
            value = 0.0
        self.set_volume(action, value, save=True)

    # --- Nhập liệu -----------------------------------------------------------------------
    def handle_event(self, event, menu) -> bool:
        """Xử lý chuột/phím cho thanh trượt. Trả về True nếu đã dùng sự kiện (scene không cần xử lý tiếp)."""
        if event.type == pygame.MOUSEBUTTONDOWN and getattr(event, "button", 0) == 1 and self._at(event.pos):
            button = self._at(event.pos)
            menu.select(self.buttons.index(button))
            self.mouse_drag = button.action
            self.set_from_x(button, event.pos[0])
            return True
        if event.type == pygame.MOUSEMOTION and self.mouse_drag and event.pos is not None:
            self.set_from_x(self._slider(self.mouse_drag), event.pos[0])
            return True
        if event.type == pygame.MOUSEBUTTONUP and self.mouse_drag:
            self.mouse_drag = None
            self.game.settings.save()
            return True
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_LEFT, pygame.K_RIGHT):
            action = self.buttons[menu.selected].action
            if action in VOLUMES:
                self.step(action, STEP if event.key == pygame.K_RIGHT else -STEP)
                return True
        return False

    def before_menu_update(self, controls, menu) -> None:
        """Gọi TRƯỚC menu.update: chụm tay trên thanh trượt thì kéo núm theo tay."""
        pinching = controls.gesture is Gesture.PINCH and controls.target is not None
        if self.game.settings.hand_menu and pinching and not self.hand_drag:
            # chỉ "nắm núm" khi tay đang nằm ngay trên hàng thanh trượt (không dựa vào mục đang chọn)
            y = controls.target[1]
            row = next((b for b in self.buttons if b.action in VOLUMES and abs(y - b.rect.centery) <= b.rect.height * 0.6),
                       None)
            if row is not None:
                self.hand_drag = row.action
                menu.select(self.buttons.index(row))
        if self.game.settings.hand_menu and pinching and self.hand_drag:
            self.game.menu_pinch_consumed = True                     # không tính là "bấm" mục
            self.set_from_x(self._slider(self.hand_drag), controls.target[0])
        elif self.hand_drag:
            self.hand_drag = None
            self.game.settings.save()

    def after_menu_update(self, menu) -> None:
        if self.hand_drag:
            menu.progress = 0.0

    # --- Vẽ ------------------------------------------------------------------------------
    def draw(self, surface, assets, button: Button, selected: bool) -> None:
        value = getattr(self.game.settings, VOLUMES[button.action])
        r = button.rect
        draw_panel(surface, r, ACCENT if selected else CORNER, SELECTED_FILL if selected else PANEL_FILL)
        color = ACCENT if selected else TEXT
        label = fit_text(assets, button.text, 20, color, LABEL_W - 28, role="ui")
        surface.blit(label, label.get_rect(midleft=(r.x + 20, r.centery)))
        track = self.track(button)
        pygame.draw.rect(surface, (30, 38, 50), track, border_radius=3)
        filled = pygame.Rect(track.x, track.y, round(track.width * value), track.height)
        pygame.draw.rect(surface, ACCENT if selected else SECONDARY, filled, border_radius=3)
        knob = (track.x + round(track.width * value), track.centery)
        dragging = button.action in (self.mouse_drag, self.hand_drag)
        pygame.draw.circle(surface, (11, 20, 30), knob, 11 if dragging else 9)
        pygame.draw.circle(surface, ACCENT if selected else TEXT, knob, 11 if dragging else 9, 3)
        percent = assets.text(f"{round(value * 100)}%", 18, color, role="ui")
        surface.blit(percent, percent.get_rect(midright=(r.right - 16, r.centery)))
