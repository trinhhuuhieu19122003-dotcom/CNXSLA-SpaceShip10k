"""Kẻ địch của "Đàn Ký Sinh".

Mỗi loại một lớp, dùng chung giao diện: ``x, y, radius, hp, max_hp, shield_hp,
update(player), draw(surface, assets)``. Cách bắn của từng loại nằm ở
``systems/attacks.py`` (khóa ``ai``), để file này chỉ lo hình dạng + di chuyển.

| Lớp | Tên trong game | Đặc điểm |
|---|---|---|
| Enemy | Lính thường | Bay vào đội hình; từ ải sau có thể là kamikaze |
| Parasite | Ký Sinh | Nhỏ, nhanh, lượn sóng lao xuống, không bắn |
| ShieldBug | Lính Khiên | Khiên phía trước chặn đạn bắn thẳng |
| Breeder | Kẻ Đẻ Trứng | Đẻ Ký Sinh; chết thì vỡ ra thêm |
| Turret | Pháo tháp | Đứng yên, vạch đỏ cảnh báo rồi bắn laser |
| InfectedAlly | Tàu đồng minh bị nhiễm | Lượn nhanh, bắn đôi |
| Meteor / Wreck | Thiên thạch / Xác tàu | Chướng ngại; xác tàu chặn cả đạn địch |
| Boss | 6 loại boss | Thông số trong ``BOSS_SPECS`` |
"""
from __future__ import annotations

import itertools
import math
import random
from dataclasses import dataclass
from typing import Optional

import pygame

from spaceship import config
from spaceship.config import HEIGHT, NEON_GREEN, NEON_MAGENTA, NEON_RED, WIDTH
from spaceship.ui import glow, shields

_ids = itertools.count(1)

ENEMY_WIDTH = 80


class EnemyBase:
    is_boss = False
    is_meteor = False
    is_obstacle = False          # xác tàu: chặn đạn địch
    threat = 1.0                 # trọng số trong "ngân sách đe dọa" (config.THREAT_CAP)
    gone = False                 # đã rời màn hình theo lối khác ngoài mép dưới (vd. lính rút lui)
    hp_bar_timer = 0             # > 0: vừa trúng đạn -> hiện thanh máu
    front_shield = False         # Lính Khiên
    ai: Optional[str] = None     # khóa trong systems/attacks.py
    sprite: Optional[str] = None
    sprite_width = ENEMY_WIDTH
    score = config.SCORE_ENEMY
    counts_as_kill = True        # tính vào "quái diệt"
    drops = True                 # có rơi đồ khi chết
    death_fx = "explode"         # "explode" | "dissolve" (tan thành hạt, không nổ lửa)

    def __init__(self, hp: float, radius: int) -> None:
        self.id = next(_ids)
        self.x: float = 0
        self.y: float = 0
        self.dx: float = 0
        self.radius = radius
        self.rx = self.ry = radius   # vùng trúng đạn hình elip (boss bề ngang lớn)
        self.hp = self.max_hp = hp
        self.shield_hp = 0.0
        self.max_shield = 0.0
        self.burning = False
        self.hit_flash = 0          # > 0: vừa trúng đạn, vẽ nháy trắng
        self.shoot_timer = 90
        self.age = 0

    @property
    def dead(self) -> bool:
        return self.hp <= 0

    def contains(self, x: float, y: float, margin: float = 0.0) -> bool:
        dx = (x - self.x) / (self.rx + margin)
        dy = (y - self.y) / (self.ry + margin)
        return dx * dx + dy * dy < 1.0

    def update(self, player=None) -> None:
        self.age += 1

    # --- Vẽ -----------------------------------------------------------------------------
    def draw(self, surface: pygame.Surface, assets) -> None:
        self._draw_sprite(surface, assets)
        self._draw_hp_bar(surface, 30, self.radius + 10)

    def _draw_sprite(self, surface, assets, angle: float = 0, add: bool = False) -> None:
        sprite = assets.image(self.sprite, self.sprite_width) if self.sprite else None
        if sprite is None:
            r = self.radius
            pts = [(self.x, self.y + r), (self.x + r, self.y), (self.x, self.y - r), (self.x - r, self.y)]
            pygame.draw.polygon(surface, (40, 10, 20), pts)
            pygame.draw.polygon(surface, NEON_RED, pts, 2)
            return
        if angle:
            sprite = pygame.transform.rotate(sprite, angle)
        surface.blit(sprite, sprite.get_rect(center=(int(self.x), int(self.y))),
                     special_flags=pygame.BLEND_RGB_ADD if add else 0)
        self._draw_hit_flash(surface, assets, self.sprite, self.sprite_width, angle)

    def _draw_hit_flash(self, surface, assets, name: str, width: int, angle: float = 0) -> None:
        if self.hit_flash <= 0:
            return
        white = assets.silhouette(name, width)
        if white is None:
            return
        if angle:
            white = pygame.transform.rotate(white, angle)
        white.set_alpha(30 * self.hit_flash)          # tối đa ~120: trúng liên tục vẫn nhìn rõ địch
        surface.blit(white, white.get_rect(center=(int(self.x), int(self.y))))

    def _draw_hp_bar(self, surface, width: int, offset_y: float) -> None:
        """Chỉ hiện ngay sau khi trúng đạn (tự ẩn sau ~1,5 giây) cho màn hình đỡ rối."""
        if self.hp >= self.max_hp or self.hp_bar_timer <= 0:
            return
        x, y = self.x - width / 2, self.y - offset_y
        pygame.draw.rect(surface, (20, 8, 10), (x - 1, y - 1, width + 2, 5))
        pygame.draw.rect(surface, (120, 30, 36), (x, y, width, 3))
        pygame.draw.rect(surface, NEON_GREEN, (x, y, width * max(0, self.hp) / self.max_hp, 3))


