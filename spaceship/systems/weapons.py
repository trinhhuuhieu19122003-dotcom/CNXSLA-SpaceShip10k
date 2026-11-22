"""Bắn súng của người chơi, súng Tia Sét và 4 kỹ năng Nộ (mỗi súng một kiểu).

| Súng | Vai trò | Cấp 6 (tối thượng) | Kỹ năng Nộ |
|---|---|---|---|
| Plasma | Quét đông | Đạn nổ lan | VÒNG PLASMA: tụ lực rồi nổ đĩa sáng quanh tàu, xóa đạn địch |
| Laser | Diệt boss | Tia xuyên thấu liền mạch | ĐẠI PHÁO: tia khổng lồ 3 giây |
| Homing | An toàn, tự đuổi | 7 tên lửa xoắn ốc | MƯA TÊN LỬA: khóa mục tiêu rồi 20 tên lửa từ 2 cánh |
| Tia Sét | Nhảy dây chuyền | Nhảy 8 mục tiêu | BÃO SÉT: trời tối sầm, sét đánh mọi địch 3 lần |
"""
from __future__ import annotations

import math
import random
from typing import List, Optional

import pygame

from spaceship import config
from spaceship.config import HEIGHT, LASER_COLOR, PLASMA_COLOR
from spaceship.entities.effects import Flash, Shockwave
from spaceship.entities.projectiles import Bullet
from spaceship.systems import combat
from spaceship.systems.world import World
from spaceship.ui import glow

LIGHTNING_COLOR = (255, 230, 60)


# --- Hiệu ứng tia sét ------------------------------------------------------------------------
def _jagged(start, end, rng, segments: int = 9, spread: float = 17.0) -> List[tuple]:
    pts = [start]
    for i in range(1, segments):
        t = i / segments
        x = start[0] + (end[0] - start[0]) * t + rng.uniform(-spread, spread)
        y = start[1] + (end[1] - start[1]) * t + rng.uniform(-spread, spread)
        pts.append((x, y))
    pts.append(end)
    return pts


LIGHTNING_EDGE = (170, 210, 255)        # viền/nhánh xanh điện quanh lõi vàng-trắng


