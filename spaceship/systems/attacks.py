"""AI tấn công của địch.

- Lính thường / Lính Khiên / Tàu đồng minh bị nhiễm: bắn theo người chơi.
- Pháo tháp: kẻ vạch đỏ cảnh báo (khóa hướng) rồi mới bắn laser -> né được nếu để ý.
- Kẻ Đẻ Trứng: đẻ Ký Sinh theo nhịp.
- Boss: mỗi loại một bộ chiêu, đổi chiêu theo 3 pha máu. Mỗi pha là một hàm
  nhỏ trả về thời gian hồi chiêu; muốn thêm chiêu chỉ cần thêm hàm.

Tốc độ bắn nhân với ``world.fire_mult`` (độ khó Dễ/Thường/Khó).
"""
from __future__ import annotations

import math

from spaceship import config
from spaceship.config import GameMode
from spaceship.entities.enemies import Boss, Enemy, InfectedAlly, Parasite
from spaceship.entities.projectiles import EnemyBullet
from spaceship.systems.world import World

MAX_PARASITES = 24


def aim(src, dst) -> float:
    return math.degrees(math.atan2(dst.y - src.y, dst.x - src.x))


def _cooldown(world: World, ticks: float) -> int:
    return max(4, int(ticks / world.fire_mult))


def _on_screen(enemy) -> bool:
    return enemy.y > 0


def _hold_fire(world: World, enemy) -> bool:
    """Trần đạn: màn hình đã đủ đạn của lính thì lính chờ một chút rồi mới bắn (đạn boss không tính trần)."""
    if len(world.enemy_bullets) >= config.ENEMY_BULLET_CAP[world.mode]:
        enemy.shoot_timer = 20
        return True
    return False


# --- Lính các loại ---------------------------------------------------------------------------
def grunt_fire(world: World, enemy: Enemy) -> None:
    if not enemy.armed:                            # đang bay vào / vừa tới chỗ: chưa bắn
        return
    enemy.shoot_timer -= 1
    if enemy.shoot_timer > 0 or not _on_screen(enemy) or _hold_fire(world, enemy):
        return
    shots = world.enemy_bullets
    a = aim(enemy, world.player)
    rng = world.rng
    if world.mode is GameMode.INFERNO:
        shots += [EnemyBullet(enemy.x, enemy.y, a - 15, "blue_bullet"),
                  EnemyBullet(enemy.x, enemy.y, a, "normal"),
                  EnemyBullet(enemy.x, enemy.y, a + 15, "blue_bullet")]
        enemy.shoot_timer = _cooldown(world, rng.randint(40, 80))
        return
    style = getattr(enemy, "style", "single")
    if style == "pink":
        shots.append(EnemyBullet(enemy.x, enemy.y, a, "blue_bullet"))
    elif style == "triple":
        shots += [EnemyBullet(enemy.x, enemy.y, a + off, "normal") for off in (-15, 0, 15)]
    else:
        shots.append(EnemyBullet(enemy.x, enemy.y, a, "normal"))
    enemy.shoot_timer = _cooldown(world, rng.randint(80, 150))


def shield_fire(world: World, enemy) -> None:
    enemy.shoot_timer -= 1
    if enemy.shoot_timer > 0 or not _on_screen(enemy) or _hold_fire(world, enemy):
        return
    a = aim(enemy, world.player)
    world.enemy_bullets += [EnemyBullet(enemy.x, enemy.y + 20, a + off, "blue_bullet") for off in (-20, 0, 20)]
    enemy.shoot_timer = _cooldown(world, world.rng.randint(110, 160))


def ally_fire(world: World, enemy) -> None:
    enemy.shoot_timer -= 1
    if enemy.shoot_timer > 0 or not _on_screen(enemy) or _hold_fire(world, enemy):
        return
    a = aim(enemy, world.player)
    world.enemy_bullets += [EnemyBullet(enemy.x + dx, enemy.y + 15, a, "normal") for dx in (-14, 14)]
    enemy.shoot_timer = _cooldown(world, world.rng.randint(70, 120))


def breeder_spawn(world: World, enemy) -> None:
    enemy.shoot_timer -= 1
    if enemy.shoot_timer > 0 or not _on_screen(enemy):
        return
    if sum(isinstance(e, Parasite) for e in world.enemies) < MAX_PARASITES:
        for dx in (-20, 20):
            world.enemies.append(Parasite(world.hp_mult, enemy.x + dx, enemy.y + 20, rng=world.rng, small=True))
    enemy.shoot_timer = _cooldown(world, world.rng.randint(180, 240))


def turret_fire(world: World, enemy) -> None:
    if enemy.warning > 0:                          # đang cảnh báo: đếm xong thì bắn theo hướng đã khóa
        enemy.warning -= 1
        if enemy.warning == 0:
            rad = math.radians(enemy.aim)
            for k in range(3):                     # 3 viên nối đuôi thành một tia
                x = enemy.x + math.cos(rad) * (30 + k * 26)
                y = enemy.y + math.sin(rad) * (30 + k * 26)
                world.enemy_bullets.append(EnemyBullet(x, y, enemy.aim, "laser"))
            enemy.shoot_timer = _cooldown(world, world.rng.randint(140, 200))
        return
    enemy.shoot_timer -= 1
    if enemy.shoot_timer <= 0 and _on_screen(enemy) and not _hold_fire(world, enemy):
        enemy.warning = enemy.WARN_TICKS


