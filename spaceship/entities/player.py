"""Phi thuyền người chơi: di chuyển, vũ khí, nâng cấp, vẽ."""
from __future__ import annotations

import math
import random
from typing import List

import pygame

from spaceship import config
from spaceship.config import (
    HEIGHT,
    HOMING_COLOR,
    LASER_COLOR,
    NEON_CYAN,
    NEON_ORANGE,
    NEON_RED,
    PLASMA_COLOR,
    WIDTH,
    YELLOW,
)
from spaceship.entities.projectiles import Bullet

WEAPON_COLORS = {"plasma": PLASMA_COLOR, "laser": LASER_COLOR, "homing": HOMING_COLOR}

# Góc bắn (độ) / độ lệch ngang theo cấp vũ khí 1..6
PLASMA_ANGLES = {1: [90], 2: [85, 95], 3: [75, 90, 105], 4: [60, 80, 100, 120],
                 5: [50, 70, 90, 110, 130], 6: [30, 54, 78, 102, 126, 150]}
LASER_OFFSETS = {1: [0], 2: [-15, 15], 3: [-20, 0, 20], 4: [-30, -10, 10, 30], 5: [-40, -20, 0, 20, 40]}
HOMING_ANGLES = {1: [90], 2: [80, 100], 3: [70, 90, 110], 4: [60, 80, 100, 120],
                 5: [50, 70, 90, 110, 130], 6: [0, 72, 144, 216, 288]}

SHIP_WIDTH = 100
DRONE_WIDTH = 54
DRONE_OFFSET = (55, 15)


