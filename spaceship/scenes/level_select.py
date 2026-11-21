"""Chọn ải: 10 ải chia 3 hồi, sao đã đạt, ải bị khóa, chọn độ khó, bắt đầu chu kỳ mới sau khi phá đảo."""
from __future__ import annotations

import pygame

from spaceship import config
from spaceship.campaign.levels import LEVEL_COUNT, LEVELS
from spaceship.campaign.story import ACTS
from spaceship.config import WIDTH
from spaceship.core.scene import Scene
from spaceship.ui.menu_list import MenuList
from spaceship.ui.widgets import (
    ACCENT, CORNER, DANGER, LOCKED, MUTED, PANEL_FILL, SECONDARY, SELECTED_FILL, TEXT,
    Button, blit_center, draw_lock, draw_panel, draw_star, fit_text, wrap_text,
)

CARD_W, CARD_H, GAP = 140, 150, 12
GRID_X = (WIDTH - (CARD_W * 5 + GAP * 4)) // 2
GRID_Y = 150
PANEL = pygame.Rect(14, 14, WIDTH - 28, 633)
LOCKED_FILL = (10, 15, 23, 240)
CONFIRM_TICKS = 240                    # nút CHU KỲ MỚI: chọn lần 2 trong 4 giây mới thực hiện


def card_rect(index: int) -> pygame.Rect:
    row, col = divmod(index, 5)
    return pygame.Rect(GRID_X + col * (CARD_W + GAP), GRID_Y + row * (CARD_H + 44), CARD_W, CARD_H)