ENEMY_AI = {"grunt": grunt_fire, "shield": shield_fire, "ally": ally_fire,
            "breeder": breeder_spawn, "turret": turret_fire}


# --- Boss ---------------------------------------------------------------------------------
def _phase_for(ratio: float) -> int:
    return 3 if ratio <= 0.33 else (2 if ratio <= 0.66 else 1)


#: Boss gọi lính: chỉ gọi khi lính quanh boss còn ít (tránh boss + 20 lính như bản cũ)
BOSS_MINION_THREAT = 6


def _minion_threat(world: World) -> float:
    return sum(e.threat for e in world.enemies if not (e.is_boss or e.is_meteor or e.is_obstacle))


def _summon(world: World, boss: Boss, stage: int, spread: int = 0) -> None:
    if _minion_threat(world) >= BOSS_MINION_THREAT:
        return
    minion = Enemy(world.hp_mult, stage=stage, rng=world.rng)
    minion.x = boss.x + (world.rng.randint(-spread, spread) if spread else 0)
    minion.y = boss.y
    world.enemies.append(minion)


def _crab(world: World, boss: Boss, ratio: float) -> int:
    b = world.enemy_bullets
    b += [EnemyBullet(boss.x, boss.y, ang, "normal") for ang in (80, 90, 100)]
    if ratio < 0.5 and world.rng.random() < 0.3:
        b += [EnemyBullet(boss.x - 30, boss.y, 90, "laser"), EnemyBullet(boss.x + 30, boss.y, 90, "laser")]
    return 50


def _octopus(world: World, boss: Boss, ratio: float) -> int:
    b = world.enemy_bullets
    if ratio > 0.66:                                   # pha 1: xoắn ốc 3 tia
        boss.spiral_angle += 15
        b += [EnemyBullet(boss.x, boss.y, boss.spiral_angle + i * 120, "normal") for i in range(3)]
        return 15
    if ratio > 0.33:                                   # pha 2: gọi lính + bắn tỉa
        if world.rng.random() < 0.05:
            _summon(world, boss, stage=1)
        b.append(EnemyBullet(boss.x, boss.y, aim(boss, world.player), "blue_bullet"))
        return 30
    b += [EnemyBullet(boss.x, boss.y, ang, "laser") for ang in (70, 90, 110)]   # pha 3: laser quạt
    return 45


def _spider(world: World, boss: Boss, ratio: float) -> int:
    b, rng = world.enemy_bullets, world.rng
    if ratio > 0.66:
        boss.spiral_angle += 20
        b += [EnemyBullet(boss.x, boss.y, boss.spiral_angle + i * 90, "blue_bullet") for i in range(4)]
        a = aim(boss, world.player)
        b += [EnemyBullet(boss.x, boss.y, a + off, "normal") for off in (-15, 0, 15)]
        return 20
    if ratio > 0.33:
        for ang in (80, 100):
            b += [EnemyBullet(boss.x - 50, boss.y, ang, "purple_laser"), EnemyBullet(boss.x + 50, boss.y, ang, "purple_laser")]
        if rng.random() < 0.4:
            b.append(EnemyBullet(boss.x, boss.y, rng.randint(45, 135), "boss_homing"))
        return 35
    if rng.random() < 0.1:
        _summon(world, boss, stage=2, spread=50)
    boss.spiral_angle += 13
    for i in range(6):
        b.append(EnemyBullet(boss.x, boss.y, boss.spiral_angle + i * 60, "normal"))
        b.append(EnemyBullet(boss.x, boss.y, -boss.spiral_angle + i * 60, "blue_bullet"))
    if ratio < 0.3 and rng.random() < 0.3:
        b.append(EnemyBullet(boss.x, boss.y, 90, "purple_laser"))
    return 12


def _nest(world: World, boss: Boss, ratio: float) -> int:
    """TỔ MẸ: thả Ký Sinh từ các lỗ tổ + vòng đạn xoay."""
    rng = world.rng
    if sum(isinstance(e, Parasite) for e in world.enemies) < MAX_PARASITES:
        for _ in range(2 if ratio > 0.5 else 3):
            world.enemies.append(Parasite(world.hp_mult, boss.x + rng.randint(-100, 100), boss.y + 30, rng=rng))
    boss.spiral_angle += 17
    count = 10 if ratio > 0.33 else 14
    world.enemy_bullets += [EnemyBullet(boss.x, boss.y + 20, boss.spiral_angle + i * 360 / count, "blue_bullet")
                            for i in range(count)]
    return 55 if ratio > 0.5 else 40


class _Point:
    def __init__(self, x: float, y: float) -> None:
        self.x, self.y = x, y