# --- Lính thường ------------------------------------------------------------------------
class Enemy(EnemyBase):
    """Lính thường. Có thể là kamikaze: lao vào người chơi khi còn ít máu."""

    ai = "grunt"
    sprite = "enemy"

    def __init__(self, difficulty: float, stage: int = 1, rng=random, hp_scale: float = 1.0,
                 kamikaze_chance: Optional[float] = None) -> None:
        super().__init__(hp=30 * difficulty * 2 ** (min(stage, 3) - 1) * hp_scale, radius=15)
        self.x = rng.randint(30, WIDTH - 30)
        self.y = rng.randint(-100, -40)
        self.target_y = rng.randint(100, 250)
        self.reached_target = False
        self.arrived_at = 0
        self.shoot_timer = rng.randint(60, 120)
        self.kamikaze = False
        self.windup = 0                 # > 0: đang khóa mục tiêu, sắp lao
        self.heading: Optional[float] = None
        self.dive_ticks = 0
        self.just_locked = False        # tick đầu tiên khóa mục tiêu (để phát tiếng bíp)
        chance = kamikaze_chance if kamikaze_chance is not None else (0.3 if stage >= 2 else 0.0)
        if stage >= 2:
            self.dx = rng.choice([-2, -1.5, 1.5, 2]) * min(difficulty, 2.0)
        self.kamikaze = rng.random() < chance

    @property
    def enraged(self) -> bool:
        return self.kamikaze and self.hp < self.max_hp * 0.4

    @property
    def retreating(self) -> bool:
        return self.reached_target and not self.enraged and self.age - self.arrived_at >= config.RETREAT_AFTER_TICKS

    @property
    def gone(self) -> bool:
        if self.heading is not None and self.windup == 0:        # kamikaze lao trượt ra khỏi màn
            return not (-80 < self.x < WIDTH + 80 and -80 < self.y < HEIGHT + 80)
        return self.retreating and self.y < -60

    @property
    def armed(self) -> bool:
        """Chỉ bắn khi đã vào vị trí được một lúc (không bắn lúc đang bay vào, không bắn khi rút lui)."""
        return (self.reached_target and not self.retreating
                and self.age - self.arrived_at >= config.ARRIVAL_GRACE_TICKS)

    def update(self, player=None) -> None:
        self.age += 1
        self.just_locked = False
        if self.enraged and player is not None:
            self._dive(player)
        elif self.retreating:
            self.y -= 4                                    # rút lui: bay ngược lên khỏi màn hình
        elif not self.reached_target and self.y < self.target_y:
            # bay vào đội hình: nhanh rồi chậm dần khi gần tới chỗ (dễ nhìn, dễ bắn hạ giữa đường)
            self.y += max(3.0, min(11.0, (self.target_y - self.y) * 0.09))
        else:
            if not self.reached_target:
                self.reached_target, self.arrived_at = True, self.age
            if self.y < config.FORMATION_FLOOR:              # trôi xuống chậm, không lấn nửa dưới màn hình
                self.y += 0.5
            self.x += self.dx
            if self.x < self.radius or self.x > WIDTH - self.radius:
                self.dx *= -1

    def _dive(self, player) -> None:
        """Kamikaze: khóa mục tiêu (đứng rung tại chỗ) -> lao, bẻ lái có giới hạn -> bay thẳng."""
        aim = math.atan2(player.y - self.y, player.x - self.x)
        if self.heading is None:
            self.heading, self.windup, self.just_locked = aim, config.KAMIKAZE_WINDUP_TICKS, True
        if self.windup > 0:
            self.windup -= 1
            self.heading = aim                                   # vẫn nhắm theo người chơi khi đang khóa
            return
        self.dive_ticks += 1
        if self.dive_ticks <= config.KAMIKAZE_HOMING_TICKS:
            turn = math.radians(config.KAMIKAZE_TURN_DEG)
            diff = (aim - self.heading + math.pi) % (2 * math.pi) - math.pi
            self.heading += max(-turn, min(turn, diff))
        self.x += math.cos(self.heading) * config.KAMIKAZE_SPEED
        self.y += math.sin(self.heading) * config.KAMIKAZE_SPEED

    def draw(self, surface: pygame.Surface, assets) -> None:
        if self.windup > 0:
            self._draw_lock_on(surface, assets)
            return
        self._draw_sprite(surface, assets, add=self.enraged)
        self._draw_hp_bar(surface, 30, 25)

    def _draw_lock_on(self, surface: pygame.Surface, assets) -> None:
        """Cảnh báo sắp lao: thân rung, vòng đỏ co lại, vạch ngắm hướng lao."""
        k = 1 - self.windup / config.KAMIKAZE_WINDUP_TICKS          # 0 -> 1 khi sắp lao
        jitter = 2 if self.windup % 4 < 2 else -2
        x, y = self.x, self.y
        self.x += jitter
        self._draw_sprite(surface, assets, add=self.windup % 6 < 3)
        self.x = x
        red = (255, int(80 * (1 - k)), 60)
        pygame.draw.circle(surface, red, (int(x), int(y)), int(36 - 14 * k), 3)
        if self.windup % 10 < 5:                                      # vòng ngoài nhấp nháy: dễ thấy khi đạn dày
            pygame.draw.circle(surface, (255, 200, 80), (int(x), int(y)), int(44 - 14 * k), 1)
        if self.heading is not None:
            for i in range(5):                                        # vạch đứt khúc theo hướng sẽ lao
                a, b = 30 + i * 24, 44 + i * 24
                start = (x + math.cos(self.heading) * a, y + math.sin(self.heading) * a)
                end = (x + math.cos(self.heading) * b, y + math.sin(self.heading) * b)
                pygame.draw.line(surface, red, start, end, 2 + int(k * 2))


