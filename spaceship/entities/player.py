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
    PLASMA_COLOR,
    WIDTH,
    YELLOW,
)
from spaceship.entities.projectiles import Bullet
from spaceship.ui import glow

LIGHTNING_COLOR = (255, 230, 60)
WEAPON_COLORS = {"plasma": PLASMA_COLOR, "laser": LASER_COLOR, "homing": HOMING_COLOR, "lightning": LIGHTNING_COLOR}

# Góc bắn (độ) / độ lệch ngang theo cấp vũ khí 1..6
PLASMA_ANGLES = {1: [90], 2: [85, 95], 3: [75, 90, 105], 4: [60, 80, 100, 120],
                 5: [50, 70, 90, 110, 130], 6: [30, 54, 78, 102, 126, 150]}
LASER_OFFSETS = {1: [0], 2: [-15, 15], 3: [-20, 0, 20], 4: [-30, -10, 10, 30], 5: [-40, -20, 0, 20, 40]}
HOMING_ANGLES = {1: [90], 2: [80, 100], 3: [70, 90, 110], 4: [60, 80, 100, 120],
                 5: [50, 70, 90, 110, 130], 6: [0, 51, 103, 154, 206, 257, 309]}   # cấp 6: 7 tên lửa xoắn ốc

SHIP_WIDTH = 100
DRONE_WIDTH = 54
DRONE_OFFSETS = ((55, 15), (-55, 15))      # drone 1 bên phải, drone 2 bên trái


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
        self.drones = 0                 # 0..2
        self.drone_cooldown = 0
        self.burn_unlocked = False
        self.focus = False              # đang né chậm (hiện điểm va chạm)
        self.muzzle = 0                 # > 0: đang lóe sáng đầu nòng
        self.beam = 0                   # > 0: đang phát tia laser cấp 6

    # --- Trạng thái ------------------------------------------------------------------
    @property
    def color(self):
        return WEAPON_COLORS[self.weapon]

    @property
    def has_drone(self) -> bool:
        return self.drones > 0

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
        self.focus = controls.focus
        if controls.target is not None:
            tx, ty = controls.target
            dx = (tx - self.x) * config.PLAYER_HAND_FOLLOW
            dy = (ty - self.y) * config.PLAYER_HAND_FOLLOW
            step = math.hypot(dx, dy)
            if self.focus and step > config.FOCUS_HAND_SPEED:   # né chậm: giới hạn tốc độ để luồn khe đạn
                dx, dy = dx / step * config.FOCUS_HAND_SPEED, dy / step * config.FOCUS_HAND_SPEED
            self.x += dx
            self.y += dy
        else:
            speed = config.FOCUS_KEYBOARD_SPEED if self.focus else config.PLAYER_KEYBOARD_SPEED
            self.x += controls.move_x * speed
            self.y += controls.move_y * speed
        self.x = max(20, min(WIDTH - 20, self.x))
        self.y = max(50, min(HEIGHT - 50, self.y))

    def tick_timers(self) -> None:
        for name in ("invincible_timer", "shield_timer", "fire_cooldown", "drone_cooldown", "muzzle", "beam"):
            value = getattr(self, name)
            if value > 0:
                setattr(self, name, value - 1)

    def fire(self, bullets: List[Bullet]) -> bool:
        """Bắn theo vũ khí hiện tại. Trả về True nếu thực sự bắn (để phát âm thanh)."""
        if self.fire_cooldown > 0 or self.weapon == "lightning":     # Tia Sét do systems/weapons.py bắn
            return False
        lvl = min(self.level, config.MAX_WEAPON_LEVEL)
        x, y = self.x, self.y - 20
        self.muzzle = 4
        if self.weapon == "plasma":
            self.fire_cooldown = max(5, 14 - lvl * 2)
            bullets.extend(Bullet(x, y, "plasma", angle=a, level=lvl) for a in PLASMA_ANGLES[lvl])
        elif self.weapon == "laser":
            self.fire_cooldown = max(10, (14 - lvl * 2) * 2)
            if lvl == 6:
                bullets.append(Bullet(x, y, "laser", angle=90, level=6))
                self.beam = self.fire_cooldown + 2
            else:
                for off in LASER_OFFSETS[lvl]:
                    angle = 90 - off / 3 if lvl == 5 else 90
                    bullets.append(Bullet(x + off, y, "laser", angle=angle, level=lvl))
        else:
            self.fire_cooldown = max(10, 22 - lvl * 2)
            bullets.extend(Bullet(x, y, "homing", angle=a, level=lvl) for a in HOMING_ANGLES[lvl])
        return True

    def fire_drone(self, bullets: List[Bullet]) -> None:
        if self.drones and self.drone_cooldown <= 0:
            for ox, _ in DRONE_OFFSETS[: self.drones]:
                bullets.append(Bullet(self.x + ox, self.y + 5, "drone_laser"))
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
        if self.beam > 0:
            self._draw_beam(surface)
        if self.shield_active:
            self._draw_shield(surface)
        self._draw_ship(surface, assets)
        if self.drones:
            self._draw_drone(surface, assets)
        if self.focus:
            self._draw_hitbox(surface)

    def _draw_beam(self, surface: pygame.Surface) -> None:
        """Laser cấp 6: một dải sáng liền từ mũi tàu lên tới mép trên màn hình."""
        top = int(self.y) - 30
        if top <= 0:
            return
        width = 22 + (self.beam % 3) * 3                    # nhấp nháy giữa 3 độ rộng đã cache
        tex = glow.beam(self.color, width, HEIGHT)
        area = pygame.Rect(0, HEIGHT - top, tex.get_width(), top)
        surface.blit(tex, (int(self.x) - tex.get_width() // 2, 0), area, special_flags=pygame.BLEND_RGB_ADD)
        glow.add(surface, glow.orb(self.color, 15, core=0.6), (self.x, top))

    def _draw_hitbox(self, surface: pygame.Surface) -> None:
        """Né chậm: hiện đúng vùng va chạm thật để người chơi biết mình nhỏ cỡ nào."""
        ring = pygame.Surface((40, 40), pygame.SRCALPHA)
        pygame.draw.circle(ring, (255, 255, 255, 60), (20, 20), config.PLAYER_HITBOX)
        pygame.draw.circle(ring, (255, 80, 80, 220), (20, 20), config.PLAYER_HITBOX, 2)
        surface.blit(ring, (int(self.x) - 20, int(self.y) - 20))
        pygame.draw.circle(surface, (255, 255, 255), (int(self.x), int(self.y)), 4)

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
        aura = pygame.Surface((60, 60), pygame.SRCALPHA)
        local = [(px - x + 30, py - y + 30) for px, py in hull]
        for thickness in range(5, 0, -1):
            pygame.draw.polygon(aura, self.color + (int(100 / thickness),), local, thickness)
        surface.blit(aura, (x - 30, y - 30))

        sprite = assets.image("player", SHIP_WIDTH)
        flame = random.randint(10, 25)
        for ex in (-12, 12):                                       # quầng sáng động cơ
            glow.add(surface, glow.orb((0, 150, 200), 7, core=0.0, halo=1.0), (x + ex, y + 34))
        if sprite is not None:
            surface.blit(sprite, sprite.get_rect(center=(int(x), int(y))))
            if self.muzzle > 0:                                    # lóe sáng đầu nòng khi bắn
                glow.add(surface, glow.orb(self.color, 4 + self.muzzle * 2, core=0.6), (x, y - 34))
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
        sprite = assets.image("drone_ally", DRONE_WIDTH)
        for ox, oy in DRONE_OFFSETS[: self.drones]:
            dx, dy = self.x + ox, self.y + oy
            glow.add(surface, glow.orb((0, 150, 200), 5, core=0.0), (dx, dy + 20))
            if sprite is None:
                pygame.draw.polygon(surface, NEON_CYAN, [(dx, dy - 10), (dx - 10, dy + 10), (dx + 10, dy + 10)])
                continue
            surface.blit(sprite, sprite.get_rect(center=(int(dx), int(dy))))
            if self.drone_cooldown <= 10:                          # sắp bắn: đầu drone sáng lên
                glow.add(surface, glow.orb(NEON_ORANGE, 4, core=0.6), (dx, dy - 16))
