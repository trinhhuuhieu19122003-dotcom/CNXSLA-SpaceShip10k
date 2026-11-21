"""Hiệu ứng thuần hình ảnh: sao nền, sao băng, hạt nổ, số sát thương."""
from __future__ import annotations

import math
import random

import pygame

from spaceship.config import HEIGHT, WHITE, WIDTH

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
        if self.radius > 0:
            pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), int(self.radius))


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
