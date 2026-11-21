"""Thanh thông tin trong trận: điểm, máu, nộ, mạng, trạng thái điều khiển."""
from __future__ import annotations

import math

import pygame

from spaceship import config
from spaceship.config import GRAY, HEIGHT, NEON_CYAN, NEON_GREEN, NEON_ORANGE, NEON_RED, WHITE, WIDTH, YELLOW
from spaceship.input.gestures import Gesture
from spaceship.entities.items import draw_item_icon
from spaceship.systems.world import World
from spaceship.ui import glow

GESTURE_LABELS = {
    Gesture.FIST: ("NẮM TAY: NÉ CHẬM", NEON_CYAN),
    Gesture.PINCH: ("CHỤM: KỸ NĂNG NỘ", NEON_ORANGE),
}

BAR_W, BAR_H = 200, 15


def format_time(seconds: float) -> str:
    seconds = int(seconds)
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


SEGMENTS = 10


def _hp_bar(surface, assets, x, y, ratio) -> None:
    """Thanh máu chia 10 ô, đổi màu xanh -> vàng -> đỏ khi tụt máu."""
    ratio = max(0.0, min(1.0, ratio))
    color = NEON_GREEN if ratio > 0.5 else (YELLOW if ratio > 0.25 else NEON_RED)
    surface.blit(assets.text("HP", 12, GRAY), (x, y + 1))
    seg_w = (BAR_W - 24) / SEGMENTS
    for i in range(SEGMENTS):
        rect = pygame.Rect(x + 24 + i * seg_w, y, seg_w - 2, BAR_H)
        filled = ratio * SEGMENTS - i
        pygame.draw.rect(surface, (30, 34, 42), rect)
        if filled > 0:
            pygame.draw.rect(surface, color, (rect.x, rect.y, rect.w * min(1.0, filled), rect.h))


def _rage_bar(surface, assets, x, y, ratio, t, skill: str = "") -> None:
    """Thanh Nộ; đầy thì phát sáng nhấp nháy + nhắc cách dùng."""
    ratio = max(0.0, min(1.0, ratio))
    surface.blit(assets.text("NỘ", 12, GRAY), (x, y + 1))
    rect = pygame.Rect(x + 24, y, BAR_W - 24, BAR_H)
    pygame.draw.rect(surface, (30, 34, 42), rect)
    pygame.draw.rect(surface, NEON_ORANGE, (rect.x, rect.y, rect.w * ratio, rect.h))
    if ratio >= 1.0:
        pulse = 0.6 + 0.4 * math.sin(t * 8)
        pygame.draw.rect(surface, glow.scale((255, 220, 120), pulse), rect.inflate(4, 4), 2)
        surface.blit(assets.text(f"{skill} - chụm tay / K", 12, NEON_ORANGE), (x + 24, y + BAR_H + 3))


def _weapon_panel(surface, assets, p, cx, cy, t) -> None:
    """Biểu tượng súng + 6 vạch cấp + sát thương cộng thêm."""
    draw_item_icon(surface, assets, f"upgrade_{p.weapon}", cx, cy, t=t, size=1.1)
    x = cx + 26
    surface.blit(assets.text(config.WEAPON_NAMES.get(p.weapon, p.weapon.upper()), 14, p.color), (x, cy - 18))
    for i in range(config.MAX_WEAPON_LEVEL):
        rect = pygame.Rect(x + i * 13, cy + 2, 10, 8)
        if i < p.level:
            pygame.draw.rect(surface, p.color, rect)
        else:
            pygame.draw.rect(surface, (60, 64, 74), rect, 1)
    if p.bonus_damage:
        surface.blit(assets.text(f"+{p.bonus_damage} DMG", 12, YELLOW), (x + 82, cy - 2))


def draw_hud(surface: pygame.Surface, assets, world: World, controls=None, director=None) -> None:
    p = world.player
    progress = director.progress_text if director is not None else ""
    if world.level is not None:
        info = f"ĐIỂM: {world.score} | ẢI {world.level.number} - {progress}"
    else:
        info = f"ĐIỂM: {world.score} | THỜI GIAN: {format_time(world.survival_time)}"
        if progress:
            info += f" | {progress}"
    surface.blit(assets.text(info, 18, WHITE), (10, 10))

    _hp_bar(surface, assets, 10, 40, p.hp / p.max_hp)
    _rage_bar(surface, assets, 10, 62, p.rage / p.max_rage, world.survival_time, config.SKILL_NAMES.get(p.weapon, ""))
    _weapon_panel(surface, assets, p, 248, 52, world.survival_time)

    for i in range(p.lives):
        hx = WIDTH - 30 - i * 30
        pygame.draw.polygon(surface, NEON_GREEN, [(hx, 12), (hx - 8, 28), (hx, 24), (hx + 8, 28)], 2)

    icon = "TAY" if controls is not None and controls.source == "hand" else "PHÍM"
    surface.blit(assets.text(f"ĐIỀU KHIỂN: {icon}", 12, GRAY), (WIDTH - 150, 36))
    if p.shield_active:
        surface.blit(assets.text(f"KHIÊN {p.shield_timer / config.TICK_RATE:.1f}s", 14, (0, 255, 255)), (10, 98))
    if p.burn_unlocked or p.drones:
        drone = "DRONE x2" if p.drones > 1 else "DRONE"
        perks = " + ".join(t for t, on in ((drone, p.drones), ("THIÊU ĐỐT", p.burn_unlocked)) if on)
        surface.blit(assets.text(perks, 12, YELLOW), (10, 118))
    boss = next((e for e in world.enemies if e.is_boss), None)
    if boss is not None:
        _boss_bar(surface, assets, boss)
    if controls is not None:
        draw_hand_indicator(surface, assets, controls, p.rage_full)


