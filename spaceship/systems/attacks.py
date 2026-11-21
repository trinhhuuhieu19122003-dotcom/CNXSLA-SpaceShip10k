"""AI tấn công của địch: lính bắn theo người chơi, boss có 3 pha theo % máu.

Mỗi pha boss là một hàm nhỏ trả về thời gian hồi chiêu, thay cho khối if/elif
lồng 5 tầng ở bản cũ. Muốn thêm kiểu tấn công mới chỉ cần thêm một hàm.
"""
from __future__ import annotations

import math

from spaceship.config import GameMode
from spaceship.entities.enemies import Boss, Enemy
from spaceship.entities.projectiles import EnemyBullet
from spaceship.systems.world import World


def aim(src, dst) -> float:
    return math.degrees(math.atan2(dst.y - src.y, dst.x - src.x))


# --- Lính thường ------------------------------------------------------------------------
def grunt_fire(world: World, enemy: Enemy) -> None:
    enemy.shoot_timer -= 1
    if enemy.shoot_timer > 0:
        return
    shots = world.enemy_bullets
    a = aim(enemy, world.player)
    rng = world.rng
    if world.mode is GameMode.INFERNO:
        shots += [EnemyBullet(enemy.x, enemy.y, a - 15, "blue_bullet"),
                  EnemyBullet(enemy.x, enemy.y, a, "normal"),
                  EnemyBullet(enemy.x, enemy.y, a + 15, "blue_bullet")]
        enemy.shoot_timer = rng.randint(40, 80)
        return
    stage, wave = world.stage, world.wave
    if (stage == 2 and wave == 6) or (stage == 3 and wave in (7, 8)):
        shots.append(EnemyBullet(enemy.x, enemy.y, a, "blue_bullet"))
    elif stage == 3 and wave in (4, 5, 6):
        shots += [EnemyBullet(enemy.x, enemy.y, a + off, "normal") for off in (-15, 0, 15)]
    else:
        shots.append(EnemyBullet(enemy.x, enemy.y, a, "normal"))
    enemy.shoot_timer = rng.randint(80, 150)


# --- Boss ---------------------------------------------------------------------------------
def _phase_for(ratio: float) -> int:
    return 3 if ratio <= 0.33 else (2 if ratio <= 0.66 else 1)


def _summon(world: World, boss: Boss, stage: int, spread: int = 0) -> None:
    minion = Enemy(world.difficulty, stage=stage, rng=world.rng)
    minion.x = boss.x + (world.rng.randint(-spread, spread) if spread else 0)
    minion.y = boss.y
    world.enemies.append(minion)


def _stage1(world: World, boss: Boss, ratio: float) -> int:
    b = world.enemy_bullets
    b += [EnemyBullet(boss.x, boss.y, ang, "normal") for ang in (80, 90, 100)]
    if ratio < 0.5 and world.rng.random() < 0.3:
        b += [EnemyBullet(boss.x - 30, boss.y, 90, "laser"), EnemyBullet(boss.x + 30, boss.y, 90, "laser")]
    return 50


def _stage2(world: World, boss: Boss, ratio: float) -> int:
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


def _stage3(world: World, boss: Boss, ratio: float) -> int:
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


def _inferno(world: World, boss: Boss, ratio: float) -> int:
    boss.spiral_angle += 20
    world.enemy_bullets.extend(EnemyBullet(boss.x, boss.y, boss.spiral_angle + i * 45, "normal") for i in range(8))
    if ratio < 0.5:
        world.enemy_bullets.append(EnemyBullet(boss.x, boss.y, aim(boss, world.player), "purple_laser"))
    return 10


STAGE_PATTERNS = {1: _stage1, 2: _stage2, 3: _stage3}


def boss_attack(world: World, boss: Boss) -> None:
    ratio = boss.hp_ratio
    phase = _phase_for(ratio)
    if phase != boss.phase:
        boss.phase = phase
        if boss.stage >= 2:                           # chuyển pha → hồi một lớp khiên
            boss.shield_hp += boss.max_hp * 0.11
            boss.max_shield = max(boss.max_shield, boss.shield_hp)

    boss.attack_cooldown -= 1
    if boss.attack_cooldown > 0:
        return
    pattern = _inferno if world.mode is GameMode.INFERNO else STAGE_PATTERNS[boss.stage]
    cooldown = pattern(world, boss, ratio)
    boss.attack_cooldown = int(cooldown * (0.5 if boss.raging else 1.0))


def run_enemy_ai(world: World) -> None:
    for enemy in list(world.enemies):
        enemy.update(world.player)
        if enemy.is_boss:
            boss_attack(world, enemy)
        elif not enemy.is_meteor:
            grunt_fire(world, enemy)
