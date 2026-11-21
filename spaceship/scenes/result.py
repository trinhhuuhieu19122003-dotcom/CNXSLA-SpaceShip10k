"""Màn kết quả sau mỗi ván / mỗi ải (thắng, thua, phá đảo) kèm thống kê và số sao."""
from __future__ import annotations

from typing import List, Optional

import pygame

from spaceship.campaign.levels import LEVEL_COUNT
from spaceship.config import HEIGHT, WIDTH
from spaceship.core.scene import Scene
from spaceship.core.storage import GameResult
from spaceship.ui.hud import format_time
from spaceship.ui.menu_list import MenuList
from spaceship.ui.widgets import ACCENT, DANGER, MUTED, SECONDARY, TEXT, Button, blit_center, dim, draw_panel, draw_star, fit_text

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
        self.music = "ending" if ending else None      # đoạn kết: giữ nhạc kết thúc
        self._jingle_played = False
        self.ticks = 0
        self.buttons = self._make_buttons()
        self.menu = MenuList.for_buttons(game, self.buttons, self._do)

    def on_enter(self) -> None:
        if not self._jingle_played:                   # không phát lại khi quay về từ màn khác
            self._jingle_played = True
            self.game.audio.play("victory" if self.result.victory else "defeat")

    def _make_buttons(self) -> List[Button]:
        r = self.result
        if self.level is None:
            actions = [("CHƠI LẠI", "retry"), ("VỀ MENU", "menu")]
        elif self.ending:
            actions = [("CHỌN ẢI", "levels"), ("VỀ MENU", "menu")]
        elif r.victory:
            actions = [("ẢI TIẾP THEO", "next"), ("CHỌN ẢI", "levels"), ("VỀ MENU", "menu")]
        else:
            actions = [("CHƠI LẠI ẢI", "retry"), ("CHỌN ẢI", "levels"), ("VỀ MENU", "menu")]
        buttons, y = [], PANEL.bottom - 58 * len(actions) - 4
        for text, action in actions:
            buttons.append(Button(text, pygame.Rect(WIDTH // 2 - 125, y, 250, 44), action, 20))
            y += 56
        return buttons

    def handle_event(self, event) -> None:
        if self.ticks < INPUT_GRACE_TICKS:
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r:
                self._do(self.buttons[0].action)
                return
            elif event.key == pygame.K_ESCAPE:
                self.game.audio.play("ui_back")
                self._do("menu")
                return
        self.menu.handle_event(event)

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
        self.menu.update(controls, enabled=self.ticks >= INPUT_GRACE_TICKS)
        self.ticks += 1
        self.game.starfield.update()

    # --- Vẽ -----------------------------------------------------------------------------
    def _title(self):
        r = self.result
        if self.ending:
            return "PHÁ ĐẢO!", ACCENT
        if self.level is not None:
            return (f"QUA ẢI {self.level}!", ACCENT) if r.victory else ("THẤT BẠI", DANGER)
        return ("CHIẾN THẮNG", ACCENT) if r.victory else ("THẤT BẠI", DANGER)

    def draw(self, surface: pygame.Surface) -> None:
        a, r = self.game.assets, self.result
        self.gameplay.draw(surface)
        dim(surface, 170)
        title, color = self._title()
        draw_panel(surface, PANEL, color, header_height=92)
        blit_center(surface, a.text(title, 40, color, role="display"), PANEL.y + 10)
        sub = f"ẢI {self.level} · ĐỘ KHÓ {self._difficulty()}" if self.level else f"CHẾ ĐỘ {r.mode.label}"
        blit_center(surface, a.text(sub, 16, MUTED, role="label"), PANEL.y + 62)

        y = PANEL.y + 112
        if self.level is not None and r.victory:
            for s in range(3):
                draw_star(surface, (WIDTH // 2 - 44 + s * 44, y + 12), 17, s < self.stars)
            y += 42
        rows = [("ĐIỂM", str(r.score), ACCENT), ("QUÁI DIỆT", str(r.kills), TEXT),
                ("BOSS DIỆT", str(r.boss_kills), TEXT), ("THỜI GIAN", format_time(r.survival_time), TEXT)]
        for i, (label, value, c) in enumerate(rows):
            ry = y + i * 26
            surface.blit(a.text(label, 17, SECONDARY, role="label"), (PANEL.x + 70, ry))
            val = fit_text(a, value, 18, c, 185, role="ui")
            surface.blit(val, (PANEL.right - 70 - val.get_width(), ry))
        y += len(rows) * 26 + 6
        if self.ending:
            blit_center(surface, a.text("Đã mở khóa chế độ Hỏa ngục", 18, ACCENT, role="body"), y)
        elif self.new_record:
            record = a.text("KỶ LỤC MỚI!", 18, ACCENT, role="ui")
            rect = record.get_rect(midtop=(WIDTH // 2, y))
            surface.blit(record, rect)
            draw_star(surface, (rect.left - 16, rect.centery), 7, True)
            draw_star(surface, (rect.right + 16, rect.centery), 7, True)
        for i, button in enumerate(self.buttons):
            button.draw(surface, a, i == self.menu.selected)
        self.menu.draw_progress(surface)

    def _difficulty(self) -> str:
        from spaceship import config
        return config.DIFFICULTY_LABELS[self.game.settings.difficulty]

