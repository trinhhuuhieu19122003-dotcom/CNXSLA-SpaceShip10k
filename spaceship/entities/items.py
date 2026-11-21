"""Vật phẩm rơi ra khi hạ địch.

Mỗi loại một HÌNH DẠNG riêng (không chỉ khác màu) để nhìn lướt cũng nhận ra
giữa màn đạn dày. Hộp súng KHÁC loại súng đang cầm thì nháy viền đỏ + dấu "!"
(ăn vào sẽ về cấp 1 - luật "cay cú" có chủ đích, nhưng phải được báo rõ).
"""
from __future__ import annotations

import math

import pygame

from spaceship.config import HEIGHT, HOMING_COLOR, LASER_COLOR, PLASMA_COLOR
from spaceship.ui import glow

WARN_RED = (255, 60, 60)

# kind -> màu viền / quầng sáng
ITEM_STYLES = {
    "heal": (60, 255, 120),
    "shield": (0, 240, 255),
    "upgrade_plasma": PLASMA_COLOR,
    "upgrade_laser": LASER_COLOR,
    "upgrade_homing": HOMING_COLOR,
    "upgrade_universal": (230, 230, 230),
    "upgrade_lightning": (255, 230, 60),
    "upgrade_drone": (255, 80, 220),
    "upgrade_burn": (255, 130, 30),
}
WEAPON_ITEMS = {"upgrade_plasma": "plasma", "upgrade_laser": "laser",
                "upgrade_homing": "homing", "upgrade_lightning": "lightning"}


class Item:
    SPEED = 3

    def __init__(self, x, y, kind: str) -> None:
        if kind not in ITEM_STYLES:
            raise ValueError(f"Vật phẩm không hợp lệ: {kind}")
        self.x, self.y, self.kind = x, y, kind
        self.age = 0

    @property
    def on_screen(self) -> bool:
        return self.y <= HEIGHT + 20

    def update(self) -> None:
        self.y += self.SPEED
        self.age += 1

    def warns(self, current_weapon: str) -> bool:
        """Ăn vào có làm mất cấp súng hiện tại không."""
        weapon = WEAPON_ITEMS.get(self.kind)
        return weapon is not None and weapon != current_weapon

    def draw(self, surface: pygame.Surface, assets, current_weapon: str = "") -> None:
        draw_item_icon(surface, assets, self.kind, self.x, self.y, t=self.age / 60,
                       warn=self.warns(current_weapon))


def _icon(surface: pygame.Surface, kind: str, cx: float, cy: float, k: float, t: float) -> None:
    """Hình biểu tượng bên trong hộp. ``k`` = hệ số kích thước (1.0 = hộp chuẩn)."""
    def p(dx, dy):
        return (cx + dx * k, cy + dy * k)

    color = ITEM_STYLES[kind]
    if kind == "heal":
        pygame.draw.rect(surface, color, (*p(-3, -9), 6 * k, 18 * k), border_radius=2)
        pygame.draw.rect(surface, color, (*p(-9, -3), 18 * k, 6 * k), border_radius=2)
    elif kind == "shield":
        pts = [p(9 * math.cos(math.radians(60 * i + 30)), 9 * math.sin(math.radians(60 * i + 30))) for i in range(6)]
        pygame.draw.polygon(surface, color, pts, max(2, int(2 * k)))
    elif kind == "upgrade_plasma":
        glow.add(surface, glow.orb(color, max(2, int(6 * k)), core=0.5, halo=0.6), (cx, cy))
    elif kind == "upgrade_laser":
        pygame.draw.polygon(surface, color, [p(0, -11), p(5, 0), p(0, 11), p(-5, 0)])
        pygame.draw.polygon(surface, (255, 220, 220), [p(0, -6), p(2, 0), p(0, 6), p(-2, 0)])
    elif kind == "upgrade_homing":
        for dy in (-4, 4):
            pygame.draw.polygon(surface, color, [p(0, -6 + dy), p(7, 2 + dy), p(0, -1 + dy), p(-7, 2 + dy)])
    elif kind == "upgrade_universal":
        for i, c in enumerate((PLASMA_COLOR, LASER_COLOR, HOMING_COLOR)):
            a = math.radians(120 * i - 90) + t * 2
            pygame.draw.circle(surface, c, p(6 * math.cos(a), 6 * math.sin(a)), max(2, int(4 * k)))
    elif kind == "upgrade_lightning":
        pygame.draw.polygon(surface, color, [p(2, -11), p(-5, 1), p(0, 1), p(-2, 11), p(5, -2), p(0, -2)])
    elif kind == "upgrade_drone":
        pygame.draw.polygon(surface, color, [p(0, -8), p(8, 6), p(0, 2), p(-8, 6)])
    elif kind == "upgrade_burn":
        pygame.draw.polygon(surface, (255, 80, 0), [p(-6, 7), p(0, -10), p(6, 7)])
        pygame.draw.polygon(surface, (255, 210, 60), [p(-3, 7), p(0, -3), p(3, 7)])


def draw_item_icon(surface: pygame.Surface, assets, kind: str, cx: float, cy: float,
                   t: float = 0.0, warn: bool = False, size: float = 1.0) -> None:
    """Hộp lục giác phát sáng. Dùng chung cho vật phẩm trong trận, HUD và bảng hướng dẫn."""
    color = ITEM_STYLES[kind]
    blink = warn and int(t * 6) % 2 == 0
    rim = WARN_RED if blink else color
    r = 16 * size
    pulse = 0.75 + 0.25 * math.sin(t * 5)
    glow.add(surface, glow.orb(glow.scale(rim, pulse), max(2, int(r * 0.8)), core=0.0, halo=1.0), (cx, cy))
    hexagon = [(cx + r * math.cos(math.radians(60 * i)), cy + r * math.sin(math.radians(60 * i))) for i in range(6)]
    pygame.draw.polygon(surface, (14, 18, 26), hexagon)
    pygame.draw.polygon(surface, rim, hexagon, 2)
    _icon(surface, kind, cx, cy, size, t)
    if warn:
        bx, by = cx + r * 0.85, cy - r * 0.85
        pygame.draw.circle(surface, WARN_RED, (int(bx), int(by)), int(7 * size))
        mark = assets.text("!", max(10, int(12 * size)), (255, 255, 255))
        surface.blit(mark, mark.get_rect(center=(int(bx), int(by))))
