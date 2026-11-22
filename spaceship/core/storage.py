"""Lưu kỷ lục & thống kê.

Khác bản cũ:
- Lưu ở thư mục người dùng (không ghi vào thư mục code, không lỡ commit lên Git).
- Thống kê CỘNG DỒN qua mọi ván (bản cũ chỉ lưu số kill của ván có điểm cao nhất).
- Ghi file an toàn (ghi file tạm rồi thay thế), file hỏng thì sao lưu ra .bak.
- Tự nhập dữ liệu từ ``highscore.txt`` / ``stats.json`` của bản cũ nếu còn.
"""
from __future__ import annotations

import datetime
import json
import logging
import os
import shutil
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, Iterable, Optional

from spaceship.config import PROJECT_DIR, GameMode

TOP_RUNS = 5                             # số ván lưu ở Bảng điểm mỗi chế độ

log = logging.getLogger(__name__)

SAVE_VERSION = 5
APP_DIR_NAME = "SpaceShip10k"


def default_save_path() -> Path:
    override = os.environ.get("SPACESHIP_SAVE_DIR")
    if override:
        base = Path(override)
    elif sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA", Path.home())) / APP_DIR_NAME
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / APP_DIR_NAME
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / APP_DIR_NAME
    return base / "save.json"


@dataclass
class ModeRecord:
    best_score: int = 0
    total_kills: int = 0
    total_boss_kills: int = 0
    games_played: int = 0
    best_time: float = 0.0
    best_combo: int = 0                 # chuỗi hạ liên tiếp dài nhất
    #: 5 ván điểm cao nhất: {"score", "time", "kills", "combo", "level", "victory", "date"}
    top_runs: list = field(default_factory=list)

    def __post_init__(self) -> None:
        runs = self.top_runs if isinstance(self.top_runs, list) else []
        clean = []
        for run in runs:                                    # file lưu sửa tay / hỏng một phần: bỏ dòng lạ
            if isinstance(run, dict) and isinstance(run.get("score"), (int, float)):
                clean.append(run)
        self.top_runs = sorted(clean, key=lambda r: -r["score"])[:TOP_RUNS]


@dataclass
class GameResult:
    mode: GameMode
    score: int
    kills: int
    boss_kills: int
    survival_time: float
    victory: bool = False
    best_combo: int = 0
    level: Optional[int] = None         # Vượt ải: ải vừa chơi


