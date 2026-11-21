"""Nhạc nền + hiệu ứng âm thanh. Không có loa/âm thanh thì game vẫn chạy bình thường.

Ba ý chính:
* **Hiệu ứng** (``SFX``): mỗi tiếng có âm lượng gốc, số bản phát cùng lúc tối đa và khoảng nghỉ tối thiểu,
  để 10 viên đạn nổ cùng tick không chồng thành tiếng rè. Tiếng lặp nhiều (bắn, trúng, nổ nhỏ) có 3 bản
  cao độ hơi khác nhau, chọn ngẫu nhiên để nghe không "máy móc".
* **Nhạc** (``MUSIC``): đổi bài thì bài cũ nhỏ dần rồi bài mới to dần, không cắt cụt. Có "duck": khi có
  hội thoại, nhạc tự nhỏ lại cho dễ nghe.
* **Tiếng tổng hợp** bằng numpy: còi báo boss, tiếng gõ chữ riêng cho từng nhân vật, radar, nhiễu sóng.

Mọi âm lượng nhân với hai thanh chỉnh trong Cài đặt (``set_volumes``).
"""
from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pygame

from spaceship.config import AUDIO_DIR

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Sfx:
    file: str
    volume: float
    max_voices: int = 2          # số bản phát chồng tối đa
    min_gap_ms: int = 0          # không phát lại sớm hơn khoảng này
    pitch: bool = False          # tạo 3 bản cao độ khác nhau


SFX: Dict[str, Sfx] = {
    # Súng (tự bắn liên tục nên để nhỏ)
    "fire_plasma": Sfx("sfx/fire_plasma.ogg", 0.20, 2, 70, True),
    "fire_laser": Sfx("sfx/fire_laser.ogg", 0.22, 2, 90, True),
    "fire_homing": Sfx("sfx/fire_homing.ogg", 0.28, 2, 90, True),
    "fire_lightning": Sfx("sfx/fire_lightning.ogg", 0.16, 2, 90, True),
    # Trúng / nổ
    "hit": Sfx("sfx/hit.ogg", 0.30, 3, 70, True),
    "explode_small": Sfx("sfx/explode_small.ogg", 0.40, 4, 40, True),
    "explode_big": Sfx("sfx/explode_big.ogg", 0.60, 3, 80, True),
    "explode_boss": Sfx("sfx/explode_boss.ogg", 0.90, 1),
    "player_hurt": Sfx("sfx/player_hurt.ogg", 0.65, 1, 150),
    "shield_block": Sfx("sfx/shield_block.ogg", 0.40, 2, 80, True),
    # Vật phẩm, Nộ, kỹ năng
    "pickup": Sfx("sfx/pickup.ogg", 0.55, 2, 50),
    "level_up": Sfx("sfx/level_up.ogg", 0.60, 1, 80),
    "wrong_weapon": Sfx("sfx/wrong_weapon.ogg", 0.55, 1, 80),
    "rage_full": Sfx("sfx/rage_full.ogg", 0.70, 1, 500),
    "skill_laser": Sfx("sfx/skill_laser.ogg", 0.85, 1),
    "skill_plasma": Sfx("sfx/skill_plasma.ogg", 0.85, 1),
    "skill_homing": Sfx("sfx/skill_homing.ogg", 0.85, 1),
    "skill_lightning": Sfx("sfx/skill_lightning.ogg", 0.85, 1),
    # Diễn biến trận
    "boss_phase": Sfx("sfx/boss_phase.ogg", 0.75, 1, 500),
    "wave_clear": Sfx("sfx/wave_clear.ogg", 0.60, 1, 500),
    "victory": Sfx("sfx/victory.ogg", 0.60, 1, 1000),
    "defeat": Sfx("sfx/defeat.ogg", 0.70, 1, 1000),
    # Giao diện
    "ui_move": Sfx("sfx/ui_move.ogg", 0.55, 2, 30),
    "ui_select": Sfx("sfx/ui_select.ogg", 0.50, 1, 60),
    "ui_back": Sfx("sfx/ui_back.ogg", 0.50, 1, 60),
}
PITCH_STEPS = (0.93, 1.0, 1.07)

