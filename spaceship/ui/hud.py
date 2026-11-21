"""Thanh thông tin trong trận: điểm, máu, nộ, mạng, trạng thái điều khiển."""
from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

import pygame

from spaceship import config
from spaceship.config import HEIGHT, NEON_GREEN, NEON_ORANGE, NEON_RED, WIDTH, YELLOW
from spaceship.input.gestures import Gesture
from spaceship.entities.items import draw_item_icon
from spaceship.systems.world import World
from spaceship.ui import glow
from spaceship.ui.widgets import ACCENT, FRAME, MUTED, TEXT, draw_panel, draw_progress_ring, fit_text, wrap_text

GESTURE_LABELS = {
    Gesture.FIST: ("NẮM TAY: NÉ CHẬM", ACCENT),
    Gesture.PINCH: ("CHỤM: KỸ NĂNG NỘ", NEON_ORANGE),
}

HUD_FILL = (8, 15, 25, 194)
ENCOUNTER_WIDTH, ENCOUNTER_HEIGHT = 380, 56


def format_time(seconds: float) -> str:
    seconds = int(seconds)
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


SEGMENTS = 10


def _weapon_panel(surface, assets, p, cx, cy, t) -> None:
    """Biểu tượng súng + 6 vạch cấp + sát thương cộng thêm."""
    draw_item_icon(surface, assets, f"upgrade_{p.weapon}", cx, cy, t=t, size=1.1)
    x = cx + 26
    name = config.WEAPON_NAMES.get(p.weapon, p.weapon).upper()
    surface.blit(assets.text(name, 14, p.color, role="ui"), (x, cy - 18))
    for i in range(config.MAX_WEAPON_LEVEL):
        rect = pygame.Rect(x + i * 13, cy + 2, 10, 8)
        if i < p.level:
            pygame.draw.rect(surface, p.color, rect)
        else:
            pygame.draw.rect(surface, (60, 64, 74), rect, 1)
    if p.bonus_damage:
        surface.blit(assets.text(f"+{p.bonus_damage} DMG", 12, YELLOW, role="label"), (x + 82, cy - 2))


STRIP_H = 34                     # dải mảnh trên cùng: điểm · ải · wave
CORNER_FILL = (6, 12, 20, 168)


@lru_cache(maxsize=4)
def _top_strip(width: int) -> pygame.Surface:
    strip = pygame.Surface((width, STRIP_H + 14), pygame.SRCALPHA)
    for y in range(STRIP_H + 14):
        alpha = 170 if y < STRIP_H - 6 else int(170 * (1 - (y - STRIP_H + 6) / 20))
        pygame.draw.line(strip, (4, 8, 14, max(0, alpha)), (0, y), (width, y))
    return strip


def _status_line(world: World, director) -> str:
    progress = director.progress_text if director is not None else ""
    score = f"ĐIỂM {world.score:,}".replace(",", " ")
    if world.combo_mult > 1:
        score += f" x{world.combo_mult}"
    if world.level is not None:
        cycle = f"CHU KỲ {world.cycle} · " if world.cycle > 1 else ""
        parts = [score, f"{cycle}ẢI {world.level.number}", progress]
    else:
        parts = [score, format_time(world.survival_time), progress]
    return "  ·  ".join(x for x in parts if x)


_LAYER: list = []


def _corner_layer() -> pygame.Surface:
    if not _LAYER:
        _LAYER.append(pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA))
    layer = _LAYER[0]
    layer.fill((0, 0, 0, 0))
    return layer


def _corner_box(surface, rect: pygame.Rect, color=FRAME) -> None:
    surface.fill(CORNER_FILL, rect)
    pygame.draw.rect(surface, color, rect, 1)


