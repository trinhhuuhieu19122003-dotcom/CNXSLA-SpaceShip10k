"""Hiệu ứng phát sáng kiểu neon, vẽ sẵn một lần rồi dùng lại (cache).

Nguyên lý: mỗi "texture" là ảnh màu trên NỀN ĐEN, dán lên màn hình bằng phép
CỘNG màu (``BLEND_RGB_ADD``): chỗ đen cộng 0 nên vô hình, chỗ sáng cộng dồn
nên nhiều viên đạn chồng nhau sẽ càng chói, giống đèn neon.
Quầng mờ được làm bằng cách thu nhỏ rồi phóng to lại ảnh (nhanh, không cần thư viện).
"""
from __future__ import annotations

import random
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


blur = _blur        # dùng ngoài module (vd. quầng tia sét)


def glyph_halo(text: pygame.Surface) -> pygame.Surface:
    """Quầng sáng theo nét chữ, để dán bên dưới mặt chữ bằng hàm add."""
    padding = 18
    texture = pygame.Surface((text.get_width() + 2 * padding, text.get_height() + 2 * padding))
    texture.fill((0, 0, 0))
    texture.blit(text, (padding, padding))
    halo = _blur(texture, 10)
    halo.fill((135, 135, 135), special_flags=pygame.BLEND_RGB_MULT)
    tight = _blur(texture, 4)
    tight.fill((144, 144, 144), special_flags=pygame.BLEND_RGB_MULT)
    halo.blit(tight, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
    return halo


def soft_halo(color: Color, radius: int) -> pygame.Surface:
    """Quầng sáng giảm dần từ tâm, dùng cho động cơ trong menu."""
    key = ("soft_halo", color, radius)
    if key not in _cache:
        texture = pygame.Surface((2 * radius + 1, 2 * radius + 1))
        for r in range(radius, 0, -1):
            strength = (1 - r / radius) ** 2
            pygame.draw.circle(texture, scale(color, strength), (radius, radius), r)
        _cache[key] = texture
    return _cache[key]


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


NOVA_BASE = 160          # bán kính gốc của ảnh vòng nổ; khi vẽ sẽ phóng theo bán kính thật


def nova(color: Color) -> pygame.Surface:
    """Đĩa nổ plasma: lòng sáng mờ, càng ra mép càng chói, quầng mờ bên ngoài (vẽ sẵn 1 lần)."""
    key = ("nova", color)
    if key not in _cache:
        R = NOVA_BASE
        pad = R // 5
        size = 2 * (R + pad)
        c = size // 2
        s = pygame.Surface((size, size))
        pygame.draw.circle(s, scale(color, 0.5), (c, c), R + pad // 2)          # quầng ngoài (sẽ được làm mờ)
        for r in range(R, 0, -2):                                             # lòng: mờ ở giữa, sáng dần ra mép
            t = r / R
            pygame.draw.circle(s, scale(color, 0.14 + 0.86 * t ** 6), (c, c), r)
        _cache[key] = _blur(s, 3)          # viền sắc được vẽ riêng mỗi khung (xem PlasmaNova.draw)
    return _cache[key]


def add_scaled(surface: pygame.Surface, texture: pygame.Surface, center, radius: int, k: float = 1.0,
               base: int = NOVA_BASE, shrink: int = 4) -> None:
    """Phóng ``texture`` (vẽ cho bán kính ``base``) tới ``radius`` rồi cộng sáng, nhân độ sáng ``k``.

    Ảnh vốn rất mờ nên chỉ làm mượt ở 1/``shrink`` kích thước rồi phóng lên kiểu điểm ảnh (rẻ hơn hàng chục
    lần, mắt không phân biệt được); chỉ phần nằm trong màn hình mới được phóng và dán."""
    if radius <= 0 or k <= 0:
        return
    small = max(1, int(texture.get_width() * radius / base) // shrink)
    img = pygame.transform.smoothscale(texture, (small, small))
    if k < 0.99:
        v = int(255 * max(0.0, min(1.0, k)))
        img.fill((v, v, v), special_flags=pygame.BLEND_RGB_MULT)
    size = small * shrink
    left, top = int(center[0]) - size // 2, int(center[1]) - size // 2
    visible = pygame.Rect(left, top, size, size).clip(surface.get_rect())
    if visible.w <= 0 or visible.h <= 0:
        return
    x0, y0 = (visible.x - left) // shrink, (visible.y - top) // shrink
    x1, y1 = -(-(visible.right - left) // shrink), -(-(visible.bottom - top) // shrink)
    src = pygame.Rect(x0, y0, x1 - x0, y1 - y0).clip(img.get_rect())
    if src.w <= 0 or src.h <= 0:
        return
    part = pygame.transform.scale(img.subsurface(src), (src.w * shrink, src.h * shrink))
    surface.blit(part, (left + src.x * shrink, top + src.y * shrink), special_flags=pygame.BLEND_RGB_ADD)


def tint(surface: pygame.Surface, color: Color) -> None:
    """Ám màu cả màn bằng phép cộng sáng (dán một tấm màu đặc đã cache: nhanh hơn fill có cờ ~20 lần)."""
    color = tuple(c // 4 * 4 for c in color)                 # làm tròn để cache ít tấm
    if not any(color):
        return
    key = ("tint", surface.get_size(), color)
    if key not in _cache:
        solid = pygame.Surface(surface.get_size())
        if pygame.display.get_surface() is not None:
            solid = solid.convert()
        solid.fill(color)
        _cache[key] = solid
    surface.blit(_cache[key], (0, 0), special_flags=pygame.BLEND_RGB_ADD)


def storm_cloud(width: int, height: int) -> pygame.Surface:
    """Mây giông phủ nửa trên màn: đen-xanh đậm ở mép trên, trong dần xuống dưới, có vài mảng mây."""
    key = ("storm", width, height)
    if key not in _cache:
        s = pygame.Surface((width, height), pygame.SRCALPHA)
        for y in range(height):
            t = 1 - y / height
            pygame.draw.line(s, (8, 10, 26, int(235 * t ** 1.6)), (0, y), (width, y))
        lumps = pygame.Surface((width, height), pygame.SRCALPHA)
        rng = random.Random(7)                                        # cố định: mây lần nào cũng giống nhau
        for _ in range(26):
            r = rng.randint(40, 90)
            pygame.draw.circle(lumps, (14, 16, 34, rng.randint(50, 110)),
                               (rng.randint(0, width), rng.randint(-20, int(height * 0.35))), r)
        small = pygame.transform.smoothscale(lumps, (max(1, width // 8), max(1, height // 8)))
        lumps = pygame.transform.smoothscale(small, (width, height))
        s.blit(lumps, (0, 0))
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
