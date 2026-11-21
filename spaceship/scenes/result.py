"""Màn kết quả sau mỗi ván / mỗi ải (thắng, thua, phá đảo) kèm thống kê và số sao."""
from __future__ import annotations

from typing import List, Optional

import pygame

from spaceship.campaign.levels import LEVEL_COUNT
from spaceship.config import GRAY, HEIGHT, NEON_CYAN, NEON_GREEN, NEON_ORANGE, NEON_RED, WHITE, WIDTH, YELLOW
from spaceship.core.scene import Scene
from spaceship.core.storage import GameResult
from spaceship.scenes.level_select import draw_star
from spaceship.ui.hud import format_time
from spaceship.ui.widgets import Button, blit_center, dim, draw_panel

INPUT_GRACE_TICKS = 45          # chặn click/phím vô tình ngay khi vừa thua
PANEL = pygame.Rect(WIDTH // 2 - 260, HEIGHT // 2 - 230, 520, 480)


class ResultScene(Scene):
    music = None

    def __init__(self, game, gameplay, result: GameResult, new_record: bool, level: Optional[int] = None,
                 stars: int = 0, loadout: Optional[dict] = None, ending: bool = False) -> None:
        super().__init__(game)
        self.gameplay = gameplay
        self.result = result
        self.new_record = new_record
        self.level, self.stars, self.loadout, self.ending = level, stars, loadout, ending
        self.ticks = 0
        self.buttons = self._make_buttons()

    def _make_buttons(self) -> List[Button]:
        r = self.result
        if self.level is None:
            actions = [("CHƠI LẠI", NEON_CYAN, "retry"), ("VỀ MENU", GRAY, "menu")]
        elif self.ending:
            actions = [("CHỌN ẢI", NEON_CYAN, "levels"), ("VỀ MENU", GRAY, "menu")]
        elif r.victory:
            actions = [("ẢI TIẾP THEO", NEON_GREEN, "next"), ("CHỌN ẢI", NEON_CYAN, "levels"), ("VỀ MENU", GRAY, "menu")]
        else:
            actions = [("CHƠI LẠI ẢI", NEON_CYAN, "retry"), ("CHỌN ẢI", NEON_CYAN, "levels"), ("VỀ MENU", GRAY, "menu")]
        buttons, y = [], PANEL.bottom - 58 * len(actions) - 4
        for text, color, action in actions:
            buttons.append(Button(text, pygame.Rect(WIDTH // 2 - 125, y, 250, 44), color, action, 20))
            y += 56
        return buttons

    def handle_event(self, event) -> None:
        if self.ticks < INPUT_GRACE_TICKS:
            return
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_r):
                self._do(self.buttons[0].action)
            elif event.key == pygame.K_ESCAPE:
                self._do("menu")
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for button in self.buttons:
                if button.hovered(event.pos):
                    self._do(button.action)

    def _do(self, action: str) -> None:
        from spaceship.scenes.flow import start_level, start_survival
        from spaceship.scenes.level_select import LevelSelectScene
        from spaceship.scenes.menu import MenuScene

        game = self.game
        if action == "retry":
            if self.level is None:
                start_survival(game, self.result.mode)
            else:
                start_level(game, self.level)
        elif action == "next":
            start_level(game, min(LEVEL_COUNT, self.level + 1), self.loadout)
        elif action == "levels":
            game.change_scene(LevelSelectScene(game))
        else:
            game.change_scene(MenuScene(game))

    def update(self, controls) -> None:
        self.ticks += 1
        self.game.starfield.update()

    # --- Vẽ -----------------------------------------------------------------------------
    def _title(self):
        r = self.result
        if self.ending:
            return "PHÁ ĐẢO!", NEON_ORANGE
        if self.level is not None:
            return (f"QUA ẢI {self.level}!", NEON_GREEN) if r.victory else ("THẤT BẠI", NEON_RED)
        return ("CHIẾN THẮNG", NEON_GREEN) if r.victory else ("THẤT BẠI", NEON_RED)

    def draw(self, surface: pygame.Surface) -> None:
        a, r = self.game.assets, self.result
        self.gameplay.draw(surface)
        dim(surface, 170)
        title, color = self._title()
        draw_panel(surface, PANEL, color)
        blit_center(surface, a.text(title, 40, color), PANEL.y + 18)
        sub = f"ẢI {self.level} · ĐỘ KHÓ {self._difficulty()}" if self.level else f"CHẾ ĐỘ {r.mode.label}"
        blit_center(surface, a.text(sub, 16, GRAY), PANEL.y + 72)

        y = PANEL.y + 100
        if self.level is not None and r.victory:
            for s in range(3):
                draw_star(surface, (WIDTH // 2 - 50 + s * 50, y + 20), 20, s < self.stars)
            y += 52
        rows = [("ĐIỂM", str(r.score), YELLOW), ("QUÁI DIỆT", str(r.kills), WHITE),
                ("BOSS DIỆT", str(r.boss_kills), WHITE), ("THỜI GIAN", format_time(r.survival_time), WHITE)]
        for i, (label, value, c) in enumerate(rows):
            ry = y + i * 30
            surface.blit(a.text(label, 18, GRAY), (PANEL.x + 70, ry))
            val = a.text(value, 18, c)
            surface.blit(val, (PANEL.right - 70 - val.get_width(), ry))
        y += len(rows) * 30 + 6
        if self.ending:
            blit_center(surface, a.text("Đã mở khóa: CHẾ ĐỘ HỎA NGỤC", 18, NEON_ORANGE), y)
        elif self.new_record:
            blit_center(surface, a.text("★ KỶ LỤC MỚI! ★", 20, YELLOW), y)
        for button in self.buttons:
            button.draw(surface, a, self.game.mouse_pos)

    def _difficulty(self) -> str:
        from spaceship import config
        return config.DIFFICULTY_LABELS[self.game.settings.difficulty]

