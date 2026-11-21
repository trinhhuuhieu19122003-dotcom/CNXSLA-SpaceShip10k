"""Hiệu ứng phát sáng kiểu neon, vẽ sẵn một lần rồi dùng lại (cache).

Nguyên lý: mỗi "texture" là ảnh màu trên NỀN ĐEN, dán lên màn hình bằng phép
CỘNG màu (``BLEND_RGB_ADD``): chỗ đen cộng 0 nên vô hình, chỗ sáng cộng dồn
nên nhiều viên đạn chồng nhau sẽ càng chói, giống đèn neon.
Quầng mờ được làm bằng cách thu nhỏ rồi phóng to lại ảnh (nhanh, không cần thư viện).
"""
from __future__ import annotations

from typing import Dict, Tuple

import pygame

Color = Tuple[int, int, int]
_cache: Dict[tuple, pygame.Surface] = {}


def scale(color: Color, k: float) -> Color:
    return tuple(max(0, min(255, int(c * k))) for c in color)


def _blur(surface: pygame.Surface, factor: int) -> pygame.Surface:
    w, h = surface.get_size()
    small = pygame.transform.smoothscale(surface, (max(1, w // factor), max(1, h // factor)))
    return pygame.transform.smoothscale(small, (w, h))


def orb(color: Color, radius: int, core: float = 0.45, halo: float = 1.0) -> pygame.Surface:
    """Quả cầu sáng: quầng màu mờ bên ngoài, thân màu, lõi trắng."""
    radius = max(1, int(radius))
    key = ("orb", color, radius, core, halo)
    if key not in _cache:
        size = radius * 4
        s = pygame.Surface((size, size))
        c = size // 2
        if halo > 0:
            pygame.draw.circle(s, scale(color, 0.55 * halo), (c, c), int(radius * 1.7))
            s = _blur(s, 4)
        pygame.draw.circle(s, color, (c, c), radius)
        if core > 0:
            pygame.draw.circle(s, (255, 255, 255), (c, c), max(1, int(radius * core)))
        _cache[key] = s
    return _cache[key]


def streak(color: Color, length: int, width: int) -> pygame.Surface:
    """Vệt sáng dọc (thân laser): viên nang màu có quầng, lõi trắng mảnh ở giữa."""
    key = ("streak", color, length, width)
    if key not in _cache:
        pad = width * 2
        s = pygame.Surface((width + pad * 2, length + pad * 2))
        body = pygame.Rect(pad, pad, width, length)
        pygame.draw.rect(s, scale(color, 0.6), body.inflate(width, width), border_radius=width)
        s = _blur(s, 3)
        pygame.draw.rect(s, color, body, border_radius=width // 2)
        core = body.inflate(-max(2, width * 2 // 3), -2)
        pygame.draw.rect(s, (255, 255, 255), core, border_radius=max(1, core.width // 2))
        _cache[key] = s
    return _cache[key]


def beam(color: Color, width: int, length: int) -> pygame.Surface:
    """Tia laser dài (cấp 6): dải sáng dọc mờ dần ra hai bên."""
    key = ("beam", color, width, length)
    if key not in _cache:
        s = pygame.Surface((width * 3, length))
        cx = s.get_width() // 2
        for w, k in ((width * 3, 0.25), (width * 2, 0.45), (width, 0.85)):
            pygame.draw.rect(s, scale(color, k), (cx - w // 2, 0, w, length))
        s = _blur(s, 3)
        pygame.draw.rect(s, (255, 255, 255), (cx - max(2, width // 5), 0, max(4, width * 2 // 5), length))
        _cache[key] = s
    return _cache[key]


def add(surface: pygame.Surface, texture: pygame.Surface, center) -> None:
    surface.blit(texture, texture.get_rect(center=(int(center[0]), int(center[1]))),
                 special_flags=pygame.BLEND_RGB_ADD)


def glow_line(surface: pygame.Surface, color: Color, start, end, width: int) -> None:
    """Đường sáng không cần cache (dùng cho tia đạn địch đủ mọi góc)."""
    pygame.draw.line(surface, scale(color, 0.35), start, end, width * 2)
    pygame.draw.line(surface, color, start, end, width)
    pygame.draw.line(surface, (255, 255, 255), start, end, max(1, width // 3))


def clear_cache() -> None:
    _cache.clear()
