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
from spaceship.entities.effects import DamageNumber, Flash, FloatText, Shockwave
from spaceship.entities.enemies import EnemyBase
from spaceship.systems import loot
from spaceship.systems.world import World
from spaceship.ui import shields

HIT_SPARK = {"plasma": (120, 200, 255), "laser": (255, 120, 100), "homing": (220, 140, 255), "drone_bolt": (255, 170, 60)}
BLOCK_SPARK = (120, 220, 255)
BURN_ORANGE = (255, 100, 0)
SHIELD_SPARK = (100, 255, 255)
PLAYER_BULLET_RADIUS = config.PLAYER_HITBOX
PLAYER_BODY_RADIUS = 20


# --- Khiên -------------------------------------------------------------------------
def shield_break(world: World, boss) -> None:
    """Khiên boss vỡ: mảnh tổ ong văng ra, sóng xung kích, chữ "KHIÊN VỠ!", khựng hình + rung."""
    rx, ry = shields.boss_shield_axes(boss)
    shields.shatter(world.particles, boss.x, boss.y, rx, ry, shields.BOSS_SHIELD_COLOR, 36, 10, 7, rng=world.rng)
    world.particles.append(Shockwave(boss.x, boss.y, shields.BOSS_SHIELD_COLOR, max_radius=rx * 1.35, life=22))
    world.particles.append(Flash(boss.x, boss.y, (255, 220, 150), radius=60, life=12))
    world.damage_numbers.append(FloatText(boss.x, boss.y + ry * 0.4, "KHIÊN VỠ!", (255, 190, 90), size=30))
    world.freeze(config.HITSTOP_SHIELD_BREAK)
    world.shake(12)
    world.flash = 2
    world.play("shield_break")


def _boss_shield_ripple(world: World, enemy, x: float, y: float, laser: bool = False) -> None:
    """Đạn trúng khiên boss: gợn sóng ở đúng chỗ trúng trên viền khiên (laser: to và tóe lửa hơn)."""
    if not enemy.is_boss or enemy.shield_hp <= 0:
        return
    rx_, ry_ = shields.boss_rim_point(enemy, x, y)
    world.particles.append(shields.ShieldRipple(rx_, ry_, shields.BOSS_SHIELD_COLOR, size=1.4 if laser else 1.0))
    if laser:
        world.sparks(rx_, ry_, (255, 200, 120), 3)


def tick_player_fx(world: World) -> None:
    """Hiệu ứng theo trạng thái tàu (gọi sau ``Player.tick_timers``): khiên hết giờ thì vỡ, hồi sinh có tiếng."""
    p = world.player
    if p.shield_ended:
        r = shields.PLAYER_SHIELD_RADIUS
        shields.shatter(world.particles, p.x, p.y, r, r, shields.PLAYER_SHIELD_COLOR, 16, 6, 4, rng=world.rng)
        world.play("shield_break")
    if p.respawn_glow:
        if p.warp_timer == config.RESPAWN_WARP_TICKS - 8:
            world.play("warp_in")
        if p.warp_timer == 0 and p.invincible_timer in (30, 20, 10):    # sắp hết bất tử: tích - tích - tích
            world.play("tick")


# --- Sát thương ---------------------------------------------------------------------
def damage_enemy(world: World, enemy: EnemyBase, amount: float, *, crit: bool = False, gain_rage: bool = True) -> None:
    player = world.player
    amount *= getattr(enemy, "damage_mult", 1.0)  # Trái Tim Đàn pha 3: lõi bọc giáp / lõi lộ ra
    enemy.hit_flash = 4                           # nháy trắng vài tick: cảm giác "trúng"
    enemy.hp_bar_timer = 90
    world.play("hit")
    if player.burn_unlocked:
        enemy.burning = True
    if enemy.is_boss and amount >= 3:             # sát thương lắt nhắt (tia liên tục) không hiện số cho đỡ rối
        world.damage_numbers.append(DamageNumber(enemy.x, enemy.y, amount, crit, rng=world.rng))
    if enemy.shield_hp > 0:                       # khiên hấp thụ trước, phần dư trừ vào máu
        enemy.shield_hp -= amount
        if enemy.is_boss:
            enemy.shield_flash = 6
        if enemy.shield_hp < 0:
            enemy.hp += enemy.shield_hp
            enemy.shield_hp = 0
        if enemy.shield_hp <= 0 and enemy.is_boss:
            shield_break(world, enemy)
    else:
        before = enemy.hp
        enemy.hp -= amount
        # Boss: mỗi khi mất thêm 10% máu có 25% cơ hội rơi đồ
        if enemy.is_boss and enemy.hp > 0 and int(before / enemy.max_hp * 10) > int(enemy.hp / enemy.max_hp * 10):
            if world.rng.random() < 0.25 * world.drop_mult:
                world.drop(enemy.x, enemy.y, loot.boss_chunk_drop(world))
    if gain_rage:
        player.add_rage(config.RAGE_PER_HIT)


