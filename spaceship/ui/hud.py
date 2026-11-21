"""Thanh thông tin trong trận: điểm, máu, nộ, mạng, trạng thái điều khiển."""
from __future__ import annotations

import math

import pygame

from spaceship import config
from spaceship.config import GRAY, HEIGHT, NEON_CYAN, NEON_GREEN, NEON_ORANGE, NEON_RED, WHITE, WIDTH, YELLOW
from spaceship.input.gestures import Gesture
from spaceship.systems.world import World

GESTURE_LABELS = {
    Gesture.FIST: ("NẮM TAY: NÉ CHẬM", NEON_CYAN),
    Gesture.PINCH: ("CHỤM: KỸ NĂNG NỘ", NEON_ORANGE),
}

BAR_W, BAR_H = 200, 15


def format_time(seconds: float) -> str:
    seconds = int(seconds)
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def _bar(surface, x, y, ratio, border, fill) -> None:
    pygame.draw.rect(surface, border, (x, y, BAR_W, BAR_H), 2)
    pygame.draw.rect(surface, fill, (x + 2, y + 2, (BAR_W - 4) * max(0.0, min(1.0, ratio)), BAR_H - 4))


def draw_hud(surface: pygame.Surface, assets, world: World, controls=None) -> None:
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
    surface.blit(assets.text("[NỘ]", 14, NEON_ORANGE if p.rage_full else GRAY), (215, 63))
    weapon = assets.text(f"{p.weapon.upper()} Lv{p.level}", 14, p.color)
    surface.blit(weapon, (215, 38))

    for i in range(p.lives):
        hx = WIDTH - 30 - i * 30
        pygame.draw.polygon(surface, NEON_GREEN, [(hx, 12), (hx - 8, 28), (hx, 24), (hx + 8, 28)], 2)

    icon = "TAY" if controls is not None and controls.source == "hand" else "PHÍM"
    surface.blit(assets.text(f"ĐIỀU KHIỂN: {icon}", 12, GRAY), (WIDTH - 150, 36))
    if p.shield_active:
        surface.blit(assets.text(f"KHIÊN {p.shield_timer / config.TICK_RATE:.1f}s", 14, (0, 255, 255)), (10, 88))
    if p.burn_unlocked or p.has_drone:
        perks = " + ".join(t for t, on in (("DRONE", p.has_drone), ("THIÊU ĐỐT", p.burn_unlocked)) if on)
        surface.blit(assets.text(perks, 12, YELLOW), (10, 108))
    if controls is not None:
        draw_hand_indicator(surface, assets, controls, p.rage_full)


def draw_hand_indicator(surface: pygame.Surface, assets, controls, rage_full: bool) -> None:
    """Góc dưới trái: game đang thấy cử chỉ gì, vòng tròn đầy dần khi giữ chụm ngón."""
    x, y = 14, HEIGHT - 46
    if controls.hand_absent > 0.3:
        ratio = min(1.0, controls.hand_absent / config.HAND_PAUSE_SECONDS)
        surface.blit(assets.text("MẤT TAY - sắp tạm dừng để nghỉ", 14, YELLOW), (x, y))
        pygame.draw.rect(surface, GRAY, (x, y + 22, 200, 5), 1)
        pygame.draw.rect(surface, YELLOW, (x, y + 22, 200 * ratio, 5))
        return
    if controls.gesture == Gesture.NONE:
        return
    label, color = GESTURE_LABELS.get(controls.gesture, ("TAY: LÁI", WHITE))
    center, r = (x + 14, y + 14), 12
    pygame.draw.circle(surface, (40, 45, 55), center, r, 3)
    if controls.gesture == Gesture.PINCH:
        if not rage_full:
            label, color = "CHỤM: NỘ CHƯA ĐẦY", GRAY
        elif controls.skill_progress > 0:
            rect = pygame.Rect(center[0] - r, center[1] - r, r * 2, r * 2)
            pygame.draw.arc(surface, NEON_ORANGE, rect, math.pi / 2 - controls.skill_progress * 2 * math.pi, math.pi / 2, 3)
    else:
        pygame.draw.circle(surface, color, center, 4)
    surface.blit(assets.text(label, 14, color), (x + 34, y + 5))
