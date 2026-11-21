"""Nạp và cache tài nguyên (ảnh, font).

Bản cũ tạo font mới mỗi lần vẽ (``pygame.font.SysFont`` trong ``draw``) và
nuốt lỗi thiếu file bằng ``except:`` trống. Ở đây mọi thứ được cache, và
file thiếu được ghi log đúng một lần để dễ phát hiện.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Optional, Tuple
from unicodedata import normalize

import pygame

from spaceship.config import ASSETS_DIR, FONT_NAMES, IMAGES_DIR
from spaceship.ui.crisp import TextSurface

log = logging.getLogger(__name__)
FONTS_DIR = ASSETS_DIR / "fonts"
FONT_FILES = {
    "display": "ChakraPetch-Bold.ttf",
    "ui": "ChakraPetch-SemiBold.ttf",
    "label": "ChakraPetch-Medium.ttf",
    "body": "Exo2.ttf",
}


#: Ảnh của Hồi IV chưa có file thì tạm dùng ảnh có sẵn (thả file thật vào assets/images là game tự dùng).
PLACEHOLDERS = {
    "bg_act4": "bg_act3", "bg_blackhole": "bg_act3", "bg_heart": "bg_act3",
    "storm_eye": "boss2", "listener": "nest_mother",
    "swarm_heart": "mothership_boss", "swarm_heart_core": "mothership_boss",
    "lifeboat": "infected_ally", "portrait_aria_glitch": "portrait_aria",
}


class Assets:
    def __init__(self, images_dir: Path = IMAGES_DIR, *, fonts_dir: Path = FONTS_DIR) -> None:
        self.images_dir = images_dir
        self.fonts_dir = fonts_dir
        self._raw: Dict[str, Optional[pygame.Surface]] = {}
        self._scaled: Dict[Tuple[str, int], Optional[pygame.Surface]] = {}
        self._fonts: Dict[Tuple[int, str, bool], pygame.font.Font] = {}
        self._missing_fonts: set[Path] = set()

    # --- Ảnh -------------------------------------------------------------------
    def _path(self, name: str) -> Path:
        path = self.images_dir / f"{name}.png"
        if not path.exists() and (self.images_dir / f"{name}.jpg").exists():
            path = self.images_dir / f"{name}.jpg"          # ảnh nền/chân dung lưu JPG cho nhẹ
        return path

    def _load_raw(self, name: str) -> Optional[pygame.Surface]:
        if name not in self._raw:
            path = self._path(name)
            if not path.exists() and name in PLACEHOLDERS:
                self._raw[name] = self._load_raw(PLACEHOLDERS[name])
                return self._raw[name]
            try:
                surface = pygame.image.load(str(path))
                if pygame.display.get_surface() is not None:
                    surface = surface.convert_alpha() if path.suffix == ".png" else surface.convert()
                self._raw[name] = surface
            except (pygame.error, FileNotFoundError) as exc:
                log.warning("Không nạp được ảnh %s (%s) - dùng hình vẽ thay thế", path, exc)
                self._raw[name] = None
        return self._raw[name]

    def image(self, name: str, width: int) -> Optional[pygame.Surface]:
        """Ảnh co theo chiều rộng ``width`` và GIỮ ĐÚNG tỉ lệ (bản cũ ép vào ô vuông)."""
        key = (name, int(width))
        if key not in self._scaled:
            raw = self._load_raw(name)
            if raw is None:
                self._scaled[key] = None
            else:
                height = max(1, round(raw.get_height() * width / raw.get_width()))
                self._scaled[key] = pygame.transform.smoothscale(raw, (int(width), height))
        return self._scaled[key]

    def raw(self, name: str) -> Optional[pygame.Surface]:
        """Ảnh gốc, không co giãn (ảnh nền cuộn, ảnh kết thúc)."""
        return self._load_raw(name)

    def silhouette(self, name: str, width: int) -> Optional[pygame.Surface]:
        """Bóng trắng cùng hình dạng sprite (giữ kênh alpha) để làm hiệu ứng nháy khi trúng đạn."""
        key = ("__white__" + name, int(width))
        if key not in self._scaled:
            base = self.image(name, width)
            if base is None:
                self._scaled[key] = None
            else:
                white = base.copy()
                white.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGBA_MAX)
                self._scaled[key] = white
        return self._scaled[key]

    # --- Font ------------------------------------------------------------------
    def font(self, size: int, bold: bool = True, italic: bool = False, *,
             role: Optional[str] = None) -> pygame.font.Font:
        role = role if role is not None else ("ui" if bold else "body")
        key = (size, role, italic)
        if key not in self._fonts:
            path = self.fonts_dir / FONT_FILES[role]
            if path not in self._missing_fonts:
                try:
                    font = pygame.font.Font(str(path), size)
                except (OSError, pygame.error) as exc:
                    self._missing_fonts.add(path)
                    log.warning("Không nạp được font %s (%s) - dùng font hệ thống", path, exc)
                else:
                    font.set_italic(italic)
                    self._fonts[key] = font
                    return font
            self._fonts[key] = pygame.font.SysFont(FONT_NAMES, size, bold=role in ("display", "ui"), italic=italic)
        return self._fonts[key]

    def text(self, text: str, size: int, color, bold: bool = True, italic: bool = False, *,
             role: Optional[str] = None) -> pygame.Surface:
        """Một dòng chữ. Kết quả nhớ cách vẽ (``TextSurface.spec``) để khi phóng to toàn màn hình, chữ được vẽ
        lại ở cỡ lớn cho sắc nét (xem ``ui/crisp.py``)."""
        text = normalize("NFC", text)
        image = self.font(size, bold, italic, role=role).render(text, True, color)
        try:
            spec = (text, size, tuple(pygame.Color(color)), bold, italic, role)
        except (TypeError, ValueError):
            return image
        return TextSurface.wrap(image, spec)