# --- Ký Sinh ------------------------------------------------------------------------------
class Parasite(EnemyBase):
    threat = 0.75
    sprite = "parasite"
    sprite_width = 44
    score = 5

    def __init__(self, difficulty: float, x: float, y: float = -30, rng=random, small: bool = False) -> None:
        super().__init__(hp=(8 if small else 14) * difficulty, radius=10 if small else 13)
        self.base_x, self.x, self.y = x, x, y
        self.vy = rng.uniform(2.6, 3.6)
        self.amp = rng.uniform(40, 90)
        self.phase = rng.uniform(0, math.pi * 2)
        if small:
            self.sprite_width = 30

    def update(self, player=None) -> None:
        self.age += 1
        self.y += self.vy
        self.x = self.base_x + math.sin(self.age * 0.06 + self.phase) * self.amp


# --- Lính Khiên ---------------------------------------------------------------------------
class ShieldBug(EnemyBase):
    ai = "shield"
    threat = 2.0
    sprite = "shield_enemy"
    sprite_width = 92
    front_shield = True
    score = 25

    def __init__(self, difficulty: float, x: float, target_y: float, rng=random) -> None:
        super().__init__(hp=70 * difficulty, radius=28)
        self.rx, self.ry = 40, 26
        self.x, self.y, self.target_y = x, -60, target_y
        self.dx = rng.choice([-1.0, 1.0])
        self.shoot_timer = rng.randint(70, 130)

    def blocks(self, bullet) -> bool:
        """Đạn bay thẳng lên vào phía trước (phía dưới con này) thì bị khiên chặn."""
        return bullet.vy > 0 and bullet.y > self.y and abs(bullet.x - self.x) < 34

    def update(self, player=None) -> None:
        self.age += 1
        if self.y < self.target_y:
            self.y += 3
            return
        self.y += 0.25
        self.x += self.dx
        if self.x < 50 or self.x > WIDTH - 50:
            self.dx *= -1


