"""Hai bảng thông tin hai bên chiến trường khi màn hình rộng (toàn màn hình 16:9, cửa sổ phóng to).

Chiến trường vẫn là khung 800x700 ở giữa (độ khó và tầm vung tay không đổi); mọi thông tin vốn vẽ đè lên
chiến trường được dời ra đây, để vùng bay thoáng hoàn toàn:

* Bảng trái - trạng thái trận: ải/chế độ, điểm, thời gian, máu, Nộ, vũ khí, tăng cường, số mạng.
* Bảng phải - điều khiển & liên lạc: ô camera tay (luôn thấy tay đang ở đâu), cử chỉ đang nhận, lời thoại.
"""
from __future__ import annotations

import math

import pygame

from spaceship import config
from spaceship.config import NEON_GREEN, NEON_ORANGE, NEON_RED, YELLOW
from spaceship.entities.items import draw_item_icon
from spaceship.input.gestures import Gesture
from spaceship.input.hand_tracker import PREVIEW_SIZE
from spaceship.ui import glow
from spaceship.ui.hud import GESTURE_LABELS, format_time
from spaceship.ui.widgets import ACCENT, FRAME, MUTED, SECONDARY, TEXT, draw_progress_ring, fit_text, wrap_text

PANEL_BG = (7, 11, 18)
PAD = 18
SEGMENTS = 10


class _Column:
    """Con trỏ vẽ từ trên xuống trong một cột: mỗi mục tự đẩy ``y`` xuống."""

    def __init__(self, surface: pygame.Surface, assets, rect: pygame.Rect) -> None:
        self.surface, self.assets = surface, assets
        self.x, self.y = rect.x + PAD, rect.y + PAD
        self.width = rect.width - 2 * PAD
        self.right = self.x + self.width

    def label(self, text: str, color=MUTED) -> None:
        img = self.assets.text(text, 13, color, role="label")
        self.surface.blit(img, (self.x, self.y))
        self.y += img.get_height() + 4

    def value(self, text: str, size: int = 18, color=TEXT, role: str = "ui") -> None:
        img = fit_text(self.assets, text, size, color, self.width, role=role)
        self.surface.blit(img, (self.x, self.y))
        self.y += img.get_height() + 2

    def gap(self, h: int = 10) -> None:
        self.y += h

    def divider(self) -> None:
        self.y += 6
        pygame.draw.line(self.surface, FRAME, (self.x, self.y), (self.right, self.y))
        self.y += 12


def _segment_bar(surface, x, y, width, ratio, color, height=12) -> None:
    ratio = max(0.0, min(1.0, ratio))
    seg_w = width / SEGMENTS
    for i in range(SEGMENTS):
        rect = pygame.Rect(round(x + i * seg_w), y, max(1, round(seg_w) - 2), height)
        pygame.draw.rect(surface, (30, 34, 42), rect)
        filled = ratio * SEGMENTS - i
        if filled > 0:
            pygame.draw.rect(surface, color, (rect.x, rect.y, rect.w * min(1.0, filled), rect.h))


def _panel_frame(surface: pygame.Surface, rect: pygame.Rect, edge: str) -> None:
    surface.fill(PANEL_BG, rect)
    x = rect.right - 1 if edge == "right" else rect.x
    pygame.draw.line(surface, FRAME, (x, rect.y), (x, rect.bottom))


