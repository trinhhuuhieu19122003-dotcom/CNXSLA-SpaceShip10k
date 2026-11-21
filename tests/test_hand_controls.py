"""Điều khiển tay mới: chụm ngón, nắm tay, tự bắn, hiệu chỉnh, tự tạm dừng khi bỏ tay."""
import tempfile
import unittest
from pathlib import Path

from tests import helpers  # noqa: F401
from tests.test_gestures import make_hand
from spaceship import config
from spaceship.app import Game
from spaceship.config import GameMode
from spaceship.core.settings import Settings
from spaceship.entities.player import Player
from spaceship.input.controls import ControlHub, ControlState
from spaceship.input.gestures import Gesture, Point, classify, zone_around
from spaceship.input.hand_tracker import HandReading
from spaceship.scenes.calibration import CalibrationScene
from spaceship.scenes.gameplay import GameplayScene
from spaceship.scenes.menu import MenuScene
from spaceship.scenes.options import OptionsScene
from spaceship.scenes.pause import PauseScene

class NoKeys(dict):
    def __missing__(self, key):
        return False


class FakeTracker:
    """Thay webcam thật: test tự đặt ``reading``."""

    def __init__(self):
        self.state = "running"
        self.reading = HandReading()
        self.zone = (0, 0, 1, 1)
        self.message, self.backend_name, self.fps = "", "fake", 30.0

    def show(self, gesture=Gesture.OPEN, x=0.5, y=0.5, raw=(0.5, 0.6)):
        self.reading = HandReading(True, x, y, gesture, raw[0], raw[1])

    def hide(self):
        self.reading = HandReading()

    def preview(self):
        return None

    def stop(self):
        pass


def settings():
    return Settings(path=Path(tempfile.mkdtemp()) / "settings.json")


class GestureTest(unittest.TestCase):
    def test_pinch_and_fist(self):
        hand = make_hand(set(["middle", "ring", "pinky"]))
        hand[4] = Point(hand[8].x + 0.01, hand[8].y + 0.01)         # đầu ngón cái chạm đầu ngón trỏ
        self.assertEqual(classify(hand), Gesture.PINCH)
        fist = make_hand()
        fist[4] = fist[8]                                         # nắm tay: ngón cái cũng sát ngón trỏ
        self.assertEqual(classify(fist), Gesture.FIST)

    def test_zone_stays_inside_camera(self):
        x0, y0, x1, y1 = zone_around((0.95, 0.98), 0.18, 1.15)
        self.assertTrue(0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1)
        self.assertAlmostEqual(x1 - x0, 0.36)


class ControlHubTest(unittest.TestCase):
    def setUp(self):
        self.tracker = FakeTracker()
        self.settings = settings()
        self.hub = ControlHub(self.tracker, self.settings)

    def poll(self, n=1):
        state = None
        for _ in range(n):
            state = self.hub.poll(NoKeys())
        return state

    def test_auto_fire_and_hand_target(self):
        self.tracker.show(x=0.25, y=0.5)
        s = self.poll()
        self.assertTrue(s.fire)
        self.assertEqual(s.source, "hand")
        self.assertEqual(s.target, (0.25 * config.WIDTH, 0.5 * config.HEIGHT))
        self.settings.auto_fire = False
        self.assertFalse(self.poll().fire)
        self.tracker.show(Gesture.POINT)
        self.assertTrue(self.poll().fire)

    def test_pinch_must_be_held(self):
        self.tracker.show(Gesture.PINCH)
        hold = int(config.PINCH_HOLD_SECONDS * config.TICK_RATE)
        self.assertFalse(self.poll(hold - 1).nuke)
        s = self.poll()
        self.assertTrue(s.nuke)
        self.assertEqual(s.skill_progress, 1.0)
        self.tracker.show(Gesture.OPEN)
        self.assertFalse(self.poll().nuke)

    def test_fist_is_focus(self):
        self.tracker.show(Gesture.FIST)
        self.assertTrue(self.poll().focus)

    def test_hand_lost_only_after_hand_play(self):
        self.tracker.hide()
        self.assertFalse(self.poll(200).hand_lost)                # chưa từng lái bằng tay
        self.tracker.show()
        self.poll()
        self.tracker.hide()
        ticks = int(config.HAND_PAUSE_SECONDS * config.TICK_RATE)
        self.assertFalse(self.poll(ticks - 2).hand_lost)
        self.assertTrue(self.poll(3).hand_lost)
        self.hub.reset_hand_mode()
        self.assertFalse(self.poll().hand_lost)

    def test_settings_update_tracker_zone(self):
        self.settings.hand_center = (0.3, 0.7)
        self.settings.sensitivity = "high"
        self.hub.apply_settings()
        x0, y0, x1, y1 = self.tracker.zone
        self.assertAlmostEqual((x0 + x1) / 2, 0.3)
        self.assertAlmostEqual(x1 - x0, 2 * config.HAND_SENSITIVITY["high"])


