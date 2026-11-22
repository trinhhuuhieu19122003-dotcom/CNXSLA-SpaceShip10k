"""Vòng lặp tín hiệu: chu kỳ mới sau khi phá đảo."""
import json
import tempfile
import unittest
from pathlib import Path

import pygame

from tests import helpers  # noqa: F401
from spaceship.app import Game
from spaceship.campaign.levels import LEVEL_COUNT
from spaceship.config import CYCLE_HP_STEP, GameMode
from spaceship.core.settings import Settings
from spaceship.core.storage import SaveData
from spaceship.scenes.cutscene import CutsceneScene
from spaceship.scenes.flow import start_level
from spaceship.scenes.gameplay import GameplayScene
from spaceship.scenes.level_select import LevelSelectScene


def cleared_save(folder: Path) -> SaveData:
    save = SaveData.load(folder / "save.json")
    for n in range(1, LEVEL_COUNT + 1):
        save.record_level(n, 3 if n % 2 else 2, LEVEL_COUNT)
    save.highscore = 9999
    save.seen_enemies = {"grunt", "boss"}
    return save


class CycleStorageTest(unittest.TestCase):
    def test_new_cycle_resets_progress_but_keeps_collection(self):
        folder = Path(tempfile.mkdtemp())
        save = cleared_save(folder)
        self.assertTrue(save.cycle_complete)
        self.assertEqual(save.cycle_history, {1: save.total_stars})
        self.assertTrue(save.start_new_cycle())
        self.assertEqual((save.cycle, save.unlocked_level, save.level_stars, save.cycle_complete), (2, 1, {}, False))
        self.assertTrue(save.campaign_cleared)                        # Hỏa ngục vẫn mở
        self.assertEqual((save.highscore, save.seen_enemies), (9999, {"grunt", "boss"}))
        self.assertFalse(save.start_new_cycle())                      # chưa phá đảo chu kỳ 2
        again = SaveData.load(folder / "save.json")
        self.assertEqual((again.cycle, again.unlocked_level, again.cycle_history[1]), (2, 1, save.cycle_history[1]))

    def test_old_cleared_save_can_start_cycle_two(self):
        folder = Path(tempfile.mkdtemp())
        (folder / "save.json").write_text(json.dumps({
            "version": 3, "highscore": 5,
            "campaign": {"unlocked_level": 10, "level_stars": {"1": 3, "2": 2}, "cleared": True},
        }), encoding="utf-8")
        save = SaveData.load(folder / "save.json")
        self.assertEqual((save.cycle, save.cycle_complete, save.cycle_history), (1, True, {1: 5}))


class CycleGameTest(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp())
        self.game = Game(camera=False, seed=2, save=cleared_save(self.folder),
                         settings=Settings(path=self.folder / "settings.json"))

    def go(self, scene):
        self.game.change_scene(scene)
        self.game._apply_pending_scene()
        return scene

    def test_level_select_new_cycle_needs_confirmation(self):
        scene = self.go(LevelSelectScene(self.game))
        actions = [b.action for b in scene.buttons]
        self.assertIn("new_cycle", actions)
        index = LEVEL_COUNT + actions.index("new_cycle")
        scene.menu.select(index)
        scene.menu.activate(index)
        self.assertEqual(self.game.save.cycle, 1)                     # lần 1 chỉ hỏi lại
        self.assertIn("CHẮC", scene.buttons[actions.index("new_cycle")].text)
        scene.draw(self.game.screen)
        scene.menu.activate(index)
        self.assertEqual((self.game.save.cycle, self.game.save.unlocked_level), (2, 1))
        self.assertNotIn("new_cycle", [b.action for b in scene.buttons])
        scene.draw(self.game.screen)

    def test_cycle_two_is_harder_and_has_new_intro(self):
        base = GameplayScene(self.game, GameMode.CAMPAIGN, 1).world.hp_mult
        self.game.save.start_new_cycle()
        play = GameplayScene(self.game, GameMode.CAMPAIGN, 1)
        self.assertEqual(play.world.cycle, 2)
        self.assertAlmostEqual(play.world.hp_mult, base * (1 + CYCLE_HP_STEP))
        self.assertEqual(GameplayScene(self.game, GameMode.ENDLESS).world.cycle, 1)   # chế độ khác không đổi
        self.game.calibrated = True
        start_level(self.game, 1)
        self.game._apply_pending_scene()
        intro = self.game.scene
        self.assertIsInstance(intro, CutsceneScene)
        self.assertIn("Mô phỏng ký ức số 1", intro.script[0].text)     # chu kỳ 2+ = "Mô phỏng ký ức"
        self.assertIn("MÔ PHỎNG KÝ ỨC 1", intro.subtitle)
        self.game.window = pygame.display.set_mode((1280, 720))
        self.go(play)
        self.game.render()                                             # bảng bên hiện chu kỳ không lỗi


if __name__ == "__main__":
    unittest.main()


class JourneyMapTest(unittest.TestCase):
    def test_every_level_intro_shows_map_and_ship_arrives(self):
        from spaceship.input.controls import ControlState

        folder = Path(tempfile.mkdtemp())
        game = Game(camera=False, seed=1, save=SaveData.load(folder / "save.json"),
                    settings=Settings(path=folder / "settings.json"))
        game.calibrated = True
        for number in range(1, LEVEL_COUNT + 1):
            start_level(game, number)
            game._apply_pending_scene()
            intro = game.scene
            self.assertIsInstance(intro, CutsceneScene)
            self.assertIsNotNone(intro.journey)
            for _ in range(160):
                intro.update(ControlState())
            intro.draw(game.screen)
            self.assertTrue(intro.journey.arrived)
        start_level(game, 1)
        game._apply_pending_scene()
        intro = game.scene
        for _ in range(60 * 30):                                 # tới câu thoại "nhiều mục tiêu áp sát"
            intro.update(ControlState())
            if intro.journey.blips or game.scene is not intro:
                break
        self.assertTrue(intro.journey.blips)
