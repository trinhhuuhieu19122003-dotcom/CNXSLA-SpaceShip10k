"""Cơ chế riêng của Hồi IV (đợt 2-6): Bóng KX, hộ tống, hố đen, màn tối, Trái Tim Đàn."""
import random
import unittest

import pygame

from tests import helpers  # noqa: F401  (khởi tạo pygame không màn hình)
from spaceship import config
from spaceship.campaign.bestiary import BESTIARY
from spaceship.campaign.levels import get_level
from spaceship.config import GameMode
from spaceship.core.assets import Assets
from spaceship.entities.enemies import ShadowKX
from spaceship.entities.player import WEAPON_COLORS
from spaceship.systems import attacks, combat
from spaceship.systems.world import World


def world(level=None):
    w = World(mode=GameMode.CAMPAIGN, rng=random.Random(0))
    if level:
        w.level = get_level(level)
    return w


def spawned(level_number, wave_index, world_):
    for _tick, spawn in get_level(level_number).waves[wave_index]:
        spawn(world_)
    return world_.enemies


class ShadowKXTest(unittest.TestCase):
    def run_ticks(self, w, xs):
        for x in xs:
            w.player.x = x
            w.player.tick_timers()
            attacks.run_enemy_ai(w)

    def test_replays_player_x_after_delay(self):
        w = world()
        shadow = ShadowKX(1.0, 2.0)
        w.enemies.append(shadow)
        xs = [100 + t for t in range(300)]
        self.run_ticks(w, xs)
        self.assertEqual(shadow.x, xs[-shadow.delay])           # đúng vị trí ngang 2 giây trước
        self.assertEqual(shadow.y, config.SHADOW_HOVER_Y)

    def test_standing_still_means_it_sits_on_your_head_and_fires_down(self):
        w = world()
        shadow = ShadowKX(1.0, 2.0)
        w.enemies.append(shadow)
        w.player.weapon = "plasma"
        self.run_ticks(w, [333.0] * 400)
        shots = [b for b in w.enemy_bullets if b.kind == "shadow"]
        self.assertGreaterEqual(len(shots), 5)
        self.assertTrue(all(abs(b.dx) < 1e-9 and b.dy > 0 for b in shots))      # thẳng xuống
        self.assertTrue(all(b.tint == WEAPON_COLORS["plasma"] for b in shots))   # màu súng của bạn
        self.assertTrue(all(abs(b.x - 333) < 1 for b in shots))

    def test_dies_into_particles_without_drops(self):
        w = world()
        shadow = ShadowKX(1.0)
        shadow.x, shadow.y = 300, 130
        w.enemies.append(shadow)
        w.rng = random.Random(1)
        w.preset = "easy"
        shadow.hp = 0
        combat.reap_dead(w)
        self.assertEqual(w.items, [])
        self.assertEqual(w.kills, 1)
        self.assertEqual(w.score, config.SHADOW_SCORE)
        self.assertIn("glitch", w.sounds)

    def test_levels_use_shadows(self):
        for level, wave_i, count in ((11, 0, 1), (11, 2, 2), (11, 4, 3), (14, 2, 3), (15, 0, 2)):
            enemies = spawned(level, wave_i, world())
            self.assertEqual(sum(isinstance(e, ShadowKX) for e in enemies), count, (level, wave_i))
        delays = sorted(e.delay for e in spawned(11, 4, world()) if isinstance(e, ShadowKX))
        self.assertEqual(delays, [120, 180, 240])

    def test_bestiary_and_sprite(self):
        self.assertIn("shadow", BESTIARY)
        img = Assets().raw("shadow_kx")
        self.assertIsNotNone(img)
        self.assertEqual(img.get_size(), Assets().raw("player").get_size())

    def test_draws(self):
        surface = pygame.Surface((800, 700))
        w = world()
        shadow = ShadowKX(1.0)
        w.enemies.append(shadow)
        self.run_ticks(w, [100 + 3 * t for t in range(200)])
        shadow.draw(surface, Assets())
        shadow.draw_halo(surface)
        for b in w.enemy_bullets:
            b.draw(surface)


if __name__ == "__main__":
    unittest.main()
