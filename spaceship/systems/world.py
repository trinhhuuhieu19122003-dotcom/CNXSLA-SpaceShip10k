"""Trạng thái của một ván chơi, gom về một chỗ thay cho ~20 biến cục bộ trong ``main()`` bản cũ."""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, List, Optional

from spaceship import config
from spaceship.config import GameMode
from spaceship.entities.effects import DamageNumber, Flash, Particle, Shockwave, Spark
from spaceship.entities.enemies import Boss, EnemyBase
from spaceship.entities.items import Item
from spaceship.entities.player import Player
from spaceship.entities.projectiles import Bullet, EnemyBullet


@dataclass
class RadioLine:
    """Câu thoại hiện ở góc dưới màn hình ngay trong trận (không dừng game)."""
    speaker: str
    text: str
    ticks: int


@dataclass
class World:
    mode: GameMode
    rng: random.Random = field(default_factory=random.Random)
    player: Player = field(default_factory=Player)
    enemies: List[EnemyBase] = field(default_factory=list)
    bullets: List[Bullet] = field(default_factory=list)
    enemy_bullets: List[EnemyBullet] = field(default_factory=list)
    items: List[Item] = field(default_factory=list)
    particles: List[Any] = field(default_factory=list)
    damage_numbers: List[DamageNumber] = field(default_factory=list)
    skills: List[Any] = field(default_factory=list)       # kỹ năng Nộ đang diễn ra

    stage: int = 1
    wave: int = 0
    difficulty: float = 1.0
    survival_time: float = 0.0
    score: int = 0
    kills: int = 0
    boss_kills: int = 0
    lives_lost: int = 0

    #: độ khó người chơi chọn: "easy" | "normal" | "hard"
    preset: str = "normal"
    #: ải đang chơi (chế độ Vượt ải), xem campaign/levels.py
    level: Any = None

    screen_shake: int = 0
    flash: int = 0
    banner: str = ""
    banner_ticks: int = 0
    #: chu kỳ Vượt ải (Vòng lặp tín hiệu); chế độ khác luôn 1
    cycle: int = 1
    radio: List[RadioLine] = field(default_factory=list)
    #: âm thanh cần phát trong tick này (scene sẽ phát rồi xóa)
    sounds: List[str] = field(default_factory=list)
    #: boss vừa bị hạ, chờ kịch bản chế độ chơi xử lý (qua màn, thắng...)
    defeated_bosses: List[Boss] = field(default_factory=list)
    #: "victory" | "defeat" khi ván kết thúc
    outcome: Optional[str] = None

    # --- Độ khó ----------------------------------------------------------------------------
    @property
    def hp_mult(self) -> float:
        return self.difficulty * config.DIFFICULTY_HP[self.preset] * (1 + config.CYCLE_HP_STEP * (self.cycle - 1))

    @property
    def fire_mult(self) -> float:
        return config.DIFFICULTY_FIRE[self.preset] * (1 + config.CYCLE_FIRE_STEP * (self.cycle - 1))

    @property
    def drop_mult(self) -> float:
        return config.DIFFICULTY_DROPS[self.preset]

    # --- Tiện ích dùng chung ----------------------------------------------------------
    def play(self, sound: str) -> None:
        self.sounds.append(sound)

    def burst(self, x: float, y: float, color, count: int, speed_scale: float = 1.0) -> None:
        self.particles.extend(Particle(x, y, color, speed_scale, rng=self.rng) for _ in range(count))

    def sparks(self, x: float, y: float, color, count: int) -> None:
        self.particles.extend(Spark(x, y, color, rng=self.rng) for _ in range(count))

    def explode(self, x: float, y: float, size: float = 1.0) -> None:
        """Vụ nổ: chớp sáng + sóng xung kích + mảnh vỡ cháy + tia lửa."""
        self.particles.append(Flash(x, y, (255, 160, 60), radius=int(18 * size), life=8))
        self.particles.append(Shockwave(x, y, (255, 140, 60), max_radius=50 * size, life=int(14 + 6 * size)))
        for color in ((255, 200, 80), (255, 110, 30), (220, 40, 20)):
            self.burst(x, y, color, int(5 * size), speed_scale=0.6 + 0.3 * size)
        self.sparks(x, y, (255, 230, 150), int(6 * size))

    def spawn_particle(self, x: float, y: float, color) -> None:
        self.particles.append(Particle(x, y, color, rng=self.rng))

    def shake(self, amount: int) -> None:
        self.screen_shake = max(self.screen_shake, amount)

    def drop(self, x: float, y: float, kind: Optional[str], magnet: bool = False) -> None:
        if kind:
            self.items.append(Item(x, y, kind, magnet=magnet))

    def announce(self, text: str, seconds: float = 2.0) -> None:
        """Chữ lớn giữa màn hình (vd. "NHẬN ĐƯỢC DRONE")."""
        self.banner, self.banner_ticks = text, int(seconds * config.TICK_RATE)

    def say(self, speaker: str, text: str, seconds: float = 4.0) -> None:
        self.radio.append(RadioLine(speaker, text, int(seconds * config.TICK_RATE)))

    def tick_messages(self) -> None:
        if self.banner_ticks > 0:
            self.banner_ticks -= 1
        if self.radio:
            self.radio[0].ticks -= 1
            if self.radio[0].ticks <= 0:
                self.radio.pop(0)

    @property
    def bosses(self) -> List[EnemyBase]:
        return [e for e in self.enemies if e.is_boss]

    def clear_projectiles(self) -> None:
        self.bullets.clear()
        self.enemy_bullets.clear()
