"""Bảng rơi đồ.

Bản cũ ở chế độ Vô tận/Hỏa ngục chỉ rơi 3 loại (máu, khiên, Plasma) nên không
bao giờ đổi được sang Laser/Homing. Ở đây có bảng trọng số đầy đủ.
"""
from __future__ import annotations

import random
from typing import Optional

from spaceship.config import RANDOM_DROP_CHANCE, GameMode

WEAPON_UPGRADES = ("upgrade_plasma", "upgrade_laser", "upgrade_homing", "upgrade_universal")
LIGHTNING_FROM_LEVEL = 4          # Vượt ải: súng Tia Sét bắt đầu rơi từ ải 4 (nhặt từ xác phi đội)

# Tỉ lệ % (máu, khiên, vũ khí) mỗi khi hạ một lính, theo hồi của chế độ Vượt ải
CAMPAIGN_ACT_RATES = {1: (10, 5, 18), 2: (7, 3, 15), 3: (5, 2, 13)}

RANDOM_TABLE = (
    ("heal", 30), ("shield", 20),
    ("upgrade_plasma", 12), ("upgrade_laser", 12), ("upgrade_homing", 12),
    ("upgrade_lightning", 9), ("upgrade_universal", 10),
)
INFERNO_TABLE = (                     # Hỏa ngục: không rơi khiên, ít máu
    ("heal", 15), ("upgrade_plasma", 20), ("upgrade_laser", 20), ("upgrade_homing", 20),
    ("upgrade_lightning", 15), ("upgrade_universal", 10),
)

# Phần thưởng boss ở Vô tận/Hỏa ngục theo thứ tự hạ: Drone, Thiêu đốt, Drone thứ hai
SURVIVAL_REWARDS = ("upgrade_drone", "upgrade_burn", "upgrade_drone")


def weapon_choices(level_number: Optional[int]):
    if level_number is not None and level_number < LIGHTNING_FROM_LEVEL:
        return WEAPON_UPGRADES
    return WEAPON_UPGRADES + ("upgrade_lightning",)


def campaign_drop(act: int, level_number: Optional[int], rng=random, drop_mult: float = 1.0) -> Optional[str]:
    heal, shield, weapon = (r * drop_mult for r in CAMPAIGN_ACT_RATES.get(act, CAMPAIGN_ACT_RATES[3]))
    roll = rng.uniform(0, 100)
    if roll <= heal:
        return "heal"
    if roll <= heal + shield:
        return "shield"
    if roll <= heal + shield + weapon:
        return rng.choice(weapon_choices(level_number))
    return None


def random_drop(mode: GameMode, rng=random) -> str:
    table = INFERNO_TABLE if mode is GameMode.INFERNO else RANDOM_TABLE
    kinds, weights = zip(*table)
    return rng.choices(kinds, weights=weights, k=1)[0]


def drop_for_kill(world, rng=None) -> Optional[str]:
    """Vật phẩm rơi khi hạ một lính (None = không rơi)."""
    rng = rng or world.rng
    if world.mode is GameMode.CAMPAIGN:
        level = world.level
        act = level.act if level is not None else 1
        number = level.number if level is not None else None
        return campaign_drop(act, number, rng, world.drop_mult)
    if rng.random() < RANDOM_DROP_CHANCE[world.mode] * world.drop_mult:
        return random_drop(world.mode, rng)
    return None


def boss_chunk_drop(world) -> str:
    """Đồ rơi khi boss mất mỗi 10% máu / phá thiên thạch, xác tàu."""
    if world.mode is GameMode.CAMPAIGN:
        number = world.level.number if world.level is not None else None
        return world.rng.choice(("heal", "shield") + weapon_choices(number))
    return random_drop(world.mode, world.rng)
