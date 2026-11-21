"""Nhạc nền + hiệu ứng âm thanh. Không có loa/âm thanh thì game vẫn chạy bình thường."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import pygame

from spaceship.config import AUDIO_DIR

log = logging.getLogger(__name__)

MUSIC_TRACKS = {"menu": "menu_music.mp3", "game": "game_music.mp3"}
SFX_FILES = {"laser": ("laser.mp3", 0.4), "explosion": ("explosion.mp3", 0.6)}
# Âm "bíp" tự tổng hợp bằng sóng sin: (tần số Hz, thời lượng s, âm lượng)
SYNTH_TONES = {"beep": (800, 0.05, 0.1), "glitch": (300, 0.1, 0.2), "radar": (1200, 0.2, 0.15)}
# Không phát lại cùng một âm trong khoảng này (ms) để tránh rè khi nổ hàng loạt.
MIN_REPEAT_MS = {"explosion": 60, "laser": 40}


class Audio:
    def __init__(self, audio_dir: Path = AUDIO_DIR) -> None:
        self.audio_dir = audio_dir
        self.enabled = False
        self._sounds: Dict[str, pygame.mixer.Sound] = {}
        self._last_played: Dict[str, int] = {}
        self._current_music: Optional[str] = None
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.set_num_channels(32)
            self.enabled = True
        except pygame.error as exc:
            log.warning("Không khởi tạo được âm thanh (%s) - chạy không tiếng", exc)
            return
        for name, (filename, volume) in SFX_FILES.items():
            try:
                sound = pygame.mixer.Sound(str(audio_dir / filename))
                sound.set_volume(volume)
                self._sounds[name] = sound
            except (pygame.error, FileNotFoundError) as exc:
                log.warning("Thiếu âm thanh %s (%s)", filename, exc)
        for name, (freq, duration, volume) in SYNTH_TONES.items():
            self._sounds[name] = self.make_tone(freq, duration, volume)

    @staticmethod
    def make_tone(frequency: float, duration: float, volume: float) -> pygame.mixer.Sound:
        """Tạo âm sin bằng numpy (bản cũ dùng vòng for từng mẫu, chậm)."""
        sample_rate, _fmt, channels = pygame.mixer.get_init()
        t = np.arange(int(round(duration * sample_rate))) / sample_rate
        wave = (np.sin(2 * np.pi * frequency * t) * 32767 * volume).astype(np.int16)
        if channels > 1:
            wave = np.repeat(wave[:, None], channels, axis=1)
        return pygame.sndarray.make_sound(np.ascontiguousarray(wave))

    def play(self, name: str) -> None:
        if not self.enabled or name not in self._sounds:
            return
        now = pygame.time.get_ticks()
        if now - self._last_played.get(name, -10_000) < MIN_REPEAT_MS.get(name, 0):
            return
        self._last_played[name] = now
        self._sounds[name].play()

    def play_music(self, track: Optional[str]) -> None:
        if not self.enabled or track == self._current_music:
            return
        self._current_music = track
        pygame.mixer.music.stop()
        if track is None:
            return
        try:
            pygame.mixer.music.load(str(self.audio_dir / MUSIC_TRACKS[track]))
            pygame.mixer.music.set_volume(0.4)
            pygame.mixer.music.play(-1)
        except (pygame.error, KeyError, FileNotFoundError) as exc:
            log.warning("Không phát được nhạc %s (%s)", track, exc)
