"""Bắn súng của người chơi, súng Tia Sét và 4 kỹ năng Nộ (mỗi súng một kiểu).

| Súng | Vai trò | Cấp 6 (tối thượng) | Kỹ năng Nộ |
|---|---|---|---|
| Plasma | Quét đông | Đạn nổ lan | VÒNG PLASMA: vòng nổ quanh tàu, xóa đạn địch |
| Laser | Diệt boss | Tia xuyên thấu liền mạch | ĐẠI PHÁO: tia khổng lồ 3 giây |
| Homing | An toàn, tự đuổi | 7 tên lửa xoắn ốc | MƯA TÊN LỬA: 20 tên lửa |
| Tia Sét | Nhảy dây chuyền | Nhảy 8 mục tiêu | BÃO SÉT: sét đánh mọi địch 3 lần |
"""
from __future__ import annotations

import math
from typing import List, Optional

import pygame

from spaceship import config
from spaceship.config import HEIGHT, LASER_COLOR, PLASMA_COLOR
from spaceship.entities.projectiles import Bullet
from spaceship.systems import combat
from spaceship.systems.world import World
from spaceship.ui import glow

LIGHTNING_COLOR = (255, 230, 60)


# --- Hiệu ứng tia sét ------------------------------------------------------------------------
def _jagged(start, end, rng, segments: int = 7, spread: float = 14.0) -> List[tuple]:
    pts = [start]
    for i in range(1, segments):
        t = i / segments
        x = start[0] + (end[0] - start[0]) * t + rng.uniform(-spread, spread)
        y = start[1] + (end[1] - start[1]) * t + rng.uniform(-spread, spread)
        pts.append((x, y))
    pts.append(end)
    return pts


class LightningArc:
    """Một tia sét gấp khúc tồn tại vài tick (nằm trong world.particles)."""

    def __init__(self, points, color=LIGHTNING_COLOR, life: int = 7, width: int = 3) -> None:
        self.points, self.color, self.width = points, color, width
        self.life = self.max_life = life

    @property
    def alive(self) -> bool:
        return self.life > 0

    def update(self) -> None:
        self.life -= 1

    def draw(self, surface: pygame.Surface) -> None:
        k = self.life / self.max_life
        pygame.draw.lines(surface, glow.scale(self.color, 0.4 * k), False, self.points, self.width * 3)
        pygame.draw.lines(surface, glow.scale(self.color, k), False, self.points, self.width)
        pygame.draw.lines(surface, glow.scale((255, 255, 255), k), False, self.points, 1)


def strike_chain(world: World, origin, damage: float, jumps: int, reach: float) -> int:
    """Sét đánh mục tiêu gần nhất rồi nhảy sang địch kế bên. Trả về số địch trúng."""
    rng = world.rng
    hit_ids = set()
    pos = origin
    radius = reach
    count = 0
    for _ in range(jumps):
        candidates = [e for e in world.enemies if e.id not in hit_ids and not e.dead and e.y > 0
                      and math.hypot(e.x - pos[0], e.y - pos[1]) < radius + e.radius]
        if not candidates:
            break
        target = min(candidates, key=lambda e: math.hypot(e.x - pos[0], e.y - pos[1]))
        world.particles.append(LightningArc(_jagged(pos, (target.x, target.y), rng)))
        world.sparks(target.x, target.y, LIGHTNING_COLOR, 3)
        combat.damage_enemy(world, target, damage, crit=True)      # sét xuyên khiên của Lính Khiên
        hit_ids.add(target.id)
        pos = (target.x, target.y)
        damage *= config.LIGHTNING_CHAIN_DECAY
        radius = config.LIGHTNING_CHAIN_RANGE
        count += 1
    return count


def _fire_lightning(world: World) -> bool:
    p = world.player
    lvl = min(p.level, config.MAX_WEAPON_LEVEL)
    p.fire_cooldown = max(8, 22 - lvl * 3)
    p.muzzle = 4
    nose = (p.x, p.y - 34)
    damage = (config.WEAPON_BASE_DAMAGE["lightning"] + config.LIGHTNING_DAMAGE_PER_LEVEL * (lvl - 1)
              + p.bonus_damage * 0.6)
    jumps = 8 if lvl == 6 else 1 + lvl
    if strike_chain(world, nose, damage, jumps, config.LIGHTNING_RANGE) == 0:   # không có mục tiêu: tia xẹt lên
        end = (p.x + world.rng.uniform(-40, 40), p.y - 160)
        world.particles.append(LightningArc(_jagged(nose, end, world.rng, 5, 10), life=4, width=2))
    return True


def fire_player(world: World) -> bool:
    """Bắn súng đang cầm (nếu hết hồi chiêu). Trả về True nếu đã bắn."""
    p = world.player
    if p.fire_cooldown > 0:
        return False
    if p.weapon == "lightning":
        return _fire_lightning(world)
    return p.fire(world.bullets)


# --- Kỹ năng Nộ --------------------------------------------------------------------------------
class Skill:
    ticks = 60

    def __init__(self, world: World) -> None:
        self.t = 0

    @property
    def alive(self) -> bool:
        return self.t < self.ticks

    def update(self, world: World) -> None:
        self.t += 1

    def draw(self, surface: pygame.Surface, world: World) -> None:
        pass