def _cruiser(world: World, boss: Boss, ratio: float) -> int:
    """TÀU HỘ TỐNG: 2 dàn pháo hai bên bắn theo người chơi, xuất kích tàu nhiễm; pha sau thêm quạt laser."""
    b = world.enemy_bullets
    boss.minion_timer += 1
    for side in (-1, 1):
        gun = _Point(boss.x + side * 50, boss.y + 40)
        a = aim(gun, world.player)
        b += [EnemyBullet(gun.x, gun.y, a + off, "normal") for off in (-6, 6)]
    if boss.minion_timer % 4 == 0 and sum(isinstance(e, InfectedAlly) for e in world.enemies) < 3:
        world.enemies.append(InfectedAlly(world.hp_mult, boss.x, boss.y + 60, rng=world.rng))
    if ratio <= 0.6 and boss.minion_timer % 2 == 0:
        b += [EnemyBullet(boss.x, boss.y + 120, ang, "laser") for ang in (60, 75, 90, 105, 120)]
    return 34 if ratio > 0.6 else 28


def _mothership(world: World, boss: Boss, ratio: float) -> int:
    """TÀU MẸ: pha 1 bắn mạn tàu; pha 2 xoắn ốc + thả Ký Sinh; pha 3 con mắt bắn laser tím + vòng đạn."""
    b, rng = world.enemy_bullets, world.rng
    if ratio > 0.66:
        for side in (-1, 1):
            x = boss.x + side * 150
            b += [EnemyBullet(x, boss.y + 30, 90 + off, "normal") for off in (-20, -10, 0, 10, 20)]
        a = aim(boss, world.player)
        b += [EnemyBullet(boss.x, boss.y + 40, a + off, "blue_bullet") for off in (-12, 0, 12)]
        return 42
    if ratio > 0.33:
        boss.spiral_angle += 14
        b += [EnemyBullet(boss.x, boss.y + 30, boss.spiral_angle + i * 72, "blue_bullet") for i in range(5)]
        boss.minion_timer += 1
        if boss.minion_timer % 12 == 0 and sum(isinstance(e, Parasite) for e in world.enemies) < MAX_PARASITES:
            for dx in (-160, 0, 160):
                world.enemies.append(Parasite(world.hp_mult, boss.x + dx, boss.y + 40, rng=rng))
        return 12
    a = aim(boss, world.player)
    b += [EnemyBullet(boss.x, boss.y + 30, a + off, "purple_laser") for off in (-8, 0, 8)]
    boss.spiral_angle += 9
    b += [EnemyBullet(boss.x, boss.y + 30, boss.spiral_angle + i * 30, "normal") for i in range(12)]
    return 26


def _inferno(world: World, boss: Boss, ratio: float) -> int:
    boss.spiral_angle += 20
    world.enemy_bullets.extend(EnemyBullet(boss.x, boss.y, boss.spiral_angle + i * 45, "normal") for i in range(8))
    if ratio < 0.5:
        world.enemy_bullets.append(EnemyBullet(boss.x, boss.y, aim(boss, world.player), "purple_laser"))
    return 10


BOSS_PATTERNS = {"crab": _crab, "octopus": _octopus, "spider": _spider, "nest": _nest,
                 "cruiser": _cruiser, "mothership": _mothership}
SHIELD_REGEN_KINDS = {"octopus", "spider", "cruiser", "mothership"}


def boss_attack(world: World, boss: Boss) -> None:
    ratio = boss.hp_ratio
    phase = _phase_for(ratio)
    if phase != boss.phase:
        if phase > boss.phase and boss.arrived:
            world.cancel_enemy_bullets()              # chuyển pha: dọn đạn cũ, thưởng điểm, nhịp thở ngắn
        boss.phase = phase
        if boss.kind in SHIELD_REGEN_KINDS:           # chuyển pha -> hồi một lớp khiên
            boss.shield_hp += boss.max_hp * 0.11
            boss.max_shield = max(boss.max_shield, boss.shield_hp)
    if not boss.arrived:
        return
    boss.attack_cooldown -= 1
    if boss.attack_cooldown > 0:
        return
    if world.mode is GameMode.INFERNO and boss.kind != "mothership":
        pattern = _inferno
    else:
        pattern = BOSS_PATTERNS[boss.kind]
    cooldown = pattern(world, boss, ratio)
    boss.attack_cooldown = _cooldown(world, cooldown * (0.5 if boss.raging else 1.0))


def run_enemy_ai(world: World) -> None:
    for enemy in list(world.enemies):
        if enemy.hit_flash > 0:
            enemy.hit_flash -= 1
        if enemy.hp_bar_timer > 0:
            enemy.hp_bar_timer -= 1
        enemy.update(world.player)
        if getattr(enemy, "just_locked", False):
            world.play("lock_on")                     # kamikaze khóa mục tiêu: bíp cảnh báo
        if enemy.is_boss:
            boss_attack(world, enemy)
        elif enemy.ai in ENEMY_AI:
            ENEMY_AI[enemy.ai](world, enemy)
