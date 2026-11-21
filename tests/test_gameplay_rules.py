"""Kiểm tra các quy tắc gameplay ở mức logic (không vẽ)."""
import random
import unittest

from tests import helpers  # noqa: F401
from spaceship import config
from spaceship.config import HEIGHT, WIDTH, GameMode
from spaceship.entities.enemies import Boss, Enemy, Meteor
from spaceship.entities.items import Item
from spaceship.entities.projectiles import Bullet, EnemyBullet
from spaceship.systems import combat, loot
from spaceship.campaign.levels import LEVELS, get_level
from spaceship.systems.spawning import LevelDirector, SurvivalDirector, formation
from spaceship.systems.world import World


def world(mode=GameMode.CAMPAIGN, seed=0):
    return World(mode=mode, rng=random.Random(seed))


class DamageTest(unittest.TestCase):
    def test_shield_absorbs_then_overflows_to_hp(self):
        w = world()
        boss = Boss(1.0, stage=3)
        boss.shield_hp = 10
        hp = boss.hp
        combat.damage_enemy(w, boss, 25)
        self.assertEqual(boss.shield_hp, 0)
        self.assertEqual(boss.hp, hp - 15)

    def test_player_loses_life_then_game_over(self):
        w = world()
        p = w.player
        combat.damage_player(w, p.max_hp)
        self.assertEqual(p.lives, config.PLAYER_LIVES - 1)
        self.assertEqual(p.hp, p.max_hp)
        self.assertGreater(p.invincible_timer, 0)
        p.lives = 1
        combat.damage_player(w, p.max_hp)
        self.assertEqual(w.outcome, "defeat")

    def test_burn_is_meaningful(self):
        w = world()
        e = Enemy(1.0, rng=w.rng)
        e.burning = True
        w.enemies.append(e)
        hp = e.hp
        for _ in range(config.TICK_RATE):
            combat.apply_burn(w)
        self.assertAlmostEqual(hp - e.hp, config.BURN_DAMAGE_PER_SECOND, places=3)


class KillRewardTest(unittest.TestCase):
    def test_every_kill_goes_through_one_path(self):
        w = world(GameMode.ENDLESS)
        grunt, meteor, boss = Enemy(1.0, rng=w.rng), Meteor(1.0, rng=w.rng), Boss(1.0, stage=2)
        w.enemies += [grunt, meteor, boss]
        for e in (grunt, meteor, boss):
            e.hp = 0
        combat.reap_dead(w)
        self.assertEqual(w.enemies, [])
        self.assertEqual(w.score, config.SCORE_ENEMY + config.SCORE_METEOR + config.SCORE_BOSS_PER_STAGE * 2)
        self.assertEqual((w.kills, w.boss_kills), (1, 1))
        self.assertEqual(w.defeated_bosses, [boss])

    def test_breeder_splits_and_wreck_drops_cargo(self):
        from spaceship.entities.enemies import Breeder, Wreck
        w = world()
        b = Breeder(1.0, 400, 200, rng=w.rng)
        wr = Wreck(1.0, 300, rng=w.rng, carries="upgrade_lightning")
        w.enemies += [b, wr]
        b.hp = wr.hp = 0
        combat.reap_dead(w)
        self.assertEqual(len(w.enemies), 4)                     # 4 Ký Sinh nhỏ
        self.assertIn("upgrade_lightning", [i.kind for i in w.items])


class ProjectileTest(unittest.TestCase):
    def test_enemy_bullets_leaving_top_are_removed(self):
        w = world()
        up = EnemyBullet(400, 10, angle_deg=-90)
        w.enemy_bullets.append(up)
        for _ in range(30):
            up.update()
        combat.cleanup(w)
        self.assertEqual(w.enemy_bullets, [])

    def test_drone_aims_at_nearest_enemy_and_hits(self):
        w = world()
        e = Enemy(10.0, rng=w.rng)
        e.x, e.y = w.player.x + 250, w.player.y - 200                 # lệch hẳn sang phải
        w.enemies.append(e)
        w.player.drones = 1
        w.player.fire_drone(w.bullets, w.enemies)
        bolt = w.bullets[-1]
        self.assertEqual(bolt.kind, "drone_bolt")
        self.assertGreater(bolt.dx, 0)                                  # bay về phía địch, không thẳng lên
        hp = e.hp
        for _ in range(40):
            for b in w.bullets:
                b.update()
            combat.resolve_player_bullets(w)
        self.assertEqual(hp - e.hp, config.DRONE_DAMAGE)
        self.assertEqual(w.player.rage, 0)                              # drone không hồi Nộ

    def test_bullet_on_screen_bounds(self):
        self.assertFalse(Bullet(400, -200, "plasma").on_screen)
        self.assertFalse(EnemyBullet(-100, 300, 0).on_screen)
        self.assertTrue(EnemyBullet(WIDTH / 2, HEIGHT / 2, 0).on_screen)


