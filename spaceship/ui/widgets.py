"""Font chữ, panel và biểu tượng dùng chung giữa các màn hình."""
from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache
from unicodedata import normalize

import pygame

from spaceship.config import WIDTH

ACCENT = (0, 220, 255)
DANGER = (247, 104, 111)
TEXT = (231, 239, 246)
SECONDARY = (186, 202, 215)
MUTED = (150, 168, 185)
LOCKED = (115, 126, 142)
FRAME = (40, 61, 76)
CORNER = (89, 141, 162)
PANEL_FILL = (10, 17, 27, 235)
PANEL_HEADER = (17, 32, 45, 243)
SELECTED_FILL = (9, 40, 53, 245)


@dataclass
class Button:
    text: str
    rect: pygame.Rect
    action: str
    font_size: int = 22

    def draw(self, surface: pygame.Surface, assets, selected: bool = False) -> None:
        color = ACCENT if selected else TEXT
        draw_panel(surface, self.rect, ACCENT if selected else CORNER,
                   SELECTED_FILL if selected else PANEL_FILL)
        label = fit_text(assets, self.text, self.font_size, color, self.rect.width - 24, role="ui")
        surface.blit(label, label.get_rect(center=self.rect.center))


@lru_cache(maxsize=64)
def _panel(size, corner, fill, header_height):
    panel = pygame.Surface(size, pygame.SRCALPHA)
    panel.fill(fill)
    w, h = size
    if header_height:
        pygame.draw.rect(panel, PANEL_HEADER, (0, 0, w, header_height))
        pygame.draw.line(panel, FRAME, (1, header_height), (w - 2, header_height))
    pygame.draw.rect(panel, FRAME, panel.get_rect(), 1)
    length = min(12, w // 4, h // 4)
    for x, dx in ((1, 1), (w - 2, -1)):
        for y, dy in ((1, 1), (h - 2, -1)):
            pygame.draw.lines(panel, corner, False, ((x + dx * length, y), (x, y), (x, y + dy * length)), 2)
    return panel


def draw_panel(surface, rect: pygame.Rect, corner=CORNER, fill=PANEL_FILL, *, header_height: int = 0) -> None:
    surface.blit(_panel(rect.size, corner, fill, header_height), rect)


def blit_center(surface: pygame.Surface, image: pygame.Surface, y: int, x: int = WIDTH // 2) -> None:
    surface.blit(image, (x - image.get_width() // 2, y))


def fit_text(assets, text: str, size: int, color, width: int, *, role: str) -> pygame.Surface:
    image = assets.text(text, size, color, role=role)
    while image.get_width() > width and size > 1:
        size = max(1, min(size - 1, size * width // image.get_width()))
        image = assets.text(text, size, color, role=role)
    return image


def wrap_text(assets, text: str, size: int, width: int, *, role: str = "body") -> list[str]:
    """Ngắt dòng theo bề rộng của chính font dùng để vẽ."""
    font = assets.font(size, role=role)
    rows, current = [], ""
    for word in normalize("NFC", text).split():
        trial = f"{current} {word}".strip()
        if current and font.size(trial)[0] > width:
            rows.append(current)
            current = word
        else:
            current = trial
    if current:
        rows.append(current)
    return rows


def draw_star(surface, center, radius: int, filled: bool, *, color=ACCENT) -> None:
    points = []
    for i in range(10):
        r = radius if i % 2 == 0 else radius * 0.45
        angle = -math.pi / 2 + i * math.tau / 10
        points.append((center[0] + math.cos(angle) * r, center[1] + math.sin(angle) * r))
    pygame.draw.polygon(surface, color if filled else CORNER, points, 0 if filled else 1)


def draw_lock(surface, center, color=LOCKED) -> None:
    x, y = center
    pygame.draw.arc(surface, color, (x - 4, y - 8, 9, 10), 0, math.pi, 1)
    pygame.draw.line(surface, color, (x - 4, y - 3), (x - 4, y - 1))
    pygame.draw.line(surface, color, (x + 4, y - 3), (x + 4, y - 1))
    pygame.draw.rect(surface, color, (x - 6, y - 1, 13, 9), 1, border_radius=1)
    pygame.draw.line(surface, color, (x, y + 2), (x, y + 5))


def draw_progress_ring(surface, center, radius: int, progress: float, *, color=ACCENT, stroke: int = 2) -> None:
    pygame.draw.circle(surface, FRAME, center, radius, stroke)
    if progress >= 1:
        pygame.draw.circle(surface, color, center, radius, stroke)
    elif progress > 0:
        rect = pygame.Rect(0, 0, radius * 2, radius * 2)
        rect.center = center
        pygame.draw.arc(surface, color, rect, math.pi / 2 - progress * math.tau, math.pi / 2, stroke)


def draw_back_hint(surface: pygame.Surface, assets, y: int) -> None:
    blit_center(surface, assets.text("CLICK / CHỤM TAY / ENTER / ESC · VỀ MENU", 14, MUTED, role="label"), y)


@lru_cache(maxsize=8)
def _shade(size, alpha):
    overlay = pygame.Surface(size, pygame.SRCALPHA)
    overlay.fill((0, 0, 0, alpha))
    return overlay


def dim(surface: pygame.Surface, alpha: int = 150) -> None:
    surface.blit(_shade(surface.get_size(), alpha), (0, 0))
