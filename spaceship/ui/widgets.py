"""Nút bấm và panel phong cách sci-fi.

``Button`` tự nhớ vị trí của nó nên scene chỉ cần hỏi ``button.clicked(pos)``,
không phải tự tính lại hình chữ nhật ở hai nơi như bản cũ.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import pygame

from spaceship.config import GRAY, NEON_CYAN, WHITE, WIDTH

Color = Tuple[int, int, int]


@dataclass
class Button:
    text: str
    rect: pygame.Rect
    color: Color
    action: str
    font_size: int = 24
    arrow: Optional[str] = None          # "up" | "down" | None

    def hovered(self, pos) -> bool:
        return pos is not None and self.rect.collidepoint(pos)

    def draw(self, surface: pygame.Surface, assets, mouse_pos) -> None:
        draw_button(surface, assets, self.text, self.rect, self.color, self.hovered(mouse_pos), self.arrow, self.font_size)


def _octagon(rect: pygame.Rect, cut: int):
    x, y, w, h = rect
    return [(x + cut, y), (x + w - cut, y), (x + w, y + cut), (x + w, y + h - cut),
            (x + w - cut, y + h), (x + cut, y + h), (x, y + h - cut), (x, y + cut)]


def draw_button(surface, assets, text: str, rect: pygame.Rect, color: Color, hover: bool,
                arrow: Optional[str] = None, font_size: int = 24) -> None:
    box = rect.inflate(20, 10) if hover else rect
    points = _octagon(box, 15 if rect.height > 40 else 10)
    if hover:
        for i in range(3, 0, -1):
            glow = tuple(max(0, c - i * 50) for c in color)
            pygame.draw.polygon(surface, glow, [(px, py + i * 2) for px, py in points])
    pygame.draw.polygon(surface, (25, 30, 40) if hover else (10, 15, 20), points)
    pygame.draw.polygon(surface, color, points, 2)
    if hover:
        pygame.draw.rect(surface, color, (box.x - 8, box.centery - 6, 4, 12))
        pygame.draw.rect(surface, color, (box.right + 4, box.centery - 6, 4, 12))

    fg = WHITE if hover else color
    label = assets.text(text, font_size, fg)
    tx = box.centerx - label.get_width() // 2 - (15 if arrow else 0)
    surface.blit(label, (tx, box.centery - label.get_height() // 2))
    if arrow:
        ax, ay = box.right - 25, box.centery
        if arrow == "down":
            pygame.draw.polygon(surface, fg, [(ax - 6, ay - 3), (ax + 6, ay - 3), (ax, ay + 4)])
        else:
            pygame.draw.polygon(surface, fg, [(ax - 6, ay + 3), (ax + 6, ay + 3), (ax, ay - 4)])


def draw_panel(surface: pygame.Surface, rect: pygame.Rect, border: Color = NEON_CYAN, fill=(12, 17, 25)) -> None:
    pygame.draw.rect(surface, fill, rect, border_radius=8)
    pygame.draw.rect(surface, border, rect, 2, border_radius=8)


def blit_center(surface: pygame.Surface, image: pygame.Surface, y: int, x: int = WIDTH // 2) -> None:
    surface.blit(image, (x - image.get_width() // 2, y))


def draw_back_hint(surface: pygame.Surface, assets, y: int) -> None:
    blit_center(surface, assets.text("[ CLICK CHUỘT HOẶC ESC ĐỂ VỀ MENU ]", 16, GRAY), y)


def dim(surface: pygame.Surface, alpha: int = 150) -> None:
    overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, alpha))
    surface.blit(overlay, (0, 0))
