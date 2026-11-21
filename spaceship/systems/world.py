"""Trạng thái của một ván chơi, gom về một chỗ thay cho ~20 biến cục bộ trong ``main()`` bản cũ."""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import List, Optional

from spaceship.config import GameMode
from spaceship.entities.effects import DamageNumber, Flash, Particle, Shockwave, Spark
from spaceship.entities.enemies import Boss, EnemyBase
from spaceship.entities.items import Item
from spaceship.entities.player import Player
from spaceship.entities.projectiles import Bullet, EnemyBullet, NukeMissile


@dataclass
class World:
    mode: GameMode
    rng: random.Random = field(default_factory=random.Random)
    player: Player = field(default_factory=Player)
    enemies: List[EnemyBase] = field(default_factory=list)
    bullets: List[Bullet] = field(default_factory=list)
    enemy_bullets: List[EnemyBullet] = field(default_factory=list)
    nukes: List[NukeMissile] = field(default_factory=list)
    items: List[Item] = field(default_factory=list)
    particles: List[Particle] = field(default_factory=list)
    damage_numbers: List[DamageNumber] = field(default_factory=list)

    stage: int = 1
    wave: int = 0
    difficulty: float = 1.0
    survival_time: float = 0.0
    score: int = 0
    kills: int = 0
    boss_kills: int = 0

    screen_shake: int = 0
    flash: int = 0
    #: âm thanh cần phát trong tick này (scene sẽ phát rồi xóa)
    sounds: List[str] = field(default_factory=list)
    #: boss vừa bị hạ, chờ kịch bản chế độ chơi xử lý (qua màn, thắng...)
    defeated_bosses: List[Boss] = field(default_factory=list)
    #: "victory" | "defeat" khi ván kết thúc
    outcome: Optional[str] = None

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

    def drop(self, x: float, y: float, kind: Optional[str]) -> None:
        if kind:
            self.items.append(Item(x, y, kind))

    @property
    def bosses(self) -> List[EnemyBase]:
        return [e for e in self.enemies if e.is_boss]

    def clear_projectiles(self) -> None:
        self.bullets.clear()
        self.enemy_bullets.clear()
