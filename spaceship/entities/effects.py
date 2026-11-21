"""Hiệu ứng thuần hình ảnh: sao nền, sao băng, hạt nổ, số sát thương."""
from __future__ import annotations

import math
import random

import pygame

from spaceship.config import HEIGHT, WHITE, WIDTH
from spaceship.ui import glow

# (số sao, tốc độ, kích thước, bảng màu)
STAR_LAYERS = (
    (200, (0.2, 0.6), (0.5, 1.2), ((100, 100, 100), (80, 80, 80))),
    (100, (1.0, 2.5), (1.5, 2.0), ((150, 150, 150), (130, 130, 130))),
    (50, (3.5, 5.0), (2.0, 2.5), ((255, 255, 255), (230, 230, 230))),
)
INFERNO_STAR_COLORS = ((255, 0, 0), (255, 100, 0), (255, 255, 0))


class StarLayer:
    def __init__(self, count, speed_range, size_range, colors, rng=random) -> None:
        self.rng = rng
        self.stars = [
            [rng.randint(0, WIDTH), rng.randint(0, HEIGHT), rng.uniform(*speed_range),
             rng.uniform(*size_range), rng.choice(colors)]
            for _ in range(count)
        ]

    def update(self) -> None:
        for s in self.stars:
            s[1] += s[2]
            if s[1] > HEIGHT:
                s[1] = 0
                s[0] = self.rng.randint(0, WIDTH)

    def draw(self, surface: pygame.Surface, inferno: bool = False) -> None:
        for x, y, _speed, size, color in self.stars:
            if inferno:
                color = self.rng.choice(INFERNO_STAR_COLORS)
            pygame.draw.circle(surface, color, (int(x), int(y)), int(size))


class Starfield:
    """Nền sao nhiều lớp (parallax), dùng chung giữa menu và màn chơi."""

    def __init__(self, rng=random) -> None:
        self.layers = [StarLayer(*cfg, rng=rng) for cfg in STAR_LAYERS]

    def update(self) -> None:
        for layer in self.layers:
            layer.update()

    def draw(self, surface: pygame.Surface, inferno: bool = False) -> None:
        for layer in self.layers:
            layer.draw(surface, inferno)


