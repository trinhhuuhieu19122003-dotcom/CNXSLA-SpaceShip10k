"""Khiên năng lượng kiểu "tổ ong" cho tàu người chơi và boss, cùng các hiệu ứng đi kèm.

Ý tưởng vẽ (giống ``glow.py``): mỗi khiên là một ảnh vẽ sẵn trên NỀN ĐEN rồi dán bằng phép CỘNG màu,
nên phần đen trong suốt, phần sáng phát quang. Ảnh gồm 3 lớp:

* lòng khiên: mờ ở giữa, sáng dần ra mép (giống bong bóng xà phòng) -> vẫn nhìn rõ tàu/boss bên trong,
* lưới lục giác mảnh (tổ ong), chỉ nằm trong khiên,
* viền sáng có quầng mờ.

Mỗi khung chỉ vẽ thêm vài thứ nhỏ: vài ô lục giác lóe sáng, vết nứt khi khiên yếu, gợn sóng chỗ trúng đạn.
"""
from __future__ import annotations

import math
import random
from typing import Dict, List, Tuple

import pygame

from spaceship.ui import glow

Color = Tuple[int, int, int]

PLAYER_SHIELD_COLOR = (70, 220, 255)
BOSS_SHIELD_COLOR = (255, 165, 60)
PLAYER_SHIELD_RADIUS = 52
BOSS_SHIELD_PAD = 22                # khiên boss rộng hơn thân boss bấy nhiêu px

_cache: Dict[tuple, object] = {}
SQRT3 = math.sqrt(3)


# --- Hình học tổ ong -----------------------------------------------------------------------------
def hex_points(cx: float, cy: float, r: float, rot: float = 0.0) -> List[Tuple[float, float]]:
    return [(cx + math.cos(rot + math.pi / 3 * i) * r, cy + math.sin(rot + math.pi / 3 * i) * r) for i in range(6)]


def hex_centers(rx: float, ry: float, cell: float) -> List[Tuple[float, float]]:
    """Tâm các ô lục giác (đỉnh nhọn hai bên) nằm trong hình elip bán trục rx, ry, gốc ở tâm elip."""
    out = []
    cols = int(rx / (cell * 1.5)) + 2
    rows = int(ry / (cell * SQRT3)) + 2
    for c in range(-cols, cols + 1):
        for r in range(-rows, rows + 1):
            x = c * cell * 1.5
            y = (r + (0.5 if c % 2 else 0.0)) * cell * SQRT3
            if (x / rx) ** 2 + (y / ry) ** 2 < 0.92:
                out.append((x, y))
    return out


def ellipse_point(rx: float, ry: float, ang: float) -> Tuple[float, float]:
    return math.cos(ang) * rx, math.sin(ang) * ry


def _mask(size: Tuple[int, int], rect: pygame.Rect) -> pygame.Surface:
    m = pygame.Surface(size)
    m.fill((0, 0, 0))
    pygame.draw.ellipse(m, (255, 255, 255), rect)
    return m


