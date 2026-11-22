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


class EscortTest(unittest.TestCase):
    def setUp(self):
        from spaceship.systems.spawning import LevelDirector
        self.w = world(12)
        self.d = LevelDirector(self.w.level)
        self.d.intro_timer = 0
        self.m = self.d.mechanic
        self.w.mechanic = self.m

    def test_level_12_has_escort_and_one_boat_per_wave(self):
        from spaceship.systems.mechanics import Escort
        self.assertIsInstance(self.m, Escort)
        for i in range(4):
            spawned(12, i, self.w)
        self.assertEqual(self.m.launched, 4)

    def test_boat_crosses_and_is_saved(self):
        from spaceship.systems.mechanics import LIFEBOAT_CREW
        self.m.launch(self.w)
        for _ in range(1200):
            self.m.update(self.w)
        self.assertEqual(self.m.rescued, LIFEBOAT_CREW)
        self.assertEqual(self.m.boats, [])

    def test_bullets_and_rams_hurt_then_lose_crew(self):
        from spaceship.entities.projectiles import EnemyBullet
        from spaceship.entities.enemies import Enemy
        self.m.launch(self.w)
        boat = self.m.boats[0]
        boat.x = 300
        self.w.enemy_bullets.append(EnemyBullet(boat.x, boat.y, 90))
        self.m.update(self.w)
        self.assertEqual(boat.hp, 100 - 15)
        e = Enemy(1.0, kamikaze_chance=0)
        e.x, e.y = boat.x + 0.8, boat.y
        self.w.enemies.append(e)
        self.m.update(self.w)
        self.assertEqual(boat.hp, 100 - 15 - 30)
        self.assertNotIn(e, self.w.enemies)
        self.assertEqual(self.w.score, 0)                       # đâm vào nhau: không được điểm
        boat.hp = 1
        self.w.enemy_bullets.append(EnemyBullet(boat.x, boat.y, 90))
        self.m.update(self.w)
        self.assertEqual(self.m.lost, 1)
        self.assertTrue(any("Mất chiếc số 1" in line.text for line in self.w.radio))

    def test_losing_all_four_is_defeat(self):
        for _ in range(4):
            self.m.launch(self.w)
        for boat in self.m.boats:
            boat.x, boat.hp = 300, 0
        self.m.update(self.w)
        self.assertEqual(self.w.outcome, "defeat")

    def test_stars_by_people_saved(self):
        for rescued, stars in ((10, 1), (20, 1), (30, 2), (40, 3)):
            self.m.rescued = rescued
            self.assertEqual(self.m.stars(self.w), stars)

    def test_parasites_and_kamikaze_hunt_the_boat(self):
        from spaceship.entities.enemies import Enemy, Parasite
        self.m.launch(self.w)
        boat = self.m.boats[0]
        boat.x = 600
        p = Parasite(1.0, 200, 0, rng=random.Random(1))
        k = Enemy(1.0, kamikaze_chance=1, rng=random.Random(1))
        grunt = Enemy(1.0, kamikaze_chance=0, rng=random.Random(1))
        self.assertIs(self.m.target_for(self.w, p), boat)
        self.assertIs(self.m.target_for(self.w, k), boat)
        self.assertIs(self.m.target_for(self.w, grunt), self.w.player)
        for _ in range(80):
            p.update(boat)
        self.assertGreater(p.base_x, 350)                       # lượn dần về phía tàu cứu sinh

    def test_player_body_covers_bullets(self):
        from spaceship.entities.projectiles import EnemyBullet
        p = self.w.player
        p.invincible_timer = 30
        b = EnemyBullet(p.x + 12, p.y, 90)
        self.w.enemy_bullets.append(b)
        combat.resolve_enemy_bullets(self.w)
        self.assertNotIn(b, self.w.enemy_bullets)              # bất tử vẫn che được
        self.assertEqual(p.hp, p.max_hp)

    def test_next_wave_waits_for_the_boat(self):
        self.d.update(self.w)                                   # wave 1: thả tàu + lính
        self.w.enemies.clear()
        for _ in range(400):
            self.d.update(self.w)
            self.w.enemies.clear()
        self.assertEqual(self.w.wave, 1)                        # tàu còn đang bay: chưa sang wave 2
        for _ in range(1200):
            self.d.update(self.w)
            self.w.enemies.clear()
            if self.w.wave == 2:
                break
        self.assertEqual(self.w.wave, 2)

    def test_clear_radio_counts_people_and_true_ending_uses_it(self):
        from spaceship.campaign import story
        self.m.rescued = 30
        lines = self.m.radio(self.w, ("clear", 0))
        self.assertIn("30 trên 40", lines[0][1])
        self.assertEqual(story.true_ending(30)[-1][1], "Đưa 30 người về nhà.")
        self.assertEqual(story.true_ending(40)[-1][1], "Đưa tất cả bọn họ về nhà.")
        self.assertEqual(story.true_ending(None)[-1][1], "Đưa tất cả bọn họ về nhà.")

    def test_save_keeps_rescued(self):
        import tempfile
        from pathlib import Path
        from spaceship.core.storage import SaveData
        path = Path(tempfile.mkdtemp()) / "save.json"
        s = SaveData(path=path)
        s.rescued = 30
        s.save()
        self.assertEqual(SaveData.load(path).rescued, 30)
        self.assertIsNone(SaveData(path=Path(tempfile.mkdtemp()) / "x.json").rescued)


