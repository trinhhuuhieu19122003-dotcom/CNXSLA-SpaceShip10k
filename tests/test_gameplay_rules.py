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
from spaceship.systems.spawning import CampaignDirector, SurvivalDirector, formation
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

    def test_nuke_kills_also_give_score(self):
        w = world()
        e = Enemy(0.1, rng=w.rng)
        w.enemies.append(e)
        combat.detonate_nuke(w, type("N", (), {"x": 400, "y": 350})())
        combat.reap_dead(w)
        self.assertEqual(w.score, config.SCORE_ENEMY)


class ProjectileTest(unittest.TestCase):
    def test_enemy_bullets_leaving_top_are_removed(self):
        w = world()
        up = EnemyBullet(400, 10, angle_deg=-90)
        w.enemy_bullets.append(up)
        for _ in range(30):
            up.update()
        combat.cleanup(w)
        self.assertEqual(w.enemy_bullets, [])

    def test_drone_laser_hits_each_enemy_once(self):
        w = world()
        e = Enemy(10.0, rng=w.rng)
        e.x, e.y = 400, 300
        w.enemies.append(e)
        beam = Bullet(400, 330, "drone_laser")
        w.bullets.append(beam)
        hp = e.hp
        for _ in range(5):
            combat.resolve_player_bullets(w)
        self.assertEqual(hp - e.hp, config.DRONE_DAMAGE)

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
    def test_every_campaign_wave_has_a_formation(self):
        for stage, waves in config.CAMPAIGN_WAVES.items():
            for wave in range(1, waves + 2):
                positions, _ = formation(stage, wave)
                self.assertTrue(positions, (stage, wave))

    def test_campaign_flow_boss_reward_and_victory(self):
        w = world()
        d = CampaignDirector()
        for stage in (1, 2, 3):
            self.assertEqual(w.stage, stage)
            while not any(e.is_boss for e in w.enemies):
                w.enemies[:] = [e for e in w.enemies if e.is_boss]   # "diệt sạch" quân mỗi wave
                d.update(w)
            boss = next(e for e in w.enemies if e.is_boss)
            boss.hp = 0
            combat.reap_dead(w)
            w.enemies.clear()
            d.update(w)
            if stage < 3:
                self.assertIn(loot.BOSS_REWARDS[stage], [i.kind for i in w.items])
                for _ in range(config.STAGE_CLEAR_TICKS + config.STAGE_INTRO_TICKS + 1):
                    d.update(w)
        self.assertEqual(w.outcome, "victory")

    def test_endless_spawns_boss_on_interval(self):
        w = world(GameMode.ENDLESS)
        d = SurvivalDirector(GameMode.ENDLESS)
        while w.survival_time < config.ENDLESS_BOSS_INTERVAL + 1:
            w.survival_time += config.TICK
            d.update(w)
        self.assertEqual(len(w.bosses), 1)
        self.assertGreater(w.difficulty, 1.9)


if __name__ == "__main__":
    unittest.main()
