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
    sensitivity: str = "medium"
    hand_center: Optional[Tuple[float, float]] = None   # None = chưa hiệu chỉnh

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
                if raw.get("sensitivity") in SENSITIVITY_ORDER:
                    data.sensitivity = raw["sensitivity"]
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