class GravityWellTest(unittest.TestCase):
    def setUp(self):
        from spaceship.systems.mechanics import GravityWell
        self.w = world(13)
        self.m = GravityWell()
        self.w.mechanic = self.m
        self.w.wave = 2

    def test_pulls_player_far_gently_near_strongly(self):
        from spaceship.systems.mechanics import WELL_PULL_FAR, WELL_PULL_NEAR
        import math
        p = self.w.player
        self.m.x = 400
        p.x, p.y = 21.0, 649.0
        self.m.update(self.w)
        far = math.hypot(p.x - 21.0, p.y - 649.0)
        p.x, p.y = self.m.x, self.m.y + 70
        before = p.y
        self.m.update(self.w)
        near = before - p.y
        self.assertAlmostEqual(far, WELL_PULL_FAR, delta=0.15)
        self.assertGreater(near, WELL_PULL_NEAR * 0.8)

    def test_touching_rim_hurts_and_throws_out(self):
        from spaceship.systems.mechanics import WELL_RIM, WELL_RIM_DAMAGE
        import math
        p = self.w.player
        p.x, p.y = self.m.x + 10, self.m.y + 20
        self.m.update(self.w)
        self.assertEqual(p.hp, p.max_hp - WELL_RIM_DAMAGE)
        self.assertGreater(math.hypot(p.x - self.m.x, p.y - self.m.y), WELL_RIM + 60)

    def test_bullets_curve_and_fall_in(self):
        from spaceship.entities.projectiles import Bullet, EnemyBullet
        b = EnemyBullet(self.m.x - 150, self.m.y + 150, 0)        # bay ngang sang phải
        self.w.enemy_bullets.append(b)
        for _ in range(10):
            self.m.update(self.w)
            b.update()
        self.assertLess(b.dy, 0)                                   # bị kéo lên về phía hố đen (cong)
        mine = Bullet(self.m.x + 100, self.m.y + 200, "plasma", angle=90)
        self.w.bullets.append(mine)
        for _ in range(5):
            self.m.update(self.w)
            mine.update()
        self.assertLess(mine.dx, 0)                                 # đạn của bạn cũng bị bẻ cong
        inside = EnemyBullet(self.m.x + 5, self.m.y, 90)
        self.w.enemy_bullets.append(inside)
        self.m.update(self.w)
        self.assertNotIn(inside, self.w.enemy_bullets)

    def test_swallowed_enemies_give_no_score_and_keep_combo(self):
        from spaceship.entities.enemies import Parasite
        self.w.combo = 7
        e = Parasite(1.0, self.m.x, self.m.y + 10)
        self.w.enemies.append(e)
        self.m.update(self.w)
        self.assertNotIn(e, self.w.enemies)
        self.assertEqual(self.w.score, 0)
        self.assertEqual(self.w.combo, 7)
        self.assertEqual(self.m.swallowed, 1)

    def test_wave_4_pulses_with_one_second_warning(self):
        self.w.wave = 4
        seen_warn = seen_strong = False
        order_ok = True
        for _ in range(300):
            self.m.update(self.w)
            self.w.player.x, self.w.player.y = 60, 640               # tránh xa hố đen
            if self.m.warning > 0:
                seen_warn = True
            if self.m.strong:
                order_ok = order_ok and seen_warn
                seen_strong = True
        self.assertTrue(seen_warn and seen_strong and order_ok)
        self.w.wave = 2
        m2 = type(self.m)()
        for _ in range(300):
            m2.update(self.w)
            self.w.player.x, self.w.player.y = 60, 640
            self.assertFalse(m2.strong)                              # trước wave 4: không đập

    def test_storm_eye_sits_in_the_well_and_calls_parasites_in_phase_2(self):
        from spaceship.entities.enemies import Boss, Parasite
        boss = Boss(1.0, kind="storm_eye")
        boss.y = 260
        self.w.enemies.append(boss)
        for _ in range(30):
            self.m.update(self.w)
            self.w.player.x, self.w.player.y = 60, 640
            boss.update(self.w.player)
        self.assertAlmostEqual(boss.x, self.m.x)
        boss.hp = boss.max_hp * 0.4
        born = 0
        for _ in range(400):
            before = sum(isinstance(e, Parasite) for e in self.w.enemies)
            self.m.update(self.w)
            born += max(0, sum(isinstance(e, Parasite) for e in self.w.enemies) - before)
            for e in self.w.enemies:
                if isinstance(e, Parasite):
                    e.update(self.w.player)
            self.w.player.x, self.w.player.y = 60, 640
        self.assertGreaterEqual(born, 8)                              # 2 nhịp × 4 Ký Sinh
        self.assertLess(self.m.swallowed, born)                       # chúng thoát ra được, không bị nuốt ngay
        attacks.boss_attack(self.w, boss)                           # mẫu đạn riêng (không lỗi)

    def test_draws(self):
        from spaceship.core.assets import Assets
        surface = pygame.Surface((800, 700))
        self.w.wave = 4
        for _ in range(300):
            self.m.update(self.w)
            self.w.player.x, self.w.player.y = 60, 640
            self.m.draw_back(surface, self.w, Assets())


