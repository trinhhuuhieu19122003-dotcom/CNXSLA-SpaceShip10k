"""Kẻ địch: lính thường (có thể là kamikaze), thiên thạch, boss.

Bản cũ dồn cả 4 loại (kể cả "asteroid" không bao giờ được tạo ra) vào một
lớp ``Enemy`` với hàng loạt cờ ``is_...``. Ở đây mỗi loại một lớp, dùng chung
giao diện: ``x, y, radius, hp, max_hp, shield_hp, update(), draw()``.
"""
from __future__ import annotations

import itertools
import math
import random

import pygame

from spaceship import config
from spaceship.config import NEON_GREEN, NEON_MAGENTA, NEON_RED, WIDTH

_ids = itertools.count(1)

ENEMY_WIDTH = 80
BOSS_WIDTH = {1: 200, 2: 220, 3: 250}


class EnemyBase:
    is_boss = False
    is_meteor = False

    def __init__(self, hp: float, radius: int) -> None:
        self.id = next(_ids)
        self.x: float = 0
        self.y: float = 0
        self.dx: float = 0
        self.radius = radius
        self.hp = self.max_hp = hp
        self.shield_hp = 0.0
        self.max_shield = 0.0
        self.burning = False

    @property
    def dead(self) -> bool:
        return self.hp <= 0

    def _draw_hp_bar(self, surface, width: int, offset_y: float) -> None:
        x, y = self.x - width / 2, self.y - offset_y
        pygame.draw.rect(surface, NEON_RED, (x, y, width, 4))
        pygame.draw.rect(surface, NEON_GREEN, (x, y, width * max(0, self.hp) / self.max_hp, 4))


class Enemy(EnemyBase):
    """Lính thường. Từ stage 2 có thể là kamikaze: lao vào người chơi khi còn ít máu."""

    def __init__(self, difficulty: float, stage: int = 1, rng=random) -> None:
        super().__init__(hp=30 * difficulty * 2 ** (stage - 1), radius=15)
        self.x = rng.randint(30, WIDTH - 30)
        self.y = rng.randint(-100, -40)
        self.target_y = rng.randint(100, 250)
        self.reached_target = False
        self.shoot_timer = rng.randint(60, 120)
        self.kamikaze = False
        if stage >= 2:
            self.dx = rng.choice([-2, -1.5, 1.5, 2]) * difficulty
            self.kamikaze = rng.random() < 0.3

    @property
    def enraged(self) -> bool:
        return self.kamikaze and self.hp < self.max_hp * 0.4

    def update(self, player=None) -> None:
        if self.enraged and player is not None:
            ang = math.atan2(player.y - self.y, player.x - self.x)
            self.x += math.cos(ang) * config.KAMIKAZE_SPEED
            self.y += math.sin(ang) * config.KAMIKAZE_SPEED
        elif not self.reached_target and self.y < self.target_y:
            self.y += 15                                   # bay vào đội hình
        else:
            self.reached_target = True
            self.y += 0.5
            self.x += self.dx
            if self.x < self.radius or self.x > WIDTH - self.radius:
                self.dx *= -1

    def draw(self, surface: pygame.Surface, assets) -> None:
        sprite = assets.image("enemy", ENEMY_WIDTH)
        if sprite is not None:
            flags = pygame.BLEND_RGB_ADD if self.enraged else 0
            surface.blit(sprite, sprite.get_rect(center=(int(self.x), int(self.y))), special_flags=flags)
        else:
            r = self.radius
            pts = [(self.x, self.y - r), (self.x + r + 5, self.y), (self.x, self.y + r), (self.x - r - 5, self.y)]
            pygame.draw.polygon(surface, (40, 10, 20), pts)
            pygame.draw.polygon(surface, NEON_RED, pts, 2)
        self._draw_hp_bar(surface, 30, 25)


class Meteor(EnemyBase):
    is_meteor = True

    def __init__(self, difficulty: float, rng=random) -> None:
        radius = rng.randint(30, 70)
        super().__init__(hp=150 * difficulty, radius=radius)
        self.x = rng.randint(30, WIDTH - 30)
        self.y = rng.randint(-100, -40)
        self.speed = rng.uniform(3, 6)
        self.dx = rng.uniform(-2, 2)
        self.angle = 0.0
        self.spin = rng.uniform(-4, 4)
        self.outline = [
            (math.cos(math.pi * 2 * i / 6) * (radius + rng.uniform(-5, 5)),
             math.sin(math.pi * 2 * i / 6) * (radius + rng.uniform(-5, 5)))
            for i in range(6)
        ]

    def update(self, player=None) -> None:
        self.y += self.speed
        self.x += self.dx
        self.angle += self.spin

    def draw(self, surface: pygame.Surface, assets) -> None:
        sprite = assets.image("meteor", int(self.radius * 2.5))
        if sprite is not None:
            rotated = pygame.transform.rotate(sprite, self.angle)
            surface.blit(rotated, rotated.get_rect(center=(int(self.x), int(self.y))))
        else:
            c, s = math.cos(math.radians(self.angle)), math.sin(math.radians(self.angle))
            pts = [(self.x + ox * c - oy * s, self.y + ox * s + oy * c) for ox, oy in self.outline]
            pygame.draw.polygon(surface, (50, 40, 40), pts)
            pygame.draw.polygon(surface, (150, 100, 50), pts, 2)
        self._draw_hp_bar(surface, 30, self.radius + 10)


