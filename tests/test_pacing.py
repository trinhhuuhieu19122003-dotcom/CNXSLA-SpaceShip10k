"""Nhịp sóng: địch bay vào lần lượt, không bắn khi vừa tới, trần mật độ/đạn, nghỉ giữa wave, rút lui,
nhịp dồn lên -> cao trào -> thả lỏng của Vô tận/Hỏa ngục."""
import random
import unittest

from tests import helpers  # noqa: F401
from spaceship import config
from spaceship.campaign.levels import get_level, grunts
from spaceship.config import GameMode
from spaceship.entities.enemies import Boss, Enemy
from spaceship.entities.projectiles import EnemyBullet
from spaceship.systems import attacks, combat
from spaceship.systems.spawning import PACING, LevelDirector, SurvivalDirector, formation, threat
from spaceship.systems.world import World


def world(mode=GameMode.CAMPAIGN, seed=0):
    return World(mode=mode, rng=random.Random(seed))


class EntryTest(unittest.TestCase):
    def test_formation_enters_one_by_one_inside_screen(self):
        events = grunts(3, 9)                                 # đội hình 5 hàng, 35 con
        positions, _ = formation(3, 9)
        self.assertEqual(len(events), len(positions))
        ticks = [t for t, _ in events]
        self.assertEqual(ticks, sorted(ticks))
        self.assertEqual(ticks[1] - ticks[0], config.ENTRY_STAGGER_TICKS)
        w = world()
        for _t, spawn in events:
            spawn(w)
        self.assertTrue(all(50 <= e.target_y <= 200 for e in w.enemies))   # không hàng nào nằm ngoài mép trên

    def test_grunt_holds_fire_while_entering_then_retreats(self):
        w = world()
        e = Enemy(1.0, rng=w.rng)
        e.y, e.target_y, e.shoot_timer = -40, 150, 1
        w.enemies.append(e)
        while not e.reached_target:
            e.update(w.player)
            attacks.grunt_fire(w, e)
        self.assertEqual(w.enemy_bullets, [])                  # bay vào: không bắn
        for _ in range(config.ARRIVAL_GRACE_TICKS - 1):
            e.update(w.player)
            attacks.grunt_fire(w, e)
        self.assertEqual(w.enemy_bullets, [])                  # vừa tới: còn chờ
        for _ in range(5):
            e.update(w.player)
            attacks.grunt_fire(w, e)
        self.assertTrue(w.enemy_bullets)                       # giờ mới bắn
        for _ in range(config.RETREAT_AFTER_TICKS):
            e.update(w.player)
        self.assertTrue(e.retreating)
        self.assertLessEqual(e.y, config.FORMATION_FLOOR)
        while not e.gone:
            e.update(w.player)
        combat.cleanup(w)
        self.assertNotIn(e, w.enemies)                         # rút lui khỏi mép trên -> bị xóa

    def test_bullet_cap_pauses_grunts_but_not_bosses(self):
        w = world()
        w.enemy_bullets = [EnemyBullet(400, 300, 90, "normal") for _ in range(config.ENEMY_BULLET_CAP[w.mode])]
        e = Enemy(1.0, rng=w.rng)
        e.reached_target, e.arrived_at, e.age, e.y, e.shoot_timer = True, 0, 100, 200, 1
        attacks.grunt_fire(w, e)
        self.assertEqual(len(w.enemy_bullets), config.ENEMY_BULLET_CAP[w.mode])

    def test_boss_summons_only_when_few_minions(self):
        w = world()
        boss = Boss(1.0, kind="spider")
        w.enemies.append(boss)
        for _ in range(20):
            attacks._summon(w, boss, 2)
        self.assertLessEqual(threat(w), attacks.BOSS_MINION_THREAT)


class LevelPacingTest(unittest.TestCase):
    def test_wave_waits_when_threat_budget_is_full(self):
        w = world()
        d = LevelDirector(get_level(2))
        d.intro_timer = 0
        cap = d.threat_cap(w)
        for _ in range(600):
            d.update(w)
            for e in w.enemies:                                  # không ai bị hạ: địch dồn tới trần
                e.age += 1
            self.assertLessEqual(threat(w), cap + 1)
        self.assertTrue(d.events)                                # phần còn lại của wave đang xếp hàng

    def test_cycle_raises_cap(self):
        w = world()
        d = LevelDirector(get_level(1))
        base = d.threat_cap(w)
        w.cycle = 3
        self.assertEqual(d.threat_cap(w), base + 2 * config.THREAT_CAP_PER_CYCLE)


class SurvivalPacingTest(unittest.TestCase):
    def run_mode(self, mode, seconds):
        w = world(mode, seed=3)
        d = SurvivalDirector(mode)
        states, peak_threat = [], 0.0
        for _ in range(int(seconds * config.TICK_RATE)):
            w.survival_time += config.TICK
            d.update(w)
            for e in list(w.enemies):
                e.update(w.player)
            w.enemies = [e for e in w.enemies if e.is_boss or (e.y < config.HEIGHT + 60 and not e.gone)]
            states.append(d.state)
            peak_threat = max(peak_threat, threat(w))
        return d, states, peak_threat

    def test_endless_cycles_and_stays_under_budget(self):
        d, states, peak = self.run_mode(GameMode.ENDLESS, 150)
        self.assertIn(d.RELAX, states)
        self.assertIn(d.PEAK, states)
        self.assertLessEqual(peak, PACING[GameMode.ENDLESS].cap_max + 5)   # +1 tốp đang bay vào

    def test_relax_comes_early_when_player_is_hurt(self):
        w = world(GameMode.ENDLESS)
        d = SurvivalDirector(GameMode.ENDLESS)
        d.update(w)
        w.player.hp -= w.player.max_hp * 0.5
        d.update(w)
        self.assertEqual(d.state, d.PEAK)


if __name__ == "__main__":
    unittest.main()