class LaserCannon(Skill):
    """ĐẠI PHÁO: tia laser khổng lồ bám theo tàu suốt 3 giây, xóa đạn địch trên đường đi."""
    ticks = config.SKILL_LASER_TICKS

    def update(self, world: World) -> None:
        super().update(world)
        p = world.player
        half = config.SKILL_LASER_WIDTH / 2
        dmg = config.SKILL_LASER_DPS / config.TICK_RATE
        for e in world.enemies:
            if e.y < p.y and abs(e.x - p.x) < half + e.rx:
                combat.damage_enemy(world, e, dmg, gain_rage=False)
                if self.t % 6 == 0:
                    world.sparks(e.x, e.y + e.ry * 0.5, (255, 140, 120), 2)
        world.enemy_bullets[:] = [b for b in world.enemy_bullets if not (b.y < p.y and abs(b.x - p.x) < half)]
        if self.t % 4 == 0:
            world.shake(4)

    def draw(self, surface: pygame.Surface, world: World) -> None:
        p = world.player
        top = int(p.y) - 30
        if top <= 0:
            return
        fade = min(1.0, (self.ticks - self.t) / 20)
        width = int(config.SKILL_LASER_WIDTH * (0.85 + 0.15 * math.sin(self.t * 0.8)) * fade) // 6 * 6
        if width < 6:
            return
        tex = glow.beam(LASER_COLOR, width, HEIGHT)
        area = pygame.Rect(0, HEIGHT - top, tex.get_width(), top)
        surface.blit(tex, (int(p.x) - tex.get_width() // 2, 0), area, special_flags=pygame.BLEND_RGB_ADD)
        glow.add(surface, glow.orb(LASER_COLOR, 30, core=0.6), (p.x, top))


class PlasmaNova(Skill):
    """VÒNG PLASMA: vòng nổ lan rộng quanh tàu, mỗi địch trúng một lần, xóa sạch đạn địch."""
    ticks = 40

    def __init__(self, world: World) -> None:
        super().__init__(world)
        self.cx, self.cy = world.player.x, world.player.y
        self.hit = set()
        world.flash = 4

    @property
    def radius(self) -> float:
        return config.SKILL_PLASMA_RADIUS * min(1.0, self.t / 30)

    def update(self, world: World) -> None:
        super().update(world)
        r = self.radius
        for e in world.enemies:
            if e.id not in self.hit and math.hypot(e.x - self.cx, e.y - self.cy) < r + e.radius:
                self.hit.add(e.id)
                combat.damage_enemy(world, e, config.SKILL_PLASMA_DAMAGE, crit=True, gain_rage=False)
                world.sparks(e.x, e.y, PLASMA_COLOR, 6)
        world.enemy_bullets[:] = [b for b in world.enemy_bullets if math.hypot(b.x - self.cx, b.y - self.cy) > r]

    def draw(self, surface: pygame.Surface, world: World) -> None:
        r = int(self.radius)
        k = 1 - self.t / self.ticks
        for width, c in ((14, glow.scale(PLASMA_COLOR, 0.35 * k)), (6, glow.scale(PLASMA_COLOR, k)),
                         (2, glow.scale((255, 255, 255), k))):
            if r > width:
                pygame.draw.circle(surface, c, (int(self.cx), int(self.cy)), r, width)


class MissileRain(Skill):
    """MƯA TÊN LỬA: phóng 20 tên lửa tự đuổi trong nửa giây."""
    ticks = 30

    def update(self, world: World) -> None:
        super().update(world)
        p = world.player
        if self.t <= 20:
            angle = 30 + (self.t * 37) % 120
            world.bullets.append(Bullet(p.x, p.y - 10, "homing", angle=angle, level=3,
                                        damage=config.SKILL_HOMING_DAMAGE))


class LightningStorm(Skill):
    """BÃO SÉT: sét từ trên trời giáng xuống MỌI địch trên màn, 3 đợt."""
    ticks = 50

    def update(self, world: World) -> None:
        super().update(world)
        if self.t not in (1, 20, 40):
            return
        world.flash = 2
        for e in list(world.enemies):
            if e.y < -20:
                continue
            top = (e.x + world.rng.uniform(-60, 60), 0)
            world.particles.append(LightningArc(_jagged(top, (e.x, e.y), world.rng, 9, 22), life=10, width=4))
            combat.damage_enemy(world, e, config.SKILL_LIGHTNING_DAMAGE, crit=True, gain_rage=False)


SKILLS = {"laser": LaserCannon, "plasma": PlasmaNova, "homing": MissileRain, "lightning": LightningStorm}


def trigger_skill(world: World) -> Optional[Skill]:
    """Dùng kỹ năng Nộ của súng đang cầm (cần đầy thanh Nộ)."""
    p = world.player
    if not p.rage_full:
        return None
    p.rage = 0
    skill = SKILLS[p.weapon](world)
    world.skills.append(skill)
    world.announce(config.SKILL_NAMES[p.weapon], 1.2)
    world.play(f"skill_{p.weapon}")
    world.shake(10)
    return skill


def update_skills(world: World) -> None:
    for skill in world.skills:
        skill.update(world)
    world.skills[:] = [s for s in world.skills if s.alive]


def draw_skills(surface: pygame.Surface, world: World) -> None:
    for skill in world.skills:
        skill.draw(surface, world)