class LightningArc:
    """Một tia sét gấp khúc tồn tại vài tick (nằm trong world.particles).

    Vẽ kiểu "điện": quầng sáng mờ cộng sáng (additive) + thân vàng + lõi trắng, có 1-2 nhánh rẽ xanh điện,
    rung nhẹ mỗi 2 tick (nhấp nháy) và chớp sáng ở điểm đánh trúng. Phần ngẫu nhiên chỉ để vẽ nên dùng
    ``random`` riêng, không đụng RNG của trận đấu."""

    PAD = 18

    def __init__(self, points, color=LIGHTNING_COLOR, life: int = 10, width: int = 3, impact: bool = True) -> None:
        self.points, self.color, self.width, self.impact = list(points), color, width, impact
        self.life = self.max_life = life
        self.forks = self._make_forks()
        self._baked = None            # (khóa, quầng, lõi, toạ độ): chỉ vẽ lại khi tia rung hoặc mờ thêm 1 nấc

    def _make_forks(self) -> list:
        forks = []
        if len(self.points) < 4:
            return forks
        for _ in range(random.randint(1, 2)):
            i = random.randint(1, len(self.points) - 2)
            (x0, y0), (x1, y1) = self.points[i - 1], self.points[i]
            base = math.atan2(y1 - y0, x1 - x0) + random.choice((-1, 1)) * random.uniform(0.5, 1.1)
            length = random.uniform(26, 56)
            mid = (x1 + math.cos(base) * length * 0.5 + random.uniform(-5, 5),
                   y1 + math.sin(base) * length * 0.5 + random.uniform(-5, 5))
            forks.append([self.points[i], mid, (x1 + math.cos(base) * length, y1 + math.sin(base) * length)])
        return forks

    @property
    def alive(self) -> bool:
        return self.life > 0

    def update(self) -> None:
        self.life -= 1
        if self.life % 2 == 0 and len(self.points) > 2:          # rung nhẹ: tia sống động, không đứng yên
            self.points[1:-1] = [(x + random.uniform(-3, 3), y + random.uniform(-3, 3)) for x, y in self.points[1:-1]]

    def draw(self, surface: pygame.Surface) -> None:
        k = self.life / self.max_life
        key = (len(self.points) and self.points[1], math.ceil(k * 5))    # đổi khi rung (2 tick) / mờ 1 nấc
        if self._baked is None or self._baked[0] != key:
            self._baked = (key,) + (self._bake(math.ceil(k * 5) / 5) or (None, None, None))
        _, halo, core, pos = self._baked
        if halo is not None:
            surface.blit(halo, pos, special_flags=pygame.BLEND_RGB_ADD)
            surface.blit(core, pos, special_flags=pygame.BLEND_RGB_ADD)
        if self.impact:
            glow.add(surface, glow.orb(glow.scale(self.color, k), max(4, int(12 * k)), core=0.6), self.points[-1])
        glow.add(surface, glow.orb(glow.scale(LIGHTNING_EDGE, 0.8 * k), 5, core=0.6), self.points[0])

    def _bake(self, k: float):
        lines = [self.points] + self.forks
        xs = [x for line in lines for x, _ in line]
        ys = [y for line in lines for _, y in line]
        left, top = int(min(xs)) - self.PAD, int(min(ys)) - self.PAD
        size = (int(max(xs)) - left + self.PAD, int(max(ys)) - top + self.PAD)
        if size[0] <= 0 or size[1] <= 0 or size[0] * size[1] > 400_000:
            return None
        shift = [[(x - left, y - top) for x, y in line] for line in lines]
        halo = pygame.Surface(size)
        w = self.width
        pygame.draw.lines(halo, glow.scale(self.color, 0.75 * k), False, shift[0], w * 5)
        for fork in shift[1:]:
            pygame.draw.lines(halo, glow.scale(LIGHTNING_EDGE, 0.6 * k), False, fork, w * 3)
        halo = glow.blur(halo, 4)
        core = pygame.Surface(size)
        pygame.draw.lines(core, glow.scale(self.color, k), False, shift[0], w + 1)
        pygame.draw.lines(core, glow.scale((255, 255, 255), k), False, shift[0], max(1, w - 1))
        for fork in shift[1:]:
            pygame.draw.lines(core, glow.scale(LIGHTNING_EDGE, k), False, fork, 3)
            pygame.draw.lines(core, glow.scale((255, 255, 255), 0.85 * k), False, fork, 1)
        return halo, core, (left, top)


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
        world.particles.append(LightningArc(_jagged(pos, (target.x, target.y), rng), width=4))
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
        world.particles.append(LightningArc(_jagged(nose, end, world.rng, 5, 10), life=6, width=2, impact=False))
    return True


def update_guard(world: World) -> bool:
    """DRONE HỘ VỆ: bắn hạ viên đạn địch gần tàu nhất (trong tầm). Trả về True nếu vừa chặn một viên."""
    p = world.player
    if not p.has_guard or p.guard_cooldown > 0 or not world.enemy_bullets:
        return False
    near = [b for b in world.enemy_bullets
            if math.hypot(b.x - p.x, b.y - p.y) < config.GUARD_RANGE]
    if not near:
        return False
    target = min(near, key=lambda b: math.hypot(b.x - p.x, b.y - p.y))
    world.enemy_bullets.remove(target)
    gx, gy = p.guard_pos
    world.particles.append(LightningArc([(gx, gy), ((gx + target.x) / 2 + random.uniform(-6, 6),
                                                    (gy + target.y) / 2 + random.uniform(-6, 6)), (target.x, target.y)],
                                        color=(110, 225, 255), life=6, width=2))
    world.sparks(target.x, target.y, (110, 225, 255), 4)
    world.play("shield_block")
    p.guard_cooldown = config.GUARD_COOLDOWN_TICKS
    world.guard_blocks += 1
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
# Công thức "chiêu cuối" (học từ ĐẠI PHÁO): phủ vùng lớn + phát sáng cộng màu + kéo dài đủ lâu + rung liên tục.
# Mỗi kỹ năng có 2 lớp vẽ: ``draw_back`` (dưới địch/đạn địch, vd. mây giông) và ``draw`` (trên cùng).
# ``fx`` = mức "Rung & nháy" trong Tùy chọn (1 đầy đủ, 0.5 giảm, 0 tắt): chỉ áp cho chớp/ám màu.
class Skill:
    ticks = 60

    def __init__(self, world: World) -> None:
        self.t = 0

    @property
    def alive(self) -> bool:
        return self.t < self.ticks

    def update(self, world: World) -> None:
        self.t += 1

    def draw_back(self, surface: pygame.Surface, world: World, fx: float = 1.0) -> None:
        pass

    def draw(self, surface: pygame.Surface, world: World, fx: float = 1.0) -> None:
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

    def draw(self, surface: pygame.Surface, world: World, fx: float = 1.0) -> None:
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