# --- Kẻ Đẻ Trứng ---------------------------------------------------------------------------
class Breeder(EnemyBase):
    ai = "breeder"
    threat = 3.0
    sprite = "breeder"
    sprite_width = 84
    score = 30

    def __init__(self, difficulty: float, x: float, target_y: float, rng=random) -> None:
        super().__init__(hp=110 * difficulty, radius=32)
        self.x, self.y, self.target_y = x, -70, target_y
        self.dx = rng.choice([-0.6, 0.6])
        self.shoot_timer = rng.randint(150, 220)       # = nhịp đẻ Ký Sinh
        self.difficulty = difficulty

    def update(self, player=None) -> None:
        self.age += 1
        if self.y < self.target_y:
            self.y += 2
            return
        self.y += 0.15
        self.x += self.dx
        if self.x < 60 or self.x > WIDTH - 60:
            self.dx *= -1

    def offspring(self, rng):
        """Chết thì vỡ ra 4 Ký Sinh nhỏ."""
        return [Parasite(self.difficulty, self.x + rng.randint(-25, 25), self.y, rng=rng, small=True) for _ in range(4)]


# --- Pháo tháp -------------------------------------------------------------------------------
class Turret(EnemyBase):
    ai = "turret"
    threat = 2.0
    sprite = "turret_base"
    sprite_width = 80
    score = 30
    WARN_TICKS = 50

    def __init__(self, difficulty: float, x: float, target_y: float, rng=random) -> None:
        super().__init__(hp=90 * difficulty, radius=34)
        self.x, self.y, self.target_y = x, -60, target_y
        self.aim = 90.0              # độ (90 = chĩa thẳng xuống)
        self.warning = 0             # > 0: đang hiện vạch cảnh báo, sắp bắn
        self.shoot_timer = rng.randint(60, 120)

    def update(self, player=None) -> None:
        self.age += 1
        if self.y < self.target_y:
            self.y += 3
        else:
            self.y += 0.2
        if player is not None and self.warning == 0:     # đang cảnh báo thì khóa hướng
            want = math.degrees(math.atan2(player.y - self.y, player.x - self.x))
            diff = (want - self.aim + 180) % 360 - 180
            self.aim += max(-2.5, min(2.5, diff))

    def draw(self, surface: pygame.Surface, assets) -> None:
        if self.warning > 0:
            rad = math.radians(self.aim)
            end = (self.x + math.cos(rad) * 900, self.y + math.sin(rad) * 900)
            k = 1 - self.warning / self.WARN_TICKS
            pygame.draw.line(surface, (int(120 + 135 * k), 20, 20), (self.x, self.y), end, 1 + int(2 * k))
        self._draw_sprite(surface, assets)
        gun = assets.image("turret_gun", 10)
        if gun is not None:
            rotated = pygame.transform.rotate(gun, -(self.aim - 90))
            surface.blit(rotated, rotated.get_rect(center=(int(self.x), int(self.y))))
        self._draw_hp_bar(surface, 40, self.radius + 8)


