"""Đạn của người chơi, đạn của địch và tên lửa Nuke."""
from __future__ import annotations

import math
import random
from typing import Callable, Optional, Sequence

import pygame

from spaceship.config import (
    HEIGHT,
    HOMING_COLOR,
    LASER_COLOR,
    NEON_CYAN,
    NEON_ORANGE,
    NEON_RED,
    PLASMA_COLOR,
    WHITE,
    WIDTH,
    YELLOW,
)

BULLET_SPEED = {"plasma": 25, "laser": 18, "homing": 12, "drone_laser": 35}
PIERCING_LASER_SPEED = 40
HOMING_TURN_SPEED = 16


class Bullet:
    """Đạn của người chơi. ``kind``: plasma | laser | homing | drone_laser."""

    def __init__(self, x, y, kind: str, angle: Optional[float] = 90, level: int = 1) -> None:
        self.x, self.y, self.kind, self.level = x, y, kind, level
        self.timer = 0
        self.trail: list = []
        self.hit_ids: set = set()      # địch đã bị tia xuyên thấu trúng (mỗi địch 1 lần)
        speed = PIERCING_LASER_SPEED if self.is_piercing_laser else BULLET_SPEED.get(kind, 15)
        rad = math.radians(angle if angle is not None else 90)
        self.dx = math.cos(rad) * speed
        self.vy = math.sin(rad) * speed  # dương = bay lên trên
        self.start_x, self.start_y = x, y
        self.base_angle = angle if angle is not None else 90

    @property
    def is_piercing_laser(self) -> bool:
        return self.kind == "laser" and self.level == 6

    @property
    def pierces(self) -> bool:
        return self.is_piercing_laser or self.kind == "drone_laser"

    @property
    def on_screen(self) -> bool:
        return -150 <= self.y <= HEIGHT + 150 and 0 <= self.x <= WIDTH

    def update(self, enemies: Sequence = (), spawn_particle: Optional[Callable] = None) -> None:
        self.timer += 1
        if self.kind != "homing":
            self.x += self.dx
            self.y -= self.vy
            return
        self.trail.append((self.x, self.y))
        if len(self.trail) > (8 if self.level == 6 else 5):
            self.trail.pop(0)
        if self.level == 6 and self.timer < 12:      # bung xoắn ốc trước khi đuổi mục tiêu
            radius = self.timer * 4
            ang = math.radians(self.timer * 30 + self.base_angle)
            self.x = self.start_x + math.cos(ang) * radius
            self.y = self.start_y - math.sin(ang) * radius
            return
        if enemies and self.timer > 10:
            target = min(enemies, key=lambda e: math.hypot(e.x - self.x, e.y - self.y))
            ang = math.atan2(target.y - self.y, target.x - self.x)
            self.dx = math.cos(ang) * HOMING_TURN_SPEED
            self.vy = -math.sin(ang) * HOMING_TURN_SPEED
            if spawn_particle is not None and random.random() < 0.2:
                spawn_particle(self.x, self.y, HOMING_COLOR)
        self.x += self.dx
        self.y -= self.vy

    def hits(self, enemy) -> bool:
        if self.kind == "drone_laser":
            return abs(self.x - enemy.x) < enemy.radius + 6 and self.y - 120 < enemy.y + enemy.radius and self.y > enemy.y - enemy.radius
        if self.is_piercing_laser:
            return abs(self.x - enemy.x) < enemy.radius + 30 and enemy.y < self.y + enemy.radius
        return math.hypot(self.x - enemy.x, self.y - enemy.y) < enemy.radius + 5

    # --- Vẽ -------------------------------------------------------------------------
    def draw(self, surface: pygame.Surface) -> None:
        x, y = int(self.x), int(self.y)
        if self.kind == "plasma":
            if self.level == 6:
                pygame.draw.circle(surface, WHITE, (x, y), 12)
                pygame.draw.circle(surface, PLASMA_COLOR, (x, y), 18, 5)
                pygame.draw.circle(surface, (0, 50, 255), (x, y), 24, 2)
                for _ in range(3):
                    end = (self.x + random.randint(-20, 20), self.y + random.randint(-20, 20))
                    pygame.draw.line(surface, WHITE, (self.x, self.y), end, 2)
            else:
                pygame.draw.circle(surface, (0, 100, 200), (x, y), 12)
                pygame.draw.circle(surface, PLASMA_COLOR, (x, y), 8)
                pygame.draw.circle(surface, WHITE, (x, y - 2), 4)
                end = (self.x - self.dx * 1.5, self.y + self.vy * 1.5)
                pygame.draw.line(surface, PLASMA_COLOR, (self.x, self.y), end, 4)
                pygame.draw.line(surface, WHITE, (self.x, self.y), end, 1)
        elif self.kind == "laser":
            if self.level == 6:
                beam = 1200
                w = 12 + math.sin(pygame.time.get_ticks() / 30) * 2
                pygame.draw.rect(surface, (120, 0, 0), (self.x - w * 2, self.y - beam, w * 4, beam), border_radius=10)
                pygame.draw.rect(surface, LASER_COLOR, (self.x - w, self.y - beam, w * 2, beam), border_radius=6)
                pygame.draw.rect(surface, WHITE, (self.x - w / 3, self.y - beam, w * 2 / 3, beam))
                for i in range(0, beam, 100):
                    offset = (pygame.time.get_ticks() / 2 + i) % beam
                    pygame.draw.ellipse(surface, WHITE, (self.x - w * 2.5, self.y - offset - 10, w * 5, 20), 2)
            else:
                w = 6 if self.level >= 3 else 4
                pygame.draw.rect(surface, (150, 0, 0), (self.x - w - 2, self.y - 25, w * 2 + 4, 45), border_radius=4)
                pygame.draw.rect(surface, LASER_COLOR, (self.x - w, self.y - 20, w * 2, 40), border_radius=3)
                pygame.draw.rect(surface, WHITE, (self.x - w / 3, self.y - 20, w * 2 / 3, 40), border_radius=2)
        elif self.kind == "homing":
            if len(self.trail) > 2:
                for i, (tx, ty) in enumerate(self.trail):
                    ratio = i / len(self.trail)
                    color = (int(200 * ratio), 0, int(255 * ratio))
                    pygame.draw.circle(surface, color, (int(tx), int(ty)), int(ratio * (8 if self.level == 6 else 4)))
            ang = math.atan2(-self.vy, self.dx)
            length, w = (16, 6) if self.level == 6 else (12, 4)
            p1 = (self.x + math.cos(ang) * length, self.y + math.sin(ang) * length)
            p2 = (self.x + math.cos(ang + 2.2) * w, self.y + math.sin(ang + 2.2) * w)
            p3 = (self.x + math.cos(ang - 2.2) * w, self.y + math.sin(ang - 2.2) * w)
            f1 = (self.x + math.cos(ang + 2.5) * (w + 4), self.y + math.sin(ang + 2.5) * (w + 4))
            f2 = (self.x + math.cos(ang - 2.5) * (w + 4), self.y + math.sin(ang - 2.5) * (w + 4))
            pygame.draw.polygon(surface, (100, 0, 150), [p1, f1, p2, p3, f2])
            pygame.draw.polygon(surface, HOMING_COLOR, [p1, p2, p3])
            pygame.draw.circle(surface, WHITE, (int(p1[0]), int(p1[1])), 2)
        elif self.kind == "drone_laser":
            pygame.draw.rect(surface, (200, 80, 0), (self.x - 8, self.y - 120, 16, 120), border_radius=4)
            pygame.draw.rect(surface, NEON_ORANGE, (self.x - 4, self.y - 120, 8, 120), border_radius=2)
            pygame.draw.rect(surface, WHITE, (self.x - 2, self.y - 120, 4, 120))


