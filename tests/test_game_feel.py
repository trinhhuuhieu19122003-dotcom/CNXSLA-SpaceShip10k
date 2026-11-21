"""Cảm giác đánh: rung kiểu trauma, khựng hình (hitstop), bất tử ngắn sau khi trúng đạn,
viền đỏ, chớp sáng mờ dần và cài đặt "Rung & nháy màn hình"."""
import random
import unittest

from tests import helpers  # noqa: F401
from spaceship import config
from spaceship.app import Game
from spaceship.config import GameMode
from spaceship.core.settings import Settings
from spaceship.entities.enemies import Boss, Enemy
from spaceship.entities.projectiles import EnemyBullet
from spaceship.input.controls import ControlState
from spaceship.scenes.gameplay import GameplayScene
from spaceship.systems import combat
from spaceship.systems.world import World
from spaceship.ui import feel


def world():
    return World(mode=GameMode.CAMPAIGN, rng=random.Random(0))


class TraumaShakeTest(unittest.TestCase):
    def test_light_hits_shake_less_than_boss_kill(self):
        w = world()
        w.shake(4)
        light = w.trauma
        w.trauma = 0
        w.shake(20)
        self.assertLess(light, w.trauma)
        self.assertEqual(w.trauma, 1.0)

    def test_trauma_decays_to_zero(self):
        w = world()
        w.shake(20)
        for _ in range(int(1 / config.TRAUMA_DECAY) + 2):
            w.tick_feel()
        self.assertEqual(w.trauma, 0.0)


class MercyAndHitstopTest(unittest.TestCase):
    def test_bullet_hit_gives_short_mercy_and_freeze(self):
        w = world()
        p = w.player
        combat.damage_player(w, 15)
        self.assertEqual(p.invincible_timer, config.MERCY_TICKS)
        self.assertEqual(w.hitstop, config.HITSTOP_HURT)
        self.assertEqual(w.hurt_timer, config.HURT_VIGNETTE_TICKS)

    def test_spread_of_bullets_only_hurts_once(self):
        w = world()
        p = w.player
        p.invincible_timer = 0
        w.enemy_bullets.extend(EnemyBullet(p.x, p.y, 90) for _ in range(3))
        combat.resolve_enemy_bullets(w)
        self.assertEqual(p.hp, p.max_hp - config.ENEMY_BULLET_DAMAGE["normal"])

    def test_boss_kill_freezes_longest(self):
        w = world()
        boss = Boss(1.0, stage=1)
        w.enemies.append(boss)
        combat.kill_enemy(w, boss)
        self.assertEqual(w.hitstop, config.HITSTOP_BOSS)

    def test_freeze_does_not_stack(self):
        w = world()
        w.freeze(3)
        w.freeze(3)
        self.assertEqual(w.hitstop, 3)


class GameplayFeelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.game = Game(camera=False, seed=3)

    def setUp(self):
        self.game.settings.screen_fx = "full"
        self.play = GameplayScene(self.game, GameMode.ENDLESS)
        self.game.change_scene(self.play)
        self.game._apply_pending_scene()
        self.play.world.enemy_bullets.clear()

    def test_hitstop_freezes_enemies_then_resumes(self):
        w = self.play.world
        enemy = Enemy(1, rng=self.game.rng, kamikaze_chance=0)
        enemy.x, enemy.y = 400, 100
        w.enemies.append(enemy)
        w.freeze(5)
        before = (enemy.x, enemy.y, w.survival_time)
        for _ in range(5):
            self.play.update(ControlState())
        self.assertEqual((enemy.x, enemy.y, w.survival_time), before)
        self.play.update(ControlState())
        self.assertGreater(w.survival_time, before[2])

    def test_shake_offset_respects_setting(self):
        w = self.play.world
        w.trauma = 1.0
        offsets = {self.play.screen_offset() for _ in range(30)}
        self.assertTrue(any(dx or dy for dx, dy in offsets))
        self.assertTrue(all(abs(dx) <= config.SHAKE_MAX_OFFSET for dx, _ in offsets))
        self.game.settings.screen_fx = "off"
        self.assertEqual({self.play.screen_offset() for _ in range(30)}, {(0, 0)})

    def test_flash_is_soft_and_can_be_disabled(self):
        w = self.play.world
        w.flash = 4
        self.assertLessEqual(feel.flash_alpha(w, 1.0), config.FLASH_MAX_ALPHA)
        self.assertGreater(feel.flash_alpha(w, 1.0), 0)
        self.assertEqual(feel.flash_alpha(w, 0.0), 0)
        self.play.draw(self.game.screen)          # vẽ được với lớp phủ

    def test_hurt_and_low_hp_vignette_show_even_with_effects_off(self):
        w = self.play.world
        self.assertEqual(feel.vignette_alpha(w), 0)
        w.hurt_timer = config.HURT_VIGNETTE_TICKS
        self.assertGreater(feel.vignette_alpha(w, 0.0), 0)
        w.hurt_timer = 0
        w.player.hp = w.player.max_hp * 0.2
        self.assertGreater(feel.vignette_alpha(w, 0.0), 0)
        self.play.draw(self.game.screen)