def draw_status_panel(surface: pygame.Surface, assets, rect: pygame.Rect, world, director=None) -> None:
    """Bảng trái: trạng thái trận."""
    _panel_frame(surface, rect, "right")
    p, t = world.player, world.survival_time
    col = _Column(surface, assets, rect)

    logo = assets.text("SPACESHIP", 20, TEXT, role="display")
    surface.blit(logo, (col.x, col.y))
    number = assets.text("10K", 20, ACCENT, role="display")
    surface.blit(number, (col.x + logo.get_width() + 6, col.y))
    col.y += logo.get_height()
    col.divider()

    progress = director.progress_text if director is not None else ""
    if world.level is not None:
        from spaceship.campaign.story import ACTS

        act = ACTS.get(world.level.act, "").upper()
        col.label(f"{act} · CHU KỲ {world.cycle}" if world.cycle > 1 else act)
        for line in wrap_text(assets, world.level.title, 17, col.width, role="ui")[:2]:
            col.value(line, 17)
    else:
        col.label("CHẾ ĐỘ")
        col.value(world.mode.label.upper(), 17)
    if progress:
        col.value(progress, 14, SECONDARY, role="label")
    col.divider()

    col.label("ĐIỂM")
    col.value(f"{world.score:,}".replace(",", " "), 30, ACCENT, role="display")
    if world.combo >= 2:
        left = world.combo_timer / config.COMBO_WINDOW_TICKS
        col.value(f"CHUỖI {world.combo} · x{world.combo_mult}", 15, YELLOW if world.combo_mult > 1 else SECONDARY,
                  role="label")
        pygame.draw.rect(surface, (30, 34, 42), (col.x, col.y, col.width, 3))
        pygame.draw.rect(surface, YELLOW, (col.x, col.y, int(col.width * left), 3))
        col.y += 3
    if world.grazes:
        col.gap(4)
        col.value(f"SÁT ĐẠN {world.grazes}", 13, SECONDARY, role="label")
    col.gap(4)
    col.label("THỜI GIAN")
    col.value(format_time(t), 18)
    col.divider()

    ratio = p.hp / p.max_hp
    hp_color = NEON_GREEN if ratio > 0.5 else (YELLOW if ratio > 0.25 else NEON_RED)
    col.label(f"MÁU  {max(0, round(p.hp))}/{p.max_hp}")
    _segment_bar(surface, col.x, col.y, col.width, ratio, hp_color)
    col.y += 12
    col.gap(12)
    rage = p.rage / p.max_rage
    col.label("NỘ" if rage < 1 else "NỘ ĐẦY", NEON_ORANGE if rage >= 1 else MUTED)
    bar = pygame.Rect(col.x, col.y, col.width, 12)
    pygame.draw.rect(surface, (30, 34, 42), bar)
    pygame.draw.rect(surface, NEON_ORANGE, (bar.x, bar.y, bar.w * min(1.0, rage), bar.h))
    if rage >= 1:
        pulse = 0.6 + 0.4 * math.sin(t * 8)
        pygame.draw.rect(surface, glow.scale((255, 220, 120), pulse), bar.inflate(4, 4), 2)
    col.y += 12
    col.gap(6)
    skill = config.SKILL_NAMES.get(p.weapon, "")
    hint = f"{skill}: chụm tay / K" if rage >= 1 else skill
    col.value(hint, 14, NEON_ORANGE if rage >= 1 else SECONDARY, role="body")
    col.divider()

    col.label("VŨ KHÍ")
    icon_y = col.y + 18
    draw_item_icon(surface, assets, f"upgrade_{p.weapon}", col.x + 18, icon_y, t=t, size=1.1)
    name_x = col.x + 46
    surface.blit(fit_text(assets, config.WEAPON_NAMES.get(p.weapon, p.weapon).upper(), 17, p.color,
                          col.right - name_x, role="ui"), (name_x, col.y))
    for i in range(config.MAX_WEAPON_LEVEL):
        pip = pygame.Rect(name_x + i * 15, col.y + 26, 12, 8)
        if i < p.level:
            pygame.draw.rect(surface, p.color, pip)
        else:
            pygame.draw.rect(surface, (60, 64, 74), pip, 1)
    col.y += 44
    if p.bonus_damage:
        col.value(f"+{p.bonus_damage} sát thương", 13, YELLOW, role="label")
    perks = [txt for txt, on in (("DRONE + HỘ VỆ" if p.drones > 1 else "DRONE", p.drones),
                                 ("THIÊU ĐỐT", p.burn_unlocked)) if on]
    if p.shield_active:
        perks.append(f"KHIÊN {p.shield_timer / config.TICK_RATE:.1f}s")
    if perks:
        col.gap(4)
        col.value(" · ".join(perks), 13, YELLOW if not p.shield_active else ACCENT, role="label")

    # Số mạng: luôn ở đáy bảng
    y = rect.bottom - PAD - 26
    surface.blit(assets.text("MẠNG", 12, MUTED, role="label"), (col.x, y + 6))
    for i in range(p.lives):
        hx = col.x + 66 + i * 28
        pygame.draw.polygon(surface, NEON_GREEN, [(hx, y), (hx - 9, y + 18), (hx, y + 14), (hx + 9, y + 18)], 2)