class PickupTest(unittest.TestCase):
    def pick(self, w, kind):
        p = w.player
        w.items.append(Item(p.x, p.y, kind))
        combat.collect_items(w)

    def test_weapon_upgrade_rules(self):
        w = world()
        p = w.player
        self.pick(w, "upgrade_laser")
        self.assertEqual((p.weapon, p.level), ("laser", 2))
        self.pick(w, "upgrade_plasma")
        self.assertEqual((p.weapon, p.level), ("plasma", 1))
        for _ in range(10):
            self.pick(w, "upgrade_universal")
        self.assertEqual(p.level, config.MAX_WEAPON_LEVEL)
        self.assertGreater(p.bonus_damage, 0)

    def test_inferno_heal_is_small(self):
        w = world(GameMode.INFERNO)
        w.player.hp = 50
        self.pick(w, "heal")
        self.assertEqual(w.player.hp, 50 + config.HEAL_AMOUNT[GameMode.INFERNO])


class LootTest(unittest.TestCase):
    def test_random_table_includes_all_weapons(self):
        rng = random.Random(1)
        drops = {loot.random_drop(GameMode.ENDLESS, rng) for _ in range(500)}
        self.assertTrue({"upgrade_laser", "upgrade_homing", "upgrade_plasma", "upgrade_universal"} <= drops)

    def test_inferno_never_drops_shield(self):
        rng = random.Random(2)
        self.assertNotIn("shield", {loot.random_drop(GameMode.INFERNO, rng) for _ in range(500)})


class DirectorTest(unittest.TestCase):
    def test_every_formation_exists(self):
        for stage, waves in {1: 5, 2: 7, 3: 10}.items():
            for wave in range(1, waves + 2):
                positions, _ = formation(stage, wave)
                self.assertTrue(positions, (stage, wave))

    def _clear_level(self, number):
        w = world()
        w.level = get_level(number)
        d = LevelDirector(w.level)
        for _ in range(60 * 600):
            d.update(w)
            for e in [e for e in w.enemies if not e.is_boss]:     # "diệt sạch" quân mỗi tick
                w.enemies.remove(e)
            for boss in w.bosses:
                boss.hp = 0
            combat.reap_dead(w)
            for item in w.items:
                item.update(w.player)
            combat.collect_items(w)
            if w.outcome:
                break
        return w, d

    def test_every_level_can_be_cleared(self):
        for level in LEVELS:
            w, d = self._clear_level(level.number)
            self.assertEqual(w.outcome, "victory", level.title)
            self.assertEqual(w.wave, len(level.waves), level.title)
            self.assertEqual(w.boss_kills, 1 if level.boss else 0, level.title)

    def test_boss_rewards_fly_to_player(self):
        w, _ = self._clear_level(3)
        self.assertEqual(w.player.drones, 1)                    # phần thưởng tự bay vào tàu
        w, _ = self._clear_level(7)
        self.assertTrue(w.player.burn_unlocked)

    def test_endless_spawns_boss_on_interval(self):
        w = world(GameMode.ENDLESS)
        d = SurvivalDirector(GameMode.ENDLESS)
        while w.survival_time < config.ENDLESS_BOSS_INTERVAL + 1:
            w.survival_time += config.TICK
            d.update(w)
        self.assertEqual(len(w.bosses), 1)
        self.assertGreater(w.difficulty, 1.9)

    def test_survival_reward_sequence(self):
        w = world(GameMode.ENDLESS)
        d = SurvivalDirector(GameMode.ENDLESS)
        for expected in ("upgrade_drone", "upgrade_burn", "upgrade_drone"):
            w.items.clear()
            boss = Boss(1.0, kind="crab")
            d.on_boss_defeated(w, boss)
            self.assertIn(expected, [i.kind for i in w.items if i.magnet])


if __name__ == "__main__":
    unittest.main()
