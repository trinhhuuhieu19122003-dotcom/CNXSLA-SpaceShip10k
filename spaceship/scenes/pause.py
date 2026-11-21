"""Tạm dừng: vẽ đè lên màn chơi đang đóng băng.

Hai lý do dừng:
- ``manual``: bấm ESC/P hoặc rời cửa sổ.
- ``hand``: đang lái bằng tay mà bỏ tay xuống -> dừng để nghỉ tay.
  Đưa tay vào khung lại là tự đếm 3-2-1 rồi chơi tiếp, không cần bấm gì.
Chơi tiếp luôn có đếm ngược để người chơi kịp đặt tay/ngón vào vị trí.
"""
from __future__ import annotations

import math

import pygame

from spaceship import config
from spaceship.config import HEIGHT, WIDTH
from spaceship.core.scene import Scene
from spaceship.input.gestures import Gesture
from spaceship.ui.menu_list import MenuList
from spaceship.ui.widgets import ACCENT, MUTED, SECONDARY, TEXT, Button, blit_center, dim, draw_panel

BTN_W, BTN_H = 250, 50
PANEL = pygame.Rect(WIDTH // 2 - 215, HEIGHT // 2 - 178, 430, 314)
HAND_BACK_TICKS = int(0.3 * config.TICK_RATE)    # tay phải xuất hiện ổn định 0.3 giây


class PauseScene(Scene):
    shows_camera = True
    sidebars = True                  # màn rộng: giữ 2 bảng bên của trận đang dừng

    def __init__(self, game, gameplay, reason: str = "manual") -> None:
        super().__init__(game)
        self.gameplay = gameplay
        self.reason = reason
        self.music = gameplay.music                  # giữ nguyên nhạc, không phát lại từ đầu
        self.countdown = 0                           # > 0: đang đếm ngược (tick còn lại)
        self.hand_seen_ticks = 0
        self._auto_resume = False
        x = WIDTH // 2 - BTN_W // 2
        self.buttons = [
            Button("TIẾP TỤC", pygame.Rect(x, HEIGHT // 2 - 20, BTN_W, BTN_H), "resume"),
            Button("QUAY LẠI MENU", pygame.Rect(x, HEIGHT // 2 + 50, BTN_W, BTN_H), "menu"),
        ]
        self.menu = MenuList.for_buttons(game, self.buttons, self._do)

    @property
    def counting(self) -> bool:
        return self.countdown > 0

    def handle_event(self, event) -> None:
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_p):
            if self.counting:
                self._cancel_countdown()
            else:
                self._do("resume")
        elif not self.counting:
            self.menu.handle_event(event)

    def _do(self, action: str) -> None:
        from spaceship.scenes.menu import MenuScene

        if action == "resume":
            self.countdown = int(config.RESUME_COUNTDOWN_SECONDS * config.TICK_RATE)
            self._auto_resume = False
            self.game.audio.play("ui_move")
        else:
            self.game.change_scene(MenuScene(self.game))

    def _cancel_countdown(self) -> None:
        self.countdown = 0
        self.hand_seen_ticks = 0
        self._auto_resume = False

    def _count_number(self) -> int:
        total = config.RESUME_COUNTDOWN_SECONDS * config.TICK_RATE
        return max(1, math.ceil(self.countdown / total * 3))

    def update(self, controls) -> None:
        self.game.audio.duck()                       # nhạc nhỏ lại khi tạm dừng
        pinching = controls.gesture is Gesture.PINCH
        if self.counting and self._auto_resume and pinching and controls.target is not None:
            # Một lần chụm chủ ý có thể ngắt đếm tự động để dùng menu.
            if not self.game.menu_pinch_consumed:
                self._cancel_countdown()
        self.menu.update(controls, enabled=not self.counting)
        hand_visible = controls.gesture is not Gesture.NONE
        if self.reason == "hand" and not self.counting:
            self.hand_seen_ticks = self.hand_seen_ticks + 1 if hand_visible and not pinching else 0
            if self.hand_seen_ticks >= HAND_BACK_TICKS:
                self._do("resume")
                self._auto_resume = True
        if self.counting:
            if self.reason == "hand" and not hand_visible and controls.hand_absent > 0.5:
                self._cancel_countdown()
                return
            before = self._count_number()
            self.countdown -= 1
            if self.countdown and self._count_number() != before:
                self.game.audio.play("ui_move")
            if self.countdown == 0:
                self.game.change_scene(self.gameplay)

    # --- Vẽ -----------------------------------------------------------------------------
    def draw_sidebars(self, surface, left, right) -> None:
        self.gameplay.draw_sidebars(surface, left, right)

    def draw(self, surface: pygame.Surface) -> None:
        a = self.game.assets
        self.gameplay.draw(surface)
        dim(surface)
        draw_panel(surface, PANEL, header_height=68)
        if self.counting:
            total = config.RESUME_COUNTDOWN_SECONDS * config.TICK_RATE
            number = max(1, math.ceil(self.countdown / total * 3))
            blit_center(surface, a.text("TIẾP TỤC", 36, TEXT, role="display"), PANEL.y + 10)
            blit_center(surface, a.text(str(number), 112, ACCENT, role="display"), HEIGHT // 2 - 104)
            blit_center(surface, a.text("Chuẩn bị...", 20, SECONDARY, role="body"), HEIGHT // 2 + 62)
            return
        title = "NGHỈ TAY" if self.reason == "hand" else "TẠM DỪNG"
        blit_center(surface, a.text(title, 40, TEXT, role="display"), PANEL.y + 8)
        if self.reason == "hand":
            blit_center(surface, a.text("Đưa tay vào khung camera để chơi tiếp", 18, SECONDARY, role="body"),
                        HEIGHT // 2 - 87)
            blit_center(surface, a.text("(game sẽ tự đếm 3-2-1)", 15, MUTED, role="body"), HEIGHT // 2 - 55)
        for i, button in enumerate(self.buttons):
            button.draw(surface, a, i == self.menu.selected)
        self.menu.draw_progress(surface)
