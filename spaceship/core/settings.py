"""Tùy chọn người chơi (tự bắn, độ nhạy tay, tư thế nghỉ đã hiệu chỉnh), lưu ở settings.json
cạnh file save, để lần sau mở game không phải chỉnh lại."""
from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional, Tuple

from spaceship import config
from spaceship.core.storage import default_save_path

log = logging.getLogger(__name__)
SENSITIVITY_ORDER = ("low", "medium", "high")


def default_settings_path() -> Path:
    return default_save_path().parent / "settings.json"


@dataclass
class Settings:
    path: Optional[Path] = field(default=None, repr=False, compare=False)
    auto_fire: bool = True
    hand_menu: bool = True                               # di tay + chụm tay để chọn trong các màn menu
    fullscreen: bool = False                             # mở game ở chế độ toàn màn hình
    sensitivity: str = "medium"
    hand_center: Optional[Tuple[float, float]] = None   # None = chưa hiệu chỉnh
    difficulty: str = "normal"                           # easy | normal | hard
    music_volume: float = 0.7                            # 0..1
    sfx_volume: float = 0.8                              # 0..1
    screen_fx: str = "full"                              # rung & nháy màn hình: full | reduced | off

    @staticmethod
    def step_volume(value: float, step: float, wrap: bool = False) -> float:
        """Tăng/giảm 10%. ``wrap``: quá 100% thì vòng về 0 (khi chỉ có một nút "chọn", vd. chụm tay)."""
        new = round(value + step, 1)
        if wrap and new > 1.0:
            return 0.0
        return min(1.0, max(0.0, new))

    def cycle_screen_fx(self) -> None:
        order = config.SCREEN_FX_LEVELS
        i = order.index(self.screen_fx) if self.screen_fx in order else 0
        self.screen_fx = order[(i + 1) % len(order)]

    def cycle_difficulty(self) -> None:
        order = config.DIFFICULTIES
        i = order.index(self.difficulty) if self.difficulty in order else 1
        self.difficulty = order[(i + 1) % len(order)]

    @property
    def center(self) -> Tuple[float, float]:
        return tuple(self.hand_center) if self.hand_center else config.HAND_DEFAULT_CENTER

    @property
    def half_width(self) -> float:
        return config.HAND_SENSITIVITY.get(self.sensitivity, config.HAND_SENSITIVITY["medium"])

    def cycle_sensitivity(self) -> None:
        i = SENSITIVITY_ORDER.index(self.sensitivity) if self.sensitivity in SENSITIVITY_ORDER else 1
        self.sensitivity = SENSITIVITY_ORDER[(i + 1) % len(SENSITIVITY_ORDER)]

    # --- Đọc / ghi -------------------------------------------------------------------
    @classmethod
    def load(cls, path: Optional[Path] = None) -> "Settings":
        path = path or default_settings_path()
        data = cls(path=path)
        if path.exists():
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                data.auto_fire = bool(raw.get("auto_fire", True))
                data.hand_menu = bool(raw.get("hand_menu", True))
                data.fullscreen = bool(raw.get("fullscreen", False))
                if raw.get("sensitivity") in SENSITIVITY_ORDER:
                    data.sensitivity = raw["sensitivity"]
                if raw.get("screen_fx") in config.SCREEN_FX_LEVELS:
                    data.screen_fx = raw["screen_fx"]
                if raw.get("difficulty") in config.DIFFICULTIES:
                    data.difficulty = raw["difficulty"]
                for key in ("music_volume", "sfx_volume"):
                    if isinstance(raw.get(key), (int, float)):
                        setattr(data, key, max(0.0, min(1.0, float(raw[key]))))
                center = raw.get("hand_center")
                if isinstance(center, list) and len(center) == 2:
                    data.hand_center = (float(center[0]), float(center[1]))
            except (ValueError, TypeError, AttributeError) as exc:
                log.warning("File cài đặt lỗi (%s) - dùng mặc định", exc)
        return data

    def save(self) -> None:
        if self.path is None:
            return
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            payload = {k: v for k, v in asdict(self).items() if k != "path"}
            tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(tmp, self.path)
        except OSError as exc:
            log.error("Không lưu được cài đặt vào %s: %s", self.path, exc)
