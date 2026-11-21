"""Hồi IV (đợt 1 - khung): 15 ải, mở sau ải 10, đoạn kết giữa chừng, kết thúc thật, ảnh tạm, bản đồ riêng."""
import json
import tempfile
import unittest
from pathlib import Path

import pygame

from tests import helpers  # noqa: F401
from spaceship.app import Game
from spaceship.campaign import story
from spaceship.campaign.levels import LEVEL_COUNT, LEVELS, MAIN_LEVELS
from spaceship.core.assets import PLACEHOLDERS, Assets
from spaceship.core.storage import SaveData
from spaceship.entities.enemies import BOSS_SPECS, MINI_BOSSES, Boss
from spaceship.scenes.level_select import LevelSelectScene
from spaceship.ui.journey_map import NODES_ACT4, JourneyMap


def fresh_save():
    return SaveData(path=Path(tempfile.mkdtemp()) / "save.json")


class Act4DataTest(unittest.TestCase):
    def test_fifteen_levels_four_acts(self):
        self.assertEqual((LEVEL_COUNT, MAIN_LEVELS), (15, 10))
        self.assertEqual([lv.act for lv in LEVELS[10:]], [4] * 5)
        self.assertEqual(sorted(story.ACTS), [1, 2, 3, 4])

    def test_every_level_has_intro_and_radio(self):
        for level in LEVELS:
            self.assertIn(level.number, story.INTROS, level.number)
            self.assertIn(level.number, story.RADIO, level.number)
            if level.boss:
                self.assertIn(level.boss, BOSS_SPECS)

    def test_new_bosses(self):
        self.assertEqual(BOSS_SPECS["swarm_heart"].title, "TRÁI TIM ĐÀN")
        self.assertTrue({"storm_eye", "listener"} <= MINI_BOSSES)
        boss = Boss(1.0, kind="swarm_heart")
        self.assertGreater(boss.shield_hp, 0)


class ProgressionTest(unittest.TestCase):
    def test_level_10_opens_inferno_and_act4_not_new_cycle(self):
        save = fresh_save()
        for n in range(1, MAIN_LEVELS + 1):
            save.record_level(n, 3, LEVEL_COUNT, MAIN_LEVELS)
        self.assertTrue(save.campaign_cleared)
        self.assertFalse(save.cycle_complete)
        self.assertEqual(save.unlocked_level, 11)
        for n in range(MAIN_LEVELS + 1, LEVEL_COUNT + 1):
            save.record_level(n, 2, LEVEL_COUNT, MAIN_LEVELS)
        self.assertTrue(save.cycle_complete)
        self.assertEqual(save.cycle_history[1], 30 + 10)

    def test_old_save_that_cleared_level_10_gets_level_11(self):
        path = Path(tempfile.mkdtemp()) / "save.json"
        raw = {"version": 5, "highscore": 0, "modes": {},
               "campaign": {"unlocked_level": 10, "level_stars": {str(n): 3 for n in range(1, 11)},
                            "cleared": True, "cycle": 1, "cycle_complete": True, "cycle_history": {"1": 30}}}
        path.write_text(json.dumps(raw), encoding="utf-8")
        save = SaveData.load(path, legacy_dirs=())
        self.assertEqual(save.unlocked_level, 11)
        self.assertTrue(save.cycle_complete)                 # người đã phá đảo bản cũ vẫn mở được chu kỳ mới

    def test_cycle_two_in_progress_is_not_skipped_ahead(self):
        path = Path(tempfile.mkdtemp()) / "save.json"
        raw = {"version": 5, "campaign": {"unlocked_level": 3, "level_stars": {"1": 3, "2": 2},
                                          "cleared": True, "cycle": 2, "cycle_complete": False}}
        path.write_text(json.dumps(raw), encoding="utf-8")
        self.assertEqual(SaveData.load(path, legacy_dirs=()).unlocked_level, 3)


class LevelSelectAct4Test(unittest.TestCase):
    def test_act4_hidden_until_level_10_cleared(self):
        game = Game(camera=False, seed=1)
        game.save = fresh_save()
        scene = LevelSelectScene(game)
        self.assertEqual(len(scene.cards), 15)
        self.assertTrue(scene.hidden(11))
        scene.draw(game.screen)
        for n in range(1, MAIN_LEVELS + 1):
            game.save.record_level(n, 1, LEVEL_COUNT, MAIN_LEVELS)
        self.assertFalse(scene.hidden(11))
        self.assertTrue(scene.unlocked(11))
        self.assertFalse(scene.unlocked(12))
        scene.draw(game.screen)
        self.assertTrue(all(card.bottom < 600 for card in scene.cards))   # 3 hàng không đè lên nút


class JourneyMapAct4Test(unittest.TestCase):
    def test_act4_uses_own_chart_and_draws(self):
        surface = pygame.Surface((800, 700))
        for number in (11, 15):
            chart = JourneyMap(number, {n: 3 for n in range(1, number)})
            self.assertIs(chart.nodes, NODES_ACT4)
            self.assertEqual(chart.origin, NODES_ACT4[number - 1])
            for _ in range(200):
                chart.update()
            self.assertTrue(chart.arrived)
            chart.draw(surface, Assets())
        self.assertIsNot(JourneyMap(10, {}).nodes, NODES_ACT4)


class PlaceholderArtTest(unittest.TestCase):
    def test_missing_act4_art_falls_back_to_existing_images(self):
        assets = Assets()
        for name, fallback in PLACEHOLDERS.items():
            image = assets.raw(name)
            self.assertIsNotNone(image, name)
            self.assertIsNotNone(assets.raw(fallback))


if __name__ == "__main__":
    unittest.main()