#: tên cũ trong code -> tiếng mới
ALIASES = {"beep": "ui_move", "laser": "fire_laser", "explosion": "explode_small"}

#: tên bài -> (file trong assets/audio, hệ số âm lượng). Hai bài gốc thời đại học to hơn các bài mới
#: khoảng 9 dB nên được hạ xuống cho đều.
MUSIC: Dict[str, Tuple[str, float]] = {
    "menu": ("menu_music.mp3", 0.38),          # bản gốc thời đại học
    "game": ("game_music.mp3", 0.38),          # bản gốc: boss thường + chế độ Vô tận
    "briefing": ("music/menu_ambient.ogg", 1.0),
    "act1": ("music/act1.ogg", 1.0),
    "act2": ("music/act2.ogg", 1.0),
    "act3": ("music/act3.ogg", 1.0),
    "final_boss": ("music/final_boss.ogg", 1.0),
    "ending": ("music/ending.ogg", 1.0),
}
MUSIC_LEVEL = 0.6            # trần âm lượng nhạc (thanh chỉnh 100% = mức này)
FADE_OUT_TICKS = 36          # 0,6 giây
FADE_IN_TICKS = 48           # 0,8 giây
DUCK_LEVEL = 0.5             # nhạc còn 50% khi có hội thoại
DUCK_SPEED = 0.08

#: người nói -> giọng gõ chữ
SPEAKER_VOICES = {"KX-17": "kx", "ARIA": "aria", "CHỈ HUY": "cmd"}