def _boss_bar(surface, assets, boss) -> None:
    """Thanh máu boss lớn ở giữa trên màn hình, kèm tên và khiên."""
    w, x, y = 360, WIDTH // 2 - 180, 92
    name = assets.text(boss.title, 14, NEON_RED)
    surface.blit(name, (WIDTH // 2 - name.get_width() // 2, y - 18))
    pygame.draw.rect(surface, (40, 10, 14), (x, y, w, 10))
    pygame.draw.rect(surface, NEON_RED, (x, y, w * boss.hp_ratio, 10))
    for k in (0.33, 0.66):                                      # vạch chia 3 pha
        pygame.draw.line(surface, (255, 255, 255), (x + w * k, y), (x + w * k, y + 9), 1)
    if boss.shield_hp > 0:
        pygame.draw.rect(surface, (120, 200, 255), (x, y + 12, w * min(1.0, boss.shield_hp / max(1, boss.max_shield)), 4))
    pygame.draw.rect(surface, GRAY, (x, y, w, 10), 1)


def draw_banner(surface, assets, world: World, director=None) -> None:
    """Chữ lớn giữa màn hình: tên ải lúc mở màn, cảnh báo boss, phần thưởng..."""
    text, size, color = "", 40, NEON_CYAN
    if director is not None and director.banner_text:
        text, size = director.banner_text, 36
    elif world.banner_ticks > 0:
        text, size, color = world.banner, 34, YELLOW
    if not text:
        return
    label = assets.text(text, size, color)
    if label.get_width() > WIDTH - 40:
        label = pygame.transform.smoothscale(label, (WIDTH - 40, int(label.get_height() * (WIDTH - 40) / label.get_width())))
    y = HEIGHT // 2 - 90
    shade = pygame.Surface((WIDTH, label.get_height() + 24), pygame.SRCALPHA)
    shade.fill((0, 0, 0, 120))
    surface.blit(shade, (0, y - 12))
    surface.blit(label, (WIDTH // 2 - label.get_width() // 2, y))
    if director is not None and director.banner_text and world.level is not None:
        from spaceship.campaign.story import ACTS
        act = assets.text(ACTS.get(world.level.act, ""), 16, GRAY)
        surface.blit(act, (WIDTH // 2 - act.get_width() // 2, y - 30))


def draw_radio(surface, assets, world: World) -> None:
    """Thoại trong trận: chân dung nhỏ + lời thoại ở dưới màn hình, không dừng game."""
    if not world.radio:
        return
    from spaceship.campaign.story import PORTRAITS, SPEAKER_COLORS

    line = world.radio[0]
    box = pygame.Rect(150, 122, WIDTH - 300, 64)          # trên cùng: không che tàu và đạn quanh tàu
    panel = pygame.Surface(box.size, pygame.SRCALPHA)
    panel.fill((8, 12, 20, 170))
    surface.blit(panel, box)
    color = SPEAKER_COLORS.get(line.speaker, WHITE)
    pygame.draw.rect(surface, color, box, 1)
    portrait = assets.image(PORTRAITS.get(line.speaker, ""), 56) if line.speaker in PORTRAITS else None
    tx = box.x + 8
    if portrait is not None:
        surface.blit(portrait, (box.x + 4, box.y + 4))
        tx = box.x + 68
    surface.blit(assets.text(line.speaker, 13, color), (tx, box.y + 6))
    for i, row in enumerate(wrap_text(assets, line.text, 14, box.right - tx - 8)[:2]):
        surface.blit(assets.text(row, 14, WHITE, bold=False), (tx, box.y + 24 + i * 18))


def wrap_text(assets, text: str, size: int, width: int, bold: bool = False):
    """Ngắt dòng theo bề rộng pixel."""
    font = assets.font(size, bold)
    rows, current = [], ""
    for word in text.split():
        trial = f"{current} {word}".strip()
        if font.size(trial)[0] <= width or not current:
            current = trial
        else:
            rows.append(current)
            current = word
    if current:
        rows.append(current)
    return rows


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