class DarknessTest(unittest.TestCase):
    def setUp(self):
        from spaceship.systems.mechanics import Darkness
        self.w = world(14)
        self.m = Darkness()
        self.w.mechanic = self.m

    def test_level_14_uses_darkness_not_fog(self):
        from spaceship.systems.spawning import LevelDirector
        from spaceship.systems.mechanics import Darkness
        self.assertIsInstance(LevelDirector(get_level(14)).mechanic, Darkness)
        self.assertFalse(get_level(14).fog)

    def test_dark_everywhere_except_around_ship_and_bullets(self):
        from spaceship.entities.projectiles import Bullet
        surface = pygame.Surface((800, 700))
        surface.fill((200, 200, 200))
        p = self.w.player
        self.w.bullets.append(Bullet(600, 200, "laser"))
        self.m.draw_front(surface, self.w, None)
        self.assertGreater(surface.get_at((int(p.x), int(p.y)))[0], 150)      # quanh tàu sáng
        self.assertGreater(surface.get_at((600, 200))[0], 150)                 # đạn soi đường
        self.assertLess(surface.get_at((100, 100))[0], 30)                     # chỗ khác tối

    def test_rage_skill_lights_everything_for_3_seconds(self):
        from spaceship.systems import weapons
        p = self.w.player
        p.rage = p.max_rage
        weapons.trigger_skill(self.w)
        for _ in range(40):
            self.m.update(self.w)
        self.assertEqual(self.m.darkness, 0.0)
        for _ in range(180):
            self.m.update(self.w)
        self.assertEqual(self.m.darkness, 1.0)

    def test_danger_signs_drawn_over_darkness(self):
        from spaceship.entities.enemies import Turret
        surface = pygame.Surface((800, 700))
        t = Turret(1.0, 100, 100)
        t.y, t.aim, t.warning = 100, 0.0, 10                       # vạch cảnh báo nằm ngang sang phải
        self.w.enemies.append(t)
        self.m.draw_front(surface, self.w, None)
        self.assertGreater(surface.get_at((400, 100))[0], 100)     # vạch đỏ vẫn thấy trong tối

    def test_aria_silent_radio_is_static(self):
        self.assertTrue(self.m.radio_static)
        self.assertEqual(self.m.radio(self.w, ("boss", 0)), [])
        self.assertIn("radar", self.w.sounds)


class ListenerTest(unittest.TestCase):
    def setUp(self):
        from spaceship.entities.enemies import Boss
        from spaceship.systems.mechanics import Darkness
        self.w = world(14)
        self.m = Darkness()
        self.w.mechanic = self.m
        self.boss = Boss(1.0, kind="listener")
        self.boss.y = 200
        self.w.enemies.append(self.boss)

    def tick(self, n):
        for _ in range(n):
            self.m.update(self.w)
            attacks.run_enemy_ai(self.w)

    def test_ears_glow_before_each_aimed_burst(self):
        from spaceship.entities.enemies import LISTENER_TELL_TICKS
        fired_after_tell = []
        charging_run = 0
        for _ in range(400):
            before = len(self.w.enemy_bullets)
            self.tick(1)
            charging_run = charging_run + 1 if self.boss.charging else 0
            if len(self.w.enemy_bullets) > before:
                fired_after_tell.append(charging_run)
            if self.boss.charging:
                last_run = charging_run
        self.assertGreaterEqual(len(fired_after_tell), 3)
        self.assertGreaterEqual(last_run, LISTENER_TELL_TICKS - 2)

    def test_phase_2_splits_into_decoys_that_die_in_one_hit(self):
        from spaceship.entities.enemies import ListenerDecoy
        self.boss.hp = self.boss.max_hp * 0.45
        self.tick(2)
        decoys = [e for e in self.w.enemies if isinstance(e, ListenerDecoy)]
        self.assertEqual(len(decoys), 2)
        combat.damage_enemy(self.w, decoys[0], 3)
        combat.reap_dead(self.w)
        self.assertNotIn(decoys[0], self.w.enemies)
        self.assertEqual(self.w.score, 0)
        self.boss.hp = 0                                             # hạ hình thật: hình giả biến mất
        combat.reap_dead(self.w)
        self.m.update(self.w)
        self.assertFalse(any(isinstance(e, ListenerDecoy) for e in self.w.enemies))

    def test_radio_glitch_uses_glitch_portrait(self):
        from spaceship.campaign.story import ARIA, portrait_for
        self.assertEqual(portrait_for(ARIA, "glitch"), "portrait_aria_glitch")
        self.assertEqual(portrait_for(ARIA), "portrait_aria")
        self.w.say(ARIA, "---", effect="glitch")
        self.assertEqual(self.w.radio[-1].effect, "glitch")
