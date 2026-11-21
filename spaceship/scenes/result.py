"""Màn kết quả sau mỗi ván / mỗi ải (thắng, thua, phá đảo) kèm thống kê và số sao."""
from __future__ import annotations

from typing import List, Optional

import pygame

from spaceship.campaign.levels import LEVEL_COUNT
from spaceship.config import HEIGHT, WIDTH, YELLOW
from spaceship.core.scene import Scene
from spaceship.core.storage import GameResult
from spaceship.ui import glow
from spaceship.ui.hud import format_time
from spaceship.ui.menu_list import MenuList
from spaceship.ui.widgets import ACCENT, DANGER, MUTED, SECONDARY, TEXT, Button, blit_center, dim, draw_panel, draw_star, fit_text

INPUT_GRACE_TICKS = 45          # chặn click/phím vô tình ngay khi vừa thua
PANEL = pygame.Rect(WIDTH // 2 - 260, HEIGHT // 2 - 270, 520, 560)
STAR_START, STAR_GAP = 20, 14     # sao bật lên lần lượt (tick)
COUNT_TICKS = 45                  # điểm/số liệu đếm tăng dần trong ~0,75 giây
BADGES_AT = STAR_START + 3 * STAR_GAP + 12


class ResultScene(Scene):
    music = None

    def __init__(self, game, gameplay, result: GameResult, new_record: bool, level: Optional[int] = None,
                 stars: int = 0, loadout: Optional[dict] = None, ending: bool = False) -> None:
        super().__init__(game)
        self.gameplay = gameplay
        self.result = result
        self.new_record = new_record
        self.board_rank = self._board_rank(game, result)
        self.level, self.stars, self.loadout, self.ending = level, stars, loadout, ending
        self.music = "ending" if ending else None      # đoạn kết: giữ nhạc kết thúc
        self._jingle_played = False
        self.ticks = 0
        self.buttons = self._make_buttons()
        self.menu = MenuList.for_buttons(game, self.buttons, self._do)

    @staticmethod
    def _board_rank(game, result: GameResult) -> Optional[int]:
        """Hạng của ván này trong Bảng điểm (chỉ khi đúng là ván vừa ghi)."""
        rank = getattr(game.save, "last_rank", None)
        runs = game.save.modes[result.mode].top_runs
        if rank is None or rank >= len(runs) or runs[rank].get("score") != result.score:
            return None
        return rank

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
        if self.level is not None and self.result.victory:
            for s in range(self.stars):                         # mỗi sao bật lên kèm một tiếng
                if self.ticks == STAR_START + s * STAR_GAP:
                    self.game.audio.play("ui_select")
        if self.ticks == BADGES_AT and getattr(self.gameplay, "new_achievements", None):
            self.game.audio.play("level_up")

    # --- Vẽ -----------------------------------------------------------------------------
    def _draw_badges(self, surface, a, earned, y: int) -> None:
        from spaceship.scenes.info import BADGE_COLOR, draw_badge_icon

        shown = earned[:3]
        w, gap = 150, 10
        x = WIDTH // 2 - (len(shown) * w + (len(shown) - 1) * gap) // 2
        label = a.text("HUY HIỆU MỚI" + (f"  (+{len(earned) - 3})" if len(earned) > 3 else ""), 13, YELLOW, role="label")
        surface.blit(label, label.get_rect(midbottom=(WIDTH // 2, y - 4)))
        for i, item in enumerate(shown):
            card = pygame.Rect(x + i * (w + gap), y, w, 46)
            draw_panel(surface, card, BADGE_COLOR)
            draw_badge_icon(surface, item.icon, (card.x + 22, card.centery), BADGE_COLOR, r=15)
            name = fit_text(a, item.name, 13, TEXT, w - 48, role="ui")
            surface.blit(name, name.get_rect(midleft=(card.x + 42, card.centery)))

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
                center = (WIDTH // 2 - 44 + s * 44, y + 12)
                shown = s < self.stars and self.ticks >= STAR_START + s * STAR_GAP
                if shown:
                    k = max(0.0, 1 - (self.ticks - STAR_START - s * STAR_GAP) / 9)
                    if k > 0:
                        glow.add(surface, glow.orb(glow.scale(ACCENT, 0.7 * k), 22, core=0.0), center)
                    draw_star(surface, center, int(17 * (1 + 0.45 * k)), True)
                else:
                    draw_star(surface, center, 17, False)
            y += 42
        f = min(1.0, self.ticks / COUNT_TICKS)                     # số liệu đếm tăng dần
        kills = str(round(r.kills * f))
        best = getattr(getattr(self.gameplay, "world", None), "best_combo", 0)
        if best >= 2:
            kills += f" · chuỗi {best}"                           # chuỗi hạ liên tiếp dài nhất
        rows = [("ĐIỂM", f"{round(r.score * f):,}".replace(",", " "), ACCENT), ("QUÁI DIỆT", kills, TEXT),
                ("BOSS DIỆT", str(round(r.boss_kills * f)), TEXT), ("THỜI GIAN", format_time(r.survival_time * f), TEXT)]
        for i, (label, value, c) in enumerate(rows):
            ry = y + i * 26
            surface.blit(a.text(label, 17, SECONDARY, role="label"), (PANEL.x + 70, ry))
            val = fit_text(a, value, 18, c, 185, role="ui")
            surface.blit(val, (PANEL.right - 70 - val.get_width(), ry))
        y += len(rows) * 26 + 6
        if self.ending:
            unlock = "Đã mở Hỏa ngục · " if self.game.save.cycle == 1 else ""
            text = f"{unlock}Chu kỳ {self.game.save.cycle + 1} đã mở ở màn Chọn ải"
            blit_center(surface, fit_text(a, text, 17, ACCENT, PANEL.width - 40, role="body"), y)
        elif self.new_record:
            record = a.text("KỶ LỤC MỚI!", 18, ACCENT, role="ui")
            rect = record.get_rect(midtop=(WIDTH // 2, y))
            surface.blit(record, rect)
            draw_star(surface, (rect.left - 16, rect.centery), 7, True)
            draw_star(surface, (rect.right + 16, rect.centery), 7, True)
        elif self.board_rank is not None:                     # lọt Bảng điểm của chế độ này
            text = f"HẠNG {self.board_rank + 1} BẢNG ĐIỂM {self.result.mode.label.upper()}"
            blit_center(surface, fit_text(a, text, 16, SECONDARY, PANEL.width - 60, role="ui"), y)
        earned = getattr(self.gameplay, "new_achievements", [])
        if earned and self.ticks >= BADGES_AT:                 # huy hiệu đạt trong ván này: thẻ có biểu tượng
            self._draw_badges(surface, a, earned, y + 52)
        for i, button in enumerate(self.buttons):
            button.draw(surface, a, i == self.menu.selected)
        self.menu.draw_progress(surface)

    def _difficulty(self) -> str:
        from spaceship import config
        return config.DIFFICULTY_LABELS[self.game.settings.difficulty]

