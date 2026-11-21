"""Chọn ải: 10 ải chia 3 hồi, sao đã đạt, ải bị khóa, chọn độ khó."""
from __future__ import annotations

import pygame

from spaceship import config
from spaceship.campaign.levels import LEVEL_COUNT, LEVELS
from spaceship.campaign.story import ACTS
from spaceship.config import GRAY, NEON_CYAN, NEON_ORANGE, NEON_RED, WHITE, WIDTH, YELLOW
from spaceship.core.scene import Scene
from spaceship.ui.hud import wrap_text
from spaceship.ui.widgets import Button, blit_center

ACT_COLORS = {1: NEON_CYAN, 2: (255, 80, 160), 3: NEON_ORANGE}
CARD_W, CARD_H, GAP = 140, 150, 12
GRID_X = (WIDTH - (CARD_W * 5 + GAP * 4)) // 2
GRID_Y = 150


def card_rect(index: int) -> pygame.Rect:
    row, col = divmod(index, 5)
    return pygame.Rect(GRID_X + col * (CARD_W + GAP), GRID_Y + row * (CARD_H + 44), CARD_W, CARD_H)


def draw_star(surface, center, r: int, filled: bool) -> None:
    import math
    pts = []
    for i in range(10):
        rad = r if i % 2 == 0 else r * 0.45
        ang = math.radians(-90 + i * 36)
        pts.append((center[0] + math.cos(ang) * rad, center[1] + math.sin(ang) * rad))
    if filled:
        pygame.draw.polygon(surface, YELLOW, pts)
    else:
        pygame.draw.polygon(surface, (70, 70, 80), pts, 2)


class LevelSelectScene(Scene):
    music = "menu"

    def __init__(self, game) -> None:
        super().__init__(game)
        self.buttons = [
            Button("", pygame.Rect(WIDTH // 2 - 260, 600, 250, 44), NEON_CYAN, "difficulty", 18),
            Button("VỀ MENU", pygame.Rect(WIDTH // 2 + 10, 600, 250, 44), GRAY, "menu", 18),
        ]
        self.hover = None
        self._refresh()

    def _refresh(self) -> None:
        label = config.DIFFICULTY_LABELS[self.game.settings.difficulty]
        self.buttons[0].text = f"ĐỘ KHÓ: {label}"

    def unlocked(self, number: int) -> bool:
        return number <= self.game.save.unlocked_level

    def handle_event(self, event) -> None:
        from spaceship.scenes.flow import start_level
        from spaceship.scenes.menu import MenuScene

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.game.change_scene(MenuScene(self.game))
            elif pygame.K_1 <= event.key <= pygame.K_9 or event.key == pygame.K_0:
                number = 10 if event.key == pygame.K_0 else event.key - pygame.K_0
                if self.unlocked(number):
                    start_level(self.game, number)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and event.pos is not None:
            for i in range(LEVEL_COUNT):
                if card_rect(i).collidepoint(event.pos) and self.unlocked(i + 1):
                    return start_level(self.game, i + 1)
            for button in self.buttons:
                if button.hovered(event.pos):
                    if button.action == "difficulty":
                        self.game.settings.cycle_difficulty()
                        self.game.settings.save()
                        self._refresh()
                    else:
                        self.game.change_scene(MenuScene(self.game))

    def update(self, controls) -> None:
        self.game.starfield.update()
        mouse = self.game.mouse_pos
        self.hover = next((i for i in range(LEVEL_COUNT) if mouse and card_rect(i).collidepoint(mouse)), None)

    def draw(self, surface: pygame.Surface) -> None:
        a = self.game.assets
        surface.fill((0, 0, 0))
        self.game.starfield.draw(surface)
        blit_center(surface, a.text("CHẾ ĐỘ VƯỢT ẢI", 34, YELLOW), 22)
        save = self.game.save
        blit_center(surface, a.text(f"★ {save.total_stars} / {LEVEL_COUNT * 3}", 18, YELLOW), 66)
        acts = "   ·   ".join(ACTS[k] for k in (1, 2, 3))
        blit_center(surface, a.text(acts, 13, GRAY, bold=False), 98)
        for i, level in enumerate(LEVELS):
            self._draw_card(surface, i, level)
        hint = ""
        if self.hover is not None:
            level = LEVELS[self.hover]
            hint = level.hint if self.unlocked(level.number) else "Qua ải trước để mở khóa"
        else:
            hint = "1 sao: qua ải · 2 sao: mất tối đa 1 mạng · 3 sao: không mất mạng nào"
        blit_center(surface, a.text(hint, 15, WHITE, bold=False), 548)
        for button in self.buttons:
            button.draw(surface, a, self.game.mouse_pos)
        blit_center(surface, a.text("Độ khó: DỄ = địch ít máu, bắn chậm, rơi nhiều đồ · KHÓ = ngược lại", 12, GRAY, bold=False), 660)

    def _draw_card(self, surface, index: int, level) -> None:
        a = self.game.assets
        rect = card_rect(index)
        open_ = self.unlocked(level.number)
        color = ACT_COLORS[level.act] if open_ else (60, 60, 70)
        hover = index == self.hover and open_
        box = rect.inflate(8, 8) if hover else rect
        pygame.draw.rect(surface, (22, 28, 40) if hover else (12, 16, 24), box, border_radius=10)
        pygame.draw.rect(surface, color, box, 2, border_radius=10)
        surface.blit(a.text(f"ẢI {level.number}", 22, color), (box.x + 12, box.y + 10))
        if level.boss:
            tag = a.text("MINI-BOSS" if level.boss in ("nest", "cruiser") else "BOSS", 11, NEON_RED)
            surface.blit(tag, (box.right - tag.get_width() - 10, box.y + 16))
        for j, row in enumerate(wrap_text(a, level.name, 14, box.width - 20, bold=True)[:3]):
            surface.blit(a.text(row, 14, WHITE if open_ else GRAY), (box.x + 12, box.y + 46 + j * 19))
        if not open_:
            label = a.text("KHÓA", 16, GRAY)
            surface.blit(label, (box.centerx - label.get_width() // 2, box.bottom - 34))
            return
        stars = self.game.save.level_stars.get(level.number, 0)
        for s in range(3):
            draw_star(surface, (box.centerx - 30 + s * 30, box.bottom - 24), 11, s < stars)