def shell(rx: int, ry: int, color: Color, cell: int, level: int = 10, cache_level: bool = True) -> pygame.Surface:
    """Ảnh khiên ở độ sáng ``level``/10. Bản sáng nhất luôn được cache; các mức tối hơn chỉ cache khi
    ``cache_level`` (khiên tàu: ảnh nhỏ). Khiên boss ảnh to nên mỗi khung nhân độ sáng trên bản sao."""
    key = ("shell", rx, ry, color, cell, level)
    if key in _cache:
        return _cache[key]
    base_key = ("shell", rx, ry, color, cell, 10)
    if base_key not in _cache:
        pad = max(14, min(rx, ry) // 4)
        size = (2 * (rx + pad), 2 * (ry + pad))
        c = (size[0] // 2, size[1] // 2)
        body = pygame.Rect(0, 0, 2 * rx, 2 * ry)
        body.center = c
        s = pygame.Surface(size)
        s.fill((0, 0, 0))
        steps = 18                                                   # lòng: mờ giữa, sáng dần ra mép
        for i in range(steps, 0, -1):
            t = i / steps
            r = body.inflate(-2 * rx * (1 - t), -2 * ry * (1 - t))
            pygame.draw.ellipse(s, glow.scale(color, 0.05 + 0.32 * t ** 5), r)
        grid = pygame.Surface(size)                                  # lưới tổ ong, cắt theo hình khiên
        grid.fill((0, 0, 0))
        for hx, hy in hex_centers(rx * 1.1, ry * 1.1, cell):
            pygame.draw.polygon(grid, glow.scale(color, 0.32), hex_points(c[0] + hx, c[1] + hy, cell * 0.96), 1)
        grid.blit(_mask(size, body.inflate(-4, -4)), (0, 0), special_flags=pygame.BLEND_RGB_MULT)
        s.blit(grid, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        halo = pygame.Surface(size)                                  # quầng viền
        halo.fill((0, 0, 0))
        pygame.draw.ellipse(halo, glow.scale(color, 0.8), body.inflate(6, 6), 8)
        s.blit(glow.blur(halo, 4), (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        pygame.draw.ellipse(s, color, body, 2)                       # viền sắc
        pygame.draw.ellipse(s, glow.scale((255, 255, 255), 0.7), body.inflate(-3, -3), 1)
        _cache[base_key] = s
    if level == 10:
        return _cache[base_key]
    img = _cache[base_key].copy()
    v = int(255 * level / 10)
    img.fill((v, v, v), special_flags=pygame.BLEND_RGB_MULT)
    if cache_level:
        _cache[key] = img
    return img


def hex_glow(cell: int, color: Color, level: int = 10) -> pygame.Surface:
    """Một ô lục giác phát sáng (để chớp lên trên lưới)."""
    key = ("hexglow", cell, color, level)
    if key not in _cache:
        k = level / 10
        size = cell * 4
        s = pygame.Surface((size, size))
        s.fill((0, 0, 0))
        pts = hex_points(size / 2, size / 2, cell * 0.9)
        pygame.draw.polygon(s, glow.scale(color, 0.55 * k), pts)
        s = glow.blur(s, 3)
        pygame.draw.polygon(s, glow.scale(color, 0.45 * k), pts)
        pygame.draw.polygon(s, glow.scale((255, 255, 255), 0.8 * k), pts, 1)
        _cache[key] = s
    return _cache[key]


def cracks(rx: float, ry: float, seed: int, count: int) -> List[List[Tuple[float, float]]]:
    """Vết nứt cố định (cùng ``seed`` thì cùng hình): đi từ mép vào trong, gấp khúc."""
    key = ("cracks", int(rx), int(ry), seed)
    if key not in _cache:
        rng = random.Random(seed)
        lines = []
        for _ in range(8):
            ang = rng.uniform(0, math.tau)
            x, y = ellipse_point(rx, ry, ang)
            pts = [(x, y)]
            for _ in range(rng.randint(3, 4)):
                ang += rng.uniform(-0.5, 0.5)
                x -= math.cos(ang) * rng.uniform(0.1, 0.2) * rx
                y -= math.sin(ang) * rng.uniform(0.1, 0.2) * ry
                pts.append((x, y))
            lines.append(pts)
        _cache[key] = lines
    return _cache[key][:count]


def _draw_cracks(surface, cx, cy, rx, ry, seed, count, color, k) -> None:
    for line in cracks(rx, ry, seed, count):
        pts = [(cx + x, cy + y) for x, y in line]
        pygame.draw.lines(surface, glow.scale(color, 0.5 * k), False, pts, 4)
        pygame.draw.lines(surface, glow.scale((255, 255, 255), k), False, pts, 1)


def _blit_add(surface, img, center) -> None:
    surface.blit(img, img.get_rect(center=(int(center[0]), int(center[1]))), special_flags=pygame.BLEND_RGB_ADD)


def _lit_cells(centers, tick: int, count: int, salt: int) -> List[Tuple[float, float]]:
    """Vài ô "lóe sáng" đổi chỗ mỗi 6 tick - chọn bằng phép băm, không dùng RNG của trận."""
    if not centers:
        return []
    slot = tick // 6
    return [centers[(slot * 7919 + i * 104729 + salt) % len(centers)] for i in range(count)]


# --- Khiên tàu người chơi ------------------------------------------------------------------------
PLAYER_CELL = 9
SHIELD_OPEN_TICKS = 8               # nở ra
SHIELD_WARN_TICKS = 60              # 1 giây cuối: chớp + nứt


def draw_player_shield(surface: pygame.Surface, x: float, y: float, age: int, remaining: int) -> None:
    """Bong bóng tổ ong quanh tàu. ``age``: số tick đã bật; ``remaining``: số tick còn lại."""
    open_k = min(1.0, age / SHIELD_OPEN_TICKS)
    scale = 1.0 + 0.12 * math.sin(open_k * math.pi) if open_k < 1 else 1.0    # nở hơi lố rồi co về
    r = max(8, int(PLAYER_SHIELD_RADIUS * (0.4 + 0.6 * open_k) * scale) // 4 * 4)   # bội 4: ít ảnh cache
    if open_k >= 1:
        r = PLAYER_SHIELD_RADIUS
    level = 10
    warn = remaining < SHIELD_WARN_TICKS
    if warn and (remaining // 4) % 2 == 0:
        level = 4                                                         # sắp hết: chớp tắt-sáng
    pulse = 0.9 + 0.1 * math.sin(age / 7)
    level = max(1, min(10, round(level * pulse)))
    img = shell(r, r, PLAYER_SHIELD_COLOR, PLAYER_CELL, level)
    _blit_add(surface, img, (x, y))
    if r == PLAYER_SHIELD_RADIUS:
        centers = _cache.setdefault(("centers", r, PLAYER_CELL), hex_centers(r, r, PLAYER_CELL))
        cell = hex_glow(PLAYER_CELL, PLAYER_SHIELD_COLOR, level)
        for hx, hy in _lit_cells(centers, age, 3, 11):
            _blit_add(surface, cell, (x + hx, y + hy))
        spin = age * 0.06                                                 # 2 vệt sáng chạy quanh viền
        for i in range(2):
            a0 = spin + i * math.pi
            rect = pygame.Rect(0, 0, 2 * r + 4, 2 * r + 4)
            rect.center = (int(x), int(y))
            pygame.draw.arc(surface, glow.scale((210, 250, 255), level / 10), rect, a0, a0 + 0.9, 2)
    if warn:
        n = 1 + int((1 - remaining / SHIELD_WARN_TICKS) * 5)
        _draw_cracks(surface, x, y, r, r, 3, n, PLAYER_SHIELD_COLOR, 0.9)


def player_rim_point(px: float, py: float, tx: float, ty: float) -> Tuple[float, float]:
    """Điểm trên viền khiên tàu theo hướng tới (tx, ty) - chỗ hiện gợn sóng khi đỡ đạn."""
    ang = math.atan2(ty - py, tx - px)
    return px + math.cos(ang) * PLAYER_SHIELD_RADIUS, py + math.sin(ang) * PLAYER_SHIELD_RADIUS


# --- Khiên boss ----------------------------------------------------------------------------------
BOSS_CELL = 16
BOSS_REGEN_TICKS = 40               # hồi khiên: lớp tổ ong mọc lan ra


def boss_shield_axes(boss) -> Tuple[int, int]:
    return int(boss.rx + BOSS_SHIELD_PAD), int(boss.ry + BOSS_SHIELD_PAD)


def boss_rim_point(boss, tx: float, ty: float) -> Tuple[float, float]:
    rx, ry = boss_shield_axes(boss)
    ang = math.atan2((ty - boss.y) / ry, (tx - boss.x) / rx)
    ex, ey = ellipse_point(rx, ry, ang)
    return boss.x + ex, boss.y + ey


def draw_boss_shield(surface: pygame.Surface, boss) -> None:
    """Rào chắn tổ ong màu cam: càng mất máu khiên càng mờ và nứt; vừa trúng đòn thì sáng bừng."""
    rx, ry = boss_shield_axes(boss)
    ratio = max(0.0, min(1.0, boss.shield_hp / max(1.0, boss.max_shield)))
    regen = getattr(boss, "shield_regen", 0)
    flash = getattr(boss, "shield_flash", 0)
    pulse = (math.sin(boss.age / 6.0) + 1) / 2
    k = (0.45 + 0.4 * ratio + 0.15 * pulse) + 0.35 * (flash / 6) + 0.5 * (regen / BOSS_REGEN_TICKS)
    level = max(1, min(10, round(k * 10)))
    _blit_add(surface, shell(rx, ry, BOSS_SHIELD_COLOR, BOSS_CELL, level, cache_level=False), (boss.x, boss.y))
    centers = _cache.setdefault(("centers", rx, ry, BOSS_CELL), hex_centers(rx, ry, BOSS_CELL))
    cell = hex_glow(BOSS_CELL, BOSS_SHIELD_COLOR, max(3, level))
    if regen:                                    # hồi khiên: các ô lục giác sáng lên lan từ tâm ra viền
        front = 1 - regen / BOSS_REGEN_TICKS
        for hx, hy in centers:
            d = math.hypot(hx / rx, hy / ry)
            if abs(d - front) < 0.12:
                _blit_add(surface, cell, (boss.x + hx, boss.y + hy))
    for hx, hy in _lit_cells(centers, boss.age, 5, boss.id if hasattr(boss, "id") else 0):
        _blit_add(surface, cell, (boss.x + hx, boss.y + hy))
    n = int((1 - ratio) * 7)                                                # vết nứt theo máu khiên đã mất
    if n:
        _draw_cracks(surface, boss.x, boss.y, rx, ry, 17, n, BOSS_SHIELD_COLOR, 0.8)
    if boss.age % 5 == 0 or flash:                                          # tia điện chạy dọc viền
        rng = random.Random(boss.age // 3)
        for _ in range(2):
            a0 = rng.uniform(0, math.tau)
            pts = []
            for step in range(6):
                ang = a0 + 0.12 * step
                ex, ey = ellipse_point(rx * rng.uniform(0.92, 1.02), ry * rng.uniform(0.92, 1.02), ang)
                pts.append((boss.x + ex, boss.y + ey))
            glow.glow_line(surface, (255, 210, 120), pts[0], pts[-1], 1)
            pygame.draw.lines(surface, (255, 235, 170), False, pts, 2)


# --- Hạt hiệu ứng (nằm trong world.particles) ------------------------------------------------------
class ShieldRipple:
    """Gợn sóng lục giác ở chỗ khiên đỡ đòn: một vòng lục giác nở ra + chớp sáng nhỏ."""

    def __init__(self, x, y, color: Color, size: float = 1.0, life: int = 14) -> None:
        self.x, self.y, self.color, self.size = x, y, color, size
        self.life = self.max_life = life
        self.rot = random.uniform(0, math.pi)

    @property
    def alive(self) -> bool:
        return self.life > 0

    def update(self) -> None:
        self.life -= 1

    def draw(self, surface: pygame.Surface) -> None:
        t = 1 - self.life / self.max_life
        k = 1 - t
        r = (6 + 22 * (1 - (1 - t) ** 2)) * self.size
        pygame.draw.polygon(surface, glow.scale(self.color, 0.5 * k), hex_points(self.x, self.y, r + 2, self.rot), 4)
        pygame.draw.polygon(surface, glow.scale((255, 255, 255), k), hex_points(self.x, self.y, r, self.rot), 1)
        if t < 0.4:
            glow.add(surface, glow.orb(glow.scale(self.color, 1 - t / 0.4), int(6 * self.size) // 2 * 2 + 4,
                                       core=0.6), (self.x, self.y))


class HexShard:
    """Mảnh khiên vỡ: lục giác nhỏ xoay tròn bay ra ngoài, mờ dần."""

    def __init__(self, x, y, vx, vy, color: Color, size: float, life: int = 30) -> None:
        self.x, self.y, self.vx, self.vy, self.color, self.size = x, y, vx, vy, color, size
        self.life = self.max_life = life
        self.rot = random.uniform(0, math.pi)
        self.spin = random.uniform(-0.3, 0.3)

    @property
    def alive(self) -> bool:
        return self.life > 0

    def update(self) -> None:
        self.life -= 1
        self.x += self.vx
        self.y += self.vy
        self.vx *= 0.94
        self.vy *= 0.94
        self.rot += self.spin

    def draw(self, surface: pygame.Surface) -> None:
        k = self.life / self.max_life
        pts = hex_points(self.x, self.y, self.size * (0.6 + 0.4 * k), self.rot)
        pygame.draw.polygon(surface, glow.scale(self.color, 0.45 * k), pts)
        pygame.draw.polygon(surface, glow.scale((255, 255, 255), k), pts, 1)


def shatter(particles: list, x: float, y: float, rx: float, ry: float, color: Color, count: int,
            size: float, speed: float, rng=random) -> None:
    """Khiên vỡ: rải ``count`` mảnh lục giác dọc viền elip, bay ra ngoài."""
    for i in range(count):
        ang = math.tau * i / count + rng.uniform(-0.15, 0.15)
        ex, ey = ellipse_point(rx, ry, ang)
        v = speed * rng.uniform(0.6, 1.3)
        particles.append(HexShard(x + ex, y + ey, math.cos(ang) * v, math.sin(ang) * v, color,
                                  size * rng.uniform(0.7, 1.3), life=rng.randint(22, 34)))


# --- Hồi sinh ------------------------------------------------------------------------------------
WARP_COLOR = (255, 215, 90)


def draw_warp(surface: pygame.Surface, x: float, y: float, k: float) -> None:
    """Dịch chuyển về chiến trường. ``k``: 0 -> 1 trong suốt quá trình (1 = tàu đã hiện hẳn)."""
    top = int(y)
    width = max(6, int(46 * (1 - k)) // 6 * 6)                       # cột sáng chiếu xuống, thu hẹp dần
    if top > 0 and k < 0.95:
        tex = glow.beam(WARP_COLOR, width, surface.get_height())
        area = pygame.Rect(0, surface.get_height() - top, tex.get_width(), top)
        surface.blit(tex, (int(x) - tex.get_width() // 2, 0), area, special_flags=pygame.BLEND_RGB_ADD)
    for i in range(3):                                                # 3 vòng sáng thu dần vào tàu
        rr = int(30 + 120 * max(0.0, 1 - k - i * 0.18))
        if rr > 30:
            c = glow.scale(WARP_COLOR, 0.35 + 0.65 * k)
            pygame.draw.circle(surface, c, (int(x), int(y)), rr, 2)
    glow.add(surface, glow.orb(WARP_COLOR, 8 + int(20 * k) // 2 * 2, core=0.7, halo=1.3), (x, y))


def draw_countdown(surface: pygame.Surface, x: float, y: float, remaining: int, total: int) -> None:
    """Vòng đếm ngược bất tử: cung vàng ngắn dần như kim đồng hồ; nửa giây cuối chớp nhanh."""
    frac = max(0.0, min(1.0, remaining / max(1, total)))
    if remaining < 30 and (remaining // 3) % 2 == 0:
        return
    rect = pygame.Rect(0, 0, 116, 116)
    rect.center = (int(x), int(y))
    pygame.draw.circle(surface, glow.scale(WARP_COLOR, 0.22), rect.center, 58, 1)          # vòng mờ đầy đủ
    start = math.pi / 2                                                                     # bắt đầu ở đỉnh
    end = start + math.tau * frac
    if frac > 0.01:
        pygame.draw.arc(surface, glow.scale(WARP_COLOR, 0.45), rect.inflate(6, 6), start, end, 5)
        pygame.draw.arc(surface, WARP_COLOR, rect, start, end, 3)
        hx, hy = x + math.cos(end) * 58, y - math.sin(end) * 58                              # đầu kim
        glow.add(surface, glow.orb(WARP_COLOR, 4, core=0.9), (hx, hy))


def clear_cache() -> None:
    _cache.clear()