def draw_hud(surface: pygame.Surface, assets, world: World, controls=None, director=None) -> None:
    """HUD gọn 4 góc (cửa sổ thường): dải mảnh trên cùng, máu/Nộ/mạng góc dưới trái, vũ khí góc dưới phải.
    Chiến trường ở giữa để trống; thanh boss nằm ngay dưới dải trên."""
    p, t = world.player, world.survival_time
    surface.blit(_top_strip(WIDTH), (0, 0))
    line = fit_text(assets, _status_line(world, director), 18, TEXT, WIDTH - 40, role="ui")
    surface.blit(line, (14, 7))
    screen, surface = surface, _corner_layer()           # 2 ô góc vẽ lên lớp riêng để làm mờ khi tàu bay sát

    # --- Góc dưới trái: mạng + cử chỉ tay, máu, Nộ ---------------------------------------------
    full = p.rage_full
    block = pygame.Rect(10, HEIGHT - (100 if full else 80) - 10, 236, 100 if full else 80)
    _corner_box(surface, block, NEON_ORANGE if full else FRAME)
    x, y = block.x + 10, block.y + 8
    for i in range(p.lives):
        hx = x + 8 + i * 20
        pygame.draw.polygon(surface, NEON_GREEN, [(hx, y), (hx - 7, y + 14), (hx, y + 11), (hx + 7, y + 14)], 2)
    if controls is not None:
        _hand_status(surface, assets, controls, full, block.right - 10, y + 7)
    ratio = max(0.0, min(1.0, p.hp / p.max_hp))
    hp_color = NEON_GREEN if ratio > 0.5 else (YELLOW if ratio > 0.25 else NEON_RED)
    surface.blit(assets.text("HP", 14, MUTED, role="label"), (x, y + 23))
    seg_w = (block.width - 54) / SEGMENTS
    for i in range(SEGMENTS):
        seg = pygame.Rect(x + 34 + i * seg_w, y + 25, seg_w - 2, 12)
        pygame.draw.rect(surface, (30, 34, 42), seg)
        filled = ratio * SEGMENTS - i
        if filled > 0:
            pygame.draw.rect(surface, hp_color, (seg.x, seg.y, seg.w * min(1.0, filled), seg.h))
    surface.blit(assets.text("NỘ", 14, NEON_ORANGE if full else MUTED, role="label"), (x, y + 44))
    bar = pygame.Rect(x + 34, y + 46, block.width - 54, 12)
    pygame.draw.rect(surface, (30, 34, 42), bar)
    pygame.draw.rect(surface, NEON_ORANGE, (bar.x, bar.y, bar.w * min(1.0, p.rage / p.max_rage), bar.h))
    if full:
        pulse = 0.6 + 0.4 * math.sin(t * 8)
        pygame.draw.rect(surface, glow.scale((255, 220, 120), pulse), bar.inflate(4, 4), 2)
        hint = f"{config.SKILL_NAMES.get(p.weapon, '')} · chụm tay / K"
        surface.blit(fit_text(assets, hint, 15, NEON_ORANGE, block.width - 20, role="body"), (x, y + 64))

    # --- Góc dưới phải: vũ khí + tăng cường ----------------------------------------------------
    perks = []
    if p.drones:
        perks.append("DRONE + HỘ VỆ" if p.drones > 1 else "DRONE")
    if p.burn_unlocked:
        perks.append("THIÊU ĐỐT")
    if p.shield_active:
        perks.append(f"KHIÊN {p.shield_timer / config.TICK_RATE:.1f}s")
    wbox = pygame.Rect(WIDTH - 216, HEIGHT - (80 if perks else 60) - 10, 206, 80 if perks else 60)
    _corner_box(surface, wbox)
    _weapon_panel(surface, assets, p, wbox.x + 28, wbox.y + 30, t)
    if perks:
        text = fit_text(assets, " · ".join(perks), 13, ACCENT if p.shield_active else YELLOW, wbox.width - 20, role="label")
        surface.blit(text, (wbox.x + 10, wbox.bottom - 22))

    ship = pygame.Rect(0, 0, 90, 80)
    ship.center = (int(p.x), int(p.y))
    for rect in (block, wbox):
        piece = surface.subsurface(rect).copy()
        piece.set_alpha(70 if rect.inflate(16, 16).colliderect(ship) else 255)
        screen.blit(piece, rect)
    draw_boss_bar(screen, assets, world, y=56)


def _hand_status(surface, assets, controls, rage_full: bool, right: int, cy: int) -> None:
    """Cử chỉ tay đang nhận (canh phải trong ô góc dưới trái); vòng tròn đầy dần khi giữ chụm ngón."""
    if controls.hand_absent > 0.3:
        label, color, progress = "MẤT TAY - SẮP NGHỈ", YELLOW, min(1.0, controls.hand_absent / config.HAND_PAUSE_SECONDS)
    elif controls.gesture == Gesture.NONE:
        return
    else:
        label, color = GESTURE_LABELS.get(controls.gesture, ("TAY: LÁI", TEXT))
        progress = 0.0
        if controls.gesture == Gesture.PINCH:
            if rage_full:
                progress = controls.skill_progress
            else:
                label, color = "NỘ CHƯA ĐẦY", MUTED
    text = assets.text(label, 13, color, role="label")
    rect = text.get_rect(midright=(right, cy))
    surface.blit(text, rect)
    draw_progress_ring(surface, (rect.x - 12, cy), 8, progress, color=color, stroke=2)


def draw_boss_bar(surface, assets, world: World, y: int = 92) -> None:
    boss = next((e for e in world.enemies if e.is_boss), None)
    if boss is not None:
        _boss_bar(surface, assets, boss, y)