def damage_player(world: World, amount: float) -> None:
    player = world.player
    player.hp -= amount
    world.break_combo()
    world.shake(10)
    world.hurt_timer = config.HURT_VIGNETTE_TICKS
    if player.hp > 0:
        world.play("player_hurt")
        world.freeze(config.HITSTOP_HURT)
        # bất tử ngắn: một chùm đạn sát nhau không rút sạch máu trong vài tick
        player.invincible_timer = max(player.invincible_timer, config.MERCY_TICKS)
        return
    world.lives_lost += 1
    world.freeze(config.HITSTOP_LIFE_LOST)
    if player.lives > 1:
        player.lives -= 1
        player.respawn()
        world.play("explode_big")
        world.explode(player.x, player.y, 1.5)
    else:
        player.lives = 0
        world.outcome = "defeat"


def kill_enemy(world: World, enemy: EnemyBase) -> None:
    """Điểm, hiệu ứng, rơi đồ cho MỌI cái chết của địch."""
    if enemy in world.enemies:
        world.enemies.remove(enemy)
    world.score += enemy.score * world.combo_mult
    if enemy.counts_as_kill or enemy.is_boss:
        world.add_combo()
    if enemy.is_boss:
        world.play("explode_boss")
        for dx, dy, size in ((0, 0, 3.0), (-50, -20, 1.6), (55, 15, 1.6), (-20, 40, 1.2), (30, -40, 1.2)):
            world.explode(enemy.x + dx, enemy.y + dy, size)
        world.boss_kills += 1
        world.cancel_enemy_bullets()
        world.shake(20)
        world.freeze(config.HITSTOP_BOSS)
        world.defeated_bosses.append(enemy)
        return
    if enemy.death_fx == "dissolve":              # Bóng KX / tàu ma: tan thành hạt, không nổ lửa
        world.play("glitch")
        world.burst(enemy.x, enemy.y, getattr(enemy, "dissolve_color", (170, 110, 255)), 14, speed_scale=0.7)
        world.burst(enemy.x, enemy.y, (230, 200, 255), 6, speed_scale=0.4)
        world.sparks(enemy.x, enemy.y, (200, 160, 255), 5)
        if enemy.counts_as_kill:
            world.kills += 1
        return
    big = enemy.is_meteor or enemy.is_obstacle or enemy.radius >= 28   # Lính Khiên, Kẻ Đẻ Trứng, Pháo tháp...
    world.play("explode_big" if big else "explode_small")
    if big and not enemy.is_meteor and not enemy.is_obstacle:
        world.freeze(config.HITSTOP_ELITE)
        world.shake(4)
    world.explode(enemy.x, enemy.y, 1.5 if enemy.is_meteor else (0.6 if enemy.radius < 14 else 1.0))
    if hasattr(enemy, "offspring"):                # Kẻ Đẻ Trứng vỡ ra Ký Sinh
        world.enemies.extend(enemy.offspring(world.rng))
    if getattr(enemy, "carries", None):           # xác tàu giấu đồ
        world.drop(enemy.x, enemy.y, enemy.carries)
    if enemy.counts_as_kill:
        world.kills += 1
        if enemy.drops:
            world.drop(enemy.x, enemy.y, loot.drop_for_kill(world))
    elif world.rng.random() < 0.05 * world.drop_mult:
        world.drop(enemy.x, enemy.y, loot.boss_chunk_drop(world))


def reap_dead(world: World) -> None:
    for enemy in [e for e in world.enemies if e.dead]:
        kill_enemy(world, enemy)


# --- Đạn người chơi ---------------------------------------------------------------------
def _splash(world: World, x: float, y: float, damage: float, skip_id: int) -> None:
    """Plasma cấp 6: nổ lan sang địch xung quanh."""
    world.particles.append(Flash(x, y, (120, 200, 255), radius=18, life=6))
    for enemy in world.enemies:
        if enemy.id != skip_id and math.hypot(enemy.x - x, enemy.y - y) < config.PLASMA_SPLASH_RADIUS + enemy.radius:
            damage_enemy(world, enemy, damage * config.PLASMA_SPLASH_SHARE, gain_rage=False)