class Boss(EnemyBase):
    is_boss = True

    def __init__(self, difficulty: float, stage: int = 1) -> None:
        stage = max(1, min(3, stage))
        hp = 600 * difficulty * {1: 1.0, 2: 1.5, 3: 3.0}[stage]
        super().__init__(hp=hp, radius=60)
        self.stage = stage
        self.x, self.y = WIDTH // 2, -100
        self.speed = 1.5
        self.dx = 2.5
        self.spiral_angle = 0
        self.shield_rotation = 0
        self.attack_cooldown = 60
        self.phase = 1
        if stage >= 3:
            self.max_shield = self.shield_hp = hp / 3

    @property
    def hp_ratio(self) -> float:
        return max(0.0, self.hp / self.max_hp)

    @property
    def raging(self) -> bool:
        return self.stage >= 3 and self.hp_ratio < 0.5

    def update(self, player=None) -> None:
        if self.y < 150:
            self.y += self.speed
        else:
            self.x += self.dx * (2.0 if self.raging else 1.0)
            if self.x < 100 or self.x > WIDTH - 100:
                self.dx *= -1
        self.shield_rotation += 5

    def draw(self, surface: pygame.Surface, assets) -> None:
        if self.shield_hp > 0:
            self._draw_shield(surface)
        name = {1: "boss", 2: "boss2", 3: "boss3"}[self.stage]
        sprite = assets.image(name, BOSS_WIDTH[self.stage])
        if sprite is not None:
            flash = self.raging and pygame.time.get_ticks() % 200 < 100
            surface.blit(sprite, sprite.get_rect(center=(int(self.x), int(self.y))),
                         special_flags=pygame.BLEND_RGB_ADD if flash else 0)
        else:
            pygame.draw.circle(surface, NEON_MAGENTA, (int(self.x), int(self.y)), self.radius, 3)
        pygame.draw.rect(surface, NEON_RED, (self.x - 40, self.y - 60, 80, 6))
        pygame.draw.rect(surface, NEON_GREEN, (self.x - 40, self.y - 60, 80 * self.hp_ratio, 6))
        if self.shield_hp > 0:
            pygame.draw.rect(surface, (0, 50, 100), (self.x - 40, self.y - 52, 80, 4))
            pygame.draw.rect(surface, (100, 200, 255),
                             (self.x - 40, self.y - 52, 80 * self.shield_hp / max(1, self.max_shield), 4))

    def _draw_shield(self, surface: pygame.Surface) -> None:
        pulse = (math.sin(pygame.time.get_ticks() / 100.0) + 1) / 2
        fill = (200, int(50 + 50 * pulse), 0, int(100 + 100 * pulse))
        edge = (255, int(150 + 100 * pulse), 100, 255)
        rad = self.radius + 20
        pts = []
        for i in range(24):
            ang = math.radians(i * 15 + self.shield_rotation)
            r = rad if i % 2 == 0 else rad - 10
            pts.append((math.cos(ang) * r + rad + 10, math.sin(ang) * r + rad + 10))
        layer = pygame.Surface((rad * 2 + 20, rad * 2 + 20), pygame.SRCALPHA)
        pygame.draw.polygon(layer, fill, pts)
        pygame.draw.polygon(layer, edge, pts, 3)
        surface.blit(layer, (self.x - rad - 10, self.y - rad - 10))
        if random.random() < 0.3:                      # tia điện chập chờn quanh khiên
            for _ in range(4):
                start = math.radians(random.randint(0, 360))
                end = start + math.radians(random.randint(20, 90))
                arc = []
                for step in range(6):
                    ang = start + (end - start) * step / 5
                    r = random.randint(self.radius, rad - 5)
                    arc.append((self.x + math.cos(ang) * r, self.y + math.sin(ang) * r))
                pygame.draw.lines(surface, edge[:3], False, arc, 2)