def _boss_bar(surface, assets, boss, y: int = 92) -> None:
    """Thanh máu boss lớn ở giữa trên màn hình, kèm tên và khiên."""
    w, x = 360, WIDTH // 2 - 180
    name = assets.text(boss.title, 14, NEON_RED, role="label")
    surface.blit(name, (WIDTH // 2 - name.get_width() // 2, y - 18))
    pygame.draw.rect(surface, (40, 10, 14), (x, y, w, 10))
    pygame.draw.rect(surface, NEON_RED, (x, y, w * boss.hp_ratio, 10))
    for k in (0.33, 0.66):                                      # vạch chia 3 pha
        pygame.draw.line(surface, (255, 255, 255), (x + w * k, y), (x + w * k, y + 9), 1)
    if boss.shield_hp > 0:
        pygame.draw.rect(surface, (120, 200, 255), (x, y + 12, w * min(1.0, boss.shield_hp / max(1, boss.max_shield)), 4))
    pygame.draw.rect(surface, FRAME, (x, y, w, 10), 1)


def draw_banner(surface, assets, world: World, director=None) -> None:
    """Chữ lớn giữa màn hình: tên ải lúc mở màn, cảnh báo boss, phần thưởng..."""
    text, size, color = "", 40, ACCENT
    if director is not None and director.banner_text:
        text, size = director.banner_text, 36
    elif world.banner_ticks > 0:
        text, size, color = world.banner, 34, YELLOW
    if not text:
        return
    label = fit_text(assets, text, size, color, WIDTH - 40, role="display")
    y = HEIGHT // 2 - 90
    shade = pygame.Surface((WIDTH, label.get_height() + 24), pygame.SRCALPHA)
    shade.fill((0, 0, 0, 120))
    surface.blit(shade, (0, y - 12))
    surface.blit(label, (WIDTH // 2 - label.get_width() // 2, y))
    if director is not None and director.banner_text and world.level is not None:
        from spaceship.campaign.story import ACTS
        act = assets.text(ACTS.get(world.level.act, ""), 16, MUTED, role="label")
        surface.blit(act, (WIDTH // 2 - act.get_width() // 2, y - 30))


def draw_radio(surface, assets, world: World) -> None:
    """Thoại trong trận: chân dung nhỏ + lời thoại ngay dưới dải trên, không dừng game."""
    if not world.radio:
        return
    from spaceship.campaign.story import PORTRAITS, SPEAKER_COLORS

    line = world.radio[0]
    top = 84 if any(e.is_boss for e in world.enemies) else 44
    box = pygame.Rect(150, top, WIDTH - 300, 64)          # trên cùng: không che tàu và đạn quanh tàu
    color = SPEAKER_COLORS.get(line.speaker, TEXT)
    draw_panel(surface, box, color, HUD_FILL, header_height=22)
    portrait = assets.image(PORTRAITS.get(line.speaker, ""), 56) if line.speaker in PORTRAITS else None
    tx = box.x + 8
    if portrait is not None:
        surface.blit(portrait, (box.x + 4, box.y + 4))
        tx = box.x + 68
    surface.blit(assets.text(line.speaker.upper(), 13, color, role="label"), (tx, box.y + 3))
    for i, row in enumerate(wrap_text(assets, line.text, 14, box.right - tx - 8)[:2]):
        surface.blit(assets.text(row, 14, TEXT, role="body"), (tx, box.y + 24 + i * 18))


@dataclass(frozen=True)
class Toast:
    """Thẻ thông báo nhỏ góc phải trên (dùng chung với thẻ ĐỊCH MỚI)."""
    title: str
    name: str
    tip: str
    color: tuple = YELLOW


def draw_encounter(surface: pygame.Surface, assets, entry, y: int) -> None:
    """Thẻ góc phải: ĐỊCH MỚI (mục Sổ tay) hoặc THÀNH TỰU MỚI (Toast)."""
    color = getattr(entry, "color", ACCENT)
    box = pygame.Rect(WIDTH - ENCOUNTER_WIDTH - 14, y, ENCOUNTER_WIDTH, ENCOUNTER_HEIGHT)
    draw_panel(surface, box, color, header_height=27)
    title = fit_text(assets, f"{getattr(entry, 'title', 'ĐỊCH MỚI')} · {entry.name}", 16, color, box.width - 24, role="ui")
    tip = fit_text(assets, entry.tip, 14, TEXT, box.width - 24, role="body")
    surface.blit(title, (box.x + 12, box.y + 2))
    surface.blit(tip, (box.x + 12, box.y + 31))