def resolve_player_bullets(world: World) -> None:
    player = world.player
    for bullet in list(world.bullets):
        if bullet.is_piercing_laser:
            dmg = config.PIERCING_LASER_DAMAGE + player.bonus_damage * config.PIERCING_LASER_BONUS_SHARE
            for enemy in world.enemies:
                if enemy.id not in bullet.hit_ids and bullet.hits(enemy):
                    bullet.hit_ids.add(enemy.id)
                    _boss_shield_ripple(world, enemy, bullet.x, enemy.y + enemy.ry, laser=True)
                    damage_enemy(world, enemy, dmg, crit=True)
                    world.sparks(enemy.x, enemy.y + enemy.ry * 0.6, HIT_SPARK["laser"], 6)
        else:
            for enemy in world.enemies:
                if not bullet.hits(enemy):
                    continue
                world.bullets.remove(bullet)
                if enemy.front_shield and enemy.blocks(bullet):      # Lính Khiên chặn đạn bắn thẳng
                    world.sparks(bullet.x, bullet.y, BLOCK_SPARK, 3)
                    world.play("shield_block")
                    break
                _boss_shield_ripple(world, enemy, bullet.x, bullet.y, laser=bullet.kind == "laser")
                skill_shot = bullet.damage is not None           # tên lửa của kỹ năng Nộ: không hồi Nộ
                if skill_shot:
                    dmg = bullet.damage
                else:
                    dmg = min(50, config.WEAPON_BASE_DAMAGE.get(bullet.kind, 6) + player.bonus_damage)
                damage_enemy(world, enemy, dmg, crit=bullet.kind == "plasma", gain_rage=not skill_shot)
                world.sparks(bullet.x, bullet.y, HIT_SPARK.get(bullet.kind, NEON_CYAN), 4)
                if skill_shot:                                   # tên lửa Nộ: trúng đâu nổ cam tới đó
                    world.explode(bullet.x, bullet.y, 0.6)
                if bullet.kind == "plasma" and bullet.level == 6:
                    _splash(world, bullet.x, bullet.y, dmg, enemy.id)
                break


# --- Đạn địch & va chạm thân --------------------------------------------------------------
def resolve_enemy_bullets(world: World) -> None:
    player = world.player
    obstacles = [e for e in world.enemies if e.is_obstacle]
    # Ải hộ tống: thân tàu (không chỉ điểm va chạm) che đạn cho tàu cứu sinh - chạm thân là đạn tan,
    # kể cả lúc đang bất tử; chỉ trúng điểm va chạm khi không bất tử mới mất máu như thường.
    cover = getattr(world.mechanic, "cover_radius", 0)
    for bullet in list(world.enemy_bullets):
        if obstacles and any(o.contains(bullet.x, bullet.y) for o in obstacles):   # núp sau xác tàu
            world.enemy_bullets.remove(bullet)
            world.sparks(bullet.x, bullet.y, (200, 200, 200), 2)
            continue
        dist = math.hypot(player.x - bullet.x, player.y - bullet.y)
        if cover and dist < cover and not player.shield_active and \
                (dist >= PLAYER_BULLET_RADIUS or player.invincible_timer > 0):
            world.enemy_bullets.remove(bullet)
            world.sparks(bullet.x, bullet.y, (200, 230, 255), 3)
            continue
        if dist >= PLAYER_BULLET_RADIUS:
            if dist < config.GRAZE_RADIUS and not bullet.grazed and player.invincible_timer <= 0:
                _graze(world, bullet)
            continue
        if player.shield_active:
            world.enemy_bullets.remove(bullet)
            rx_, ry_ = shields.player_rim_point(player.x, player.y, bullet.x, bullet.y)
            world.particles.append(shields.ShieldRipple(rx_, ry_, shields.PLAYER_SHIELD_COLOR))
            world.sparks(rx_, ry_, NEON_CYAN, 4)
            world.play("shield_block")
        elif player.invincible_timer <= 0:
            world.enemy_bullets.remove(bullet)
            damage_player(world, config.ENEMY_BULLET_DAMAGE.get(bullet.kind, config.ENEMY_BULLET_DAMAGE_DEFAULT))
            if world.outcome:
                return


