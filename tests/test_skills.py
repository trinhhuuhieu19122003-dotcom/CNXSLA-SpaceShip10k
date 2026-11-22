"""Kỹ năng Nộ (bản hiệu ứng mới) và drone hộ vệ: đúng luật, đủ sát thương, vẽ không lỗi ở mọi mức hiệu ứng."""
import math
import random
import unittest

import pygame

from tests import helpers  # noqa: F401  (khởi tạo pygame không màn hình)
from spaceship import config
from spaceship.config import HEIGHT, WIDTH, GameMode
from spaceship.entities.enemies import Enemy
from spaceship.entities.projectiles import Bullet, EnemyBullet
from spaceship.systems import combat, weapons
from spaceship.systems.world import World


def world(enemies=4, seed=0):
    w = World(mode=GameMode.CAMPAIGN, rng=random.Random(seed))
    for i in range(enemies):
        e = Enemy(1.0, rng=w.rng, kamikaze_chance=0)
        e.x, e.y = 250 + i * 100, 380
        e.hp = e.max_hp = 10_000                 # sống sót hết chiêu để đếm sát thương
        w.enemies.append(e)
    return w


def run(w, skill, ticks=None):
    for _ in range(ticks if ticks is not None else skill.ticks):
        skill.update(w)
        for b in list(w.bullets):
            b.update(w.enemies)
        combat.resolve_player_bullets(w)


class PlasmaNovaTest(unittest.TestCase):
    def test_charge_then_burst_hits_each_enemy_once(self):
        w = world()
        skill = weapons.PlasmaNova(w)
        run(w, skill, weapons.PlasmaNova.CHARGE - 1)
        self.assertTrue(all(e.hp == e.max_hp for e in w.enemies))         # đang tụ lực: chưa nổ
        run(w, skill, skill.ticks - skill.t)
        for e in w.enemies:
            self.assertEqual(e.max_hp - e.hp, config.SKILL_PLASMA_DAMAGE)  # trúng đúng 1 lần

    def test_charge_still_clears_bullets_next_to_ship(self):
        w = world(0)
        p = w.player
        near = EnemyBullet(p.x + 40, p.y - 30, 90)
        far = EnemyBullet(p.x, 300, 90)
        w.enemy_bullets += [near, far]
        skill = weapons.PlasmaNova(w)
        run(w, skill, 1)
        self.assertNotIn(near, w.enemy_bullets)                            # vẫn cứu nguy ngay lập tức
        self.assertIn(far, w.enemy_bullets)
        run(w, skill, skill.ticks - skill.t)
        self.assertNotIn(far, w.enemy_bullets)                             # nổ xong: sạch đạn


class MissileRainTest(unittest.TestCase):
    def test_locks_then_launches_all_missiles_at_locked_targets(self):
        w = world()
        skill = weapons.MissileRain(w)
        self.assertEqual(sorted(skill.locks), sorted(e.id for e in w.enemies))
        for _ in range(weapons.MissileRain.LOCK - 1):
            skill.update(w)
        self.assertEqual(w.bullets, [])                                    # đang khóa mục tiêu
        for _ in range(skill.ticks - skill.t):
            skill.update(w)
        missiles = [b for b in w.bullets if b.is_skill_missile]
        self.assertEqual(len(missiles), config.SKILL_HOMING_MISSILES)
        self.assertTrue(all(b.damage == config.SKILL_HOMING_DAMAGE for b in missiles))
        self.assertEqual({b.target_id for b in missiles}, set(skill.locks))   # chia đều cho các mục tiêu
        self.assertEqual({round(b.x - w.player.x) for b in missiles}, {-34, 34})  # phóng từ 2 cánh

    def test_missile_follows_its_locked_target_not_the_nearest(self):
        w = world(2)
        near, far = w.enemies
        near.x, near.y, far.x, far.y = 400, 500, 700, 100
        m = Bullet(400, 600, "homing", angle=90, level=3, damage=14)
        m.target_id = far.id
        for _ in range(12):
            m.update(w.enemies)
        self.assertGreater(m.dx, 0)                                        # lái về phía con ở xa đã khóa

    def test_skill_missile_hit_explodes_and_gives_no_rage(self):
        w = world(1)
        e = w.enemies[0]
        w.bullets.append(Bullet(e.x, e.y, "homing", level=3, damage=14))
        before = len(w.particles)
        combat.resolve_player_bullets(w)
        self.assertEqual(e.max_hp - e.hp, 14)
        self.assertGreater(len(w.particles), before + 5)
        self.assertEqual(w.player.rage, 0)

    def test_no_enemies_still_launches(self):
        w = world(0)
        skill = weapons.MissileRain(w)
        for _ in range(skill.ticks):
            skill.update(w)
        self.assertEqual(len(w.bullets), config.SKILL_HOMING_MISSILES)


