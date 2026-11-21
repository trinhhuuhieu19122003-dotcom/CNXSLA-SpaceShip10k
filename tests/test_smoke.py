"""Chạy thật toàn bộ game ở chế độ không màn hình: mọi scene, mọi chế độ."""
import unittest

import pygame

from tests import helpers  # noqa: F401
from spaceship.app import Game
from spaceship.config import GameMode
from spaceship.input.controls import ControlState
from spaceship.scenes.cutscene import INTRO_SCRIPT, CutsceneScene
from spaceship.scenes.gameplay import GameplayScene
from spaceship.scenes.info import AchievementsScene, HowToPlayScene
from spaceship.scenes.menu import MenuScene
from spaceship.scenes.pause import PauseScene
from spaceship.scenes.result import ResultScene


def key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="", scancode=0)


class SmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.game = Game(camera=False, seed=7)

    def go(self, scene):
        self.game.change_scene(scene)
        self.game._apply_pending_scene()
        return scene

    def run_ticks(self, n, draw_every=30):
        for i in range(n):
            self.game.step()
            if i % draw_every == 0:
                self.game.render()

    def test_static_scenes_render(self):
        for make in (MenuScene, HowToPlayScene, AchievementsScene):
            self.go(make(self.game))
            self.run_ticks(60)

    def test_cutscene_space_skips(self):
        g = self.game
        self.go(CutsceneScene(g, INTRO_SCRIPT, lambda: MenuScene(g)))
        g.scene.handle_event(key(pygame.K_SPACE))
        self.run_ticks(60)
        self.assertIsInstance(g.scene, MenuScene)

    def test_pause_and_resume(self):
        g = self.game
        play = self.go(GameplayScene(g, GameMode.ENDLESS))
        self.run_ticks(30)
        g.scene.handle_event(key(pygame.K_ESCAPE))
        g._apply_pending_scene()
        self.assertIsInstance(g.scene, PauseScene)
        t = play.world.survival_time
        self.run_ticks(30)
        self.assertEqual(play.world.survival_time, t)          # đang dừng thì thời gian đứng yên
        g.scene.handle_event(key(pygame.K_ESCAPE))
        g._apply_pending_scene()
        self.assertIs(g.scene, play)

    def test_every_mode_runs_with_bosses(self):
        g = self.game
        for mode in GameMode:
            play = self.go(GameplayScene(g, mode))
            w = play.world
            for t in range(60 * 130):
                w.player.weapon, w.player.level, w.player.bonus_damage = "laser", 6, 30
                w.player.hp, w.player.lives = w.player.max_hp, 3  # "bất tử" để đi hết nội dung
                target = next(iter(w.bosses), None) or min(w.enemies, key=lambda e: abs(e.x - w.player.x), default=None)
                g.scene.update(ControlState(target=(target.x if target else 400, 620), fire=True, nuke=True))
                g._apply_pending_scene()
                if t % 600 == 0:
                    g.render()
                if g.scene is not play:
                    break
            self.assertIsNone(w.outcome if mode.is_timed else None, mode)
            self.assertGreater(w.boss_kills, 0, mode)
            self.assertLess(len(w.enemy_bullets), 1500, mode)   # đạn được dọn, không rò rỉ

    def test_defeat_leads_to_result_and_saves(self):
        g = self.game
        play = self.go(GameplayScene(g, GameMode.INFERNO))
        before = g.save.modes[GameMode.INFERNO].games_played
        play.world.player.lives = 1
        play.world.player.invincible_timer = 0
        play.world.player.hp = 1
        play.world.enemy_bullets.clear()
        from spaceship.entities.projectiles import EnemyBullet
        p = play.world.player
        play.world.enemy_bullets.append(EnemyBullet(p.x, p.y, 90))
        self.run_ticks(2)
        self.assertIsInstance(g.scene, ResultScene)
        self.assertEqual(g.save.modes[GameMode.INFERNO].games_played, before + 1)
        self.run_ticks(60)


if __name__ == "__main__":
    unittest.main()
