"""Bản đồ hành trình: phông nền của đoạn hội thoại mở đầu mỗi ải (thay màn radar cũ).

Hồi IV (ải 11-15) có tấm bản đồ riêng (``NODES_ACT4``). Hồi I-III: 10 ải = 10 điểm sao chia 3 cụm theo hồi, nối bằng đường bay. Ải đã qua sáng xanh kèm số sao, ải sắp chơi
nhấp nháy đỏ, ải chưa tới mờ. Tàu bay từ ải trước tới ải này trong ~2 giây đầu. Ải có boss gắn dấu thoi đỏ,
ải cuối là bóng Tàu Mẹ. Câu thoại có hiệu ứng "radar" làm hiện một bầy chấm đỏ áp sát điểm ải hiện tại.

Chỉ dùng ``random`` riêng cho phần trang trí: không đụng RNG của trận đấu.
"""
from __future__ import annotations

import math
import random
from typing import Dict, List, Optional, Tuple

import pygame

from spaceship.campaign.levels import LEVELS
from spaceship.config import HEIGHT, WIDTH
from spaceship.entities.enemies import MINI_BOSSES
from spaceship.ui import glow
from spaceship.ui.widgets import ACCENT, DANGER, FRAME, MUTED, TEXT, draw_star

#: Toạ độ 10 ải: từ dưới-trái (vành đai) đi lên trên-phải (Tàu Mẹ). Nằm giữa tiêu đề (trên) và khung thoại (dưới).
NODES: Dict[int, Tuple[int, int]] = {
    1: (92, 418), 2: (172, 366), 3: (256, 404),
    4: (338, 336), 5: (408, 286), 6: (478, 326), 7: (548, 262),
    8: (612, 212), 9: (664, 160), 10: (722, 112),
}
#: Hồi IV có tấm bản đồ riêng: xuất phát từ xác Tàu Mẹ (điểm 10, dưới trái) tới nguồn tín hiệu (trên phải).
NODES_ACT4: Dict[int, Tuple[int, int]] = {
    10: (96, 420), 11: (228, 372), 12: (352, 410), 13: (462, 318), 14: (566, 246), 15: (690, 150),
}
ACT_COLORS = {1: (90, 200, 255), 2: (200, 120, 255), 3: (255, 110, 110), 4: (255, 90, 190)}
ACT_LABELS = {1: ("HỒI I", (150, 456)), 2: ("HỒI II", (440, 376)), 3: ("HỒI III", (708, 214))}
ACT_LABELS_ACT4 = {4: ("HỒI IV", (470, 450))}
START = (30, 466)                     # ải 1: tàu bay vào từ mép bản đồ
TRAVEL_TICKS = 130
CLEARED = (90, 230, 255)
LOCKED = (70, 84, 102)


