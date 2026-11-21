"""Kịch bản cho từng chế độ chơi ("director"): khi nào ra quân, khi nào gọi boss,
khi nào qua màn/chiến thắng.

Mỗi chế độ là một lớp riêng cùng giao diện ``update(world)``; GameplayScene
không còn phải ``if game_mode == ...`` ở khắp nơi.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from spaceship import config
from spaceship.config import WIDTH, GameMode
from spaceship.entities.enemies import BOSS_SPECS, Boss, Enemy, InfectedAlly, Meteor, Parasite, ShieldBug, Wreck
from spaceship.systems import loot
from spaceship.systems.world import World

Formation = List[Tuple[int, int]]

WAVE_DELAY_TICKS = 60
FORMATION_Y = 150
ENDLESS_MAX_ENEMY_STAGE = 3
LEVEL_INTRO_TICKS = 100
CLEAR_AFTER_BOSS_TICKS = 170          # đủ lâu để phần thưởng boss bay vào tàu
CLEAR_NO_BOSS_TICKS = 90


def _grid(xs, ys) -> Formation:
    return [(x, y) for x in xs for y in ys]


def formation(stage: int, wave: int) -> Tuple[Formation, float]:
    """Trả về (vị trí tương đối so với giữa màn hình, tốc độ ngang). Port nguyên từ bản gốc."""
    if stage == 1:
        if wave == 1:
            return [(0, 0), (-100, -80), (100, -80), (-200, -160), (200, -160)], 0
        if wave == 2:
            return [(x, 0) for x in range(-200, 201, 80)], 0
        if wave == 3:
            return [(0, 0), (-80, -80), (80, -80), (0, -160), (-160, -160), (160, -160), (0, -240)], 0
        if wave == 4:
            return _grid([-120, -40, 40, 120], [0, -80]), 2
        return _grid(range(-200, 201, 80), [0, -80, -160]), 0
    if stage == 2:
        if wave in (1, 2):
            return _grid(range(-160, 161, 80), [0, -80]), 0
        if wave == 3:
            return [(0, 0), (100, -100), (0, -200), (-100, -100), (160, -160), (-160, -160), (0, -260)], 0
        if wave in (4, 5):
            return _grid([-160, -80, 0, 80, 160], [0, -80, -160]), 3.5
        if wave == 6:
            return _grid([-80, 80], [0, -80, -160, -240]), 0
        return _grid(range(-200, 201, 80), [0, -80, -160, -240]), 0
    if wave in (1, 2, 3):
        return _grid(range(-160, 161, 80), [0, -100, -200]), 2
    if wave in (4, 5, 6):
        return _grid(range(-200, 201, 80), [0, -80]), 0
    if wave in (7, 8):
        return [(0, 0), (120, -120), (0, -240), (-120, -120), (200, -200), (-200, -200), (0, -120)], 0
    if wave == 9:
        return _grid(range(-240, 241, 80), [0, -80, -160, -240, -320]), 0
    return _grid([-160, -80, 80, 160], [0, -80]), 0


class Director:
    """Lớp cơ sở. ``banner`` là chữ lớn giữa màn hình lúc mở màn, ``paused`` = đang chờ giới thiệu."""

    def __init__(self) -> None:
        self.intro_timer = 0
        self.banner = ""

    @property
    def paused(self) -> bool:
        return self.intro_timer > 0

    @property
    def banner_text(self) -> str:
        return self.banner if self.intro_timer > 0 else ""

    @property
    def progress_text(self) -> str:
        return ""

    def update(self, world: World) -> None:
        raise NotImplementedError

    def _handle_defeated_bosses(self, world: World) -> None:
        for boss in world.defeated_bosses:
            self.on_boss_defeated(world, boss)
        world.defeated_bosses.clear()

    def on_boss_defeated(self, world: World, boss: Boss) -> None:
        pass


def _counting(enemy) -> bool:
    """Địch phải diệt hết mới sang wave mới (thiên thạch, xác tàu không tính)."""
    return not (enemy.is_boss or enemy.is_meteor or enemy.is_obstacle)


class LevelDirector(Director):
    """Chạy một ải của chế độ Vượt ải theo dữ liệu trong campaign/levels.py."""

    def __init__(self, level, radio: Optional[dict] = None) -> None:
        super().__init__()
        self.level = level
        self.radio = radio or {}
        self.intro_timer = LEVEL_INTRO_TICKS
        self.banner = level.title
        self.wave_index = -1
        self.events: list = []
        self.wave_tick = 0
        self.gap = WAVE_DELAY_TICKS // 2
        self.boss: Optional[Boss] = None
        self.boss_phase = 1
        self.clear_timer = 0
        self.wreck_timer = 0

    @property
    def total_waves(self) -> int:
        return len(self.level.waves)

    @property
    def progress_text(self) -> str:
        if self.boss is not None:
            return "BOSS"
        return f"WAVE {max(1, self.wave_index + 1)}/{self.total_waves}"

    def _say(self, world: World, key) -> None:
        for line in self.radio.get(key, []):
            world.say(line[0], line[1])

    def update(self, world: World) -> None:
        if self.intro_timer > 0:
            self.intro_timer -= 1
            return
        self._handle_defeated_bosses(world)
        if world.outcome:
            return
        if self.clear_timer > 0:
            self.clear_timer -= 1
            if self.clear_timer == 0:
                world.outcome = "victory"
            return
        self._hazards(world)
        if self.boss is not None:
            if self.boss.phase != self.boss_phase:
                self.boss_phase = self.boss.phase
                self._say(world, ("phase", self.boss_phase))
            return
        if self.events:
            self.wave_tick += 1
            while self.events and self.events[0][0] <= self.wave_tick:
                self.events.pop(0)[1](world)
            return
        if any(_counting(e) for e in world.enemies):
            return
        self.gap += 1
        if self.gap < WAVE_DELAY_TICKS:
            return
        self.gap = 0
        if self.wave_index + 1 < self.total_waves:
            self.wave_index += 1
            world.wave = self.wave_index + 1
            self.events = list(self.level.waves[self.wave_index])
            self.wave_tick = 0
            self._say(world, ("wave", world.wave))
            while self.events and self.events[0][0] <= 0:
                self.events.pop(0)[1](world)
        elif self.level.boss:
            self.boss = Boss(world.hp_mult, kind=self.level.boss)
            world.enemies.append(self.boss)
            world.announce(f"CẢNH BÁO · {BOSS_SPECS[self.level.boss].title}", 2.5)
            world.play("boss_siren")
            self._say(world, ("boss", 0))
        else:
            self.clear_timer = CLEAR_NO_BOSS_TICKS
            world.announce("QUA ẢI!", 1.5)
            world.play("wave_clear")
            self._say(world, ("clear", 0))

    def _hazards(self, world: World) -> None:
        if self.level.meteor_rate and world.rng.random() < self.level.meteor_rate:
            world.enemies.append(Meteor(world.hp_mult, rng=world.rng))
        if self.level.wreck_every:
            self.wreck_timer += 1
            if self.wreck_timer >= self.level.wreck_every:
                self.wreck_timer = 0
                variant = world.rng.choice((1, 2))
                world.enemies.append(Wreck(world.hp_mult, world.rng.randint(120, WIDTH - 120), rng=world.rng, variant=variant))

    def on_boss_defeated(self, world: World, boss: Boss) -> None:
        if self.level.reward:
            world.drop(boss.x, boss.y, self.level.reward, magnet=True)
        world.enemy_bullets.clear()
        world.announce("ĐÃ HẠ " + boss.title, 2.0)
        self._say(world, ("clear", 0))
        self.clear_timer = CLEAR_AFTER_BOSS_TICKS


class SurvivalDirector(Director):
    """Vô tận & Hỏa ngục: quân ra liên tục, độ khó tăng theo thời gian, boss theo chu kỳ.

    Càng sống lâu càng gặp nhiều loại địch mới; boss lần lượt đổi loại.
    Hạ boss lần 1/2/3 được Drone / Thiêu đốt / Drone thứ hai (tự bay vào tàu)."""

    ENDLESS_BOSSES = ("crab", "octopus", "nest", "spider", "cruiser", "mothership")
    INFERNO_BOSSES = ("spider", "cruiser", "nest", "mothership")

    def __init__(self, mode: GameMode) -> None:
        super().__init__()
        self.mode = mode
        self.spawn_timer = 0
        self.extra_timer = 0
        self.last_boss_time = 0.0
        self.bosses_spawned = 0
        self.rewards_given = 0
        inferno = mode is GameMode.INFERNO
        self.base_difficulty = 2.0 if inferno else 1.0
        self.ramp_seconds = 30.0 if inferno else 60.0
        self.boss_interval = config.INFERNO_BOSS_INTERVAL if inferno else config.ENDLESS_BOSS_INTERVAL

    @property
    def progress_text(self) -> str:
        return f"BOSS ĐÃ HẠ: {self.rewards_given}" if self.rewards_given else ""

    def spawn_interval(self, difficulty: float) -> float:
        if self.mode is GameMode.INFERNO:
            return 45 / difficulty
        return max(20, 60 / difficulty)

    def update(self, world: World) -> None:
        self._handle_defeated_bosses(world)
        world.difficulty = self.base_difficulty + world.survival_time / self.ramp_seconds
        self.spawn_timer += 1
        if self.spawn_timer > self.spawn_interval(world.difficulty):
            self.spawn_timer = 0
            stage = min(world.stage, ENDLESS_MAX_ENEMY_STAGE)
            world.enemies.append(Enemy(world.difficulty, stage=stage, rng=world.rng))
        self._extras(world)
        if world.survival_time - self.last_boss_time >= self.boss_interval:
            self.last_boss_time = world.survival_time
            roster = self.INFERNO_BOSSES if self.mode is GameMode.INFERNO else self.ENDLESS_BOSSES
            kind = roster[self.bosses_spawned % len(roster)]
            self.bosses_spawned += 1
            world.stage = 3 if self.mode is GameMode.INFERNO else world.stage + 1
            mult = 1.5 if self.mode is GameMode.INFERNO else 1.0
            world.enemies.append(Boss(world.difficulty * mult * 0.6, kind=kind))
            world.announce(f"CẢNH BÁO · {BOSS_SPECS[kind].title}", 2.0)
            world.play("boss_siren")

    def _extras(self, world: World) -> None:
        """Từ phút thứ 1 có thêm Ký Sinh, phút thứ 2 có Lính Khiên / tàu nhiễm."""
        t = world.survival_time
        self.extra_timer += 1
        if t > 50 and self.extra_timer % 240 == 0:
            for _ in range(5):
                world.enemies.append(Parasite(world.difficulty, world.rng.randint(80, WIDTH - 80), rng=world.rng))
        if t > 110 and self.extra_timer % 600 == 300:
            cls = world.rng.choice((ShieldBug, InfectedAlly))
            world.enemies.append(cls(world.difficulty, world.rng.randint(120, WIDTH - 120), 180, rng=world.rng))

    def on_boss_defeated(self, world: World, boss: Boss) -> None:
        if self.rewards_given < len(loot.SURVIVAL_REWARDS):
            world.drop(boss.x, boss.y, loot.SURVIVAL_REWARDS[self.rewards_given], magnet=True)
        self.rewards_given += 1
        for _ in range(2):
            world.drop(boss.x + world.rng.randint(-40, 40), boss.y, loot.random_drop(world.mode, world.rng))
        world.announce("ĐÃ HẠ " + boss.title, 1.8)


def create_director(mode: GameMode, level=None, radio=None) -> Director:
    if mode is GameMode.CAMPAIGN:
        return LevelDirector(level, radio)
    return SurvivalDirector(mode)