class FocusMovementTest(unittest.TestCase):
    def test_focus_caps_speed(self):
        p = Player()
        start = p.x
        p.move(ControlState(target=(p.x + 300, p.y), focus=True))
        self.assertAlmostEqual(p.x - start, config.FOCUS_HAND_SPEED)
        p.move(ControlState(move_x=1, focus=True))
        self.assertAlmostEqual(p.x - start, config.FOCUS_HAND_SPEED + config.FOCUS_KEYBOARD_SPEED)


class HandScenesTest(unittest.TestCase):
    def setUp(self):
        self.game = Game(camera=False, seed=3, settings=settings())
        self.tracker = FakeTracker()
        self.game.tracker = self.tracker
        self.game.controls = ControlHub(self.tracker, self.game.settings)

    def go(self, scene):
        self.game.change_scene(scene)
        self.game._apply_pending_scene()
        return scene

    def steps(self, n):
        for _ in range(n):
            self.game.scene.update(self.game.controls.poll(NoKeys()))
            self.game._apply_pending_scene()

    def test_menu_starts_with_calibration_then_saves_center(self):
        menu = self.go(MenuScene(self.game))
        menu._start(GameMode.ENDLESS)
        self.game._apply_pending_scene()
        self.assertIsInstance(self.game.scene, CalibrationScene)
        self.tracker.show(raw=(0.42, 0.71))
        self.game.render()
        self.steps(int(config.CALIBRATION_HOLD_SECONDS * config.TICK_RATE) + 60)
        self.assertIsInstance(self.game.scene, GameplayScene)
        self.assertEqual(self.game.settings.hand_center, (0.42, 0.71))
        self.assertAlmostEqual(sum(self.tracker.zone[::2]) / 2, 0.42)
        self.assertEqual(Settings.load(self.game.settings.path).hand_center, (0.42, 0.71))

    def test_calibration_skipped_without_camera(self):
        self.tracker.state = "unavailable"
        self.go(CalibrationScene(self.game, lambda: MenuScene(self.game)))
        self.steps(1)
        self.assertIsInstance(self.game.scene, MenuScene)

    def test_dropping_hand_pauses_and_raising_resumes(self):
        play = self.go(GameplayScene(self.game, GameMode.ENDLESS))
        self.tracker.show()
        self.steps(90)
        self.tracker.hide()
        self.steps(int(config.HAND_PAUSE_SECONDS * config.TICK_RATE) + 2)
        self.assertIsInstance(self.game.scene, PauseScene)
        self.assertEqual(self.game.scene.reason, "hand")
        self.game.render()
        t = play.world.survival_time
        self.steps(120)
        self.assertEqual(play.world.survival_time, t)
        self.tracker.show()
        self.steps(int((0.3 + config.RESUME_COUNTDOWN_SECONDS) * config.TICK_RATE) + 2)
        self.assertIs(self.game.scene, play)

    def test_options_toggle_and_persist(self):
        opts = self.go(OptionsScene(self.game))
        opts._do("auto_fire")
        opts._do("sensitivity")
        self.game.render()
        saved = Settings.load(self.game.settings.path)
        self.assertFalse(saved.auto_fire)
        self.assertEqual(saved.sensitivity, "high")


if __name__ == "__main__":
    unittest.main()
