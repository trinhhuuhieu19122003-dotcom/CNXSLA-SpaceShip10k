"""Thanh thông tin trong trận: điểm, máu, nộ, mạng, trạng thái điều khiển."""
from __future__ import annotations

import pygame

from spaceship import config
from spaceship.config import GRAY, NEON_GREEN, NEON_ORANGE, NEON_RED, WHITE, WIDTH, YELLOW
from spaceship.systems.world import World

BAR_W, BAR_H = 200, 15


def format_time(seconds: float) -> str:
    seconds = int(seconds)
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def _bar(surface, x, y, ratio, border, fill) -> None:
    pygame.draw.rect(surface, border, (x, y, BAR_W, BAR_H), 2)
    pygame.draw.rect(surface, fill, (x + 2, y + 2, (BAR_W - 4) * max(0.0, min(1.0, ratio)), BAR_H - 4))


def draw_hud(surface: pygame.Surface, assets, world: World, control_source: str = "keyboard") -> None:
    p = world.player
    dmg = p.base_damage + p.bonus_damage
    max_dmg = p.base_damage + config.MAX_BONUS_DAMAGE
    if world.mode.is_timed:
        info = f"ĐIỂM: {world.score} | THỜI GIAN: {format_time(world.survival_time)} | DMG: {dmg}/{max_dmg}"
    else:
        waves = config.CAMPAIGN_WAVES.get(world.stage, 0)
        wave = "BOSS" if world.wave > waves else f"WAVE {world.wave}/{waves}"
        info = f"ĐIỂM: {world.score} | STAGE {world.stage} - {wave} | DMG: {dmg}/{max_dmg}"
    surface.blit(assets.text(info, 18, WHITE), (10, 10))

    _bar(surface, 10, 40, p.hp / p.max_hp, NEON_RED, NEON_GREEN)
    _bar(surface, 10, 65, p.rage / p.max_rage, GRAY, NEON_ORANGE)
    surface.blit(assets.text("[NUKE]", 14, NEON_ORANGE if p.rage_full else GRAY), (215, 63))
    weapon = assets.text(f"{p.weapon.upper()} Lv{p.level}", 14, p.color)
    surface.blit(weapon, (215, 38))

    for i in range(p.lives):
        hx = WIDTH - 30 - i * 30
        pygame.draw.polygon(surface, NEON_GREEN, [(hx, 12), (hx - 8, 28), (hx, 24), (hx + 8, 28)], 2)

    icon = "TAY" if control_source == "hand" else "PHÍM"
    surface.blit(assets.text(f"ĐIỀU KHIỂN: {icon}", 12, GRAY), (WIDTH - 150, 36))
    if p.shield_active:
        surface.blit(assets.text(f"KHIÊN {p.shield_timer / config.TICK_RATE:.1f}s", 14, (0, 255, 255)), (10, 88))
    if p.burn_unlocked or p.has_drone:
        perks = " + ".join(t for t, on in (("DRONE", p.has_drone), ("THIÊU ĐỐT", p.burn_unlocked)) if on)
        surface.blit(assets.text(perks, 12, YELLOW), (10, 108))
