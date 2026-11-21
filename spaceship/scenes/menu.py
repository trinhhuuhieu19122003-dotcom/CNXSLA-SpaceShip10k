"""Menu chính."""
from __future__ import annotations

import math
from typing import List

import pygame

from spaceship.config import GRAY, HEIGHT, WIDTH, YELLOW, GameMode
from spaceship.core.scene import Scene
from spaceship.entities.effects import ShootingStar
from spaceship.ui.widgets import Button, blit_center

TITLE = "SPACESHIP 10K"
MAIN_W, MAIN_H, SUB_W, SUB_H = 340, 50, 280, 40
MODE_COLORS = {GameMode.CAMPAIGN: (0, 255, 255), GameMode.ENDLESS: (255, 255, 0), GameMode.INFERNO: (255, 100, 0)}


class MenuScene(Scene):
    music = "menu"

    def __init__(self, game) -> None:
        super().__init__(game)
        self.show_modes = False
        self.shooting_stars: List[ShootingStar] = []
        self.ticks = 0
        self.buttons: List[Button] = []
        self._layout()

    def _layout(self) -> None:
        entries = [("CÁC CHẾ ĐỘ CHƠI", (100, 150, 255), "toggle", True)]
        if self.show_modes:
            entries += [(f"CHẾ ĐỘ {m.label}", MODE_COLORS[m], f"mode:{m.value}", False) for m in GameMode]
        entries += [
            ("THÀNH TỰU", (255, 0, 255), "achievements", True),
            ("HƯỚNG DẪN CHƠI", (0, 255, 0), "how_to_play", True),
            ("THOÁT GAME", (128, 128, 128), "quit", True),
        ]
        self.buttons, y = [], 250
        for text, color, action, main in entries:
            w, h, size, gap = (MAIN_W, MAIN_H, 24, 15) if main else (SUB_W, SUB_H, 18, 10)
            arrow = ("up" if self.show_modes else "down") if action == "toggle" else None
            self.buttons.append(Button(text, pygame.Rect(WIDTH // 2 - w // 2, y, w, h), color, action, size, arrow))
            y += h + gap

    # --- Sự kiện ------------------------------------------------------------------------
    def handle_event(self, event) -> None:
        if event.type == pygame.KEYDOWN:
            shortcuts = {pygame.K_1: GameMode.CAMPAIGN, pygame.K_2: GameMode.ENDLESS, pygame.K_3: GameMode.INFERNO}
            if event.key in shortcuts:
                self._start(shortcuts[event.key])
            elif event.key == pygame.K_ESCAPE and self.show_modes:
                self.show_modes = False
                self._layout()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for button in self.buttons:
                if button.hovered(event.pos):
                    self._activate(button.action)
                    break

    def _activate(self, action: str) -> None:
        from spaceship.scenes.info import AchievementsScene, HowToPlayScene

        if action == "toggle":
            self.show_modes = not self.show_modes
            self._layout()
        elif action == "achievements":
            self.game.change_scene(AchievementsScene(self.game))
        elif action == "how_to_play":
            self.game.change_scene(HowToPlayScene(self.game))
        elif action == "quit":
            self.game.quit()
        elif action.startswith("mode:"):
            self._start(GameMode(action.split(":", 1)[1]))

    def _start(self, mode: GameMode) -> None:
        from spaceship.scenes.cutscene import CutsceneScene, INTRO_SCRIPT
        from spaceship.scenes.gameplay import GameplayScene

        if mode is GameMode.CAMPAIGN:
            self.game.change_scene(CutsceneScene(self.game, INTRO_SCRIPT, lambda: GameplayScene(self.game, mode)))
        else:
            self.game.change_scene(GameplayScene(self.game, mode))

    # --- Logic & vẽ ---------------------------------------------------------------------
    def update(self, controls) -> None:
        self.ticks += 1
        self.game.starfield.update()
        if self.game.rng.random() < 0.02:
            self.shooting_stars.append(ShootingStar(rng=self.game.rng))
        for star in self.shooting_stars:
            star.update()
        self.shooting_stars = [s for s in self.shooting_stars if s.alive]

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((0, 0, 0))
        self.game.starfield.draw(surface)
        for i in range(0, WIDTH, 50):
            pygame.draw.line(surface, (15, 20, 30), (i, 0), (i, HEIGHT))
        for i in range(0, HEIGHT, 50):
            pygame.draw.line(surface, (15, 20, 30), (0, i), (WIDTH, i))
        for star in self.shooting_stars:
            star.draw(surface)
        scan_y = (self.ticks * 8) % HEIGHT
        pygame.draw.line(surface, (0, 40, 40), (0, scan_y), (WIDTH, scan_y), 3)
        self._draw_title(surface)

        assets = self.game.assets
        blit_center(surface, assets.text(f"KỶ LỤC CAO NHẤT: {self.game.save.highscore}", 20, YELLOW), 205)
        mouse = self.game.mouse_pos
        for button in self.buttons:
            button.draw(surface, assets, mouse)
        hint = "Phím tắt: 1 Vượt ải · 2 Vô tận · 3 Hỏa ngục · F11 toàn màn hình · C ẩn/hiện camera"
        blit_center(surface, assets.text(hint, 13, GRAY, bold=False), HEIGHT - 30)

    def _draw_title(self, surface: pygame.Surface) -> None:
        font = self.game.assets.font(84)
        w, _ = font.size(TITLE)
        x, y = WIDTH // 2 - w // 2, 90
        surface.blit(font.render(TITLE, True, (0, 40, 40)), (x + 6, y + 6))
        pulse = (math.sin(self.ticks / 9.0) + 1) / 2
        glow = int(100 + 155 * pulse)
        glow_surf = font.render(TITLE, True, (0, int(glow * 0.8), glow))
        for ox, oy in ((-3, 0), (3, 0), (0, -3), (0, 3), (-2, -2), (2, 2), (-2, 2), (2, -2)):
            surface.blit(glow_surf, (x + ox, y + oy))
        surface.blit(font.render(TITLE, True, (200, 255, 255) if pulse > 0.5 else (150, 255, 255)), (x, y))
