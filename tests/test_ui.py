"""Bundled fonts and visual transitions under the dummy SDL drivers."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tests import helpers  # noqa: F401
from spaceship.app import Game
from spaceship.core.assets import Assets
from spaceship.core.scene import Scene


class FontTest(unittest.TestCase):
    def test_bundled_roles_and_legacy_arguments(self):
        assets = Assets()
        with patch("pygame.font.SysFont", side_effect=AssertionError("Expected a bundled font")):
            self.assertIs(assets.font(20, bold=True), assets.font(20, role="ui"))
            self.assertIs(assets.font(20, False), assets.font(20, role="body"))
            self.assertTrue(assets.font(20, True, True).get_italic())
            for role, line in (("display", "TÍN HIỆU CUỐI CÙNG"), ("ui", "HỎA NGỤC"),
                               ("label", "ĐỘ NHẠY TAY"), ("body", "Đạn thiêu đốt")):
                with self.subTest(role=role):
                    image = assets.text(line, 24, (255, 255, 255), role=role)
                    self.assertGreater(image.get_bounding_rect().width, 60)

    def test_missing_font_warns_once_across_sizes(self):
        with TemporaryDirectory() as folder, self.assertLogs("spaceship.core.assets", level="WARNING") as messages:
            assets = Assets(fonts_dir=Path(folder))
            self.assertGreater(assets.font(16, role="ui").size("HỎA NGỤC")[0], 0)
            assets.font(22, role="ui")
            assets.font(18, role="ui", italic=True)
        self.assertEqual(len(messages.output), 1)


class SolidScene(Scene):
    def __init__(self, game, color):
        super().__init__(game)
        self.color = color

    def draw(self, surface):
        surface.fill(self.color)


class TransitionTest(unittest.TestCase):
    def test_scene_switches_immediately_and_fades_through_black(self):
        game = Game(camera=False, seed=42)
        first, second = SolidScene(game, (255, 0, 0)), SolidScene(game, (0, 0, 255))
        with patch("spaceship.app.time.perf_counter", return_value=10.0) as clock:
            game.change_scene(first)
            game._apply_pending_scene()
            clock.return_value = 11.0
            game.render()
            game.change_scene(second)
            game._apply_pending_scene()
            self.assertIs(game.scene, second)
            clock.return_value = 11.125
            game.render()
            self.assertEqual(game.window.get_at((30, 30))[:3], (0, 0, 0))
            clock.return_value = 11.25
            game.render()
            self.assertEqual(game.window.get_at((30, 30))[:3], (0, 0, 255))

    def test_interrupted_transition_uses_last_presented_frame(self):
        game = Game(camera=False, seed=42)
        first = SolidScene(game, (255, 0, 0))
        intermediate = SolidScene(game, (0, 0, 255))
        final = SolidScene(game, (0, 255, 0))
        with patch("spaceship.app.time.perf_counter", return_value=10.0) as clock:
            game.change_scene(first)
            game._apply_pending_scene()
            clock.return_value = 11.0
            game.render()
            game.change_scene(intermediate)
            game._apply_pending_scene()
            clock.return_value = 11.05
            game.render()
            visible = game.window.get_at((30, 30))
            game.change_scene(final)
            game._apply_pending_scene()
            game.render()
            self.assertEqual(game.window.get_at((30, 30)), visible)
            self.assertIs(game.scene, final)


class MenuQuitConfirmTest(unittest.TestCase):
    def test_quit_needs_two_selections(self):
        from spaceship.app import Game
        from spaceship.scenes.menu import MENU_ITEMS, MenuScene
        from spaceship.input.controls import ControlState

        game = Game(camera=False, seed=1)
        menu = MenuScene(game)
        game.change_scene(menu)
        game._apply_pending_scene()
        game.running = True
        quit_index = len(MENU_ITEMS) - 1
        menu.menu.select(quit_index)
        menu.menu.activate(quit_index)
        self.assertTrue(game.running)                      # lần 1 chỉ hỏi lại
        menu.draw(game.screen)
        menu.menu.activate(quit_index)
        self.assertFalse(game.running)                     # lần 2 mới thoát
        game.running = True
        menu.quit_armed = 0
        menu.menu.activate(quit_index)
        for _ in range(200):                               # để quá 3 giây thì tự hủy
            menu.update(ControlState())
        self.assertEqual(menu.quit_armed, 0)
        menu.menu.activate(quit_index)
        self.assertTrue(game.running)
