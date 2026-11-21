"""Tạm dừng: vẽ đè lên màn chơi đang đóng băng."""
from __future__ import annotations

import pygame

from spaceship.config import HEIGHT, NEON_CYAN, NEON_RED, WHITE, WIDTH
from spaceship.core.scene import Scene
from spaceship.ui.widgets import Button, blit_center, dim

BTN_W, BTN_H = 250, 50


class PauseScene(Scene):
    shows_camera = True

    def __init__(self, game, gameplay) -> None:
        super().__init__(game)
        self.gameplay = gameplay
        self.music = gameplay.music                  # giữ nguyên nhạc, không phát lại từ đầu
        x = WIDTH // 2 - BTN_W // 2
        self.buttons = [
            Button("TIẾP TỤC", pygame.Rect(x, HEIGHT // 2 - 20, BTN_W, BTN_H), NEON_CYAN, "resume"),
            Button("QUAY LẠI MENU", pygame.Rect(x, HEIGHT // 2 + 50, BTN_W, BTN_H), NEON_RED, "menu"),
        ]

    def handle_event(self, event) -> None:
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_p):
            self._do("resume")
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for button in self.buttons:
                if button.hovered(event.pos):
                    self._do(button.action)

    def _do(self, action: str) -> None:
        from spaceship.scenes.menu import MenuScene

        if action == "resume":
            self.game.change_scene(self.gameplay)
        else:
            self.game.change_scene(MenuScene(self.game))

    def draw(self, surface: pygame.Surface) -> None:
        self.gameplay.draw(surface)
        dim(surface)
        blit_center(surface, self.game.assets.text("TẠM DỪNG", 60, WHITE), HEIGHT // 2 - 150)
        for button in self.buttons:
            button.draw(surface, self.game.assets, self.game.mouse_pos)