class LevelSelectScene(Scene):
    music = "menu"

    def __init__(self, game) -> None:
        super().__init__(game)
        self.cards = [card_rect(i) for i in range(LEVEL_COUNT)]
        self.confirm = 0
        self._build_buttons()

    def _build_buttons(self) -> None:
        actions = ["difficulty", "menu"]
        if self.game.save.cycle_complete:
            actions.insert(1, "new_cycle")
        w, gap = (250, 20) if len(actions) == 2 else (236, 12)
        x = WIDTH // 2 - (w * len(actions) + gap * (len(actions) - 1)) // 2
        self.buttons = [Button("", pygame.Rect(x + i * (w + gap), 600, w, 44), action, 18)
                        for i, action in enumerate(actions)]
        self.menu = MenuList(self.game, self.cards + [b.rect for b in self.buttons], self._activate)
        self._refresh()

    def _refresh(self) -> None:
        label = config.DIFFICULTY_LABELS[self.game.settings.difficulty]
        texts = {"difficulty": f"ĐỘ KHÓ: {label}", "menu": "VỀ MENU",
                 "new_cycle": "CHẮC CHẮN? CHỌN LẦN NỮA" if self.confirm else f"CHU KỲ {self.game.save.cycle + 1}"}
        for button in self.buttons:
            button.text = texts[button.action]

    def _new_cycle(self) -> None:
        if not self.confirm:
            self.confirm = CONFIRM_TICKS
            self._refresh()
            return
        self.confirm = 0
        if self.game.save.start_new_cycle():
            self.game.audio.play("level_up")
            self._build_buttons()
            self.menu.select(0)

    def unlocked(self, number: int) -> bool:
        return number <= self.game.save.unlocked_level

    def _back(self) -> None:
        from spaceship.scenes.menu import MenuScene

        self.game.change_scene(MenuScene(self.game))

    def _start_level(self, number: int) -> None:
        from spaceship.scenes.flow import start_level

        if self.unlocked(number):
            start_level(self.game, number)
        else:
            self.game.audio.play("ui_back")

    def _activate(self, index: int) -> None:
        if index < LEVEL_COUNT:
            self._start_level(index + 1)
        elif self.buttons[index - LEVEL_COUNT].action == "difficulty":
            self.game.settings.cycle_difficulty()
            self.game.settings.save()
            self._refresh()
        elif self.buttons[index - LEVEL_COUNT].action == "new_cycle":
            self._new_cycle()
        else:
            self._back()

    def handle_event(self, event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.game.audio.play("ui_back")
                self._back()
                return
            if pygame.K_0 <= event.key <= pygame.K_9:
                number = 10 if event.key == pygame.K_0 else event.key - pygame.K_0
                self._start_level(number)
                return
        self.menu.handle_event(event)

    def update(self, controls) -> None:
        self.game.starfield.update()
        self.menu.update(controls)
        if self.confirm:
            on_button = (self.menu.selected >= LEVEL_COUNT
                         and self.buttons[self.menu.selected - LEVEL_COUNT].action == "new_cycle")
            self.confirm = self.confirm - 1 if on_button else 0
            if not self.confirm:
                self._refresh()

    def draw(self, surface: pygame.Surface) -> None:
        a = self.game.assets
        surface.fill((0, 0, 0))
        self.game.starfield.draw(surface)
        draw_panel(surface, PANEL, header_height=109)
        save = self.game.save
        blit_center(surface, a.text("CHẾ ĐỘ VƯỢT ẢI", 34, TEXT, role="display"), 20)
        cycle = f"   ·   CHU KỲ {save.cycle}" if save.cycle > 1 else ""
        stars = a.text(f"{save.total_stars} / {LEVEL_COUNT * 3}{cycle}", 18, ACCENT, role="label")
        star_rect = stars.get_rect(center=(WIDTH // 2 + 9, 79))
        surface.blit(stars, star_rect)
        draw_star(surface, (star_rect.x - 13, star_rect.centery), 8, True)
        acts = "   ·   ".join(ACTS[k] for k in (1, 2, 3))
        blit_center(surface, a.text(acts, 14, MUTED, role="label"), 97)
        for i, level in enumerate(LEVELS):
            self._draw_card(surface, i, level)
        if self.menu.selected < LEVEL_COUNT:
            level = LEVELS[self.menu.selected]
            hint = level.hint if self.unlocked(level.number) else "Qua ải trước để mở khóa"
            blit_center(surface, a.text(hint, 16, SECONDARY, role="body"), 529)
        elif self.buttons[self.menu.selected - LEVEL_COUNT].action == "new_cycle":
            hint = (f"Vòng lặp tín hiệu: chơi lại từ ải 1, địch mạnh hơn (+{round(config.CYCLE_HP_STEP * 100)}% máu "
                    "mỗi chu kỳ). Giữ nguyên Sổ tay, kỷ lục, Hỏa ngục.")
            blit_center(surface, fit_text(a, hint, 15, ACCENT, PANEL.width - 40, role="body"), 529)
        criteria = "1 sao: qua ải · 2 sao: mất tối đa 1 mạng · 3 sao: không mất mạng nào"
        blit_center(surface, a.text(criteria, 14, MUTED, role="body"), 559)
        for i, button in enumerate(self.buttons, LEVEL_COUNT):
            button.draw(surface, a, i == self.menu.selected)
        if self.menu.selected < LEVEL_COUNT:
            card = self.cards[self.menu.selected]
            self.menu.draw_progress(surface, (card.right - 14, card.bottom - 18))
        else:
            self.menu.draw_progress(surface)
        detail = "Độ khó: dễ = địch ít máu, bắn chậm, rơi nhiều đồ · khó = ngược lại"
        blit_center(surface, a.text(detail, 13, MUTED, role="body"), 660)

    def _draw_card(self, surface, index: int, level) -> None:
        a = self.game.assets
        rect = self.cards[index]
        unlocked = self.unlocked(level.number)
        selected = index == self.menu.selected
        corner = ACCENT if selected else CORNER if unlocked else LOCKED
        fill = SELECTED_FILL if selected else PANEL_FILL if unlocked else LOCKED_FILL
        draw_panel(surface, rect, corner, fill, header_height=36)

        color = ACCENT if selected else TEXT if unlocked else MUTED
        surface.blit(a.text(f"ẢI {level.number}", 21, color, role="ui"), (rect.x + 10, rect.y + 4))
        if level.boss:
            tag = a.text("MINI-BOSS" if level.boss in ("nest", "cruiser") else "BOSS", 11,
                         DANGER if unlocked else LOCKED, role="label")
            surface.blit(tag, tag.get_rect(midright=(rect.right - 10, rect.y + 18)))
        for j, row in enumerate(wrap_text(a, level.name, 14, rect.width - 20, role="ui")):
            surface.blit(a.text(row, 14, TEXT if unlocked else MUTED, role="ui"), (rect.x + 10, rect.y + 45 + j * 19))
        if not unlocked:
            label = a.text("KHÓA", 14, MUTED, role="label")
            surface.blit(label, label.get_rect(midleft=(rect.centerx - 13, rect.bottom - 23)))
            draw_lock(surface, (rect.centerx - 25, rect.bottom - 23))
            return
        stars = self.game.save.level_stars.get(level.number, 0)
        for s in range(3):
            draw_star(surface, (rect.centerx - 28 + s * 28, rect.bottom - 24), 10, s < stars)
