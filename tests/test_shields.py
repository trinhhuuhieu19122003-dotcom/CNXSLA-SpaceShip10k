"""Khiên tàu, khiên boss và hồi sinh (bản hiệu ứng mới): luật cũ giữ nguyên, hiệu ứng đúng lúc, vẽ không lỗi."""
import math
import random
import unittest

import pygame

from tests import helpers  # noqa: F401  (khởi tạo pygame không màn hình)
from spaceship import config
from spaceship.config import HEIGHT, WIDTH, GameMode
from spaceship.entities.effects import FloatText
from spaceship.entities.enemies import Boss
from spaceship.entities.items import Item
from spaceship.entities.projectiles import EnemyBullet
from spaceship.systems import attacks, combat
from spaceship.systems.world import World
from spaceship.ui import shields


def world():
    return World(mode=GameMode.CAMPAIGN, rng=random.Random(0))


class NoAssets:
    def image(self, *_a, **_k):
        return None


def tick(w, n=1):
    for _ in range(n):
        w.player.tick_timers()
        combat.tick_player_fx(w)


class PlayerShieldTest(unittest.TestCase):
    def test_pickup_opens_bubble_with_sound(self):
        w = world()
        p = w.player
        w.items.append(Item(p.x, p.y, "shield"))
        combat.collect_items(w)
        self.assertEqual(p.shield_timer, config.SHIELD_TICKS[GameMode.CAMPAIGN])      # thời gian khiên giữ nguyên
        self.assertEqual(p.shield_age, 0)
        self.assertIn("shield_up", w.sounds)
        tick(w, 5)
        self.assertEqual(p.shield_age, 5)

    def test_blocked_bullet_ripples_on_the_rim(self):
        w = world()
        p = w.player
        p.shield_timer = 100
        w.enemy_bullets.append(EnemyBullet(p.x + 3, p.y - 5, 90))
        combat.resolve_enemy_bullets(w)
        self.assertEqual(w.enemy_bullets, [])
        self.assertEqual(p.hp, p.max_hp)
        ripple = next(x for x in w.particles if isinstance(x, shields.ShieldRipple))
        self.assertAlmostEqual(math.hypot(ripple.x - p.x, ripple.y - p.y), shields.PLAYER_SHIELD_RADIUS, places=3)

    def test_expiry_shatters_once(self):
        w = world()
        w.player.shield_timer = 3
        tick(w, 6)
        shards = [x for x in w.particles if isinstance(x, shields.HexShard)]
        self.assertEqual(len(shards), 16)
        self.assertEqual(w.sounds.count("shield_break"), 1)
        self.assertFalse(w.player.shield_ended)


class RespawnTest(unittest.TestCase):
    def test_respawn_warps_then_counts_down_with_ticks(self):
        w = world()
        p = w.player
        p.hp = 1
        combat.damage_player(w, 50)
        self.assertEqual(p.invincible_timer, config.RESPAWN_INVINCIBLE_TICKS)        # thời gian bất tử giữ nguyên
        self.assertEqual(p.warp_timer, config.RESPAWN_WARP_TICKS)
        self.assertTrue(p.respawn_glow)
        tick(w, config.RESPAWN_INVINCIBLE_TICKS)
        self.assertEqual(w.sounds.count("warp_in"), 1)
        self.assertEqual(w.sounds.count("tick"), 3)
        self.assertFalse(p.respawn_glow)
        self.assertTrue(p.vulnerable)

    def test_mercy_after_a_normal_hit_is_not_a_respawn(self):
        w = world()
        combat.damage_player(w, 5)
        self.assertGreater(w.player.invincible_timer, 0)
        self.assertFalse(w.player.respawn_glow)
        self.assertEqual(w.player.warp_timer, 0)


class BossShieldTest(unittest.TestCase):
    def boss(self, kind="spider"):
        b = Boss(1.0, 3, kind=kind)
        b.y = b.spec.hover_y
        return b

    def test_hits_flash_then_break_once_with_overflow(self):
        w = world()
        b = self.boss()
        w.enemies.append(b)
        b.shield_hp = 30
        combat.damage_enemy(w, b, 10)
        self.assertEqual(b.shield_flash, 6)
        self.assertEqual(b.shield_hp, 20)
        hp = b.hp
        combat.damage_enemy(w, b, 25)                       # 20 vào khiên, 5 tràn vào máu (luật cũ)
        self.assertEqual(b.shield_hp, 0)
        self.assertEqual(b.hp, hp - 5)
        texts = [d.text for d in w.damage_numbers if isinstance(d, FloatText)]
        self.assertEqual(texts.count("KHIÊN VỠ!"), 1)
        self.assertEqual(w.sounds.count("shield_break"), 1)
        self.assertEqual(w.hitstop, config.HITSTOP_SHIELD_BREAK)
        self.assertGreaterEqual(sum(isinstance(x, shields.HexShard) for x in w.particles), 30)
        combat.damage_enemy(w, b, 10)                       # khiên đã vỡ: không vỡ lần nữa
        self.assertEqual(w.sounds.count("shield_break"), 1)

    def test_bullet_on_shield_ripples_at_rim(self):
        w = world()
        b = self.boss()
        w.enemies.append(b)
        combat._boss_shield_ripple(w, b, b.x + 10, b.y + 300)
        r = next(x for x in w.particles if isinstance(x, shields.ShieldRipple))
        rx, ry = shields.boss_shield_axes(b)
        self.assertAlmostEqual(((r.x - b.x) / rx) ** 2 + ((r.y - b.y) / ry) ** 2, 1.0, places=3)

    def test_phase_change_regrows_shield(self):
        w = world()
        b = self.boss("spider")
        w.enemies.append(b)
        b.shield_hp = 0
        b.hp = b.max_hp * 0.5
        attacks.boss_attack(w, b)
        self.assertGreater(b.shield_hp, 0)
        self.assertEqual(b.shield_regen, shields.BOSS_REGEN_TICKS)
        self.assertIn("shield_up", w.sounds)


class DrawTest(unittest.TestCase):
    def test_player_draws_in_every_state(self):
        surface = pygame.Surface((WIDTH, HEIGHT))
        w = world()
        p = w.player
        p.drones = 2
        p.shield_timer = config.SHIELD_TICKS[GameMode.CAMPAIGN]
        for _ in range(p.shield_timer + 2):
            tick(w)
            p.draw(surface, NoAssets())
        p.hp = 1
        combat.damage_player(w, 50)
        for _ in range(config.RESPAWN_INVINCIBLE_TICKS + 2):
            tick(w)
            p.draw(surface, NoAssets())
        for particle in w.particles:
            particle.draw(surface)

    def test_boss_shield_draws_and_cache_stays_small(self):
        shields.clear_cache()
        surface = pygame.Surface((WIDTH, HEIGHT))
        for kind in ("spider", "mothership", "swarm_heart"):
            b = Boss(1.0, 3, kind=kind)
            b.y = 200
            for i in range(200):
                b.update()
                b.shield_hp = b.max_shield * (1 - i / 200)
                b.shield_flash = 6 if i % 7 == 0 else b.shield_flash
                if i == 50:
                    b.shield_regen = shields.BOSS_REGEN_TICKS
                shields.draw_boss_shield(surface, b)
        big = [k for k, v in shields._cache.items() if isinstance(v, pygame.Surface) and v.get_width() > 300]
        self.assertLessEqual(len(big), 3)                    # mỗi boss chỉ 1 ảnh khiên lớn


if __name__ == "__main__":
    unittest.main()
