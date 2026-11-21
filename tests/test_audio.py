"""Âm thanh: nạp đủ file, giới hạn tiếng chồng, chuyển nhạc mượt, nhạc theo hồi/boss, chỉnh âm lượng."""
import json
import tempfile
import unittest
from pathlib import Path

import pygame

from tests import helpers  # noqa: F401
from spaceship.app import Game
from spaceship.config import AUDIO_DIR, GameMode
from spaceship.core import audio as audio_mod
from spaceship.core.audio import Audio
from spaceship.core.settings import Settings
from spaceship.core.storage import SaveData
from spaceship.entities.enemies import Boss
from spaceship.input.controls import ControlState
from spaceship.scenes.gameplay import GameplayScene
from spaceship.scenes.options import OptionsScene


def key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="", scancode=0)


class AudioUnitTest(unittest.TestCase):
    def setUp(self):
        self.audio = Audio(seed=1)

    def test_every_file_exists_and_loads(self):
        self.assertTrue(self.audio.enabled)
        for name, rule in audio_mod.SFX.items():
            self.assertTrue(self.audio.has(name), name)
        for track, (file, _gain) in audio_mod.MUSIC.items():
            self.assertTrue((AUDIO_DIR / file).exists(), track)
        for name in ("boss_siren", "radar", "glitch", "blip_kx", "blip_aria", "blip_cmd", "radio_cmd"):
            self.assertTrue(self.audio.has(name), name)
        self.assertTrue(self.audio.has("beep"))          # tên cũ vẫn dùng được

    def test_rapid_repeats_are_limited(self):
        self.assertTrue(self.audio.play("explode_boss"))
        self.assertFalse(self.audio.play("explode_boss"))   # tối đa 1 bản cùng lúc
        self.assertTrue(self.audio.play("pickup"))
        self.assertFalse(self.audio.play("pickup"))         # chưa qua khoảng nghỉ tối thiểu
        self.assertFalse(self.audio.play("khong_ton_tai"))

    def test_muted_sfx_plays_nothing(self):
        self.audio.set_volumes(0.5, 0.0)
        self.assertFalse(self.audio.play("ui_select"))

    def test_music_fades_out_then_in(self):
        a = self.audio
        a.play_music("act1")
        for _ in range(audio_mod.FADE_IN_TICKS + 2):
            a.update()
        self.assertEqual((a._playing, a._fade), ("act1", 1.0))
        a.play_music("game")
        a.update()
        self.assertEqual(a._playing, "act1")                # bài cũ còn đang nhỏ dần
        self.assertLess(a._fade, 1.0)
        for _ in range(audio_mod.FADE_OUT_TICKS + audio_mod.FADE_IN_TICKS + 2):
            a.update()
        self.assertEqual((a._playing, a._fade), ("game", 1.0))
        a.play_music(None)
        for _ in range(audio_mod.FADE_OUT_TICKS + 2):
            a.update()
        self.assertIsNone(a._playing)

    def test_dialogue_ducks_music(self):
        a = self.audio
        for _ in range(40):
            a.duck()
            a.update()
        self.assertLess(a._duck, 0.6)
        for _ in range(80):
            a.update()
        self.assertGreater(a._duck, 0.95)


class VolumeSettingsTest(unittest.TestCase):
    def test_step_volume(self):
        self.assertEqual(Settings.step_volume(0.7, 0.1), 0.8)
        self.assertEqual(Settings.step_volume(1.0, 0.1), 1.0)
        self.assertEqual(Settings.step_volume(1.0, 0.1, wrap=True), 0.0)
        self.assertEqual(Settings.step_volume(0.0, -0.1), 0.0)

    def test_round_trip_and_clamp(self):
        path = Path(tempfile.mkdtemp()) / "settings.json"
        s = Settings(path=path, music_volume=0.3, sfx_volume=0.9)
        s.save()
        loaded = Settings.load(path)
        self.assertEqual((loaded.music_volume, loaded.sfx_volume), (0.3, 0.9))
        path.write_text(json.dumps({"music_volume": 7, "sfx_volume": "to"}), encoding="utf-8")
        loaded = Settings.load(path)
        self.assertEqual((loaded.music_volume, loaded.sfx_volume), (1.0, 0.8))


class GameAudioTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        folder = Path(tempfile.mkdtemp())
        cls.game = Game(camera=False, seed=3, save=SaveData.load(folder / "save.json"),
                        settings=Settings(path=folder / "settings.json"))
        cls.played = []
        original = cls.game.audio.play

        def record(name, volume=1.0):
            cls.played.append(name)
            return original(name, volume)

        cls.game.audio.play = record

    def go(self, scene):
        self.game.change_scene(scene)
        self.game._apply_pending_scene()
        return scene

    def test_battle_events_have_sounds(self):
        g = self.game
        self.played.clear()
        play = self.go(GameplayScene(g, GameMode.CAMPAIGN, 3))
        w = play.world
        self.assertEqual(play.music, "act1")
        saw_boss_music = False
        for _ in range(60 * 200):
            p = w.player
            p.hp, p.lives = p.max_hp, 3
            target = next(iter(w.bosses), None) or min(
                (e for e in w.enemies if e.y > 0), key=lambda e: abs(e.x - p.x), default=None)
            g.scene.update(ControlState(target=(target.x if target else 400, 620), fire=True, nuke=True))
            g._apply_pending_scene()
            saw_boss_music |= bool(w.bosses) and play.music == "game"
            if g.scene is not play:
                break
        self.assertTrue(saw_boss_music, "trận boss phải chuyển sang nhạc gốc")
        unknown = sorted({n for n in self.played if not g.audio.has(n)})
        self.assertEqual(unknown, [], "có tên tiếng không tồn tại")
        for expected in ("fire_laser", "hit", "explode_small", "boss_siren", "explode_boss", "rage_full",
                         "skill_laser", "victory"):
            self.assertIn(expected, self.played)

    def test_final_boss_and_inferno_music(self):
        g = self.game
        play = self.go(GameplayScene(g, GameMode.CAMPAIGN, 10))
        self.assertEqual(play.music, "act3")
        play.world.enemies.append(Boss(1.0, kind="mothership"))
        play.update(ControlState(target=None))
        self.assertEqual((play.music, g.audio.music_track), ("final_boss", "final_boss"))
        inferno = self.go(GameplayScene(g, GameMode.INFERNO))
        self.assertEqual(inferno.music, "act3")             # bản cũ Hỏa ngục im lặng

    def test_options_volume_controls(self):
        g = self.game
        scene = self.go(OptionsScene(g))
        g.settings.music_volume = 0.7
        actions = [b.action for b in scene.buttons]
        scene.menu.select(actions.index("music"))
        scene.handle_event(key(pygame.K_RIGHT))
        self.assertAlmostEqual(g.settings.music_volume, 0.8)
        self.assertAlmostEqual(g.audio.music_volume, 0.8)
        self.assertEqual(json.loads(g.settings.path.read_text(encoding="utf-8"))["music_volume"], 0.8)
        g.settings.sfx_volume = 1.0
        scene.menu.select(actions.index("sfx"))             # chọn (chụm tay) quá 100% thì về 0
        scene.handle_event(key(pygame.K_RETURN))
        self.assertEqual(g.settings.sfx_volume, 0.0)
        self.assertIn("0%", scene.buttons[actions.index("sfx")].text)


if __name__ == "__main__":
    unittest.main()
