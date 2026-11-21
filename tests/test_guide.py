"""Hướng dẫn và Sổ tay chiến đấu dưới SDL dummy."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pygame

from tests import helpers  # noqa: F401
from tests.test_hand_controls import FakeTracker
from spaceship import config
from spaceship.app import Game
from spaceship.core.settings import Settings
from spaceship.core.storage import SaveData
from spaceship.entities.enemies import Enemy, Parasite
from spaceship.input.controls import ControlHub, ControlState
from spaceship.input.gestures import Gesture
from spaceship.scenes.gameplay import GameplayScene
from spaceship.scenes.info import HowToPlayScene
from spaceship.scenes.menu import MenuScene


class GuideTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / "save.json"
        self.game = Game(camera=False, seed=11, save=SaveData(self.path),
                         settings=Settings(path=self.path.with_name("settings.json")))

    def go(self, scene):
        self.game.change_scene(scene)
        self.game._apply_pending_scene()
        return scene

    def press(self, key):
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=key))
        self.game._dispatch_events()

    def test_keyboard_changes_tabs_and_escape_returns(self):
        guide = self.go(HowToPlayScene(self.game))
        self.press(pygame.K_RIGHT)
        self.assertEqual(getattr(guide, "tab", 0), 1)
        self.press(pygame.K_LEFT)
        self.press(pygame.K_LEFT)
        self.assertEqual(guide.tab, 4)
        self.press(pygame.K_ESCAPE)
        self.assertIsInstance(self.game.scene, MenuScene)

    def test_hand_moves_focus_then_confirms_a_tab(self):
        guide = self.go(HowToPlayScene(self.game))
        tracker = FakeTracker()
        self.game.tracker = tracker
        self.game.controls = ControlHub(tracker, self.game.settings)
        x, y = guide.menu.rects[2].center
        x, y = x / config.WIDTH, y / config.HEIGHT
        tracker.show(x=x, y=y)
        self.game.step()
        self.assertEqual(guide.menu.selected, 2)
        self.assertEqual(guide.tab, 0)
        tracker.show(Gesture.PINCH, x=x, y=y)
        for _ in range(int(config.PINCH_HOLD_SECONDS * config.TICK_RATE) - 1):
            self.game.step()
        self.assertEqual(guide.tab, 0)
        self.game.step()
        self.assertEqual(guide.tab, 2)

    def test_bestiary_keyboard_can_pick_cards_and_switch_tab(self):
        guide = self.go(HowToPlayScene(self.game))
        self.press(pygame.K_LEFT)
        self.press(pygame.K_LEFT)
        self.press(pygame.K_DOWN)
        self.press(pygame.K_DOWN)
        self.press(pygame.K_RETURN)
        self.assertEqual(guide.book.selected, 1)
        self.press(pygame.K_LEFT)
        self.assertEqual(guide.tab, 2)

    def test_stationary_hand_does_not_steal_mouse_focus_in_bestiary(self):
        guide = self.go(HowToPlayScene(self.game))
        tracker = FakeTracker()
        self.game.tracker = tracker
        self.game.controls = ControlHub(tracker, self.game.settings)
        x, y = guide.menu.rects[0].center
        tracker.show(x=x / config.WIDTH, y=y / config.HEIGHT)
        self.game.step()
        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=guide.menu.rects[3].center, button=1))
        self.game._dispatch_events()
        self.game.step()
        self.assertEqual((guide.tab, guide.menu.selected), (3, 3))

    def test_bestiary_card_reveals_text_only_after_discovery(self):
        guide = self.go(HowToPlayScene(self.game))
        self.press(pygame.K_LEFT)
        self.press(pygame.K_LEFT)
        x, y = guide.menu.rects[5].center
        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(x, y), button=1))
        self.game._dispatch_events()
        with patch.object(self.game.assets, "text", wraps=self.game.assets.text) as draw_text:
            guide.draw(self.game.screen)
            self.assertNotIn("LÍNH ĐÀN", [c.args[0] for c in draw_text.call_args_list])
            self.assertIn("???", [c.args[0] for c in draw_text.call_args_list])
        self.game.save.mark_seen("grunt")
        with patch.object(self.game.assets, "text", wraps=self.game.assets.text) as draw_text:
            guide.draw(self.game.screen)
            self.assertIn("LÍNH ĐÀN", [c.args[0] for c in draw_text.call_args_list])

    def test_enemy_is_registered_when_it_enters_play_and_notice_expires(self):
        play = self.go(GameplayScene(self.game, config.GameMode.ENDLESS))
        enemy = Enemy(1, rng=self.game.rng, kamikaze_chance=0)
        enemy.x, enemy.y = 125, -20
        play.world.enemies.append(enemy)
        play.update(ControlState())
        self.assertFalse(self.path.exists())
        play.update(ControlState())
        self.assertEqual(SaveData.load(self.path, legacy_dirs=()).seen_enemies, {"grunt"})
        with patch.object(self.game.assets, "text", wraps=self.game.assets.text) as draw_text:
            play.draw(self.game.screen)
            self.assertIn("ĐỊCH MỚI · LÍNH ĐÀN", [c.args[0] for c in draw_text.call_args_list])

        # Các mục xuất hiện cùng đợt đều được lưu, nhưng lần lượt hiện thẻ.
        play.world.enemies.append(Parasite(1, 450, y=35, rng=self.game.rng))
        play.update(ControlState())
        self.assertEqual(SaveData.load(self.path, legacy_dirs=()).seen_enemies, {"grunt", "parasite"})
        self.assertEqual(play.encounter.name, "LÍNH ĐÀN")
        before = play.world.survival_time
        for _ in range(2 * 3 * config.TICK_RATE):
            play.update(ControlState())
        self.assertIsNone(play.encounter)
        self.assertGreater(play.world.survival_time, before)

    def test_enemy_is_registered_if_destroyed_as_it_crosses_the_top(self):
        play = self.go(GameplayScene(self.game, config.GameMode.ENDLESS))
        enemy = Enemy(1, rng=self.game.rng, kamikaze_chance=0)
        enemy.x, enemy.y, enemy.hp, enemy.burning = 125, -1, 0.01, True
        play.world.enemies.append(enemy)
        play.update(ControlState())
        self.assertNotIn(enemy, play.world.enemies)
        self.assertEqual(self.game.save.seen_enemies, {"grunt"})
        self.assertEqual(play.encounter.name, "LÍNH ĐÀN")