class ScreenFxSettingTest(unittest.TestCase):
    def test_cycle_and_round_trip(self):
        import tempfile
        from pathlib import Path

        path = Path(tempfile.mkdtemp()) / "settings.json"
        s = Settings(path=path)
        self.assertEqual(s.screen_fx, "full")
        s.cycle_screen_fx()
        self.assertEqual(s.screen_fx, "reduced")
        s.save()
        self.assertEqual(Settings.load(path).screen_fx, "reduced")
        s.cycle_screen_fx()
        s.cycle_screen_fx()
        self.assertEqual(s.screen_fx, "full")

    def test_options_row_toggles(self):
        from spaceship.scenes.options import OptionsScene

        game = Game(camera=False, seed=1)
        options = OptionsScene(game)
        button = next(b for b in options.buttons if b.action == "screen_fx")
        self.assertIn("ĐẦY ĐỦ", button.text)
        options._do("screen_fx")
        self.assertIn("NHẸ", button.text)
        options.draw(game.screen)


if __name__ == "__main__":
    unittest.main()


class KamikazeTelegraphTest(unittest.TestCase):
    def make(self):
        from spaceship.entities.player import Player

        w = world()
        e = Enemy(1, stage=2, rng=random.Random(1), kamikaze_chance=1)
        e.x, e.y, e.reached_target = 400, 150, True
        e.hp = e.max_hp * 0.2                      # bị thương nặng -> nổi điên
        w.enemies.append(e)
        return w, e

    def test_locks_on_before_diving_and_beeps(self):
        from spaceship.systems import attacks

        w, e = self.make()
        attacks.run_enemy_ai(w)
        self.assertIn("lock_on", w.sounds)
        start = (e.x, e.y)
        for _ in range(config.KAMIKAZE_WINDUP_TICKS - 1):
            e.update(w.player)
        self.assertEqual((e.x, e.y), start)        # đang khóa: đứng yên (chỉ rung khi vẽ)
        e.update(w.player)
        e.update(w.player)
        self.assertGreater(e.y, start[1])          # đã lao xuống phía tàu

    def test_dive_turns_slowly_so_a_side_step_dodges(self):
        w, e = self.make()
        p = w.player
        p.x, p.y = 400, 600
        for _ in range(config.KAMIKAZE_WINDUP_TICKS + 1):
            e.update(p)
        p.x = 650                                  # né ngang ngay khi nó lao
        closest = 10 ** 9
        for _ in range(200):
            e.update(p)
            closest = min(closest, ((e.x - p.x) ** 2 + (e.y - p.y) ** 2) ** 0.5)
            if e.gone:
                break
        self.assertGreater(closest, 30)            # không đâm trúng
        self.assertTrue(e.gone)                    # bay trượt ra khỏi màn và được dọn

    def test_lock_on_draws(self):
        import pygame
        from spaceship.core.assets import Assets

        w, e = self.make()
        e.update(w.player)
        e.draw(pygame.Surface((800, 700)), Assets())


class BulletCancelTest(unittest.TestCase):
    def test_boss_kill_turns_bullets_into_points(self):
        w = world()
        w.enemy_bullets.extend(EnemyBullet(100 + i * 10, 200, 90) for i in range(10))
        boss = Boss(1.0, stage=1)
        w.enemies.append(boss)
        score = w.score
        combat.kill_enemy(w, boss)
        self.assertEqual(w.enemy_bullets, [])
        self.assertEqual(w.score - score, boss.score + 10 * config.BULLET_CANCEL_SCORE)
        self.assertIn("bullet_cancel", w.sounds)

    def test_boss_phase_change_cancels_bullets(self):
        from spaceship.systems import attacks

        w = world()
        boss = Boss(1.0, stage=1)
        boss.y = boss.hover_y if hasattr(boss, "hover_y") else 150
        w.enemies.append(boss)
        for _ in range(400):
            if boss.arrived:
                break
            boss.update(w.player)
        self.assertTrue(boss.arrived)
        w.enemy_bullets.extend(EnemyBullet(300, 300, 90) for _ in range(5))
        boss.hp = boss.max_hp * 0.5                # sang pha 2
        attacks.boss_attack(w, boss)
        self.assertEqual(boss.phase, 2)
        self.assertFalse(any(b.y == 300 and b.x == 300 for b in w.enemy_bullets))