class ShootingStar:
    def __init__(self, rng=random) -> None:
        self.x = rng.randint(WIDTH // 2, WIDTH + 400)
        self.y = rng.randint(-200, 0)
        self.speed_x = rng.uniform(-25, -15)
        self.speed_y = rng.uniform(15, 25)
        self.length = rng.randint(50, 120)

    @property
    def alive(self) -> bool:
        return -100 <= self.x <= WIDTH + 400 and self.y <= HEIGHT

    def update(self) -> None:
        self.x += self.speed_x
        self.y += self.speed_y

    def draw(self, surface: pygame.Surface) -> None:
        end = (self.x - self.speed_x * self.length / 20, self.y - self.speed_y * self.length / 20)
        pygame.draw.line(surface, WHITE, (self.x, self.y), end, 2)


class Particle:
    def __init__(self, x, y, color, speed_scale: float = 1.0, rng=random) -> None:
        self.x, self.y, self.color = x, y, color
        self.radius = rng.uniform(2, 5)
        angle = rng.uniform(0, math.pi * 2)
        speed = rng.uniform(3, 8) * speed_scale
        self.dx, self.dy = math.cos(angle) * speed, math.sin(angle) * speed
        self.life = 20

    @property
    def alive(self) -> bool:
        return self.life > 0

    def update(self) -> None:
        self.x += self.dx
        self.y += self.dy
        self.radius -= 0.2
        self.life -= 1

    def draw(self, surface: pygame.Surface) -> None:
        if self.radius >= 1:
            glow.add(surface, glow.orb(self.color, int(self.radius), core=0.3, halo=0.8), (self.x, self.y))


class Spark:
    """Tia lửa: vệt sáng ngắn văng ra khi đạn trúng."""

    def __init__(self, x, y, color, rng=random, speed=(4, 9)) -> None:
        self.x, self.y, self.color = x, y, color
        angle = rng.uniform(0, math.pi * 2)
        v = rng.uniform(*speed)
        self.dx, self.dy = math.cos(angle) * v, math.sin(angle) * v
        self.life = self.max_life = rng.randint(6, 12)

    @property
    def alive(self) -> bool:
        return self.life > 0

    def update(self) -> None:
        self.x += self.dx
        self.y += self.dy
        self.dx *= 0.85
        self.dy *= 0.85
        self.life -= 1

    def draw(self, surface: pygame.Surface) -> None:
        k = self.life / self.max_life
        tail = (self.x - self.dx * 2.5, self.y - self.dy * 2.5)
        pygame.draw.line(surface, glow.scale(self.color, k), (self.x, self.y), tail, 2)


class Shockwave:
    """Vòng sóng xung kích lan ra từ tâm vụ nổ."""

    def __init__(self, x, y, color, max_radius: float = 60, life: int = 18) -> None:
        self.x, self.y, self.color = x, y, color
        self.max_radius = max_radius
        self.life = self.max_life = life

    @property
    def alive(self) -> bool:
        return self.life > 0

    def update(self) -> None:
        self.life -= 1

    def draw(self, surface: pygame.Surface) -> None:
        t = 1 - self.life / self.max_life                      # 0 -> 1
        radius = int(6 + (self.max_radius - 6) * (1 - (1 - t) ** 2))
        width = max(1, int(6 * (1 - t)))
        pygame.draw.circle(surface, glow.scale(self.color, 1 - t), (int(self.x), int(self.y)), radius, width)


class Flash:
    """Chớp sáng tròn ở tâm vụ nổ / đầu nòng súng."""

    def __init__(self, x, y, color, radius: int = 24, life: int = 8) -> None:
        self.x, self.y, self.color = x, y, color
        self.radius = radius
        self.life = self.max_life = life

    @property
    def alive(self) -> bool:
        return self.life > 0

    def update(self) -> None:
        self.life -= 1

    def draw(self, surface: pygame.Surface) -> None:
        k = self.life / self.max_life
        r = max(2, int(self.radius * (0.5 + 0.5 * k)) // 3 * 3)         # làm tròn để cache ít ảnh
        glow.add(surface, glow.orb(glow.scale(self.color, k), r, core=0.5 * k), (self.x, self.y))


class DamageNumber:
    MAX_LIFE = 30

    def __init__(self, x, y, damage, crit: bool = False, rng=random) -> None:
        self.x = x + rng.randint(-20, 20)
        self.y = y + rng.randint(-10, 10)
        self.damage = int(damage)
        self.life = self.MAX_LIFE
        self.color = (255, 255, 0) if crit else (255, 255, 255)

    @property
    def alive(self) -> bool:
        return self.life > 0

    def update(self) -> None:
        self.y -= 2
        self.life -= 1

    def draw(self, surface: pygame.Surface, assets) -> None:
        if self.life <= 0:
            return
        txt = assets.text(f"-{self.damage}", 20, self.color, italic=True)
        txt.set_alpha(int(self.life / self.MAX_LIFE * 255))
        surface.blit(txt, (self.x, self.y))


class FloatText:
    """Chữ nổi lên rồi mờ dần (vd. "CHUỖI x3"). Nằm chung danh sách với số sát thương."""
    MAX_LIFE = 50

    def __init__(self, x, y, text: str, color, size: int = 22) -> None:
        self.x, self.y, self.text, self.color, self.size = x, y, text, color, size
        self.life = self.MAX_LIFE

    @property
    def alive(self) -> bool:
        return self.life > 0

    def update(self) -> None:
        self.y -= 1
        self.life -= 1

    def draw(self, surface: pygame.Surface, assets) -> None:
        if self.life <= 0:
            return
        txt = assets.text(self.text, self.size, self.color, role="display")
        txt.set_alpha(int(min(1.0, self.life / 20) * 255))
        surface.blit(txt, (int(self.x - txt.get_width() / 2), int(self.y)))
