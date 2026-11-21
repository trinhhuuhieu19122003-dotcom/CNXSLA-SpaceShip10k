"""Sát thương, va chạm, nhặt đồ — mỗi quy tắc nằm ở ĐÚNG MỘT chỗ.

Bản cũ lặp đoạn "địch chết → cộng điểm → rơi đồ" 4 lần ở 4 nơi khác nhau
(đạn, nuke, va chạm khi có khiên, hết máu), mỗi nơi lệch nhau một chút
(ví dụ nuke giết thiên thạch thì không được điểm). Giờ mọi cái chết đi qua
``kill_enemy``.
"""
from __future__ import annotations

import math

from spaceship import config
from spaceship.config import HEIGHT, NEON_CYAN
from spaceship.entities.effects import DamageNumber
from spaceship.entities.enemies import EnemyBase
from spaceship.systems import loot
from spaceship.systems.world import World

HIT_SPARK = {"plasma": (120, 200, 255), "laser": (255, 120, 100), "homing": (220, 140, 255), "drone_laser": (255, 170, 60)}
BURN_ORANGE = (255, 100, 0)
SHIELD_SPARK = (100, 255, 255)
PLAYER_BULLET_RADIUS = config.PLAYER_HITBOX
PLAYER_BODY_RADIUS = 20


# --- Sát thương ---------------------------------------------------------------------
def damage_enemy(world: World, enemy: EnemyBase, amount: float, *, crit: bool = False, gain_rage: bool = True) -> None:
    player = world.player
    enemy.hit_flash = 4                           # nháy trắng vài tick: cảm giác "trúng"
    if player.burn_unlocked:
        enemy.burning = True
    if enemy.is_boss:
        world.damage_numbers.append(DamageNumber(enemy.x, enemy.y, amount, crit, rng=world.rng))
    if enemy.shield_hp > 0:                       # khiên hấp thụ trước, phần dư trừ vào máu
        enemy.shield_hp -= amount
        if enemy.shield_hp < 0:
            enemy.hp += enemy.shield_hp
            enemy.shield_hp = 0
    else:
        before = enemy.hp
        enemy.hp -= amount
        # Boss: mỗi khi mất thêm 10% máu có 25% cơ hội rơi đồ
        if enemy.is_boss and enemy.hp > 0 and int(before / enemy.max_hp * 10) > int(enemy.hp / enemy.max_hp * 10):
            if world.rng.random() < 0.25:
                world.drop(enemy.x, enemy.y, loot.random_drop(world.mode, world.rng))
    if gain_rage:
        player.add_rage(config.RAGE_PER_HIT)


def damage_player(world: World, amount: float) -> None:
    player = world.player
    player.hp -= amount
    world.shake(10)
    if player.hp > 0:
        return
    if player.lives > 1:
        player.lives -= 1
        player.respawn()
        world.play("explosion")
    else:
        player.lives = 0
        world.outcome = "defeat"


def kill_enemy(world: World, enemy: EnemyBase) -> None:
    """Điểm, hiệu ứng, rơi đồ cho MỌI cái chết của địch."""
    if enemy in world.enemies:
        world.enemies.remove(enemy)
    world.play("explosion")
    if enemy.is_boss:
        for dx, dy, size in ((0, 0, 3.0), (-50, -20, 1.6), (55, 15, 1.6), (-20, 40, 1.2), (30, -40, 1.2)):
            world.explode(enemy.x + dx, enemy.y + dy, size)
    else:
        world.explode(enemy.x, enemy.y, 1.5 if enemy.is_meteor else 1.0)
    if enemy.is_boss:
        world.score += config.SCORE_BOSS_PER_STAGE * enemy.stage
        world.boss_kills += 1
        world.shake(20)
        world.defeated_bosses.append(enemy)
    elif enemy.is_meteor:
        world.score += config.SCORE_METEOR
        if world.rng.random() < 0.05:
            world.drop(enemy.x, enemy.y, loot.random_drop(world.mode, world.rng))
    else:
        world.score += config.SCORE_ENEMY
        world.kills += 1
        world.drop(enemy.x, enemy.y, loot.drop_for_kill(world.mode, world.stage, world.wave, world.rng))


def reap_dead(world: World) -> None:
    for enemy in [e for e in world.enemies if e.dead]:
        kill_enemy(world, enemy)