class EnemyBullet:
    """``kind``: normal | blue_bullet | boss_homing | laser | purple_laser."""

    HOMING_TRACK_TICKS = 45

    def __init__(self, x, y, angle_deg: float, kind: str = "normal") -> None:
        self.x, self.y, self.kind = x, y, kind
        self.speed = 6 if kind in ("normal", "blue_bullet") else (5 if kind == "boss_homing" else 18)
        self.dx = math.cos(math.radians(angle_deg)) * self.speed
        self.dy = math.sin(math.radians(angle_deg)) * self.speed
        self.track_time = self.HOMING_TRACK_TICKS if kind == "boss_homing" else 0

    @property
    def on_screen(self) -> bool:
        # Bản cũ quên mép TRÊN: đạn xoắn ốc bay lên không bao giờ bị xóa → càng đánh càng giật.
        return -50 <= self.y <= HEIGHT + 50 and -50 <= self.x <= WIDTH + 50

    def update(self, target=None) -> None:
        if self.track_time > 0 and target is not None:
            ang = math.atan2(target.y - self.y, target.x - self.x)
            self.dx, self.dy = math.cos(ang) * self.speed, math.sin(ang) * self.speed
            self.track_time -= 1
        self.x += self.dx
        self.y += self.dy

    def draw(self, surface: pygame.Surface) -> None:
        x, y = int(self.x), int(self.y)
        if self.kind == "normal":
            pygame.draw.circle(surface, (150, 0, 0), (x, y), 8)
            pygame.draw.circle(surface, NEON_RED, (x, y), 5)
            pygame.draw.circle(surface, WHITE, (x, y), 2)
        elif self.kind == "blue_bullet":
            pygame.draw.circle(surface, (0, 100, 150), (x, y), 10)
            pygame.draw.circle(surface, NEON_CYAN, (x, y), 6)
            pygame.draw.circle(surface, WHITE, (x, y), 2)
        elif self.kind == "boss_homing":
            pygame.draw.circle(surface, (100, 0, 150), (x, y), 12)
            pygame.draw.circle(surface, HOMING_COLOR, (x, y), 8)
            pygame.draw.circle(surface, YELLOW, (x, y), 3)
        else:
            color = (200, 50, 255) if self.kind == "purple_laser" else NEON_ORANGE
            tail = (self.x - self.dx * 4, self.y - self.dy * 4)
            pygame.draw.line(surface, color, (self.x, self.y), tail, 10)
            pygame.draw.line(surface, WHITE, (self.x, self.y), tail, 4)