def _draw_camera(surface, assets, game, col: _Column) -> None:
    col.label("CAMERA TAY")
    height = round(col.width * PREVIEW_SIZE[1] / PREVIEW_SIZE[0])
    box = pygame.Rect(col.x, col.y, col.width, height)
    image = game.camera_surface((box.width, box.height)) if game.show_camera else None
    if image is not None:
        surface.blit(image, box)
        pygame.draw.rect(surface, config.NEON_CYAN, box, 1)
        status = f"{game.tracker.fps:.0f} fps"
    else:
        pygame.draw.rect(surface, (12, 18, 28), box)
        pygame.draw.rect(surface, FRAME, box, 1)
        if game.tracker is None:
            message = "Đang chơi bằng bàn phím"
        elif not game.show_camera:
            message = "Đã ẩn (phím C)"
        else:
            message = game.tracker.message or "Đang mở camera..."
        for i, line in enumerate(wrap_text(assets, message, 13, box.width - 16, role="body")[:3]):
            img = assets.text(line, 13, MUTED, role="body")
            surface.blit(img, img.get_rect(center=(box.centerx, box.centery - 9 + i * 17)))
        status = ""
    col.y = box.bottom + 4
    if status:
        img = assets.text(status, 11, MUTED, role="label")
        surface.blit(img, img.get_rect(topright=(col.right, col.y)))
    col.y += 14


def _draw_gesture(surface, assets, controls, rage_full: bool, col: _Column) -> None:
    source = "TAY" if controls is not None and controls.source == "hand" else "BÀN PHÍM"
    col.label(f"ĐIỀU KHIỂN: {source}")
    if controls is None:
        return
    center = (col.x + 13, col.y + 12)
    if controls.hand_absent > 0.3:
        ratio = min(1.0, controls.hand_absent / config.HAND_PAUSE_SECONDS)
        col.value("Mất tay - sắp nghỉ", 14, YELLOW, role="body")
        pygame.draw.rect(surface, FRAME, (col.x, col.y + 2, col.width, 5), 1)
        pygame.draw.rect(surface, YELLOW, (col.x, col.y + 2, col.width * ratio, 5))
        col.y += 12
        return
    if controls.gesture == Gesture.NONE:
        col.value("Không thấy tay" if source == "TAY" else "WASD · Shift · K", 14, MUTED, role="body")
        return
    label, color = GESTURE_LABELS.get(controls.gesture, ("XÒE TAY: LÁI", TEXT))
    progress = 0.0
    if controls.gesture == Gesture.PINCH:
        if rage_full:
            progress = controls.skill_progress
        else:
            label, color = "CHỤM: NỘ CHƯA ĐẦY", MUTED
    else:
        pygame.draw.circle(surface, color, center, 4)
    draw_progress_ring(surface, center, 11, progress, color=color, stroke=3)
    img = fit_text(assets, label, 14, color, col.width - 34, role="label")
    surface.blit(img, img.get_rect(midleft=(col.x + 32, center[1])))
    col.y += 28


def _draw_radio(surface, assets, world, col: _Column, bottom: int) -> None:
    from spaceship.campaign.story import PORTRAITS, SPEAKER_COLORS

    col.label("LIÊN LẠC")
    if not world.radio:
        col.value("Không có tín hiệu", 14, MUTED, role="body")
        return
    line = world.radio[0]
    color = SPEAKER_COLORS.get(line.speaker, TEXT)
    portrait = assets.image(PORTRAITS.get(line.speaker, ""), 64) if line.speaker in PORTRAITS else None
    if portrait is not None:
        surface.blit(portrait, (col.x, col.y))
        pygame.draw.rect(surface, color, (col.x, col.y, 64, 64), 1)
    speaker = fit_text(assets, line.speaker.upper(), 16, color, col.width - 74, role="ui")
    surface.blit(speaker, (col.x + 74, col.y + 22))
    col.y += 74
    rows = wrap_text(assets, line.text, 15, col.width, role="body")
    max_rows = max(1, (bottom - col.y) // 20)
    for row in rows[:max_rows]:
        surface.blit(assets.text(row, 15, TEXT, role="body"), (col.x, col.y))
        col.y += 20


def draw_control_panel(surface: pygame.Surface, assets, rect: pygame.Rect, game, world, controls) -> None:
    """Bảng phải: camera tay, cử chỉ đang nhận, lời thoại."""
    _panel_frame(surface, rect, "left")
    col = _Column(surface, assets, rect)
    _draw_camera(surface, assets, game, col)
    col.gap(4)
    _draw_gesture(surface, assets, controls, world.player.rage_full, col)
    col.divider()
    _draw_radio(surface, assets, world, col, rect.bottom - PAD)