# --- Tàu đồng minh bị nhiễm -----------------------------------------------------------------
class InfectedAlly(EnemyBase):
    ai = "ally"
    threat = 2.0
    sprite = "infected_ally"
    sprite_width = 90
    score = 20

    def __init__(self, difficulty: float, x: float, target_y: float, rng=random) -> None:
        super().__init__(hp=45 * difficulty, radius=22)
        self.rx, self.ry = 38, 20
        self.base_x, self.x, self.y, self.target_y = x, x, -50, target_y
        self.phase = rng.uniform(0, math.pi * 2)
        self.shoot_timer = rng.randint(60, 110)

    def update(self, player=None) -> None:
        self.age += 1
        if self.y < self.target_y:
            self.y += 6
        else:
            self.y += 0.35
        self.x = max(40, min(WIDTH - 40, self.base_x + math.sin(self.age * 0.035 + self.phase) * 150))


# --- Hồi IV · Bóng KX --------------------------------------------------------------------------
SHADOW_COLOR = (170, 110, 255)


class ShadowKX(EnemyBase):
    """Bóng KX: Đàn học cách bạn lái. Bay ở hàng trên và lặp lại ĐÚNG vị trí ngang của tàu bạn ``delay`` giây
    trước, bắn thẳng xuống mỗi 0,8 giây (đạn cùng màu súng bạn đang cầm). Đứng yên quá ``delay`` giây = nó nằm
    ngay trên đầu bạn. Không rơi đồ, chết thì tan thành hạt tím."""

    ai = "shadow"
    threat = 1.5
    sprite = "shadow_kx"
    sprite_width = 84
    score = config.SHADOW_SCORE
    drops = False
    death_fx = "dissolve"

    def __init__(self, difficulty: float, delay_seconds: float = 2.0, row: int = 0, rng=random) -> None:
        super().__init__(hp=config.SHADOW_HP * difficulty, radius=22)
        self.rx, self.ry = 34, 22
        self.delay = max(1, min(config.SHADOW_MAX_DELAY_TICKS, int(delay_seconds * config.TICK_RATE)))
        self.hover_y = config.SHADOW_HOVER_Y + row * 24
        self.x, self.y = WIDTH / 2, -50.0
        self.shoot_timer = config.SHADOW_FIRE_TICKS + rng.randint(0, 20)
        self.weapon = "laser"
        self.trail: list = []           # vài vị trí cũ để vẽ bóng mờ đuổi theo (cảm giác "tiếng vọng")

    @property
    def arrived(self) -> bool:
        return self.y >= self.hover_y - 1

    def replay_x(self, player) -> float:
        hist = player.x_history
        if not hist:
            return player.x
        return hist[-self.delay] if len(hist) >= self.delay else hist[0]

    def update(self, player=None) -> None:
        self.age += 1
        if self.y < self.hover_y:
            self.y = min(self.hover_y, self.y + 4)
        if player is not None:
            self.x = self.replay_x(player)
            self.weapon = player.weapon
        if self.age % 3 == 0:
            self.trail.append((self.x, self.y))
            del self.trail[:-4]

    def draw(self, surface: pygame.Surface, assets) -> None:
        sprite = assets.image(self.sprite, self.sprite_width)
        for i, (tx, ty) in enumerate(self.trail[:-1]):          # bóng mờ phía sau: tiếng vọng của đường bay
            if sprite is not None and abs(tx - self.x) > 3:
                ghost = sprite.copy()
                ghost.set_alpha(30 + 25 * i)
                surface.blit(ghost, ghost.get_rect(center=(int(tx), int(ty))))
        glow.add(surface, glow.orb(glow.scale(SHADOW_COLOR, 0.45), 26, core=0.0, halo=1.4), (self.x, self.y))
        self._draw_sprite(surface, assets)
        self._draw_hp_bar(surface, 34, 30)

    def draw_halo(self, surface: pygame.Surface) -> None:
        """Quầng tím mờ (vẽ trên lớp tối ở ải 14: thấy lờ mờ bóng trong bóng tối)."""
        glow.add(surface, glow.orb(glow.scale(SHADOW_COLOR, 0.5), 22, core=0.25, halo=1.5), (self.x, self.y))