class NukeMissile:
    SPEED = 12

    def __init__(self, x, y) -> None:
        self.x, self.y = x, y
        self.target_x, self.target_y = WIDTH // 2, HEIGHT // 2
        self.exploded = False

    @property
    def heading(self) -> float:
        return math.atan2(self.target_y - self.y, self.target_x - self.x)

    def update(self) -> None:
        if math.hypot(self.target_x - self.x, self.target_y - self.y) < self.SPEED:
            self.exploded = True
            return
        self.x += math.cos(self.heading) * self.SPEED
        self.y += math.sin(self.heading) * self.SPEED

    def draw(self, surface: pygame.Surface, assets) -> None:
        a = self.heading
        length = 50

        def polar(angle_offset: float, scale: float):
            return (self.x + math.cos(a + angle_offset) * length * scale,
                    self.y + math.sin(a + angle_offset) * length * scale)

        nose = polar(0, 1.0)
        p_r, p_l = polar(-math.pi * 0.2, 0.3), polar(math.pi * 0.2, 0.3)
        back_r, back_l = polar(-math.pi * 0.8, 0.4), polar(math.pi * 0.8, 0.4)
        body = [nose, p_r, back_r, back_l, p_l]

        glow = pygame.Surface((120, 120), pygame.SRCALPHA)
        alpha = 100 + int(50 * math.sin(pygame.time.get_ticks() / 80.0))
        pygame.draw.polygon(glow, (255, 100, 100, alpha), [(px - self.x + 60, py - self.y + 60) for px, py in body], 6)
        surface.blit(glow, (self.x - 60, self.y - 60))
        pygame.draw.polygon(surface, (50, 60, 70), body)
        pygame.draw.polygon(surface, WHITE, body, 1)
        pygame.draw.polygon(surface, (255, 50, 50), [polar(-math.pi * 0.7, 0.6), polar(-math.pi, 0.6), back_r])
        pygame.draw.polygon(surface, (255, 50, 50), [polar(math.pi * 0.7, 0.6), polar(math.pi, 0.6), back_l])

        flame_len = 20 + random.randint(0, 10)
        base = polar(math.pi, 0.4)
        tip = (base[0] + math.cos(a + math.pi) * flame_len, base[1] + math.sin(a + math.pi) * flame_len)
        flame = [back_r, polar(math.pi * 1.05, 0.3), tip, polar(math.pi * 0.95, 0.3), back_l]
        pygame.draw.polygon(surface, (255, 100, 0), flame)
        pygame.draw.polygon(surface, (255, 255, 0), flame, 1)

        label = pygame.transform.rotate(assets.text("[NUKE]", 12, WHITE), -math.degrees(a))
        surface.blit(label, label.get_rect(center=(int(self.x), int(self.y))))
