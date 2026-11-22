"""Kịch bản cho từng chế độ chơi ("director"): khi nào ra quân, khi nào gọi boss,
khi nào qua màn/chiến thắng.

Mỗi chế độ là một lớp riêng cùng giao diện ``update(world)``; GameplayScene
không còn phải ``if game_mode == ...`` ở khắp nơi.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from spaceship import config
from spaceship.config import WIDTH, GameMode
from spaceship.entities.enemies import BOSS_SPECS, Boss, Enemy, InfectedAlly, Meteor, Parasite, ShieldBug, Wreck
from spaceship.systems import loot
from spaceship.systems.mechanics import create_mechanic
from spaceship.systems.world import World

Formation = List[Tuple[int, int]]

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


def threat(world: World) -> float:
    """Tổng "mức đe dọa" của địch đang có (boss, thiên thạch, xác tàu không tính)."""
    return sum(e.threat for e in world.enemies if _counting(e))


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
        self.gap = config.WAVE_BREATH_TICKS - 40       # wave đầu ra nhanh sau phần giới thiệu
        self.boss: Optional[Boss] = None
        self.boss_phase = 1
        self.clear_timer = 0
        self.wreck_timer = 0
        self.mechanic = create_mechanic(level)     # cơ chế riêng Hồi IV (None ở ải thường)

    @property
    def total_waves(self) -> int:
        return len(self.level.waves)

    @property
    def progress_text(self) -> str:
        extra = f" · {self.mechanic.hud_text}" if self.mechanic is not None and self.mechanic.hud_text else ""
        if self.boss is not None:
            return "BOSS" + extra
        return f"WAVE {max(1, self.wave_index + 1)}/{self.total_waves}{extra}"

    def threat_cap(self, world: World) -> float:
        return config.THREAT_CAP[self.level.act] + config.THREAT_CAP_PER_CYCLE * (world.cycle - 1)

    def _say(self, world: World, key) -> None:
        lines = self.mechanic.radio(world, key) if self.mechanic is not None else None
        for line in (lines if lines is not None else self.radio.get(key, [])):
            world.say(line[0], line[1], effect=line[2] if len(line) > 2 else None)

    def update(self, world: World) -> None:
        if self.mechanic is not None:
            world.mechanic = self.mechanic
        if self.intro_timer > 0:
            self.intro_timer -= 1
            return
        self._handle_defeated_bosses(world)
        if world.outcome:
            return
        if self.mechanic is not None:
            self.mechanic.update(world)
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
            # Trần mật độ: màn hình đã đủ "ngân sách đe dọa" thì dừng đồng hồ wave, địch tiếp theo xếp hàng chờ
            if self.events[0][0] <= self.wave_tick + 1 and threat(world) >= self.threat_cap(world):
                return
            self.wave_tick += 1
            while self.events and self.events[0][0] <= self.wave_tick:
                self.events.pop(0)[1](world)
            return
        if any(_counting(e) for e in world.enemies):
            return
        if self.mechanic is not None and self.mechanic.holds(world):   # vd. tàu cứu sinh còn đang bay qua
            return
        self.gap += 1
        breath = config.WAVE_LONG_BREATH_TICKS if self.wave_index % 2 == 1 else config.WAVE_BREATH_TICKS
        if self.gap < breath:
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
        if self.mechanic is not None:
            self.mechanic.on_boss_defeated(world, boss)
        if self.level.reward:
            world.drop(boss.x, boss.y, self.level.reward, magnet=True)
        world.enemy_bullets.clear()
        world.announce("ĐÃ HẠ " + boss.title, 2.0)
        self._say(world, ("clear", 0))
        self.clear_timer = CLEAR_AFTER_BOSS_TICKS


@dataclass(frozen=True)
class Pacing:
    """Thông số nhịp của chế độ sống sót (đơn vị giây trừ khi ghi khác)."""
    build: float              # dồn lên: thả từng tốp địch
    peak: float               # cao trào: giữ nguyên, không thả thêm
    relax: float              # thả lỏng: không thả tốp mới (tối thiểu)
    squad_every: float        # khoảng cách giữa các tốp lúc đầu ...
    squad_every_min: float    # ... rút ngắn dần tới mức này
    cap: float                # ngân sách đe dọa lúc đầu ...
    cap_per_minute: float     # ... tăng mỗi phút ...
    cap_max: float            # ... tối đa
    hurt_ratio: float         # mất chừng này phần máu trong lúc dồn lên -> chuyển sớm sang thả lỏng


PACING = {
    GameMode.ENDLESS: Pacing(build=18, peak=4, relax=6, squad_every=2.6, squad_every_min=1.4,
                             cap=7, cap_per_minute=2.0, cap_max=18, hurt_ratio=0.35),
    GameMode.INFERNO: Pacing(build=15, peak=4, relax=4, squad_every=1.8, squad_every_min=1.0,
                             cap=12, cap_per_minute=3.0, cap_max=26, hurt_ratio=0.45),
}
BOSS_THREAT_CAP = 4                   # đang đánh boss: chỉ thêm lác đác vài lính


class SurvivalDirector(Director):
    """Vô tận & Hỏa ngục theo nhịp **dồn lên -> cao trào -> thả lỏng** (kiểu AI Director của Left 4 Dead).

    * Dồn lên: cứ vài giây thả một *tốp* nhỏ (lính bay vào lần lượt, bầy Ký Sinh, Lính Khiên...), miễn chưa vượt
      "ngân sách đe dọa" - ngân sách tăng dần theo thời gian nhưng có trần.
    * Cao trào: giữ vài giây, không thả thêm.
    * Thả lỏng: không thả tốp mới cho tới khi người chơi dọn gần sạch và đủ thời gian nghỉ.
    * Bị mất nhiều máu lúc đang dồn lên -> chuyển sớm sang thả lỏng (game tự "nương tay").
    Boss vẫn đến theo chu kỳ; lúc có boss chỉ thêm lác đác vài lính.
    Hạ boss lần 1/2/3 được Drone / Thiêu đốt / Drone thứ hai (tự bay vào tàu)."""

    ENDLESS_BOSSES = ("crab", "octopus", "nest", "spider", "cruiser", "mothership")
    INFERNO_BOSSES = ("spider", "cruiser", "nest", "mothership")
    BUILD, PEAK, RELAX = "build", "peak", "relax"

    def __init__(self, mode: GameMode) -> None:
        super().__init__()
        self.mode = mode
        self.pacing = PACING[mode]
        self.state = self.BUILD
        self.state_ticks = 0
        self.squad_timer = config.TICK_RATE * 1.5
        self.squads_spawned = 0
        self.pending: List[Tuple[int, object]] = []      # (tick hẹn, hàm sinh) - để lính bay vào lần lượt
        self.ticks = 0
        self.build_hp: Optional[float] = None
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

    # --- Nhịp ----------------------------------------------------------------------------
    def threat_cap(self, world: World) -> float:
        if world.bosses:
            return BOSS_THREAT_CAP
        p = self.pacing
        return min(p.cap_max, p.cap + p.cap_per_minute * world.survival_time / 60)

    def squad_interval(self, world: World) -> float:
        p = self.pacing
        seconds = max(p.squad_every_min, p.squad_every - world.survival_time / 120)
        return seconds * config.TICK_RATE

    def _enter(self, state: str) -> None:
        self.state, self.state_ticks = state, 0

    def _update_state(self, world: World) -> None:
        p, rate = self.pacing, config.TICK_RATE
        self.state_ticks += 1
        player = world.player
        if self.state == self.BUILD:
            if self.build_hp is None:
                self.build_hp = player.hp + player.lives * player.max_hp
            lost = self.build_hp - (player.hp + player.lives * player.max_hp)
            if self.state_ticks >= p.build * rate or lost >= p.hurt_ratio * player.max_hp:
                self._enter(self.PEAK)
        elif self.state == self.PEAK:
            if self.state_ticks >= p.peak * rate:
                self._enter(self.RELAX)
        elif self.state_ticks >= p.relax * rate and threat(world) <= 3:
            self.build_hp = None
            self._enter(self.BUILD)

    def update(self, world: World) -> None:
        self._handle_defeated_bosses(world)
        world.difficulty = self.base_difficulty + world.survival_time / self.ramp_seconds
        self.ticks += 1
        while self.pending and self.pending[0][0] <= self.ticks:
            self.pending.pop(0)[1](world)
        self._update_state(world)
        self.squad_timer -= 1
        if (self.state == self.BUILD and self.squad_timer <= 0 and not self.pending
                and threat(world) < self.threat_cap(world)):
            self._spawn_squad(world)
            self.squad_timer = self.squad_interval(world)
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

    # --- Các tốp địch ----------------------------------------------------------------------
    def _later(self, delay: int, fn) -> None:
        self.pending.append((self.ticks + delay, fn))
        self.pending.sort(key=lambda e: e[0])

    def _spawn_squad(self, world: World) -> None:
        t, rng = world.survival_time, world.rng
        self.squads_spawned += 1
        options = ["line", "vee"]
        if t > 50:
            options += ["swarm"]
        if t > 110:
            options += ["shield", "ally"]
        kind = rng.choice(options)
        if kind == "swarm":
            side = rng.choice((80, WIDTH // 2, WIDTH - 300))
            for i in range(6):
                self._later(i * 10, lambda w, i=i: w.enemies.append(
                    Parasite(w.difficulty, rng.randint(side, side + 220), rng=w.rng)))
        elif kind in ("shield", "ally"):
            cls = ShieldBug if kind == "shield" else InfectedAlly
            x = rng.randint(140, WIDTH - 140)
            world.enemies.append(cls(world.difficulty, x, 170, rng=world.rng))
            self._grunt_squad(world, 2, "line", delay=30)
        else:
            self._grunt_squad(world, rng.randint(3, 5), kind)

    def _grunt_squad(self, world: World, count: int, shape: str, delay: int = 0) -> None:
        rng = world.rng
        stage = min(world.stage, ENDLESS_MAX_ENEMY_STAGE)
        center = rng.randint(200, WIDTH - 200)
        base_y = rng.randint(110, 230)
        for i in range(count):
            offset = (i - (count - 1) / 2) * 70
            y = base_y - abs(offset) * 0.6 if shape == "vee" else base_y

            def spawn(w, x=center + offset, y=y):
                e = Enemy(w.difficulty, stage=stage, rng=w.rng)
                e.x = max(30, min(WIDTH - 30, x))
                e.y, e.target_y = -40, max(60, y)
                w.enemies.append(e)
            self._later(delay + i * config.ENTRY_STAGGER_TICKS, spawn)

    def on_boss_defeated(self, world: World, boss: Boss) -> None:
        if self.rewards_given < len(loot.SURVIVAL_REWARDS):
            world.drop(boss.x, boss.y, loot.SURVIVAL_REWARDS[self.rewards_given], magnet=True)
        self.rewards_given += 1
        for _ in range(2):
            world.drop(boss.x + world.rng.randint(-40, 40), boss.y, loot.random_drop(world.mode, world.rng))
        world.announce("ĐÃ HẠ " + boss.title, 1.8)
        self._enter(self.RELAX)                          # hạ boss xong được nghỉ một nhịp


def create_director(mode: GameMode, level=None, radio=None) -> Director:
    if mode is GameMode.CAMPAIGN:
        return LevelDirector(level, radio)
    return SurvivalDirector(mode)