# --- Chướng ngại -----------------------------------------------------------------------------
class Meteor(EnemyBase):
    is_meteor = True
    sprite = "meteor"
    score = config.SCORE_METEOR
    counts_as_kill = False

    def __init__(self, difficulty: float, rng=random) -> None:
        radius = rng.randint(30, 70)
        super().__init__(hp=150 * difficulty, radius=radius)
        self.sprite_width = int(radius * 2.5)
        self.x = rng.randint(30, WIDTH - 30)
        self.y = rng.randint(-100, -40)
        self.speed = rng.uniform(3, 6)
        self.dx = rng.uniform(-2, 2)
        self.angle = 0.0
        self.spin = rng.uniform(-4, 4)

    def update(self, player=None) -> None:
        self.age += 1
        self.y += self.speed
        self.x += self.dx
        self.angle += self.spin

    def draw(self, surface: pygame.Surface, assets) -> None:
        self._draw_sprite(surface, assets, angle=self.angle)
        self._draw_hp_bar(surface, 30, self.radius + 10)


class Wreck(EnemyBase):
    """Xác tàu trôi: núp sau nó để tránh đạn địch. Bắn nát được (cứng)."""

    is_meteor = True              # va chạm nặng như thiên thạch
    is_obstacle = True
    score = config.SCORE_WRECK
    counts_as_kill = False

    def __init__(self, difficulty: float, x: float, rng=random, variant: int = 1, carries: Optional[str] = None) -> None:
        big = variant == 1
        super().__init__(hp=260 * difficulty, radius=50 if big else 42)
        self.sprite = f"wreck_{variant}"
        self.sprite_width = 200 if big else 110
        self.rx, self.ry = (90, 40) if big else (46, 80)
        self.x, self.y = x, -120
        self.speed = rng.uniform(0.9, 1.3)
        self.dx = rng.uniform(-0.3, 0.3)
        self.carries = carries        # vật phẩm giấu trong xác tàu (vd. súng Tia Sét)

    def update(self, player=None) -> None:
        self.age += 1
        self.y += self.speed
        self.x += self.dx

    def draw(self, surface: pygame.Surface, assets) -> None:
        self._draw_sprite(surface, assets)
        if self.carries and (self.age // 15) % 2 == 0:           # nhấp nháy: có đồ bên trong
            pygame.draw.circle(surface, (255, 230, 60), (int(self.x), int(self.y)), 10, 2)
        self._draw_hp_bar(surface, 50, self.ry + 8)


# --- Boss --------------------------------------------------------------------------------
@dataclass(frozen=True)
class BossSpec:
    title: str
    sprite: str
    width: int
    hp: float
    rx: int
    ry: int
    tier: int                 # nhân điểm thưởng
    shield: float = 0.0       # tỉ lệ khiên ban đầu (so với máu)
    hover_y: int = 150
    rages: bool = False       # dưới 50% máu thì điên cuồng (bắn nhanh gấp đôi)


BOSS_SPECS = {
    "crab": BossSpec("KẺ NUỐT DRONE", "boss", 200, 600, 75, 45, 1),
    "octopus": BossSpec("LÍNH GÁC TINH VÂN", "boss2", 220, 900, 80, 45, 2),
    "spider": BossSpec("LÕI TINH VÂN", "boss3", 250, 1800, 95, 55, 3, shield=1 / 3, rages=True),
    "nest": BossSpec("TỔ MẸ", "nest_mother", 270, 1300, 110, 60, 2, hover_y=140),
    "cruiser": BossSpec("TÀU HỘ TỐNG", "escort_cruiser", 170, 1700, 70, 130, 3, hover_y=165),
    "mothership": BossSpec("TÀU MẸ HY VỌNG", "mothership_boss", 460, 3200, 200, 80, 5, shield=1 / 4,
                           hover_y=185, rages=True),
    # Hồi IV (đợt 1: tạm dùng kiểu đánh của boss cũ, xem docs/design/hoi-4.md)
    "storm_eye": BossSpec("MẮT BÃO", "storm_eye", 300, 1800, 100, 70, 3, hover_y=170),
    "listener": BossSpec("KẺ NGHE", "listener", 300, 1600, 110, 60, 3, hover_y=150),
    "swarm_heart": BossSpec("TRÁI TIM ĐÀN", "swarm_heart", 480, 4200, 210, 90, 6, shield=1 / 4,
                            hover_y=185, rages=True),
}
STAGE_KIND = {1: "crab", 2: "octopus", 3: "spider"}
#: Boss nhỏ giữa hồi (thẻ "MINI-BOSS", dấu thoi nhỏ trên bản đồ)
MINI_BOSSES = frozenset({"nest", "cruiser", "storm_eye", "listener"})
#: Trận cuối của một hồi lớn: nhạc trận cuối
FINAL_BOSSES = frozenset({"mothership", "swarm_heart"})


class Boss(EnemyBase):
    is_boss = True
    counts_as_kill = False

    def __init__(self, difficulty: float, stage: int = 1, kind: Optional[str] = None) -> None:
        stage = max(1, min(3, stage))
        self.kind = kind or STAGE_KIND[stage]
        self.spec = spec = BOSS_SPECS[self.kind]
        super().__init__(hp=spec.hp * difficulty, radius=min(spec.rx, spec.ry) + 15)
        self.rx, self.ry = spec.rx, spec.ry
        self.stage = stage
        self.sprite, self.sprite_width = spec.sprite, spec.width
        self.score = config.SCORE_BOSS_PER_STAGE * spec.tier
        self.x, self.y = WIDTH // 2, -spec.ry - 40
        self.speed = 1.5
        self.dx = 2.5 if self.kind != "mothership" else 1.2
        self.spiral_angle = 0
        self.shield_rotation = 0
        self.shield_flash = 0           # > 0: khiên vừa đỡ đòn -> sáng bừng
        self.shield_regen = 0           # > 0: khiên vừa hồi lại (chuyển pha) -> lớp tổ ong mọc lan ra
        self.attack_cooldown = 60
        self.phase = 1
        self.minion_timer = 0
        self.difficulty = difficulty
        if spec.shield:
            self.max_shield = self.shield_hp = self.max_hp * spec.shield

    @property
    def title(self) -> str:
        return self.spec.title

    @property
    def hp_ratio(self) -> float:
        return max(0.0, self.hp / self.max_hp)

    @property
    def raging(self) -> bool:
        return self.spec.rages and self.hp_ratio < 0.5

    @property
    def arrived(self) -> bool:
        return self.y >= self.spec.hover_y

    def update(self, player=None) -> None:
        self.age += 1
        if not self.arrived:
            self.y += self.speed
        else:
            self.x += self.dx * (2.0 if self.raging else 1.0)
            margin = max(100, self.spec.width // 2 - 40)
            if self.x < margin or self.x > WIDTH - margin:
                self.dx *= -1
                self.x = max(margin, min(WIDTH - margin, self.x))
        self.shield_rotation += 5
        if self.shield_flash > 0:
            self.shield_flash -= 1
        if self.shield_regen > 0:
            self.shield_regen -= 1

    def draw(self, surface: pygame.Surface, assets) -> None:
        if assets.image(self.sprite, self.sprite_width) is None:
            pygame.draw.circle(surface, NEON_MAGENTA, (int(self.x), int(self.y)), self.radius, 3)
        else:
            flash = self.raging and (self.age // 6) % 2 == 0
            self._draw_sprite(surface, assets, add=flash)
        if self.shield_hp > 0:                       # khiên trùm lên thân boss như một vòm năng lượng
            shields.draw_boss_shield(surface, self)
