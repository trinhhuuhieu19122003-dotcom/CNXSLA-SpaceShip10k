"""Nạp và cache tài nguyên (ảnh, font).

Bản cũ tạo font mới mỗi lần vẽ (``pygame.font.SysFont`` trong ``draw``) và
nuốt lỗi thiếu file bằng ``except:`` trống. Ở đây mọi thứ được cache, và
file thiếu được ghi log đúng một lần để dễ phát hiện.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Optional, Tuple

import pygame

from spaceship.config import FONT_NAMES, IMAGES_DIR

log = logging.getLogger(__name__)


class Assets:
    def __init__(self, images_dir: Path = IMAGES_DIR) -> None:
        self.images_dir = images_dir
        self._raw: Dict[str, Optional[pygame.Surface]] = {}
        self._scaled: Dict[Tuple[str, int], Optional[pygame.Surface]] = {}
        self._fonts: Dict[Tuple[int, bool, bool], pygame.font.Font] = {}

    # --- Ảnh -------------------------------------------------------------------
    def _load_raw(self, name: str) -> Optional[pygame.Surface]:
        if name not in self._raw:
            path = self.images_dir / f"{name}.png"
            try:
                surface = pygame.image.load(str(path))
                if pygame.display.get_surface() is not None:
                    surface = surface.convert_alpha()
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

    # --- Font ------------------------------------------------------------------
    def font(self, size: int, bold: bool = True, italic: bool = False) -> pygame.font.Font:
        key = (size, bold, italic)
        if key not in self._fonts:
            self._fonts[key] = pygame.font.SysFont(FONT_NAMES, size, bold=bold, italic=italic)
        return self._fonts[key]

    def text(self, text: str, size: int, color, bold: bool = True, italic: bool = False) -> pygame.Surface:
        return self.font(size, bold, italic).render(text, True, color)
