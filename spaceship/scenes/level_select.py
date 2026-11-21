"""Chọn ải: 10 ải chia 3 hồi, sao đã đạt, ải bị khóa, chọn độ khó."""
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
    Button, blit_center, draw_lock, draw_panel, draw_star, wrap_text,
)

CARD_W, CARD_H, GAP = 140, 150, 12
GRID_X = (WIDTH - (CARD_W * 5 + GAP * 4)) // 2
GRID_Y = 150
PANEL = pygame.Rect(14, 14, WIDTH - 28, 633)
LOCKED_FILL = (10, 15, 23, 240)


def card_rect(index: int) -> pygame.Rect:
    row, col = divmod(index, 5)
    return pygame.Rect(GRID_X + col * (CARD_W + GAP), GRID_Y + row * (CARD_H + 44), CARD_W, CARD_H)


class LevelSelectScene(Scene):
    music = "menu"

    def __init__(self, game) -> None:
        super().__init__(game)
        self.buttons = [
            Button("", pygame.Rect(WIDTH // 2 - 260, 600, 250, 44), "difficulty", 18),
            Button("VỀ MENU", pygame.Rect(WIDTH // 2 + 10, 600, 250, 44), "menu", 18),
        ]
        self.cards = [card_rect(i) for i in range(LEVEL_COUNT)]
        self.menu = MenuList(game, self.cards + [b.rect for b in self.buttons], self._activate)
        self._refresh()

    def _refresh(self) -> None:
        label = config.DIFFICULTY_LABELS[self.game.settings.difficulty]
        self.buttons[0].text = f"ĐỘ KHÓ: {label}"

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
            self.game.audio.play("beep")

    def _activate(self, index: int) -> None:
        if index < LEVEL_COUNT:
            self._start_level(index + 1)
        elif self.buttons[index - LEVEL_COUNT].action == "difficulty":
            self.game.settings.cycle_difficulty()
            self.game.settings.save()
            self._refresh()
        else:
            self._back()

    def handle_event(self, event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
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

    def draw(self, surface: pygame.Surface) -> None:
        a = self.game.assets
        surface.fill((0, 0, 0))
        self.game.starfield.draw(surface)
        draw_panel(surface, PANEL, header_height=109)
        blit_center(surface, a.text("CHẾ ĐỘ VƯỢT ẢI", 34, TEXT, role="display"), 20)
        stars = a.text(f"{self.game.save.total_stars} / {LEVEL_COUNT * 3}", 18, ACCENT, role="label")
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
