"""Huy hiệu thành tựu: dữ liệu + cách kiểm tra.

Mỗi huy hiệu kiểm tra từ dữ liệu đã lưu (``SaveData``) và/hoặc ván đang chơi (``RunStats``).
``evaluate`` được gọi định kỳ trong trận (để hiện thẻ "THÀNH TỰU MỚI" ngay lúc đạt) và khi ván kết thúc.
Muốn thêm huy hiệu: thêm một dòng vào ``ACHIEVEMENTS``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional

from spaceship.campaign.bestiary import BESTIARY
from spaceship.campaign.levels import LEVEL_COUNT, get_level
from spaceship.config import GameMode


@dataclass
class RunStats:
    """Số liệu của ván đang chơi (chưa cộng vào file lưu cho tới khi ``recorded``)."""
    mode: GameMode
    level: Optional[int] = None
    preset: str = "normal"
    time: float = 0.0
    kills: int = 0
    boss_kills: int = 0
    skills: int = 0
    guard_blocks: int = 0
    cleared: bool = False
    stars: int = 0
    hand_ticks: int = 0
    keyboard_used: bool = False
    mother_by_lightning: bool = False
    recorded: bool = False          # True: kills/skills... đã cộng vào file lưu, không cộng lần nữa


@dataclass(frozen=True)
class Achievement:
    key: str
    name: str
    how: str                        # cách đạt (hiện cả khi chưa đạt)
    icon: str                       # star | skull | bolt | shield | clock | book | hand | loop | flag | fist
    check: Callable


def _extra(run: Optional[RunStats], field: str) -> int:
    return 0 if run is None or run.recorded else getattr(run, field)


def _total(save, attr: str) -> int:
    return sum(getattr(rec, attr) for rec in save.modes.values())


def _counter(save, run, key: str, field: str) -> int:
    return save.counters.get(key, 0) + _extra(run, field)


def _cleared(save, run, number: int) -> bool:
    return (run is not None and run.cleared and run.level == number) or number in save.level_stars \
        or (save.campaign_cleared and number <= LEVEL_COUNT)


def _survived(save, run, mode: GameMode, seconds: float) -> bool:
    live = run is not None and run.mode is mode and run.time >= seconds
    return live or save.modes[mode].best_time >= seconds


def _boss_level_on_hard(save, run) -> bool:
    return (run is not None and run.cleared and run.preset == "hard" and run.level is not None
            and get_level(run.level).boss is not None)


ACHIEVEMENTS: tuple[Achievement, ...] = (
    Achievement("first_steps", "KHỞI HÀNH", "Qua ải 1", "flag",
                lambda s, r: _cleared(s, r, 1)),
    Achievement("drone_back", "GIÀNH LẠI DRONE", "Hạ Kẻ Nuốt Drone ở ải 3", "skull",
                lambda s, r: _cleared(s, r, 3)),
    Achievement("flawless", "KHÔNG TRẦY XƯỚC", "Qua 1 ải không mất mạng nào", "star",
                lambda s, r: (r is not None and r.stars == 3) or 3 in s.level_stars.values()),
    Achievement("nebula", "XUYÊN TINH VÂN", "Qua ải 7, hạ Lõi Tinh Vân", "skull",
                lambda s, r: _cleared(s, r, 7)),
    Achievement("last_signal", "TÍN HIỆU CUỐI CÙNG", "Phá đảo chế độ Vượt ải", "flag",
                lambda s, r: s.campaign_cleared),
    Achievement("all_stars", "TOÀN SAO", f"Đủ {LEVEL_COUNT * 3}/{LEVEL_COUNT * 3} sao trong một chu kỳ", "star",
                lambda s, r: s.total_stars >= LEVEL_COUNT * 3 or any(v >= LEVEL_COUNT * 3 for v in s.cycle_history.values())),
    Achievement("loop", "VÒNG LẶP", "Phá đảo chu kỳ 2", "loop",
                lambda s, r: 2 in s.cycle_history),
    Achievement("bestiary", "NHÀ NGHIÊN CỨU", f"Mở đủ {len(BESTIARY)} mục Sổ tay chiến đấu", "book",
                lambda s, r: len(s.seen_enemies & set(BESTIARY)) >= len(BESTIARY)),
    Achievement("hardcore", "CỨNG ĐẦU", "Qua ải có boss ở độ khó Khó", "fist",
                _boss_level_on_hard),
    Achievement("endless5", "BỀN BỈ", "Trụ 5 phút ở chế độ Vô tận", "clock",
                lambda s, r: _survived(s, r, GameMode.ENDLESS, 300)),
    Achievement("endless10", "KHÔNG THỂ HẠ GỤC", "Trụ 10 phút ở chế độ Vô tận", "clock",
                lambda s, r: _survived(s, r, GameMode.ENDLESS, 600)),
    Achievement("inferno3", "THỬ LỬA", "Trụ 3 phút ở chế độ Hỏa ngục", "clock",
                lambda s, r: _survived(s, r, GameMode.INFERNO, 180)),
    Achievement("boss_hunter", "THỢ SĂN BOSS", "Hạ tổng cộng 20 boss", "skull",
                lambda s, r: _total(s, "total_boss_kills") + _extra(r, "boss_kills") >= 20),
    Achievement("thousand", "NGÀN QUÂN", "Diệt tổng cộng 1 000 địch", "fist",
                lambda s, r: _total(s, "total_kills") + _extra(r, "kills") >= 1000),
    Achievement("rage", "BÙNG NỘ", "Dùng kỹ năng Nộ 25 lần", "bolt",
                lambda s, r: _counter(s, r, "skills", "skills") >= 25),
    Achievement("guardian", "LÁ CHẮN SỐNG", "Drone hộ vệ chặn 100 viên đạn", "shield",
                lambda s, r: _counter(s, r, "guard_blocks", "guard_blocks") >= 100),
    Achievement("hand_pilot", "PHI CÔNG BẰNG TAY", "Qua 1 ải chỉ lái bằng tay", "hand",
                lambda s, r: r is not None and r.cleared and r.hand_ticks > 600 and not r.keyboard_used),
    Achievement("thunder", "SẤM SÉT CUỐI CÙNG", "Hạ Tàu Mẹ khi cầm Tia Sét", "bolt",
                lambda s, r: r is not None and r.mother_by_lightning),
)
BY_KEY = {a.key: a for a in ACHIEVEMENTS}


def evaluate(save, run: Optional[RunStats] = None) -> List[Achievement]:
    """Kiểm tra mọi huy hiệu chưa đạt; huy hiệu nào vừa đạt thì lưu (kèm ngày) và trả về."""
    new = []
    for achievement in ACHIEVEMENTS:
        if achievement.key not in save.achievements and achievement.check(save, run):
            save.unlock(achievement.key)
            new.append(achievement)
    return new