class Audio:
    def __init__(self, audio_dir: Path = AUDIO_DIR, *, music_volume: float = 0.7, sfx_volume: float = 0.8,
                 seed: Optional[int] = None) -> None:
        self.audio_dir = audio_dir
        self.enabled = False
        self.music_volume = music_volume
        self.sfx_volume = sfx_volume
        self._rng = random.Random(seed)           # riêng cho âm thanh: không làm lệch RNG của trận đấu
        self._variants: Dict[str, List[pygame.mixer.Sound]] = {}
        self._base: Dict[str, float] = {}
        self._rules: Dict[str, Sfx] = {}
        self._last_played: Dict[str, int] = {}
        # Nhạc
        self._target: Optional[str] = None          # bài được yêu cầu
        self._playing: Optional[str] = None         # bài đang nạp trong mixer
        self._fade = 0.0
        self._duck = 1.0
        self._duck_wanted = False
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.set_num_channels(40)
            self.enabled = True
        except pygame.error as exc:
            log.warning("Không khởi tạo được âm thanh (%s) - chạy không tiếng", exc)
            return
        for name, rule in SFX.items():
            try:
                sound = pygame.mixer.Sound(str(audio_dir / rule.file))
            except (pygame.error, FileNotFoundError) as exc:
                log.warning("Thiếu âm thanh %s (%s)", rule.file, exc)
                continue
            variants = [sound]
            if rule.pitch:
                variants = [sound if step == 1.0 else self._repitch(sound, step) for step in PITCH_STEPS]
            self._add(name, variants, rule.volume, rule)
        for name, (sound, volume, rule) in self._synthesize().items():
            self._add(name, [sound], volume, rule)
        self._apply_sfx_volume()

    # --- Nạp / tổng hợp ----------------------------------------------------------------------
    def _add(self, name: str, variants, volume: float, rule: Sfx) -> None:
        self._variants[name] = variants
        self._base[name] = volume
        self._rules[name] = rule

    @staticmethod
    def _repitch(sound: pygame.mixer.Sound, step: float) -> pygame.mixer.Sound:
        """Đổi cao độ bằng cách lấy mẫu lại (nhanh hơn = cao hơn, ngắn hơn)."""
        data = pygame.sndarray.array(sound).astype(np.float32)
        n = data.shape[0]
        positions = np.arange(0, n - 1, step, dtype=np.float32)
        if data.ndim == 1:
            out = np.interp(positions, np.arange(n), data)
        else:
            out = np.stack([np.interp(positions, np.arange(n), data[:, c]) for c in range(data.shape[1])], axis=1)
        return pygame.sndarray.make_sound(np.ascontiguousarray(out.astype(np.int16)))

    @staticmethod
    def _to_sound(wave: np.ndarray) -> pygame.mixer.Sound:
        _rate, _fmt, channels = pygame.mixer.get_init()
        pcm = (np.clip(wave, -1, 1) * 32767).astype(np.int16)
        if channels > 1:
            pcm = np.repeat(pcm[:, None], channels, axis=1)
        return pygame.sndarray.make_sound(np.ascontiguousarray(pcm))

    @staticmethod
    def _envelope(n: int, rate: int, attack: float = 0.004, release: float = 0.02) -> np.ndarray:
        env = np.ones(n, dtype=np.float32)
        a, r = min(n, int(attack * rate)), min(n, int(release * rate))
        if a:
            env[:a] = np.linspace(0, 1, a)
        if r:
            env[-r:] *= np.linspace(1, 0, r)
        return env

    def _synthesize(self) -> Dict[str, Tuple[pygame.mixer.Sound, float, Sfx]]:
        rate = pygame.mixer.get_init()[0]

        def t_axis(seconds: float) -> np.ndarray:
            return np.arange(int(seconds * rate), dtype=np.float32) / rate

        def blip(freq: float, seconds: float, shape: str) -> np.ndarray:
            t = t_axis(seconds)
            phase = (freq * t) % 1.0
            if shape == "square":
                wave = np.where(phase < 0.5, 0.6, -0.6)
            elif shape == "saw":
                wave = (2 * phase - 1) * 0.6
            else:
                wave = np.sin(2 * np.pi * freq * t)
            return wave * self._envelope(len(t), rate, 0.002, seconds * 0.6)

        def gap(seconds: float) -> np.ndarray:
            return np.zeros(int(seconds * rate), dtype=np.float32)

        sounds: Dict[str, Tuple[pygame.mixer.Sound, float, Sfx]] = {}
        voices = {"kx": (196, "square", 0.035), "aria": (1046, "sine", 0.030), "cmd": (147, "saw", 0.045)}
        for key, (freq, shape, length) in voices.items():
            # tiếng gõ chữ trong đoạn hội thoại
            sounds[f"blip_{key}"] = (self._to_sound(blip(freq, length, shape)), 0.16, Sfx("", 0, 2, 40))
            # "tít-tít-tít" mở bộ đàm khi có thoại trong trận
            chirp = np.concatenate([blip(freq * 2, 0.04, shape), gap(0.03), blip(freq * 2.5, 0.04, shape),
                                    gap(0.03), blip(freq * 3, 0.05, shape)])
            sounds[f"radio_{key}"] = (self._to_sound(chirp), 0.22, Sfx("", 0, 1, 300))

        # Còi báo động boss: 3 nhịp quét lên xuống
        t = t_axis(0.55)
        sweep = 420 + 340 * np.sin(np.pi * t / t[-1])
        phase = 2 * np.pi * np.cumsum(sweep) / rate
        cycle = (np.sin(phase) + 0.3 * np.sin(3 * phase)) * self._envelope(len(t), rate, 0.01, 0.05)
        siren = np.concatenate([cycle, gap(0.08), cycle, gap(0.08), cycle]) * 0.7
        sounds["boss_siren"] = (self._to_sound(siren), 0.45, Sfx("", 0, 1, 2000))

        # Radar: tiếng "ping" tắt dần
        t = t_axis(0.45)
        ping = np.sin(2 * np.pi * 1200 * t) * np.exp(-t * 9)
        sounds["radar"] = (self._to_sound(ping), 0.3, Sfx("", 0, 1, 200))

        # Nhiễu sóng: tiếng ồn trắng ngắn
        noise_rng = np.random.default_rng(7)
        t = t_axis(0.12)
        glitch = noise_rng.uniform(-1, 1, len(t)) * self._envelope(len(t), rate, 0.002, 0.05) * 0.5
        sounds["glitch"] = (self._to_sound(glitch), 0.25, Sfx("", 0, 1, 80))
        return sounds

    # --- Âm lượng ---------------------------------------------------------------------------
    def set_volumes(self, music: float, sfx: float) -> None:
        self.music_volume = max(0.0, min(1.0, music))
        self.sfx_volume = max(0.0, min(1.0, sfx))
        self._apply_sfx_volume()
        self._apply_music_volume()

    def _apply_sfx_volume(self) -> None:
        for name, variants in self._variants.items():
            for sound in variants:
                sound.set_volume(self._base[name] * self.sfx_volume)

    # --- Hiệu ứng ---------------------------------------------------------------------------
    def has(self, name: str) -> bool:
        return ALIASES.get(name, name) in self._variants

    def play(self, name: str, volume: float = 1.0) -> bool:
        """Phát một tiếng. Trả về True nếu thật sự phát (dùng cho test)."""
        name = ALIASES.get(name, name)
        if not self.enabled or self.sfx_volume <= 0 or name not in self._variants:
            return False
        rule, variants = self._rules[name], self._variants[name]
        now = pygame.time.get_ticks()
        if now - self._last_played.get(name, -10_000) < rule.min_gap_ms:
            return False
        if sum(v.get_num_channels() for v in variants) >= rule.max_voices:
            return False
        self._last_played[name] = now
        sound = variants[self._rng.randrange(len(variants))] if len(variants) > 1 else variants[0]
        channel = sound.play()
        if channel is not None and volume != 1.0:
            channel.set_volume(max(0.0, min(1.0, volume)))
        return channel is not None

    def voice(self, speaker: str, kind: str = "blip") -> bool:
        """Tiếng của nhân vật: ``blip`` (gõ chữ) hoặc ``radio`` (mở bộ đàm)."""
        return self.play(f"{kind}_{SPEAKER_VOICES.get(speaker, 'kx')}")

    # --- Nhạc ------------------------------------------------------------------------------
    @property
    def music_track(self) -> Optional[str]:
        """Bài đang được yêu cầu (có thể vẫn đang chuyển)."""
        return self._target

    def play_music(self, track: Optional[str]) -> None:
        """Yêu cầu đổi bài; việc nhỏ dần/to dần diễn ra trong ``update``."""
        self._target = track if track in MUSIC else None
        if track is not None and track not in MUSIC:
            log.warning("Không có bài nhạc %s", track)

    def duck(self) -> None:
        """Gọi mỗi tick khi đang có hội thoại: nhạc nhỏ lại."""
        self._duck_wanted = True

    def update(self) -> None:
        """Mỗi tick logic: chuyển bài mượt, hạ nhạc khi có thoại."""
        if not self.enabled:
            return
        if self._playing != self._target:
            if self._playing is None or self._fade <= 0:
                self._start(self._target)
            else:
                self._fade = max(0.0, self._fade - 1 / FADE_OUT_TICKS)
        elif self._playing is not None:
            self._fade = min(1.0, self._fade + 1 / FADE_IN_TICKS)
        target = DUCK_LEVEL if self._duck_wanted else 1.0
        self._duck += (target - self._duck) * DUCK_SPEED
        self._duck_wanted = False
        self._apply_music_volume()

    def _start(self, track: Optional[str]) -> None:
        pygame.mixer.music.stop()
        self._playing, self._fade = track, 0.0
        if track is None:
            return
        try:
            pygame.mixer.music.load(str(self.audio_dir / MUSIC[track][0]))
            pygame.mixer.music.set_volume(0.0)
            pygame.mixer.music.play(-1)
        except (pygame.error, FileNotFoundError) as exc:
            log.warning("Không phát được nhạc %s (%s)", track, exc)

    def _apply_music_volume(self) -> None:
        if not self.enabled or self._playing is None:
            return
        gain = MUSIC[self._playing][1]
        pygame.mixer.music.set_volume(gain * MUSIC_LEVEL * self.music_volume * self._fade * self._duck)