def _ease_out(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 2


def _tint(surface: pygame.Surface, color, k: float) -> None:
    """Ám màu cả màn (cộng sáng) - dùng cho chớp xanh plasma / chớp sét."""
    if k > 0:
        glow.tint(surface, glow.scale(color, k))


class PlasmaNova(Skill):
    """VÒNG PLASMA: tụ lực 0,3 giây (cầu plasma phình to, hạt sáng bị hút vào) rồi NỔ: đĩa sáng lan rộng
    quanh tàu + vòng dội thứ hai, mỗi địch trúng một lần, xóa sạch đạn địch. Lúc tụ lực vẫn có một vòng
    nhỏ quanh tàu xóa đạn, để chiêu này vẫn cứu nguy kịp như trước."""
    CHARGE = 18                    # tụ lực
    EXPAND = 30                    # vòng lan tới bán kính tối đa
    ECHO_DELAY = 8                 # vòng dội chạy sau
    ticks = CHARGE + 52
    CHARGE_GUARD = 90              # bán kính xóa đạn quanh tàu lúc đang tụ lực

    def __init__(self, world: World) -> None:
        super().__init__(world)
        self.cx, self.cy = world.player.x, world.player.y
        self.hit = set()

    @property
    def charging(self) -> bool:
        return self.t < self.CHARGE

    @property
    def radius(self) -> float:
        return config.SKILL_PLASMA_RADIUS * _ease_out((self.t - self.CHARGE) / self.EXPAND)

    @property
    def echo_radius(self) -> float:
        return config.SKILL_PLASMA_RADIUS * 0.92 * _ease_out((self.t - self.CHARGE - self.ECHO_DELAY) / (self.EXPAND + 6))

    def update(self, world: World) -> None:
        super().update(world)
        p = world.player
        if self.charging:                                        # tụ lực: bám theo tàu
            self.cx, self.cy = p.x, p.y
            world.enemy_bullets[:] = [b for b in world.enemy_bullets
                                      if math.hypot(b.x - p.x, b.y - p.y) > self.CHARGE_GUARD]
            if self.t % 3 == 0:
                world.shake(2)
            return
        if self.t == self.CHARGE:                                # NỔ
            world.flash = 4
            world.shake(14)
            world.freeze(3)
            world.particles.append(Flash(self.cx, self.cy, PLASMA_COLOR, radius=60, life=14))
        r = self.radius
        for e in world.enemies:
            if e.id not in self.hit and math.hypot(e.x - self.cx, e.y - self.cy) < r + e.radius:
                self.hit.add(e.id)
                combat.damage_enemy(world, e, config.SKILL_PLASMA_DAMAGE, crit=True, gain_rage=False)
                world.sparks(e.x, e.y, PLASMA_COLOR, 6)
                world.particles.append(Flash(e.x, e.y, (190, 235, 255), radius=24, life=10))
        world.enemy_bullets[:] = [b for b in world.enemy_bullets if math.hypot(b.x - self.cx, b.y - self.cy) > r]

    def draw(self, surface: pygame.Surface, world: World, fx: float = 1.0) -> None:
        if self.charging:
            self._draw_charge(surface, world)
            return
        since = self.t - self.CHARGE
        fade = min(1.0, (self.ticks - self.t) / 22)              # mờ dần ở cuối
        if since < 16:                                            # ám xanh cả màn lúc vừa nổ
            _tint(surface, (0, 40, 70), (1 - since / 16) * fx)
        r = int(self.radius)
        if r > 8:
            center = (int(self.cx), int(self.cy))
            glow.add_scaled(surface, glow.nova(PLASMA_COLOR), center, r, 0.95 * fade)
            pygame.draw.circle(surface, glow.scale(PLASMA_COLOR, fade), center, r, 5)          # viền sắc
            pygame.draw.circle(surface, glow.scale((255, 255, 255), fade), center, r - 1, 2)   # lõi trắng nóng
        er = int(self.echo_radius)
        if er > 8:
            k = fade * 0.8
            pygame.draw.circle(surface, glow.scale(PLASMA_COLOR, 0.45 * k), (int(self.cx), int(self.cy)), er, 9)
            pygame.draw.circle(surface, glow.scale((210, 245, 255), k), (int(self.cx), int(self.cy)), er, 2)

    def _draw_charge(self, surface: pygame.Surface, world: World) -> None:
        p = world.player
        k = self.t / self.CHARGE                                  # 0 -> 1
        glow.add(surface, glow.orb(PLASMA_COLOR, 10 + int(26 * k) // 2 * 2, core=0.55, halo=1.3), (p.x, p.y))
        ring = int(150 * (1 - k)) + 20                            # vòng co dần vào tàu
        pygame.draw.circle(surface, glow.scale(PLASMA_COLOR, 0.4 + 0.6 * k), (int(p.x), int(p.y)), ring, 3)
        for i in range(12):                                       # hạt sáng bị hút vào tâm
            ang = math.radians(i * 30 + self.t * 9)
            dist = 30 + 130 * (1 - k) * (0.7 + 0.3 * ((i * 7) % 5) / 4)
            glow.add(surface, glow.orb((170, 230, 255), 3, core=0.8, halo=0.8),
                     (p.x + math.cos(ang) * dist, p.y + math.sin(ang) * dist))


class MissileRain(Skill):
    """MƯA TÊN LỬA: 0,4 giây khóa mục tiêu (vòng ngắm đỏ co lại trên từng con, kêu "bíp"), rồi phóng
    20 tên lửa vàng từ hai bên cánh như quạt mở, chia đều cho các mục tiêu đã khóa; trúng đâu nổ cam tới đó."""
    LOCK = 24
    MISSILES = config.SKILL_HOMING_MISSILES
    MAX_LOCKS = 8
    ticks = LOCK + MISSILES + 14

    def __init__(self, world: World) -> None:
        super().__init__(world)
        self.locks: List[int] = []
        self._lock_targets(world)
        world.play("lock_on")

    def _lock_targets(self, world: World) -> None:
        p = world.player
        visible = [e for e in world.enemies if e.y > 0 and not e.dead and not e.is_obstacle]
        visible.sort(key=lambda e: math.hypot(e.x - p.x, e.y - p.y))
        self.locks = [e.id for e in visible[:self.MAX_LOCKS]]

    def update(self, world: World) -> None:
        super().update(world)
        if self.t == self.LOCK and not self.locks:                # lúc bật chưa có ai: khóa lại lần nữa
            self._lock_targets(world)
        i = self.t - self.LOCK
        if not 0 <= i < self.MISSILES:
            return
        p = world.player
        side = -1 if i % 2 == 0 else 1                            # xen kẽ cánh trái / cánh phải
        spread = 12 + (i // 2) * 7                                # quạt mở dần ra
        missile = Bullet(p.x + side * 34, p.y + 4, "homing", angle=90 - side * spread, level=3,
                         damage=config.SKILL_HOMING_DAMAGE)
        if self.locks:
            missile.target_id = self.locks[i % len(self.locks)]
        world.bullets.append(missile)
        world.sparks(p.x + side * 34, p.y + 4, (255, 210, 120), 2)
        if i % 3 == 0:
            world.shake(3)

    def draw(self, surface: pygame.Surface, world: World, fx: float = 1.0) -> None:
        alive = {e.id: e for e in world.enemies if not e.dead}
        k = min(1.0, self.t / self.LOCK)
        blink = (self.t // 3) % 2 == 0
        for eid in self.locks:
            e = alive.get(eid)
            if e is None:
                continue
            base = e.radius + 10
            r = int(base + 46 * (1 - k))                          # vòng ngắm co lại dần
            color = LOCK_COLOR if (k < 1 or blink) else (255, 230, 120)
            cx, cy = int(e.x), int(e.y)
            pygame.draw.circle(surface, glow.scale(color, 0.35), (cx, cy), r + 2, 5)
            pygame.draw.circle(surface, color, (cx, cy), r, 2)
            for a in range(4):                                    # 4 vạch ngắm
                ang = math.radians(a * 90 + 45 + (1 - k) * 90)
                inner, outer = r - 6, r + 10
                pygame.draw.line(surface, color, (cx + math.cos(ang) * inner, cy + math.sin(ang) * inner),
                                 (cx + math.cos(ang) * outer, cy + math.sin(ang) * outer), 2)
            if k >= 1:
                glow.add(surface, glow.orb(glow.scale(LOCK_COLOR, 0.8), 4, core=0.8), (cx, cy))


class LightningStorm(Skill):
    """BÃO SÉT: trời tối sầm (mây giông chớp lóe phía trên), rồi 3 đợt sét dày giáng xuống MỌI địch trên màn;
    chỗ sét đánh có quầng nổ vàng, mỗi đợt màn chớp và rung mạnh."""
    GATHER = 12
    STRIKES = (12, 30, 48)
    ticks = 72

    def __init__(self, world: World) -> None:
        super().__init__(world)
        self.flickers: list = []                                   # chớp trong mây: [x, y, r, life]

    @property
    def darkness(self) -> float:
        """0..1: tối dần lúc tụ mây, giữ, rồi sáng lại ở cuối."""
        return min(1.0, self.t / self.GATHER, (self.ticks - self.t) / 16)

    def update(self, world: World) -> None:
        super().update(world)
        for f in self.flickers:
            f[3] -= 1
        self.flickers = [f for f in self.flickers if f[3] > 0]
        if random.random() < 0.35:                                 # chỉ để vẽ: dùng random riêng, không đụng RNG trận
            self.flickers.append([random.uniform(40, config.WIDTH - 40), random.uniform(10, 120),
                                  random.choice((22, 30, 38)), 5])
        if self.t not in self.STRIKES:
            return
        world.flash = 3
        world.shake(9)
        for e in list(world.enemies):
            if e.y < -20:
                continue
            top = (e.x + world.rng.uniform(-60, 60), 0)
            world.particles.append(LightningArc(_jagged(top, (e.x, e.y), world.rng, 10, 24), life=16, width=7))
            world.particles.append(Flash(e.x, e.y, LIGHTNING_COLOR, radius=33, life=12))
            world.particles.append(Shockwave(e.x, e.y, LIGHTNING_COLOR, max_radius=55, life=14))
            combat.damage_enemy(world, e, config.SKILL_LIGHTNING_DAMAGE, crit=True, gain_rage=False)

    def draw_back(self, surface: pygame.Surface, world: World, fx: float = 1.0) -> None:
        d = self.darkness
        if d <= 0:
            return
        cloud = glow.storm_cloud(surface.get_width(), int(surface.get_height() * 0.62))
        cloud.set_alpha(int(210 * d))
        surface.blit(cloud, (0, 0))
        if fx <= 0:
            return
        for x, y, r, life in self.flickers:                        # chớp lóe trong mây: một dải đốm sáng ngang
            k = life / 5 * 0.45 * d * fx
            color = glow.scale(STORM_FLICKER, k)
            for dx, size in ((-r, 10), (0, 16), (r, 12)):
                glow.add(surface, glow.orb(color, size, core=0.0, halo=1.5), (x + dx, y + (dx % 7) - 3))

    def draw(self, surface: pygame.Surface, world: World, fx: float = 1.0) -> None:
        since = min((self.t - s for s in self.STRIKES if self.t >= s), default=99)
        if since < 6:                                              # chớp vàng nhạt mỗi đợt sét
            _tint(surface, (36, 32, 10), (1 - since / 6) * fx)


LOCK_COLOR = (255, 70, 70)
STORM_FLICKER = (150, 175, 255)


SKILLS = {"laser": LaserCannon, "plasma": PlasmaNova, "homing": MissileRain, "lightning": LightningStorm}


def trigger_skill(world: World) -> Optional[Skill]:
    """Dùng kỹ năng Nộ của súng đang cầm (cần đầy thanh Nộ)."""
    p = world.player
    if not p.rage_full:
        return None
    p.rage = 0
    world.skills_used += 1
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


def draw_skills_back(surface: pygame.Surface, world: World, fx: float = 1.0) -> None:
    """Lớp dưới của kỹ năng (vẽ ngay sau nền, trước địch và đạn địch - không che đạn cần né)."""
    for skill in world.skills:
        skill.draw_back(surface, world, fx)


def draw_skills(surface: pygame.Surface, world: World, fx: float = 1.0) -> None:
    for skill in world.skills:
        skill.draw(surface, world, fx)