# --- Đạn người chơi ---------------------------------------------------------------------
def resolve_player_bullets(world: World) -> None:
    player = world.player
    for bullet in list(world.bullets):
        if bullet.kind == "drone_laser":
            for enemy in world.enemies:
                if enemy.id not in bullet.hit_ids and bullet.hits(enemy):
                    bullet.hit_ids.add(enemy.id)
                    damage_enemy(world, enemy, config.DRONE_DAMAGE, gain_rage=False)
                    world.sparks(enemy.x, enemy.y + enemy.radius * 0.6, HIT_SPARK["drone_laser"], 3)
        elif bullet.is_piercing_laser:
            dmg = min(200, config.PIERCING_LASER_DAMAGE + player.bonus_damage)
            for enemy in world.enemies:
                if enemy.id not in bullet.hit_ids and bullet.hits(enemy):
                    bullet.hit_ids.add(enemy.id)
                    damage_enemy(world, enemy, dmg, crit=True)
                    world.sparks(enemy.x, enemy.y + enemy.radius * 0.6, HIT_SPARK["laser"], 6)
        else:
            for enemy in world.enemies:
                if bullet.hits(enemy):
                    base = config.WEAPON_BASE_DAMAGE.get(bullet.kind, 6)
                    damage_enemy(world, enemy, min(50, base + player.bonus_damage), crit=bullet.kind == "plasma")
                    world.sparks(bullet.x, bullet.y, HIT_SPARK.get(bullet.kind, NEON_CYAN), 4)
                    world.bullets.remove(bullet)
                    break


def detonate_nuke(world: World, nuke) -> None:
    world.flash = 6
    world.shake(25)
    world.play("explosion")
    world.explode(nuke.x, nuke.y, 4.0)
    for enemy in list(world.enemies):
        if enemy.is_boss:
            enemy.shield_hp = 0                    # Nuke phá khiên boss
            enemy.hp -= config.NUKE_DAMAGE
            world.damage_numbers.append(DamageNumber(enemy.x, enemy.y, config.NUKE_DAMAGE, True, rng=world.rng))
        else:
            enemy.hp -= config.NUKE_DAMAGE


# --- Đạn địch & va chạm thân --------------------------------------------------------------
def resolve_enemy_bullets(world: World) -> None:
    player = world.player
    for bullet in list(world.enemy_bullets):
        if math.hypot(player.x - bullet.x, player.y - bullet.y) >= PLAYER_BULLET_RADIUS:
            continue
        if player.shield_active:
            world.enemy_bullets.remove(bullet)
            world.sparks(bullet.x, bullet.y, NEON_CYAN, 4)
        elif player.invincible_timer <= 0:
            world.enemy_bullets.remove(bullet)
            damage_player(world, config.ENEMY_BULLET_DAMAGE.get(bullet.kind, config.ENEMY_BULLET_DAMAGE_DEFAULT))
            if world.outcome:
                return


def resolve_body_collisions(world: World) -> None:
    player = world.player
    for enemy in list(world.enemies):
        if math.hypot(player.x - enemy.x, player.y - enemy.y) >= enemy.radius + PLAYER_BODY_RADIUS:
            continue
        if player.shield_active:
            if not enemy.is_boss:                  # khiên húc chết địch thường → tính là hạ địch
                enemy.hp = 0
                kill_enemy(world, enemy)
                world.burst(enemy.x, enemy.y, SHIELD_SPARK, 15)
        elif player.invincible_timer <= 0:
            heavy = enemy.is_boss or enemy.is_meteor
            if not enemy.is_boss:                  # đâm vào nhau: địch nổ nhưng không được điểm
                world.enemies.remove(enemy)
                world.play("explosion")
                world.explode(enemy.x, enemy.y, 1.0)
            damage_player(world, config.HEAVY_COLLISION_DAMAGE if heavy else config.COLLISION_DAMAGE)
            if world.outcome:
                return


def apply_burn(world: World) -> None:
    per_tick = config.BURN_DAMAGE_PER_SECOND * config.TICK
    for enemy in world.enemies:
        if enemy.burning:
            enemy.hp -= per_tick
            if world.rng.random() < 0.1:
                world.spawn_particle(enemy.x + world.rng.randint(-15, 15), enemy.y + world.rng.randint(-15, 15), BURN_ORANGE)


# --- Vật phẩm & dọn dẹp ------------------------------------------------------------------
def collect_items(world: World) -> None:
    player = world.player
    for item in list(world.items):
        if math.hypot(player.x - item.x, player.y - item.y) >= config.ITEM_PICKUP_RADIUS:
            continue
        world.items.remove(item)
        kind = item.kind
        if kind == "upgrade_drone":
            player.has_drone = True
        elif kind == "upgrade_burn":
            player.burn_unlocked = True
        elif kind == "heal":
            player.hp = min(player.max_hp, player.hp + config.HEAL_AMOUNT[world.mode])
        elif kind == "shield":
            player.shield_timer = config.SHIELD_TICKS[world.mode]
        else:
            player.apply_weapon_pickup(kind.replace("upgrade_", ""))


def cleanup(world: World) -> None:
    world.bullets[:] = [b for b in world.bullets if b.on_screen]
    world.enemy_bullets[:] = [b for b in world.enemy_bullets if b.on_screen]
    world.items[:] = [i for i in world.items if i.on_screen]
    world.particles[:] = [p for p in world.particles if p.alive]
    world.damage_numbers[:] = [d for d in world.damage_numbers if d.alive]
    world.enemies[:] = [e for e in world.enemies if e.is_boss or e.y <= HEIGHT + e.radius]
