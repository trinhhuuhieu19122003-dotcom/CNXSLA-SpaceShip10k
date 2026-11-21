"""Lưu kỷ lục & thống kê.

Khác bản cũ:
- Lưu ở thư mục người dùng (không ghi vào thư mục code, không lỡ commit lên Git).
- Thống kê CỘNG DỒN qua mọi ván (bản cũ chỉ lưu số kill của ván có điểm cao nhất).
- Ghi file an toàn (ghi file tạm rồi thay thế), file hỏng thì sao lưu ra .bak.
- Tự nhập dữ liệu từ ``highscore.txt`` / ``stats.json`` của bản cũ nếu còn.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, Iterable, Optional

from spaceship.config import PROJECT_DIR, GameMode

log = logging.getLogger(__name__)

SAVE_VERSION = 3
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


@dataclass
class GameResult:
    mode: GameMode
    score: int
    kills: int
    boss_kills: int
    survival_time: float
    victory: bool = False


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

    def mark_seen(self, key: str) -> bool:
        """Lưu mục Sổ tay mới; các lần gặp tiếp theo không ghi file."""
        if key in self.seen_enemies:
            return False
        self.seen_enemies.add(key)
        self.save()
        return True

    def record_level(self, number: int, stars: int, last_level: int) -> None:
        """Qua ải: lưu số sao (giữ số cao nhất), mở ải tiếp theo / đánh dấu phá đảo."""
        self.level_stars[number] = max(stars, self.level_stars.get(number, 0))
        self.unlocked_level = max(self.unlocked_level, min(last_level, number + 1))
        if number >= last_level:
            self.campaign_cleared = True
        self.save()

    @property
    def total_stars(self) -> int:
        return sum(self.level_stars.values())

    # --- Ghi nhận ván chơi --------------------------------------------------------
    def record(self, result: GameResult) -> bool:
        """Cộng dồn kết quả một ván, lưu file. Trả về True nếu phá kỷ lục chung."""
        rec = self.modes[result.mode]
        rec.games_played += 1
        rec.total_kills += result.kills
        rec.total_boss_kills += result.boss_kills
        rec.best_score = max(rec.best_score, result.score)
        rec.best_time = max(rec.best_time, round(result.survival_time, 1))
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
            },
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
