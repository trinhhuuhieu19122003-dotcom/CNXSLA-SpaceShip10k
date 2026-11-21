"""Chữ sắc nét khi phóng to: ghi lại chữ, vẽ lại ở cỡ lớn, giữ đúng thứ tự vẽ."""
import unittest

import pygame

from tests import helpers  # noqa: F401
from spaceship import config
from spaceship.core.assets import Assets
from spaceship.ui.crisp import CrispSurface, TextSurface, crisp_text, make_crisp

WHITE = (255, 255, 255)


class CrispSurfaceTest(unittest.TestCase):
    def setUp(self):
        self.assets = Assets()
        self.surf = CrispSurface((200, 100)).setup()
        self.surf.fill((0, 0, 0))
        self.text = self.assets.text("ABC", 24, WHITE, role="ui")

    def test_text_remembers_how_it_was_drawn(self):
        self.assertIsInstance(self.text, TextSurface)
        self.assertEqual(self.text.spec[:3], ("ABC", 24, (255, 255, 255, 255)))

    def test_disabled_draws_immediately(self):
        self.surf.blit(self.text, (10, 10))
        self.assertEqual(self.surf.records, [])
        self.assertGreater(pygame.transform.average_color(self.surf, (10, 10, *self.text.get_size()))[0], 20)

    def test_enabled_records_then_bake_draws_same_pixels(self):
        reference = pygame.Surface((200, 100))
        reference.fill((0, 0, 0))
        reference.blit(self.text, (10, 10))
        self.surf.begin(True)
        self.surf.blit(self.text, (10, 10))
        self.assertEqual(len(self.surf.records), 1)
        w, h = self.text.get_size()
        self.assertEqual(pygame.transform.average_color(self.surf, (10, 10, w, h))[:3], (0, 0, 0))   # chưa vẽ
        self.surf.begin(False)                      # nướng
        self.assertEqual(self.surf.records, [])
        for x in range(10, 10 + self.text.get_width(), 3):
            self.assertEqual(self.surf.get_at((x, 22)), reference.get_at((x, 22)))

    def test_something_drawn_over_text_keeps_the_order(self):
        self.surf.begin(True)
        self.surf.blit(self.text, (10, 10))
        cover = pygame.Surface((200, 100))
        cover.fill((200, 0, 0))
        self.surf.blit(cover, (0, 0))               # bảng đè lên chữ
        self.assertEqual(self.surf.records, [])     # chữ đã được vẽ (thấp) TRƯỚC bảng
        self.surf.begin(False)
        self.assertEqual(self.surf.get_at((20, 22))[:3], (200, 0, 0))

    def test_opaque_full_fill_drops_text_and_darken_bakes_it(self):
        self.surf.begin(True)
        self.surf.blit(self.text, (10, 10))
        self.surf.fill((0, 0, 0))
        self.assertEqual(self.surf.records, [])
        self.surf.blit(self.text, (10, 10))
        self.surf.fill((128, 128, 128), special_flags=pygame.BLEND_MULT)
        self.assertEqual(self.surf.records, [])

    def test_text_outside_clip_is_drawn_normally(self):
        self.surf.begin(True)
        self.surf.blit(self.text, (190, 10))       # tràn mép phải
        self.assertEqual(self.surf.records, [])

    def test_crisp_text_matches_target_width(self):
        spec = self.text.spec
        hires = crisp_text(self.assets, spec, 1.54, self.text.get_width() * 1.54)
        self.assertLessEqual(abs(hires.get_width() - self.text.get_width() * 1.54), 4)
        self.assertGreater(hires.get_height(), self.text.get_height())

    def test_draw_crisp_puts_sharp_text_on_scaled_frame(self):
        self.surf.begin(True)
        self.surf.blit(self.text, (10, 10))
        frame = pygame.Surface((400, 200))
        frame.fill((0, 0, 0))
        self.surf.draw_crisp(frame, self.assets, 2.0, 2.0)
        w, h = self.text.get_size()
        self.assertGreater(pygame.transform.average_color(frame, (20, 20, w * 2, h * 2))[0], 20)


