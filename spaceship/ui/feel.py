"""Lớp phủ "cảm giác đánh": viền đỏ khi trúng đạn / máu thấp, chớp sáng mờ dần.

Viền đỏ là THÔNG TIN (bạn vừa bị trúng, bạn sắp chết) nên luôn hiện, kể cả khi tắt
"Rung & nháy màn hình"; chỉ có nhịp đập khi máu thấp và chớp sáng là bị tắt theo cài đặt.
"""
from __future__ import annotations

import math
from functools import lru_cache

import numpy as np
import pygame

from spaceship import config

HURT_RED = (255, 40, 50)
HURT_ALPHA = 200
LOW_HP_ALPHA = (60, 130)          # thấp nhất / cao nhất của nhịp đập khi máu thấp
LOW_HP_BEATS_PER_SECOND = 1.3


@lru_cache(maxsize=4)
def vignette(size: tuple) -> pygame.Surface:
    """Viền đỏ đậm dần ra mép, giữa màn trong suốt (tạo một lần cho mỗi kích thước)."""
    w, h = size
    surf = pygame.Surface(size, pygame.SRCALPHA)
    surf.fill((*HURT_RED, 0))
    xs = (np.arange(w) - w / 2) / (w / 2)
    ys = (np.arange(h) - h / 2) / (h / 2)
    d = np.sqrt(xs[:, None] ** 2 + ys[None, :] ** 2) / math.sqrt(2)     # 0 ở giữa, 1 ở góc
    alpha = np.clip((d - 0.42) / 0.58, 0, 1) ** 1.5 * 255
    pixels = pygame.surfarray.pixels_alpha(surf)
    pixels[:] = alpha.astype(np.uint8)
    del pixels
    return surf


@lru_cache(maxsize=4)
def _white(size: tuple) -> pygame.Surface:
    surf = pygame.Surface(size)
    surf.fill((255, 255, 255))
    return surf


def vignette_alpha(world, fx_scale: float = 1.0) -> int:
    """Độ đậm viền đỏ: lấy cái lớn hơn giữa "vừa trúng đạn" và "máu thấp"."""
    player = world.player
    hurt = HURT_ALPHA * world.hurt_timer / config.HURT_VIGNETTE_TICKS if world.hurt_timer > 0 else 0
    low = 0
    if 0 < player.hp <= player.max_hp * config.LOW_HP_RATIO:
        lo, hi = LOW_HP_ALPHA
        beat = 0.5
        if fx_scale > 0:
            beat = 0.5 + 0.5 * math.cos(world.survival_time * LOW_HP_BEATS_PER_SECOND * 2 * math.pi)   # đậm nhất đúng lúc tim đập
        low = lo + (hi - lo) * beat
    return int(max(hurt, low))


def draw_vignette(surface: pygame.Surface, world, fx_scale: float = 1.0) -> None:
    alpha = vignette_alpha(world, fx_scale)
    if alpha <= 0:
        return
    layer = vignette(surface.get_size())
    layer.set_alpha(alpha)
    surface.blit(layer, (0, 0))


def flash_alpha(world, fx_scale: float = 1.0) -> int:
    if world.flash <= 0:
        return 0
    return int(min(config.FLASH_MAX_ALPHA, 40 * world.flash) * fx_scale)


def draw_flash(surface: pygame.Surface, world, fx_scale: float = 1.0) -> None:
    """Chớp sáng của kỹ năng Nộ: lớp trắng bán trong suốt, mờ dần (không trắng xóa cả màn)."""
    alpha = flash_alpha(world, fx_scale)
    if alpha <= 0:
        return
    layer = _white(surface.get_size())
    layer.set_alpha(alpha)
    surface.blit(layer, (0, 0))
