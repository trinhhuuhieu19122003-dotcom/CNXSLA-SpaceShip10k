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
from spaceship.config import GRAY, HEIGHT, NEON_CYAN, NEON_RED, WHITE, WIDTH, YELLOW
from spaceship.core.scene import Scene
from spaceship.input.gestures import Gesture
from spaceship.ui.widgets import Button, blit_center, dim

BTN_W, BTN_H = 250, 50
HAND_BACK_TICKS = int(0.3 * config.TICK_RATE)    # tay phải xuất hiện ổn định 0.3 giây


class PauseScene(Scene):
    shows_camera = True

    def __init__(self, game, gameplay, reason: str = "manual") -> None:
        super().__init__(game)
        self.gameplay = gameplay
        self.reason = reason
        self.music = gameplay.music                  # giữ nguyên nhạc, không phát lại từ đầu
        self.countdown = 0                           # > 0: đang đếm ngược (tick còn lại)
        self.hand_seen_ticks = 0
        x = WIDTH // 2 - BTN_W // 2
        self.buttons = [
            Button("TIẾP TỤC", pygame.Rect(x, HEIGHT // 2 - 20, BTN_W, BTN_H), NEON_CYAN, "resume"),
            Button("QUAY LẠI MENU", pygame.Rect(x, HEIGHT // 2 + 50, BTN_W, BTN_H), NEON_RED, "menu"),
        ]

    @property
    def counting(self) -> bool:
        return self.countdown > 0

    def handle_event(self, event) -> None:
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_p):
            if self.counting:
                self.countdown = 0                   # đang đếm mà bấm lại -> dừng tiếp
            else:
                self._do("resume")
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and not self.counting:
            for button in self.buttons:
                if button.hovered(event.pos):
                    self._do(button.action)

    def _do(self, action: str) -> None:
        from spaceship.scenes.menu import MenuScene

        if action == "resume":
            self.countdown = int(config.RESUME_COUNTDOWN_SECONDS * config.TICK_RATE)
        else:
            self.game.change_scene(MenuScene(self.game))

    def update(self, controls) -> None:
        hand_visible = controls.gesture != Gesture.NONE
        if self.reason == "hand" and not self.counting:
            self.hand_seen_ticks = self.hand_seen_ticks + 1 if hand_visible else 0
            if self.hand_seen_ticks >= HAND_BACK_TICKS:
                self._do("resume")
        if self.counting:
            if self.reason == "hand" and not hand_visible and controls.hand_absent > 0.5:
                self.countdown = 0                   # lại bỏ tay xuống giữa lúc đếm -> chờ tiếp
                self.hand_seen_ticks = 0
                return
            self.countdown -= 1
            if self.countdown == 0:
                self.game.change_scene(self.gameplay)

    # --- Vẽ -----------------------------------------------------------------------------
    def draw(self, surface: pygame.Surface) -> None:
        a = self.game.assets
        self.gameplay.draw(surface)
        dim(surface)
        if self.counting:
            total = config.RESUME_COUNTDOWN_SECONDS * config.TICK_RATE
            number = max(1, math.ceil(self.countdown / total * 3))
            blit_center(surface, a.text(str(number), 120, YELLOW), HEIGHT // 2 - 90)
            blit_center(surface, a.text("Chuẩn bị...", 20, WHITE), HEIGHT // 2 + 60)
            return
        if self.reason == "hand":
            blit_center(surface, a.text("NGHỈ TAY", 60, WHITE), HEIGHT // 2 - 170)
            blit_center(surface, a.text("Đưa tay vào khung camera để chơi tiếp", 20, YELLOW), HEIGHT // 2 - 85)
            blit_center(surface, a.text("(game sẽ tự đếm 3-2-1)", 15, GRAY, bold=False), HEIGHT // 2 - 55)
        else:
            blit_center(surface, a.text("TẠM DỪNG", 60, WHITE), HEIGHT // 2 - 150)
        for button in self.buttons:
            button.draw(surface, a, self.game.mouse_pos)