class GameCrispRenderTest(unittest.TestCase):
    def make(self, size):
        from spaceship.app import Game
        from spaceship.scenes.options import OptionsScene

        game = Game(camera=False, seed=1)
        game.change_scene(OptionsScene(game))
        game._apply_pending_scene()
        game._fade_started = None
        game.window = pygame.display.set_mode(size)
        return game

    def test_fullscreen_1080p_redraws_text_and_leaves_screen_complete(self):
        game = self.make((1920, 1080))
        seen = []
        original = CrispSurface.draw_crisp

        def spy(surf, *args, **kwargs):
            seen.append(len(surf.records))
            return original(surf, *args, **kwargs)

        CrispSurface.draw_crisp = spy
        try:
            game.render()
        finally:
            CrispSurface.draw_crisp = original
        self.assertTrue(seen and max(seen) > 5)
        self.assertFalse(game.screen.enabled)
        self.assertEqual(game.screen.records, [])

    def test_one_to_one_window_does_not_record(self):
        game = self.make((config.WIDTH, config.HEIGHT))
        game.render()
        self.assertFalse(game.screen.enabled)

    def test_make_crisp_matches_display_format(self):
        pygame.display.set_mode((100, 100))
        surf = make_crisp((10, 10))
        self.assertIsInstance(surf, CrispSurface)
        self.assertEqual(surf.records, [])


if __name__ == "__main__":
    unittest.main()


class HudCornerCrispTest(unittest.TestCase):
    def test_corner_hud_text_is_redrawn_when_scaled_and_drawn_normally_at_1x(self):
        from spaceship.app import Game
        from spaceship.config import GameMode
        from spaceship.scenes.gameplay import GameplayScene

        game = Game(camera=False, seed=4)
        play = GameplayScene(game, GameMode.CAMPAIGN, 1)
        game.change_scene(play)
        game._apply_pending_scene()
        game._fade_started = None
        seen = []
        original = CrispSurface.draw_crisp

        def spy(surf, *args, **kwargs):
            seen.extend(r[0].spec[0] for r in surf.records)
            return original(surf, *args, **kwargs)

        CrispSurface.draw_crisp = spy
        try:
            game.window = pygame.display.set_mode((1024, 768))     # 4:3: khung hẹp, HUD ở 4 góc, phóng 1,1 lần
            game.render()
            self.assertIn("HP", seen)                             # chữ trong ô góc được vẽ lại sắc nét
            self.assertIn("NỘ", seen)
            seen.clear()
            game.window = pygame.display.set_mode((config.WIDTH, config.HEIGHT))
            game.render()
            self.assertEqual(seen, [])
        finally:
            CrispSurface.draw_crisp = original
        frame = pygame.Surface((config.WIDTH, config.HEIGHT))
        play.draw(frame)                                          # vẽ thẳng (không ghi) vẫn đủ chữ
        self.assertGreater(pygame.transform.average_color(frame, (20, config.HEIGHT - 70, 30, 20))[0], 5)


class UpscaleTest(unittest.TestCase):
    def test_sizes_and_sharp_paths(self):
        from spaceship.app import upscale

        src = pygame.Surface((800, 700))
        src.fill((0, 0, 0))
        src.fill((255, 255, 255), (400, 0, 1, 700))            # vạch trắng rộng 1 điểm ảnh
        self.assertIs(upscale(src, (800, 700)), src)
        for size in ((1234, 1080), (1645, 1440), (2468, 2160)):
            self.assertEqual(upscale(src, size).get_size(), size)
        big = upscale(src, (2468, 2160))                        # 4K: nhân điểm ảnh thẳng, không làm mượt
        row = [big.get_at((x, 100))[0] for x in range(1230, 1250)]
        self.assertTrue(set(row) <= {0, 255})


class BakeOutsideTest(unittest.TestCase):
    def test_text_crossing_regions_is_drawn_normally(self):
        assets = Assets()
        surf = CrispSurface((200, 50)).setup()
        surf.fill((0, 0, 0))
        surf.begin(True)
        inside = assets.text("A", 20, WHITE, role="ui")
        across = assets.text("WWWW", 20, WHITE, role="ui")
        surf.blit(inside, (5, 5))
        surf.blit(across, (100 - across.get_width() // 2, 5))   # nằm vắt qua ranh giới x = 100
        surf.bake_outside((pygame.Rect(0, 0, 100, 50), pygame.Rect(100, 0, 100, 50)))
        self.assertEqual([r[0] for r in surf.records], [inside])
        self.assertGreater(pygame.transform.average_color(surf, (100 - across.get_width() // 2, 5,
                                                                 *across.get_size()))[0], 10)