class Player:
    def __init__(self) -> None:
        self.x: float = WIDTH // 2
        self.y: float = HEIGHT - 100
        self.max_hp = config.PLAYER_MAX_HP
        self.hp = self.max_hp
        self.lives = config.PLAYER_LIVES
        self.max_rage = config.PLAYER_MAX_RAGE
        self.rage = 0
        self.weapon = "laser"
        self.level = 1
        self.bonus_damage = 0
        self.invincible_timer = 0
        self.shield_timer = 0
        self.fire_cooldown = 0
        self.has_drone = False
        self.drone_cooldown = 0
        self.burn_unlocked = False

    # --- Trạng thái ------------------------------------------------------------------
    @property
    def color(self):
        return WEAPON_COLORS[self.weapon]

    @property
    def shield_active(self) -> bool:
        return self.shield_timer > 0

    @property
    def vulnerable(self) -> bool:
        return not self.shield_active and self.invincible_timer <= 0

    @property
    def rage_full(self) -> bool:
        return self.rage >= self.max_rage

    @property
    def base_damage(self) -> int:
        return config.WEAPON_BASE_DAMAGE[self.weapon]

    def add_rage(self, amount: int) -> None:
        self.rage = min(self.max_rage, self.rage + amount)

    # --- Mỗi tick ----------------------------------------------------------------------
    def move(self, controls) -> None:
        if controls.target is not None:
            tx, ty = controls.target
            self.x += (tx - self.x) * config.PLAYER_HAND_FOLLOW
            self.y += (ty - self.y) * config.PLAYER_HAND_FOLLOW
        else:
            self.x += controls.move_x * config.PLAYER_KEYBOARD_SPEED
            self.y += controls.move_y * config.PLAYER_KEYBOARD_SPEED
        self.x = max(20, min(WIDTH - 20, self.x))
        self.y = max(50, min(HEIGHT - 50, self.y))

    def tick_timers(self) -> None:
        for name in ("invincible_timer", "shield_timer", "fire_cooldown", "drone_cooldown"):
            value = getattr(self, name)
            if value > 0:
                setattr(self, name, value - 1)

    def fire(self, bullets: List[Bullet]) -> bool:
        """Bắn theo vũ khí hiện tại. Trả về True nếu thực sự bắn (để phát âm thanh)."""
        if self.fire_cooldown > 0:
            return False
        lvl = min(self.level, config.MAX_WEAPON_LEVEL)
        x, y = self.x, self.y - 20
        if self.weapon == "plasma":
            self.fire_cooldown = max(5, 14 - lvl * 2)
            bullets.extend(Bullet(x, y, "plasma", angle=a, level=lvl) for a in PLASMA_ANGLES[lvl])
        elif self.weapon == "laser":
            self.fire_cooldown = max(10, (14 - lvl * 2) * 2)
            if lvl == 6:
                bullets.append(Bullet(x, y, "laser", angle=90, level=6))
            else:
                for off in LASER_OFFSETS[lvl]:
                    angle = 90 - off / 3 if lvl == 5 else 90
                    bullets.append(Bullet(x + off, y, "laser", angle=angle, level=lvl))
        else:
            self.fire_cooldown = max(12, 25 - lvl * 2)
            bullets.extend(Bullet(x, y, "homing", angle=a, level=lvl) for a in HOMING_ANGLES[lvl])
        return True

    def fire_drone(self, bullets: List[Bullet]) -> None:
        if self.has_drone and self.drone_cooldown <= 0:
            bullets.append(Bullet(self.x + DRONE_OFFSET[0], self.y + 5, "drone_laser"))
            self.drone_cooldown = config.DRONE_COOLDOWN_TICKS

    def apply_weapon_pickup(self, weapon: str) -> None:
        """Nhặt vũ khí cùng loại → lên cấp (tối đa 6, sau đó cộng sát thương);
        khác loại → đổi vũ khí, về cấp 1. ``weapon == "universal"`` luôn lên cấp."""
        if weapon == "universal" or weapon == self.weapon:
            if self.level < config.MAX_WEAPON_LEVEL:
                self.level += 1
            else:
                self.bonus_damage = min(config.MAX_BONUS_DAMAGE, self.bonus_damage + 2)
        else:
            self.weapon, self.level, self.bonus_damage = weapon, 1, 0

    def respawn(self) -> None:
        self.hp = self.max_hp
        self.invincible_timer = config.RESPAWN_INVINCIBLE_TICKS

    # --- Vẽ ----------------------------------------------------------------------------
    def draw(self, surface: pygame.Surface, assets) -> None:
        if self.invincible_timer > 0:
            if self.invincible_timer % 10 < 5:
                return
            pygame.draw.circle(surface, YELLOW, (int(self.x), int(self.y)), 55, 2)
        if self.shield_active:
            self._draw_shield(surface)
        self._draw_ship(surface, assets)
        if self.has_drone:
            self._draw_drone(surface, assets)

    def _draw_shield(self, surface: pygame.Surface) -> None:
        shield = pygame.Surface((110, 110), pygame.SRCALPHA)
        t = pygame.time.get_ticks()
        pulse = 100 + int(70 * math.sin(t / 150.0))
        outline = 180 + int(70 * math.sin(t / 150.0))
        pygame.draw.circle(shield, (0, 255, 255, pulse // 2), (55, 55), 45)
        for i in range(3):
            start = math.radians(t / 3.0 + i * 120)
            pygame.draw.arc(shield, (200, 255, 255, outline), (5, 5, 100, 100), start, start + math.radians(80), 4)
        surface.blit(shield, (int(self.x) - 55, int(self.y) - 55))

    def _draw_ship(self, surface: pygame.Surface, assets) -> None:
        x, y = self.x, self.y
        hull = [(x, y - 30), (x - 25, y + 20), (x, y + 10), (x + 25, y + 20)]
        glow = pygame.Surface((60, 60), pygame.SRCALPHA)
        local = [(px - x + 30, py - y + 30) for px, py in hull]
        for thickness in range(5, 0, -1):
            pygame.draw.polygon(glow, self.color + (int(100 / thickness),), local, thickness)
        surface.blit(glow, (x - 30, y - 30))

        sprite = assets.image("player", SHIP_WIDTH)
        flame = random.randint(10, 25)
        if sprite is not None:
            surface.blit(sprite, sprite.get_rect(center=(int(x), int(y))))
            base = y + 25
            pygame.draw.polygon(surface, NEON_ORANGE, [(x - 6, base), (x + 6, base), (x, base + flame)])
            pygame.draw.polygon(surface, YELLOW, [(x - 3, base), (x + 3, base), (x, base + flame / 2)])
        else:
            base = y + 15
            pygame.draw.polygon(surface, NEON_ORANGE, [(x - 8, base), (x + 8, base), (x, base + flame)])
            pygame.draw.polygon(surface, YELLOW, [(x - 4, base), (x + 4, base), (x, base + flame / 2)])
            body = [(x, y - 25), (x - 20, y + 15), (x, y + 5), (x + 20, y + 15)]
            pygame.draw.polygon(surface, (20, 30, 40), body)
            pygame.draw.polygon(surface, NEON_CYAN, [(x, y - 12), (x - 6, y + 5), (x + 6, y + 5)])
            pygame.draw.polygon(surface, self.color, body, 3)

    def _draw_drone(self, surface: pygame.Surface, assets) -> None:
        dx, dy = self.x + DRONE_OFFSET[0], self.y + DRONE_OFFSET[1]
        sprite = assets.image("drone", DRONE_WIDTH)
        if sprite is None:
            pygame.draw.polygon(surface, (255, 0, 255), [(dx, dy - 10), (dx - 10, dy + 10), (dx + 10, dy + 10)])
            return
        surface.blit(sprite, sprite.get_rect(center=(int(dx), int(dy))))
        flame = random.randint(5, 12)
        pygame.draw.polygon(surface, NEON_ORANGE, [(dx - 3, dy + 15), (dx + 3, dy + 15), (dx, dy + 15 + flame)])
        if self.drone_cooldown <= 0:
            pygame.draw.circle(surface, NEON_RED, (int(dx), int(dy - 10)), 4)