def _graze(world: World, bullet) -> None:
    """Đạn sượt qua tàu: thưởng điểm (theo hệ số chuỗi), giữ chuỗi sống, tia sáng nhỏ."""
    bullet.grazed = True
    world.grazes += 1
    world.score += config.GRAZE_SCORE * world.combo_mult
    if world.combo:
        world.combo_timer = config.COMBO_WINDOW_TICKS
    world.sparks(bullet.x, bullet.y, (255, 255, 255), 2)
    world.play("graze")


def resolve_body_collisions(world: World) -> None:
    player = world.player
    for enemy in list(world.enemies):
        if enemy.y < -20 or not enemy.contains(player.x, player.y, PLAYER_BODY_RADIUS):
            continue
        if player.shield_active:
            if not enemy.is_boss and not enemy.is_obstacle:   # khiên húc chết địch thường → tính là hạ địch
                rx_, ry_ = shields.player_rim_point(player.x, player.y, enemy.x, enemy.y)
                world.particles.append(shields.ShieldRipple(rx_, ry_, shields.PLAYER_SHIELD_COLOR, size=1.5))
                enemy.hp = 0
                kill_enemy(world, enemy)
                world.burst(enemy.x, enemy.y, SHIELD_SPARK, 15)
        elif player.invincible_timer <= 0:
            heavy = enemy.is_boss or enemy.is_meteor
            if not enemy.is_boss and not enemy.is_obstacle:   # đâm vào nhau: địch nổ nhưng không được điểm
                world.enemies.remove(enemy)
                world.play("explode_small")
                world.explode(enemy.x, enemy.y, 1.0)
            damage_player(world, config.HEAVY_COLLISION_DAMAGE if heavy else config.COLLISION_DAMAGE)
            if enemy.is_obstacle or enemy.is_boss:
                player.invincible_timer = max(player.invincible_timer, 45)   # tránh bị trừ máu liên tục mỗi tick
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
PERK_NAMES = {"upgrade_drone": "NHẬN ĐƯỢC DRONE", "upgrade_burn": "ĐẠN THIÊU ĐỐT"}


def collect_items(world: World) -> None:
    player = world.player
    for item in list(world.items):
        if math.hypot(player.x - item.x, player.y - item.y) >= config.ITEM_PICKUP_RADIUS:
            continue
        world.items.remove(item)
        kind = item.kind
        if kind == "upgrade_drone":
            world.play("level_up")
            player.drones = min(2, player.drones + 1)
            world.announce("NHẬN ĐƯỢC DRONE" if player.drones == 1 else "DRONE HỘ VỆ: CHẶN ĐẠN ĐỊCH", 2.0)
        elif kind == "upgrade_burn":
            player.burn_unlocked = True
            world.play("level_up")
            world.announce("ĐẠN THIÊU ĐỐT", 2.0)
        elif kind == "heal":
            world.play("pickup")
            player.hp = min(player.max_hp, player.hp + config.HEAL_AMOUNT[world.mode])
        elif kind == "shield":
            if not player.shield_active:                     # bật mới: bong bóng nở ra từ tàu
                player.shield_age = 0
                world.particles.append(Shockwave(player.x, player.y, shields.PLAYER_SHIELD_COLOR,
                                                 max_radius=shields.PLAYER_SHIELD_RADIUS + 30, life=14))
            world.play("shield_up")
            player.shield_timer = config.SHIELD_TICKS[world.mode]
        else:
            weapon = kind.replace("upgrade_", "")
            switched = weapon not in ("universal", player.weapon)
            # Đổi súng khi đang cấp cao = mất cấp: tiếng "hụt" cho đúng cảm giác cay cú
            world.play(("wrong_weapon" if player.level > 1 else "pickup") if switched else "level_up")
            player.apply_weapon_pickup(weapon)
            if switched:
                world.announce(config.WEAPON_NAMES.get(weapon, weapon.upper()), 1.0)


def cleanup(world: World) -> None:
    world.bullets[:] = [b for b in world.bullets if b.on_screen]
    world.enemy_bullets[:] = [b for b in world.enemy_bullets if b.on_screen]
    world.items[:] = [i for i in world.items if i.on_screen]
    world.particles[:] = [p for p in world.particles if p.alive]
    world.damage_numbers[:] = [d for d in world.damage_numbers if d.alive]
    world.enemies[:] = [e for e in world.enemies if e.is_boss or (e.y <= HEIGHT + e.ry + 40 and not e.gone)]
