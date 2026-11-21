"""Huy hiệu thành tựu, màn Thành tựu 2 thẻ, CHƠI MỚI (xóa sạch có sao lưu)."""
import json
import tempfile
import unittest
from pathlib import Path

import pygame

from tests import helpers  # noqa: F401
from spaceship.app import Game
from spaceship.campaign import achievements
from spaceship.campaign.achievements import RunStats, evaluate
from spaceship.campaign.levels import LEVEL_COUNT
from spaceship.config import GameMode
from spaceship.core.settings import Settings
from spaceship.core.storage import SaveData
from spaceship.input.controls import ControlState
from spaceship.scenes.gameplay import GameplayScene
from spaceship.scenes.info import AchievementsScene
from spaceship.scenes.level_select import LevelSelectScene


def key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="", scancode=0)


class AchievementRulesTest(unittest.TestCase):
    def setUp(self):
        self.save = SaveData.load(Path(tempfile.mkdtemp()) / "save.json")

    def test_unlocks_once_with_date_and_persists(self):
        run = RunStats(GameMode.CAMPAIGN, level=1, cleared=True, stars=3)
        keys = {a.key for a in evaluate(self.save, run)}
        self.assertEqual(keys, {"first_steps", "flawless"})
        self.assertEqual(evaluate(self.save, run), [])                       # không báo lại
        again = SaveData.load(self.save.path)
        self.assertRegex(again.achievements["first_steps"], r"\d{4}-\d{2}-\d{2}")

    def test_live_counters_are_not_double_counted(self):
        self.save.counters["skills"] = 20
        run = RunStats(GameMode.ENDLESS, skills=5)
        self.assertIn("rage", {a.key for a in evaluate(self.save, run)})
        save2 = SaveData.load(Path(tempfile.mkdtemp()) / "save.json")
        save2.counters["skills"] = 20
        run2 = RunStats(GameMode.ENDLESS, skills=5, recorded=True)            # đã cộng vào file rồi
        self.assertNotIn("rage", {a.key for a in evaluate(save2, run2)})

    def test_hand_pilot_and_hard_boss(self):
        run = RunStats(GameMode.CAMPAIGN, level=3, preset="hard", cleared=True, hand_ticks=900)
        keys = {a.key for a in evaluate(self.save, run)}
        self.assertTrue({"hand_pilot", "hardcore"} <= keys)
        run2 = RunStats(GameMode.CAMPAIGN, level=1, cleared=True, hand_ticks=900, keyboard_used=True)
        self.assertNotIn("hand_pilot", {a.key for a in evaluate(SaveData.load(Path(tempfile.mkdtemp()) / "s.json"), run2)})


class AchievementGameTest(unittest.TestCase):
    def setUp(self):
        folder = Path(tempfile.mkdtemp())
        self.folder = folder
        self.game = Game(camera=False, seed=2, save=SaveData.load(folder / "save.json"),
                         settings=Settings(path=folder / "settings.json"))

    def go(self, scene):
        self.game.change_scene(scene)
        self.game._apply_pending_scene()
        return scene

    def test_toast_in_game_and_list_on_result(self):
        play = self.go(GameplayScene(self.game, GameMode.ENDLESS))
        play.director.intro_timer = 0
        play.world.survival_time = 299.5
        for _ in range(70):
            play.update(ControlState())
        self.assertIn("endless5", self.game.save.achievements)
        self.assertTrue(any(getattr(t, "title", "") == "THÀNH TỰU MỚI" for t in play._encounters))
        play.draw(self.game.screen)
        play.world.outcome = "defeat"
        play.update(ControlState())
        self.game._apply_pending_scene()
        result = self.game.scene
        self.assertIn("endless5", [a.key for a in result.gameplay.new_achievements])
        result.draw(self.game.screen)

    def test_achievements_screen_tabs(self):
        scene = self.go(AchievementsScene(self.game))
        self.assertEqual(scene.tab, 0)
        scene.draw(self.game.screen)
        scene.handle_event(key(pygame.K_RIGHT))
        self.assertEqual(scene.tab, 1)
        scene.draw(self.game.screen)
        scene.menu.activate(0)
        self.assertEqual(scene.tab, 0)
        self.assertEqual(len(achievements.ACHIEVEMENTS), 18)

    def test_new_game_wipes_progress_keeps_settings_and_backs_up(self):
        save = self.game.save
        for n in range(1, LEVEL_COUNT + 1):
            save.record_level(n, 3, LEVEL_COUNT)
        save.seen_enemies = {"grunt"}
        save.highscore = 777
        save.counters["skills"] = 4
        evaluate(save)
        self.game.settings.music_volume = 0.35
        self.game.settings.save()
        scene = self.go(LevelSelectScene(self.game))
        index = LEVEL_COUNT + [b.action for b in scene.buttons].index("new_game")
        scene.menu.select(index)
        scene.menu.activate(index)
        self.assertEqual(save.highscore, 777)                                 # lần 1 chỉ hỏi lại
        scene.menu.activate(index)
        self.assertEqual((save.unlocked_level, save.level_stars, save.highscore, save.cycle), (1, {}, 0, 1))
        self.assertEqual((save.seen_enemies, save.achievements, save.counters), (set(), {}, {}))
        self.assertFalse(save.campaign_cleared)
        backups = list(self.folder.glob("save_backup_*.json"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(json.loads(backups[0].read_text(encoding="utf-8"))["highscore"], 777)
        self.assertAlmostEqual(Settings.load(self.folder / "settings.json").music_volume, 0.35)
        self.assertNotIn("new_cycle", [b.action for b in scene.buttons])
        scene.draw(self.game.screen)


if __name__ == "__main__":
    unittest.main()
