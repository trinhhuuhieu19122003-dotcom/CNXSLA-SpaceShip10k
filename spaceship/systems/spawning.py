"""Kịch bản cho từng chế độ chơi ("director"): khi nào ra quân, khi nào gọi boss,
khi nào qua màn/chiến thắng.

Mỗi chế độ là một lớp riêng cùng giao diện ``update(world)``; GameplayScene
không còn phải ``if game_mode == ...`` ở khắp nơi.
"""
from __future__ import annotations

from typing import List, Tuple

from spaceship import config
from spaceship.config import WIDTH, GameMode
from spaceship.entities.enemies import Boss, Enemy, Meteor
from spaceship.systems import loot
from spaceship.systems.world import World

Formation = List[Tuple[int, int]]

WAVE_DELAY_TICKS = 60
FORMATION_Y = 150
METEOR_CHANCE_STAGE3 = 0.015
ENDLESS_MAX_ENEMY_STAGE = 3


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


def spawn_wave(world: World, stage: int, wave: int) -> None:
    positions, dx = formation(stage, wave)
    for px, py in positions:
        enemy = Enemy(world.difficulty, stage=stage, rng=world.rng)
        enemy.x = max(30, min(WIDTH - 30, WIDTH // 2 + px))
        enemy.y = -150 + py * 1.5 - abs(px)
        enemy.target_y = FORMATION_Y + py
        if dx:
            enemy.dx = dx * world.rng.choice([-1, 1])
        world.enemies.append(enemy)


class Director:
    """Lớp cơ sở. ``banner`` là chữ lớn giữa màn hình (vd "STAGE 2"), ``paused`` = đang chờ giới thiệu."""

    def __init__(self) -> None:
        self.intro_timer = 0
        self.banner = ""

    @property
    def paused(self) -> bool:
        return self.intro_timer > 0

    @property
    def banner_text(self) -> str:
        return self.banner if self.intro_timer > 0 else ""

    def update(self, world: World) -> None:
        raise NotImplementedError

    def _handle_defeated_bosses(self, world: World) -> None:
        for boss in world.defeated_bosses:
            self.on_boss_defeated(world, boss)
        world.defeated_bosses.clear()

    def on_boss_defeated(self, world: World, boss: Boss) -> None:
        for _ in range(3):
            world.drop(boss.x + world.rng.randint(-30, 30), boss.y, loot.random_drop(world.mode, world.rng))


class CampaignDirector(Director):
    def __init__(self) -> None:
        super().__init__()
        self.boss_spawned = False
        self.spawn_timer = 0
        self.clear_timer = 0
        self._start_stage_intro(1)

    def _start_stage_intro(self, stage: int) -> None:
        self.intro_timer = config.STAGE_INTRO_TICKS
        self.banner = f"STAGE {stage}"

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
                world.stage += 1
                world.wave = 0
                self.boss_spawned = False
                world.clear_projectiles()
                self._start_stage_intro(world.stage)
            return

        if not self.boss_spawned:
            grunts = [e for e in world.enemies if not e.is_meteor and not e.is_boss]
            if not grunts:
                self.spawn_timer += 1
                if self.spawn_timer > WAVE_DELAY_TICKS:
                    self.spawn_timer = 0
                    world.wave += 1
                    if world.wave > config.CAMPAIGN_WAVES[world.stage]:
                        world.enemies.append(Boss(world.difficulty, stage=world.stage))
                        self.boss_spawned = True
                        if world.stage == 3:
                            spawn_wave(world, 3, 10)        # boss cuối kèm hộ vệ
                    else:
                        spawn_wave(world, world.stage, world.wave)
        if world.stage == 3 and world.rng.random() < METEOR_CHANCE_STAGE3:
            world.enemies.append(Meteor(world.difficulty, rng=world.rng))

    @property
    def banner_text(self) -> str:
        if self.clear_timer > 0:
            return "STAGE CLEAR"
        return super().banner_text

    def on_boss_defeated(self, world: World, boss: Boss) -> None:
        reward = loot.BOSS_REWARDS.get(boss.stage)
        if reward:
            world.drop(boss.x, boss.y, reward)
        if world.stage >= config.CAMPAIGN_STAGES:
            world.outcome = "victory"
        else:
            self.clear_timer = config.STAGE_CLEAR_TICKS


class SurvivalDirector(Director):
    """Vô tận & Hỏa ngục: quân ra liên tục, độ khó tăng theo thời gian, boss theo chu kỳ."""

    def __init__(self, mode: GameMode) -> None:
        super().__init__()
        self.mode = mode
        self.spawn_timer = 0
        self.last_boss_time = 0.0
        inferno = mode is GameMode.INFERNO
        self.base_difficulty = 2.0 if inferno else 1.0
        self.ramp_seconds = 30.0 if inferno else 60.0
        self.boss_interval = config.INFERNO_BOSS_INTERVAL if inferno else config.ENDLESS_BOSS_INTERVAL

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
        if world.survival_time - self.last_boss_time >= self.boss_interval:
            self.last_boss_time = world.survival_time
            if self.mode is GameMode.INFERNO:
                world.stage = 3
                world.enemies.append(Boss(world.difficulty * 1.5, stage=3))
            else:
                world.stage += 1
                world.enemies.append(Boss(world.difficulty, stage=min(3, world.stage)))


def create_director(mode: GameMode) -> Director:
    return CampaignDirector() if mode is GameMode.CAMPAIGN else SurvivalDirector(mode)
