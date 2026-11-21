"""Màn kết quả sau mỗi ván (thắng/thua) kèm thống kê."""
from __future__ import annotations

import pygame

from spaceship.config import GRAY, HEIGHT, NEON_CYAN, NEON_GREEN, NEON_RED, WHITE, WIDTH, YELLOW
from spaceship.core.scene import Scene
from spaceship.core.storage import GameResult
from spaceship.ui.hud import format_time
from spaceship.ui.widgets import Button, blit_center, dim, draw_panel

INPUT_GRACE_TICKS = 45          # chặn click/phím vô tình ngay khi vừa thua


class ResultScene(Scene):
    music = None

    def __init__(self, game, gameplay, result: GameResult, new_record: bool) -> None:
        super().__init__(game)
        self.gameplay = gameplay
        self.result = result
        self.new_record = new_record
        self.ticks = 0
        x = WIDTH // 2 - 125
        self.buttons = [
            Button("CHƠI LẠI", pygame.Rect(x, HEIGHT // 2 + 110, 250, 46), NEON_CYAN, "retry", 22),
            Button("VỀ MENU", pygame.Rect(x, HEIGHT // 2 + 170, 250, 46), GRAY, "menu", 22),
        ]

    def handle_event(self, event) -> None:
        if self.ticks < INPUT_GRACE_TICKS:
            return
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_r):
                self._do("retry")
            elif event.key == pygame.K_ESCAPE:
                self._do("menu")
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for button in self.buttons:
                if button.hovered(event.pos):
                    self._do(button.action)

    def _do(self, action: str) -> None:
        from spaceship.scenes.gameplay import GameplayScene
        from spaceship.scenes.menu import MenuScene

        if action == "retry":
            self.game.change_scene(GameplayScene(self.game, self.result.mode))
        else:
            self.game.change_scene(MenuScene(self.game))

    def update(self, controls) -> None:
        self.ticks += 1
        self.game.starfield.update()

    def draw(self, surface: pygame.Surface) -> None:
        assets, r = self.game.assets, self.result
        self.gameplay.draw(surface)
        dim(surface, 170)
        panel = pygame.Rect(WIDTH // 2 - 260, HEIGHT // 2 - 190, 520, 430)
        draw_panel(surface, panel, NEON_GREEN if r.victory else NEON_RED)
        title = "VƯỢT ẢI THÀNH CÔNG" if r.victory else "THẤT BẠI"
        blit_center(surface, assets.text(title, 38, NEON_GREEN if r.victory else NEON_RED), panel.y + 20)
        blit_center(surface, assets.text(f"CHẾ ĐỘ {r.mode.label}", 18, GRAY), panel.y + 78)

        rows = [("ĐIỂM", str(r.score), YELLOW), ("QUÁI DIỆT", str(r.kills), WHITE),
                ("BOSS DIỆT", str(r.boss_kills), WHITE), ("THỜI GIAN", format_time(r.survival_time), WHITE)]
        for i, (label, value, color) in enumerate(rows):
            y = panel.y + 115 + i * 34
            surface.blit(assets.text(label, 20, GRAY), (panel.x + 60, y))
            val = assets.text(value, 20, color)
            surface.blit(val, (panel.right - 60 - val.get_width(), y))
        if self.new_record:
            blit_center(surface, assets.text("★ KỶ LỤC MỚI! ★", 22, YELLOW), panel.y + 255)
        for button in self.buttons:
            button.draw(surface, assets, self.game.mouse_pos)