class LightningStormTest(unittest.TestCase):
    def test_three_strikes_hit_every_enemy(self):
        w = world()
        skill = weapons.LightningStorm(w)
        run(w, skill)
        for e in w.enemies:
            self.assertEqual(e.max_hp - e.hp, 3 * config.SKILL_LIGHTNING_DAMAGE)

    def test_sky_darkens_then_clears(self):
        w = world(0)
        skill = weapons.LightningStorm(w)
        seen = []
        for _ in range(skill.ticks):
            skill.update(w)
            seen.append(skill.darkness)
        self.assertEqual(max(seen), 1.0)
        self.assertLess(seen[-1], 0.1)


class DrawTest(unittest.TestCase):
    def test_every_skill_draws_whole_lifetime_at_every_fx_level(self):
        surface = pygame.Surface((WIDTH, HEIGHT))
        for name in weapons.SKILLS:
            for fx in (1.0, 0.5, 0.0):
                w = world()
                w.player.weapon = name
                w.player.rage = w.player.max_rage
                skill = weapons.trigger_skill(w)
                while skill.alive:
                    weapons.update_skills(w)
                    for b in list(w.bullets):
                        b.update(w.enemies)
                    for particle in w.particles:
                        particle.update()
                    weapons.draw_skills_back(surface, w, fx)
                    for b in w.bullets:
                        b.draw(surface)
                    for particle in w.particles:
                        particle.draw(surface)
                    weapons.draw_skills(surface, w, fx)

    def test_fx_off_means_no_full_screen_tint(self):
        w = world(0)
        skill = weapons.PlasmaNova(w)
        run(w, skill, weapons.PlasmaNova.CHARGE + 1)
        surface = pygame.Surface((WIDTH, HEIGHT))
        skill.draw(surface, w, fx=0.0)
        self.assertEqual(surface.get_at((5, 5))[:3], (0, 0, 0))           # góc xa: không bị ám xanh
        skill.draw(surface, w, fx=1.0)
        self.assertNotEqual(surface.get_at((5, 5))[:3], (0, 0, 0))

    def test_nova_scaled_blit_handles_offscreen_centers(self):
        surface = pygame.Surface((WIDTH, HEIGHT))
        from spaceship.ui import glow
        tex = glow.nova(config.PLASMA_COLOR)
        for center in ((-500, -500), (WIDTH + 900, 100), (400, HEIGHT - 5), (0, 0)):
            for r in (3, 40, 420):
                glow.add_scaled(surface, tex, center, r, 0.5)


class GuardDroneTest(unittest.TestCase):
    def test_orbit_clears_the_ship_and_attack_drone(self):
        w = world(0)
        p = w.player
        p.drones = 2
        half_ship = 50
        for step in range(0, 360, 10):
            p.guard_angle = math.radians(step)
            gx, gy = p.guard_pos
            self.assertGreater(math.hypot(gx - p.x, (gy - p.y) / 0.75), half_ship + 20)
        self.assertGreaterEqual(config.GUARD_ORBIT_RADIUS, 90)


if __name__ == "__main__":
    unittest.main()
