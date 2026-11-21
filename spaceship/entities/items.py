"""Vật phẩm rơi ra khi hạ địch."""
from __future__ import annotations

import pygame

from spaceship.config import HEIGHT, HOMING_COLOR, LASER_COLOR, PLASMA_COLOR, WHITE

# kind -> (màu, ký hiệu). Ký hiệu None = vẽ hình mũi tên nâng cấp vũ khí.
ITEM_STYLES = {
    "heal": ((0, 255, 0), "+"),
    "shield": ((0, 255, 255), "S"),
    "upgrade_plasma": (PLASMA_COLOR, None),
    "upgrade_laser": (LASER_COLOR, None),
    "upgrade_homing": (HOMING_COLOR, None),
    "upgrade_universal": (WHITE, None),
    "upgrade_drone": ((255, 0, 255), "D"),
    "upgrade_burn": ((255, 100, 0), "B"),
}


class Item:
    SPEED = 3

    def __init__(self, x, y, kind: str) -> None:
        if kind not in ITEM_STYLES:
            raise ValueError(f"Vật phẩm không hợp lệ: {kind}")
        self.x, self.y, self.kind = x, y, kind

    @property
    def on_screen(self) -> bool:
        return self.y <= HEIGHT

    def update(self) -> None:
        self.y += self.SPEED

    def draw(self, surface: pygame.Surface, assets) -> None:
        draw_item_icon(surface, assets, self.kind, self.x, self.y)


def draw_item_icon(surface: pygame.Surface, assets, kind: str, cx: float, cy: float) -> None:
    """Dùng chung cho vật phẩm trong game và bảng hướng dẫn."""
    box = pygame.Rect(cx - 12, cy - 12, 24, 24)
    pygame.draw.rect(surface, (20, 25, 30), box)
    color, char = ITEM_STYLES[kind]
    pygame.draw.rect(surface, color, box, 2, border_radius=4)
    if kind == "upgrade_universal":
        pygame.draw.circle(surface, PLASMA_COLOR, (int(cx - 5), int(cy + 4)), 4)
        pygame.draw.circle(surface, LASER_COLOR, (int(cx), int(cy - 4)), 4)
        pygame.draw.circle(surface, HOMING_COLOR, (int(cx + 5), int(cy + 4)), 4)
    elif char is None:
        pygame.draw.polygon(surface, color, [(cx, cy - 6), (cx - 6, cy + 2), (cx + 6, cy + 2)])
        pygame.draw.rect(surface, color, (cx - 2, cy + 2, 4, 6))
    else:
        txt = assets.text(char, 16, color)
        surface.blit(txt, (cx - txt.get_width() // 2, cy - txt.get_height() // 2))