@dataclass
class SaveData:
    path: Path
    highscore: int = 0
    modes: Dict[GameMode, ModeRecord] = field(default_factory=lambda: {m: ModeRecord() for m in GameMode})
    #: Vượt ải: ải cao nhất đã mở, số sao từng ải, đã xem kết thúc chưa (mở khóa Hỏa ngục)
    unlocked_level: int = 1
    level_stars: Dict[int, int] = field(default_factory=dict)
    campaign_cleared: bool = False
    seen_enemies: set[str] = field(default_factory=set)
    #: Vòng lặp tín hiệu: chu kỳ đang chơi (1 = lần đầu), chu kỳ này đã qua ải cuối chưa,
    #: tổng sao từng chu kỳ đã phá đảo. Sổ tay, kỷ lục, thống kê, Hỏa ngục KHÔNG bị đặt lại.
    cycle: int = 1
    cycle_complete: bool = False
    cycle_history: Dict[int, int] = field(default_factory=dict)
    #: Huy hiệu đã đạt: khóa -> ngày đạt (YYYY-MM-DD). Bộ đếm cộng dồn cho huy hiệu (Nộ, chặn đạn...).
    achievements: Dict[str, str] = field(default_factory=dict)
    counters: Dict[str, int] = field(default_factory=dict)
    #: Hồi IV: số người cứu được ở lần qua ải 12 gần nhất (None = chưa qua) - câu cuối của kết thúc thật
    rescued: Optional[int] = None

    def mark_seen(self, key: str) -> bool:
        """Lưu mục Sổ tay mới; các lần gặp tiếp theo không ghi file."""
        if key in self.seen_enemies:
            return False
        self.seen_enemies.add(key)
        self.save()
        return True

    def record_level(self, number: int, stars: int, last_level: int, main_level: Optional[int] = None) -> None:
        """Qua ải: lưu số sao (giữ số cao nhất), mở ải tiếp theo.

        ``main_level`` (ải 10): qua ải này là phá đảo mạch chính -> mở Hỏa ngục + Hồi IV.
        ``last_level`` (ải 15): qua ải này là kết thúc thật -> xong chu kỳ, mở chu kỳ mới."""
        main_level = last_level if main_level is None else main_level
        self.level_stars[number] = max(stars, self.level_stars.get(number, 0))
        self.unlocked_level = max(self.unlocked_level, min(last_level, number + 1))
        if number >= main_level:
            self.campaign_cleared = True
        if number >= last_level:
            self.cycle_complete = True
            self.cycle_history[self.cycle] = max(self.total_stars, self.cycle_history.get(self.cycle, 0))
        self.save()

    def start_new_cycle(self) -> bool:
        """Bắt đầu chu kỳ mới sau khi phá đảo: ải về 1, sao của chu kỳ mới tính lại từ 0."""
        if not self.cycle_complete:
            return False
        self.cycle += 1
        self.cycle_complete = False
        self.unlocked_level = 1
        self.level_stars = {}
        self.save()
        return True

    @property
    def total_stars(self) -> int:
        return sum(self.level_stars.values())

    # --- Huy hiệu & bộ đếm ------------------------------------------------------------
    def unlock(self, key: str) -> bool:
        """Ghi huy hiệu mới kèm ngày đạt. True nếu lần đầu."""
        if key in self.achievements:
            return False
        self.achievements[key] = datetime.date.today().isoformat()
        self.save()
        return True

    def add_counters(self, **amounts: int) -> None:
        for key, value in amounts.items():
            if value:
                self.counters[key] = self.counters.get(key, 0) + int(value)

    # --- Chơi mới ---------------------------------------------------------------------
    def reset_all(self) -> Optional[Path]:
        """CHƠI MỚI: xóa sạch tiến độ (ải, sao, chu kỳ, Sổ tay, kỷ lục, thống kê, huy hiệu) như mới cài game.
        Trước khi xóa, chép file lưu cũ sang ``save_backup_<ngày giờ>.json`` cạnh nó để lỡ tay còn khôi phục được.
        Cài đặt (âm lượng, tay...) nằm ở settings.json nên không bị ảnh hưởng. Trả về đường dẫn bản sao lưu."""
        backup = None
        if self.path.exists():
            stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup = self.path.with_name(f"save_backup_{stamp}.json")
            try:
                shutil.copy2(self.path, backup)
            except OSError as exc:
                log.error("Không sao lưu được %s: %s", self.path, exc)
                backup = None
        fresh = type(self)(path=self.path)
        for name in self.__dataclass_fields__:
            if name != "path":
                setattr(self, name, getattr(fresh, name))
        self.save()
        return backup

    # --- Ghi nhận ván chơi --------------------------------------------------------
    #: hạng (0 = nhất) của ván vừa ghi trong Bảng điểm chế độ đó; None = không lọt top (không lưu vào file)
    last_rank: Optional[int] = field(default=None, repr=False, compare=False)

    def record(self, result: GameResult) -> bool:
        """Cộng dồn kết quả một ván, lưu file. Trả về True nếu phá kỷ lục chung."""
        rec = self.modes[result.mode]
        rec.games_played += 1
        rec.total_kills += result.kills
        rec.total_boss_kills += result.boss_kills
        rec.best_score = max(rec.best_score, result.score)
        rec.best_time = max(rec.best_time, round(result.survival_time, 1))
        rec.best_combo = max(rec.best_combo, result.best_combo)
        if result.score > 0:
            rec.top_runs.append({
                "score": int(result.score), "time": round(result.survival_time, 1), "kills": int(result.kills),
                "combo": int(result.best_combo), "level": result.level, "victory": bool(result.victory),
                "date": datetime.date.today().isoformat(),
            })
            run = rec.top_runs[-1]
            rec.top_runs.sort(key=lambda r: -r["score"])        # sort ổn định: bằng điểm thì ván cũ đứng trước
            del rec.top_runs[TOP_RUNS:]
            self.last_rank = next((i for i, r in enumerate(rec.top_runs) if r is run), None)
        else:
            self.last_rank = None
        new_record = result.score > self.highscore
        if new_record:
            self.highscore = result.score
        self.save()
        return new_record

    # --- Đọc / ghi -------------------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "version": SAVE_VERSION,
            "highscore": self.highscore,
            "modes": {m.value: asdict(r) for m, r in self.modes.items()},
            "campaign": {
                "unlocked_level": self.unlocked_level,
                "level_stars": {str(k): v for k, v in sorted(self.level_stars.items())},
                "cleared": self.campaign_cleared,
                "seen_enemies": sorted(self.seen_enemies),
                "cycle": self.cycle,
                "cycle_complete": self.cycle_complete,
                "cycle_history": {str(k): v for k, v in sorted(self.cycle_history.items())},
                "rescued": self.rescued,
            },
            "achievements": dict(sorted(self.achievements.items())),
            "counters": dict(sorted(self.counters.items())),
        }

    def save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(tmp, self.path)
        except OSError as exc:
            log.error("Không lưu được dữ liệu vào %s: %s", self.path, exc)

    @classmethod
    def load(cls, path: Optional[Path] = None, legacy_dirs: Iterable[Path] = (PROJECT_DIR, Path.cwd())) -> "SaveData":
        path = path or default_save_path()
        data = cls(path=path)
        if path.exists():
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                data.highscore = int(raw.get("highscore", 0))
                for mode in GameMode:
                    values = raw.get("modes", {}).get(mode.value, {})
                    known = {k: v for k, v in values.items() if k in ModeRecord.__dataclass_fields__}
                    data.modes[mode] = ModeRecord(**known)
                campaign = raw.get("campaign", {})
                data.unlocked_level = max(1, int(campaign.get("unlocked_level", 1)))
                data.level_stars = {int(k): int(v) for k, v in campaign.get("level_stars", {}).items()}
                data.campaign_cleared = bool(campaign.get("cleared", False))
                data.cycle = max(1, int(campaign.get("cycle", 1)))
                # Save cũ (v3) đã phá đảo thì coi như xong chu kỳ 1, được mở chu kỳ 2
                data.cycle_complete = bool(campaign.get("cycle_complete", data.campaign_cleared))
                data.cycle_history = {int(k): int(v) for k, v in campaign.get("cycle_history", {}).items()}
                rescued = campaign.get("rescued")
                data.rescued = max(0, min(40, int(rescued))) if isinstance(rescued, (int, float)) else None
                # Save trước khi có Hồi IV: đã qua ải 10 trong chu kỳ này -> mở luôn ải 11
                if data.unlocked_level >= 10 and 10 in data.level_stars:
                    data.unlocked_level = max(data.unlocked_level, 11)
                if data.campaign_cleared and not data.cycle_history and data.cycle == 1:
                    data.cycle_history = {1: data.total_stars}
                achievements = raw.get("achievements", {})
                if isinstance(achievements, dict):
                    data.achievements = {str(k): str(v) for k, v in achievements.items()}
                counters = raw.get("counters", {})
                if isinstance(counters, dict):
                    data.counters = {str(k): int(v) for k, v in counters.items()}
                seen = campaign.get("seen_enemies", [])
                if isinstance(seen, list):
                    data.seen_enemies = {key for key in seen if isinstance(key, str)}
            except (ValueError, TypeError, AttributeError) as exc:
                backup = path.with_suffix(".bak")
                log.error("File lưu bị hỏng (%s) - sao lưu sang %s và bắt đầu lại", exc, backup)
                os.replace(path, backup)
                data = cls(path=path)
            return data
        if data._import_legacy(legacy_dirs):
            data.save()
        return data

    def _import_legacy(self, dirs: Iterable[Path]) -> bool:
        imported = False
        for folder in dict.fromkeys(Path(d) for d in dirs):
            score_file, stats_file = folder / "highscore.txt", folder / "stats.json"
            if score_file.exists():
                try:
                    self.highscore = max(self.highscore, int(score_file.read_text().strip() or 0))
                    imported = True
                except ValueError:
                    pass
            if stats_file.exists():
                try:
                    old = json.loads(stats_file.read_text(encoding="utf-8"))
                    for mode in GameMode:
                        o = old.get(mode.value, {})
                        rec = self.modes[mode]
                        rec.best_score = max(rec.best_score, int(o.get("score", 0)))
                        rec.total_kills = max(rec.total_kills, int(o.get("kills", 0)))
                        rec.total_boss_kills = max(rec.total_boss_kills, int(o.get("boss_kills", 0)))
                        self.highscore = max(self.highscore, rec.best_score)
                    imported = True
                except (ValueError, AttributeError):
                    pass
        if imported:
            log.info("Đã nhập dữ liệu từ phiên bản cũ")
        return imported
