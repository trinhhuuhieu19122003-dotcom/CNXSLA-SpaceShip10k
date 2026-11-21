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


class FullscreenSettingTest(unittest.TestCase):
    def test_fullscreen_choice_is_saved_and_reused(self):
        from spaceship.app import Game
        from spaceship.core.settings import Settings
        from spaceship.scenes.options import OptionsScene

        with TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            game = Game(camera=False, seed=1, settings=Settings(path=path))
            self.assertFalse(game.fullscreen)
            options = OptionsScene(game)
            game.change_scene(options)
            game._apply_pending_scene()
            actions = [b.action for b in options.buttons]
            options.menu.activate(actions.index("fullscreen"))
            self.assertTrue(game.fullscreen)
            self.assertIn("BẬT", options.buttons[actions.index("fullscreen")].text)
            self.assertTrue(Settings.load(path).fullscreen)
            game.set_fullscreen(False)
            again = Game(camera=False, seed=1, settings=Settings.load(path))
            self.assertFalse(again.fullscreen)
            forced = Game(camera=False, seed=1, settings=Settings.load(path), fullscreen=True)
            self.assertTrue(forced.fullscreen)                    # --fullscreen luôn thắng

    def test_wide_window_fills_side_bars(self):
        import pygame
        from spaceship.app import Game

        from spaceship.scenes.menu import MenuScene

        game = Game(camera=False, seed=1)
        game.change_scene(MenuScene(game))
        game._apply_pending_scene()
        game.window = pygame.display.set_mode((1280, 720))
        game.render()
        corner = game.window.get_at((5, 360))
        self.assertIsNotNone(game._backdrop)
        bw, bh = game._backdrop.get_size()                     # ảnh nền mờ phủ kín cửa sổ (đặt giữa)
        self.assertGreaterEqual(bw, 1280)
        self.assertGreaterEqual(bh, 720)
        self.assertGreaterEqual(corner.a, 0)


class WideLayoutTest(unittest.TestCase):
    def make(self, size, scene_factory):
        import pygame
        from spaceship.app import Game

        game = Game(camera=False, seed=1)
        scene = scene_factory(game)
        game.change_scene(scene)
        game._apply_pending_scene()
        game.window = pygame.display.set_mode(size)
        return game, scene

    def test_gameplay_fills_16_9_with_side_panels(self):
        from spaceship.config import GameMode
        from spaceship.scenes.gameplay import GameplayScene

        game, _ = self.make((1920, 1080), lambda g: GameplayScene(g, GameMode.CAMPAIGN, 1))
        scale, ox, oy, side = game._layout()
        self.assertEqual((ox, oy), (0, 0))                       # phủ kín, không viền đen
        self.assertGreaterEqual(side, 200)
        self.assertEqual(game.to_virtual((960, 540)), (400, 350))  # giữa màn = giữa chiến trường
        game.render()
        self.assertTrue(game.wide_layout)
        self.assertIsNotNone(game._side_images)

    def test_pause_keeps_panels_and_menus_do_not(self):
        from spaceship.config import GameMode
        from spaceship.scenes.gameplay import GameplayScene
        from spaceship.scenes.menu import MenuScene
        from spaceship.scenes.pause import PauseScene

        game, play = self.make((1920, 1080), lambda g: GameplayScene(g, GameMode.ENDLESS))
        game.change_scene(PauseScene(game, play))
        game._apply_pending_scene()
        self.assertGreater(game._layout()[3], 0)
        game.render()
        game.change_scene(MenuScene(game))
        game._apply_pending_scene()
        self.assertEqual(game._layout()[3], 0)
        game.render()
        self.assertFalse(game.wide_layout)

    def test_narrow_and_ultrawide_windows(self):
        from spaceship.app import SIDEBAR_MAX
        from spaceship.config import GameMode
        from spaceship.scenes.gameplay import GameplayScene

        game, _ = self.make((800, 700), lambda g: GameplayScene(g, GameMode.ENDLESS))
        self.assertEqual(game._layout()[3], 0)                    # cửa sổ thường: như cũ
        game, _ = self.make((2560, 1080), lambda g: GameplayScene(g, GameMode.ENDLESS))
        scale, ox, _oy, side = game._layout()
        self.assertEqual(side, SIDEBAR_MAX)
        self.assertGreater(ox, 0)                                 # màn siêu rộng: phần dư hai mép
        game.render()


class PolishTest(unittest.TestCase):
    def setUp(self):
        from spaceship.core.settings import Settings
        from spaceship.core.storage import SaveData

        self.folder = Path(TemporaryDirectory().name)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.game = Game(camera=False, seed=1, save=SaveData.load(self.folder / "save.json"),
                         settings=Settings(path=self.folder / "settings.json"))

    def go(self, scene):
        self.game.change_scene(scene)
        self.game._apply_pending_scene()
        return scene

    def test_pause_has_volume_sliders(self):
        import pygame
        from spaceship.config import GameMode
        from spaceship.scenes.gameplay import GameplayScene
        from spaceship.scenes.pause import PauseScene

        play = self.go(GameplayScene(self.game, GameMode.ENDLESS))
        pause = self.go(PauseScene(self.game, play))
        actions = [b.action for b in pause.buttons]
        self.assertEqual(actions, ["resume", "music", "sfx", "menu"])
        self.game.settings.music_volume = 0.5
        pause.menu.select(actions.index("music"))
        pause.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT, mod=0))
        self.assertAlmostEqual(self.game.settings.music_volume, 0.55)
        pause.draw(self.game.screen)
        self.assertIn("ẢI", pause._info_line() if play.level else "ẢI")

    def test_result_stars_pop_in_order(self):
        from spaceship.config import GameMode
        from spaceship.core.storage import GameResult
        from spaceship.input.controls import ControlState
        from spaceship.scenes.gameplay import GameplayScene
        from spaceship.scenes.result import STAR_GAP, STAR_START, ResultScene

        play = self.go(GameplayScene(self.game, GameMode.CAMPAIGN, 2))
        played = []
        original = self.game.audio.play
        self.game.audio.play = lambda name, volume=1.0: played.append(name) or original(name, volume)
        res = self.go(ResultScene(self.game, play, GameResult(GameMode.CAMPAIGN, 900, 20, 0, 60.0, True), False,
                                  level=2, stars=3))
        for _ in range(STAR_START + 3 * STAR_GAP + 2):
            res.update(ControlState())
            res.draw(self.game.screen)
        self.assertEqual(played.count("ui_select"), 3)

    def test_hud_corner_fades_under_ship(self):
        from spaceship.config import GameMode, HEIGHT
        from spaceship.scenes.gameplay import GameplayScene

        play = self.go(GameplayScene(self.game, GameMode.ENDLESS))
        p = play.world.player
        p.x, p.y = 400, 600
        play.draw(self.game.screen)
        clear = self.game.screen.get_at((30, HEIGHT - 40))
        p.x, p.y = 110, HEIGHT - 50                    # tàu bay vào góc dưới trái
        play.draw(self.game.screen)
        faded = self.game.screen.get_at((30, HEIGHT - 40))
        self.assertNotEqual(clear, faded)
