"""Phi thuyền người chơi: di chuyển, vũ khí, nâng cấp, vẽ."""
from __future__ import annotations

import math
import random
from collections import deque
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
from spaceship.ui import glow, shields

LIGHTNING_COLOR = (255, 230, 60)
WEAPON_COLORS = {"plasma": PLASMA_COLOR, "laser": LASER_COLOR, "homing": HOMING_COLOR, "lightning": LIGHTNING_COLOR}

# Góc bắn (độ) / độ lệch ngang theo cấp vũ khí 1..6
PLASMA_ANGLES = {1: [90], 2: [85, 95], 3: [75, 90, 105], 4: [60, 80, 100, 120],
                 5: [50, 70, 90, 110, 130], 6: [30, 54, 78, 102, 126, 150]}
LASER_OFFSETS = {1: [0], 2: [-15, 15], 3: [-20, 0, 20], 4: [-30, -10, 10, 30], 5: [-40, -20, 0, 20, 40]}
HOMING_ANGLES = {1: [90], 2: [80, 100], 3: [70, 90, 110], 4: [60, 80, 100, 120],
                 5: [50, 70, 90, 110, 130], 6: [0, 51, 103, 154, 206, 257, 309]}   # cấp 6: 7 tên lửa xoắn ốc

SHIP_WIDTH = 100
GUARD_COLOR = (110, 225, 255)
DRONE_WIDTH = 54
DRONE_OFFSETS = ((55, 15),)                # drone tấn công bên phải
GUARD_WIDTH = 46                           # drone hộ vệ (bay vòng quanh tàu)


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
        self.shield_age = 0             # số tick khiên đã bật (hiệu ứng nở ra, ô lục giác lóe)
        self.shield_ended = False       # khiên vừa hết giờ ở tick này -> vỡ mảnh (combat.tick_player_fx)
        self.x_history: deque = deque(maxlen=config.SHADOW_MAX_DELAY_TICKS + 1)   # x mỗi tick (Bóng KX)
        self.warp_timer = 0             # > 0: đang dịch chuyển về chiến trường sau khi mất mạng
        self.respawn_glow = False       # đang bất tử sau hồi sinh -> vẽ vòng đếm ngược, tàu mờ
        self.fire_cooldown = 0
        self.drones = 0                 # 0..2: 1 = drone tấn công, 2 = thêm drone hộ vệ
        self.drone_cooldown = 0
        self.guard_angle = 0.0
        self.guard_cooldown = 0
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
    def has_guard(self) -> bool:
        return self.drones >= 2

    @property
    def guard_pos(self):
        return (self.x + math.cos(self.guard_angle) * config.GUARD_ORBIT_RADIUS,
                self.y + 10 + math.sin(self.guard_angle) * config.GUARD_ORBIT_RADIUS * 0.75)

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
        if self.has_guard:
            self.guard_angle = (self.guard_angle + config.GUARD_ORBIT_SPEED) % math.tau
        self.x_history.append(self.x)
        had_shield = self.shield_timer > 0
        for name in ("invincible_timer", "shield_timer", "fire_cooldown", "drone_cooldown", "guard_cooldown",
                     "muzzle", "beam", "warp_timer"):
            value = getattr(self, name)
            if value > 0:
                setattr(self, name, value - 1)
        self.shield_ended = had_shield and self.shield_timer == 0
        self.shield_age = self.shield_age + 1 if self.shield_timer > 0 else 0
        if self.invincible_timer == 0:
            self.respawn_glow = False

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

    def fire_drone(self, bullets: List[Bullet], enemies=()) -> None:
        """Mỗi drone tự ngắm địch gần nó nhất trong tầm (không có thì bắn thẳng lên)."""
        if not self.drones or self.drone_cooldown > 0:
            return
        targets = [e for e in enemies if e.y > 0 and not e.is_obstacle]
        for ox, oy in DRONE_OFFSETS:
            x, y = self.x + ox, self.y + oy - 16
            near = [e for e in targets if math.hypot(e.x - x, e.y - y) < config.DRONE_RANGE]
            angle = 90.0
            if near:
                t = min(near, key=lambda e: math.hypot(e.x - x, e.y - y))
                angle = math.degrees(math.atan2(-(t.y - y), t.x - x))
            bullets.append(Bullet(x, y, "drone_bolt", angle=angle, damage=config.DRONE_DAMAGE))
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
        self.warp_timer = config.RESPAWN_WARP_TICKS
        self.respawn_glow = True

    # --- Vẽ ----------------------------------------------------------------------------
    def draw(self, surface: pygame.Surface, assets) -> None:
        alpha = 255
        if self.respawn_glow and self.invincible_timer > 0:
            # Hồi sinh: dịch chuyển về (tàu hiện dần), rồi tàu hơi trong suốt + vòng đếm ngược bất tử.
            # Không nhấp nháy biến mất nữa: lúc nào cũng thấy tàu ở đâu để né.
            if self.warp_timer > 0:
                k = 1 - self.warp_timer / config.RESPAWN_WARP_TICKS
                shields.draw_warp(surface, self.x, self.y, k)
                alpha = int(170 * k)
            else:
                shields.draw_countdown(surface, self.x, self.y, self.invincible_timer,
                                       config.RESPAWN_INVINCIBLE_TICKS - config.RESPAWN_WARP_TICKS)
                alpha = 165 + int(45 * math.sin(self.invincible_timer / 5))
        elif self.invincible_timer > 0 and self.invincible_timer % 8 < 2:
            # bất tử ngắn sau khi trúng đạn: nhấp nháy nhưng ẩn ít (1/4 thời gian)
            return
        if self.beam > 0:
            self._draw_beam(surface)
        self._draw_ship(surface, assets, alpha)
        if self.shield_active:
            shields.draw_player_shield(surface, self.x, self.y, self.shield_age, self.shield_timer)
        if self.drones and alpha >= 120:
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

    def _draw_ship(self, surface: pygame.Surface, assets, alpha: int = 255) -> None:
        """``alpha`` < 255: tàu mờ (đang hồi sinh) - bỏ viền hào quang, thân tàu trong suốt một phần."""
        x, y = self.x, self.y
        if alpha <= 0:
            return
        if alpha >= 255:
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
            if alpha < 255:
                sprite = sprite.copy()
                sprite.set_alpha(alpha)
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

    def _draw_guard(self, surface: pygame.Surface, assets) -> None:
        """Drone hộ vệ: hình riêng (drone_guard.png) nếu có, không thì vẽ khối lục giác phát khiên."""
        gx, gy = self.guard_pos
        ready = self.guard_cooldown <= 0
        glow.add(surface, glow.orb(GUARD_COLOR if ready else glow.scale(GUARD_COLOR, 0.5), 10, core=0.0), (gx, gy))
        sprite = assets.image("drone_guard", GUARD_WIDTH)
        if sprite is not None:                                  # tự xoay chậm khi bay vòng quanh tàu
            spun = pygame.transform.rotozoom(sprite, -math.degrees(self.guard_angle) * 0.5, 1)
            surface.blit(spun, spun.get_rect(center=(int(gx), int(gy))))
            if not ready:                                       # vừa bắn: lõi chớp sáng
                glow.add(surface, glow.orb(GUARD_COLOR, 6, core=0.8), (gx, gy))
            return
        pts = [(gx + math.cos(a) * 13, gy + math.sin(a) * 13) for a in (math.radians(30 + 60 * i) for i in range(6))]
        pygame.draw.polygon(surface, (30, 38, 50), pts)
        pygame.draw.polygon(surface, GUARD_COLOR, pts, 2)
        glow.add(surface, glow.orb(GUARD_COLOR, 4, core=0.8), (gx, gy))

    def _draw_drone(self, surface: pygame.Surface, assets) -> None:
        if self.has_guard:
            self._draw_guard(surface, assets)
        sprite = assets.image("drone_ally", DRONE_WIDTH)
        for ox, oy in DRONE_OFFSETS:
            dx, dy = self.x + ox, self.y + oy
            glow.add(surface, glow.orb((0, 150, 200), 5, core=0.0), (dx, dy + 20))
            if sprite is None:
                pygame.draw.polygon(surface, NEON_CYAN, [(dx, dy - 10), (dx - 10, dy + 10), (dx + 10, dy + 10)])
                continue
            surface.blit(sprite, sprite.get_rect(center=(int(dx), int(dy))))
            if self.drone_cooldown >= config.DRONE_COOLDOWN_TICKS - 3:     # vừa bắn: chớp sáng đầu nòng
                glow.add(surface, glow.orb(NEON_ORANGE, 6, core=0.7), (dx, dy - 16))
