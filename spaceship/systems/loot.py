"""Bảng rơi đồ.

Bản cũ ở chế độ Vô tận/Hỏa ngục chỉ rơi 3 loại (máu, khiên, Plasma) nên không
bao giờ đổi được sang Laser/Homing. Ở đây có bảng trọng số đầy đủ.
"""
from __future__ import annotations

import random
from typing import Optional

from spaceship.config import RANDOM_DROP_CHANCE, GameMode

WEAPON_UPGRADES = ("upgrade_plasma", "upgrade_laser", "upgrade_homing", "upgrade_universal")

# Tỉ lệ % (máu, khiên, vũ khí) theo stage/wave ở chế độ Vượt ải
CAMPAIGN_STAGE1 = {1: (10, 5, 20), 2: (8, 4, 18), 3: (7, 3, 15), 4: (6, 3, 15)}
CAMPAIGN_STAGE1_LATE = (5, 2, 12)
CAMPAIGN_STAGE2 = (6, 3, 16)
CAMPAIGN_STAGE3 = (4, 2, 13)

RANDOM_TABLE = (
    ("heal", 30), ("shield", 20),
    ("upgrade_plasma", 13), ("upgrade_laser", 13), ("upgrade_homing", 13), ("upgrade_universal", 11),
)
INFERNO_TABLE = (                     # Hỏa ngục: không rơi khiên, ít máu
    ("heal", 15), ("upgrade_plasma", 25), ("upgrade_laser", 25), ("upgrade_homing", 25), ("upgrade_universal", 10),
)

BOSS_REWARDS = {1: "upgrade_drone", 2: "upgrade_burn"}   # Vượt ải: phần thưởng hạ boss stage 1, 2


def campaign_drop(stage: int, wave: int, rng=random) -> Optional[str]:
    if stage == 1:
        heal, shield, weapon = CAMPAIGN_STAGE1.get(wave, CAMPAIGN_STAGE1_LATE)
    elif stage == 2:
        heal, shield, weapon = CAMPAIGN_STAGE2
    else:
        heal, shield, weapon = CAMPAIGN_STAGE3
    roll = rng.randint(1, 100)
    if roll <= heal:
        return "heal"
    if roll <= heal + shield:
        return "shield"
    if roll <= heal + shield + weapon:
        return rng.choice(WEAPON_UPGRADES)
    return None


def random_drop(mode: GameMode, rng=random) -> str:
    table = INFERNO_TABLE if mode is GameMode.INFERNO else RANDOM_TABLE
    kinds, weights = zip(*table)
    return rng.choices(kinds, weights=weights, k=1)[0]


def drop_for_kill(mode: GameMode, stage: int, wave: int, rng=random) -> Optional[str]:
    """Vật phẩm rơi khi hạ một lính thường (None = không rơi)."""
    if mode is GameMode.CAMPAIGN:
        return campaign_drop(stage, wave, rng)
    if rng.random() < RANDOM_DROP_CHANCE[mode]:
        return random_drop(mode, rng)
    return None