def _ease(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


class JourneyMap:
    def __init__(self, level_number: int, stars: Dict[int, int]) -> None:
        self.level = level_number
        self.stars = dict(stars)
        self.act4 = level_number > 10
        self.nodes = NODES_ACT4 if self.act4 else NODES
        self.labels = ACT_LABELS_ACT4 if self.act4 else ACT_LABELS
        self.ticks = 0
        self.blips: List[List[float]] = []
        rnd = random.Random(level_number)
        self.dust = [(rnd.randint(0, WIDTH), rnd.randint(70, HEIGHT - 220), rnd.random()) for _ in range(70)]

    # --- Trạng thái --------------------------------------------------------------------
    @property
    def origin(self) -> Tuple[float, float]:
        return self.nodes[self.level - 1] if self.level > 1 else START

    @property
    def ship_pos(self) -> Tuple[float, float]:
        k = _ease(self.ticks / TRAVEL_TICKS)
        (x0, y0), (x1, y1) = self.origin, self.nodes[self.level]
        # bay theo đường cong nhẹ (nhô lên giữa đường) cho tự nhiên
        lift = math.sin(k * math.pi) * 26
        return x0 + (x1 - x0) * k, y0 + (y1 - y0) * k - lift

    @property
    def arrived(self) -> bool:
        return self.ticks >= TRAVEL_TICKS

    def contacts(self) -> None:
        """Hiệu ứng 'nhiều mục tiêu áp sát': bầy chấm đỏ quây quanh điểm ải hiện tại."""
        cx, cy = self.nodes[self.level]
        self.blips = [[min(WIDTH - 36, max(36, cx + math.cos(a) * r)),
                       min(HEIGHT - 232, max(84, cy + math.sin(a) * r * 0.7)), random.uniform(0.4, 0.9)]
                      for a, r in ((random.uniform(0, math.tau), random.uniform(70, 130)) for _ in range(16))]

    def update(self) -> None:
        self.ticks += 1
        cx, cy = self.nodes[self.level]
        for blip in self.blips:                       # tiến dần về phía điểm ải
            dx, dy = cx - blip[0], cy - blip[1]
            dist = math.hypot(dx, dy)
            if dist > 34:
                blip[0] += dx / dist * blip[2]
                blip[1] += dy / dist * blip[2]

    # --- Vẽ ----------------------------------------------------------------------------
    def draw(self, surface: pygame.Surface, assets) -> None:
        t = self.ticks
        for x, y, k in self.dust:                    # bụi sao lấp lánh
            c = int(60 + 80 * (0.5 + 0.5 * math.sin(t * 0.03 + k * 9)) * k)
            surface.set_at((x, y), (c, c, min(255, c + 30)))
        self._draw_acts(surface, assets)
        self._draw_routes(surface)
        self._draw_mothership(surface, assets)
        for number in self.nodes:
            self._draw_node(surface, assets, number)
        self._draw_blips(surface)
        self._draw_ship(surface, assets)

    def _draw_acts(self, surface, assets) -> None:
        for act, (label, pos) in self.labels.items():
            numbers = [lv.number for lv in LEVELS if lv.act == act]
            xs = [self.nodes[n][0] for n in numbers]
            ys = [self.nodes[n][1] for n in numbers]
            area = pygame.Rect(min(xs) - 34, min(ys) - 30, max(xs) - min(xs) + 68, max(ys) - min(ys) + 60)
            active = any(n == self.level for n in numbers)
            color = ACT_COLORS[act] if active else LOCKED
            halo = pygame.Surface(area.size, pygame.SRCALPHA)
            pygame.draw.ellipse(halo, (*ACT_COLORS[act], 34 if active else 14), halo.get_rect())
            pygame.draw.ellipse(halo, (*color, 90 if active else 40), halo.get_rect(), 1)
            surface.blit(halo, area)
            text = assets.text(label, 13, color, role="label")
            surface.blit(text, text.get_rect(center=pos))

    def _segment(self, surface, a, b, color, dashed: bool, progress: float = 1.0, width: int = 2) -> None:
        (x0, y0), (x1, y1) = a, b
        length = math.hypot(x1 - x0, y1 - y0)
        steps = max(1, int(length / 9))
        last = int(steps * progress)
        for i in range(last):
            if dashed and i % 2:
                continue
            p0 = (x0 + (x1 - x0) * i / steps, y0 + (y1 - y0) * i / steps)
            p1 = (x0 + (x1 - x0) * (i + 1) / steps, y0 + (y1 - y0) * (i + 1) / steps)
            pygame.draw.line(surface, color, p0, p1, width)

    def _draw_routes(self, surface) -> None:
        numbers = sorted(self.nodes)
        points = ([] if self.act4 else [START]) + [self.nodes[n] for n in numbers]
        targets = numbers[1:] if self.act4 else numbers       # số ải ở đầu cuối mỗi đoạn
        for i, target in enumerate(targets):
            a, b = points[i], points[i + 1]
            if target < self.level:
                self._segment(surface, a, b, glow.scale(CLEARED, 0.45), False, width=5)
                self._segment(surface, a, b, CLEARED, False)
            elif target == self.level:
                self._segment(surface, a, b, LOCKED, True)
                self._segment(surface, a, b, DANGER, False, _ease(self.ticks / TRAVEL_TICKS), 3)
            else:
                self._segment(surface, a, b, LOCKED, True, width=1)

    def _draw_mothership(self, surface, assets) -> None:
        if self.act4:                                   # Hồi IV: xác Tàu Mẹ mờ ở điểm xuất phát, Trái Tim Đàn ở đích
            for name, number, alpha, width in (("mothership_boss", 10, 40, 110), ("swarm_heart", 15, 70, 120)):
                image = assets.image(name, width)
                if image is not None:
                    ghost = image.copy()
                    ghost.set_alpha(alpha * 2 if number == self.level else alpha)
                    x, y = self.nodes[number]
                    surface.blit(ghost, ghost.get_rect(center=(x - 6, y + 4)))
            return
        image = assets.image("mothership_boss", 120)
        if image is None:
            return
        ghost = image.copy()
        ghost.set_alpha(120 if self.level == 10 else 55)
        x, y = NODES[10]
        surface.blit(ghost, ghost.get_rect(center=(x - 6, y + 4)))     # bóng Tàu Mẹ phía sau điểm ải 10

    def _draw_node(self, surface, assets, number: int) -> None:
        x, y = self.nodes[number]
        level = LEVELS[number - 1]
        current = number == self.level
        cleared = not current and (number < self.level or number in self.stars)
        if current:
            pulse = 0.5 + 0.5 * math.sin(self.ticks * 0.12)
            glow.add(surface, glow.orb(glow.scale(DANGER, 0.5 + 0.5 * pulse), 14, core=0.0), (x, y))
            pygame.draw.circle(surface, DANGER, (x, y), int(17 + 5 * pulse), 2)
            color, fill = DANGER, (40, 10, 16)
        elif cleared:
            glow.add(surface, glow.orb(glow.scale(CLEARED, 0.6), 10, core=0.0), (x, y))
            color, fill = CLEARED, (10, 34, 48)
        else:
            color, fill = LOCKED, (12, 16, 24)
        pygame.draw.circle(surface, fill, (x, y), 13)
        pygame.draw.circle(surface, color, (x, y), 13, 2)
        label = assets.text(str(number), 13, TEXT if (current or cleared) else MUTED, role="ui")
        surface.blit(label, label.get_rect(center=(x, y + 1)))
        if level.boss:                              # ải có boss: dấu thoi đỏ phía trên
            size = 6 if level.boss in MINI_BOSSES else 8
            top = (x, y - 26)
            diamond = [(top[0], top[1] - size), (top[0] + size, top[1]), (top[0], top[1] + size), (top[0] - size, top[1])]
            pygame.draw.polygon(surface, (60, 12, 18), diamond)
            pygame.draw.polygon(surface, DANGER if not cleared else glow.scale(DANGER, 0.6), diamond, 2)
        if cleared:
            count = self.stars.get(number, 0)
            for s in range(3):
                draw_star(surface, (x - 12 + s * 12, y + 22), 5, s < count)

    def _draw_blips(self, surface) -> None:
        for x, y, _ in self.blips:
            if (self.ticks // 6 + int(x)) % 3:
                glow.add(surface, glow.orb(DANGER, 3, core=0.5), (x, y))

    def _draw_ship(self, surface, assets) -> None:
        x, y = self.ship_pos
        (x0, y0), (x1, y1) = self.origin, self.nodes[self.level]
        angle = math.degrees(math.atan2(-(y1 - y0), x1 - x0)) - 90
        if not self.arrived:                          # vệt động cơ khi đang bay
            for i in range(1, 6):
                k = self.ticks / TRAVEL_TICKS - i * 0.03
                if k > 0:
                    px = x0 + (x1 - x0) * _ease(k)
                    py = y0 + (y1 - y0) * _ease(k) - math.sin(_ease(k) * math.pi) * 26
                    glow.add(surface, glow.orb(glow.scale(ACCENT, 0.5 - i * 0.08), 3, core=0.0), (px, py))
        sprite = assets.image("player", 34)
        if sprite is None:
            pygame.draw.polygon(surface, ACCENT, [(x, y - 10), (x - 8, y + 8), (x + 8, y + 8)])
            return
        rotated = pygame.transform.rotozoom(sprite, angle if not self.arrived else 0, 1)
        glow.add(surface, glow.orb(glow.scale(ACCENT, 0.5), 6, core=0.0), (x, y + 10))
        surface.blit(rotated, rotated.get_rect(center=(int(x), int(y))))


def draw_frame(surface: pygame.Surface, assets, title: Optional[str] = None) -> None:
    """Khung "màn hình chiến thuật" quanh bản đồ: viền góc + nhãn nhỏ."""
    area = pygame.Rect(24, 72, WIDTH - 48, HEIGHT - 72 - 222)
    length = 18
    for x, dx in ((area.left, 1), (area.right - 1, -1)):
        for y, dy in ((area.top, 1), (area.bottom - 1, -1)):
            pygame.draw.lines(surface, FRAME, False, ((x + dx * length, y), (x, y), (x, y + dy * length)), 2)
    if title:
        surface.blit(assets.text(title, 13, MUTED, role="label"), (area.x + 10, area.y + 6))
