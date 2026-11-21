"""Các trang hướng dẫn và lưới Sổ tay chiến đấu."""
from __future__ import annotations

import pygame

from spaceship import config
from spaceship.campaign.bestiary import BESTIARY
from spaceship.campaign.levels import LEVEL_COUNT
from spaceship.campaign.story import ACTS
from spaceship.config import GameMode
from spaceship.entities.items import draw_item_icon
from spaceship.ui.guide_preview import draw_hand_demo
from spaceship.ui.widgets import (
    ACCENT, CORNER, DANGER, LOCKED, MUTED, PANEL_FILL, SECONDARY, SELECTED_FILL, TEXT,
    blit_center, draw_lock, draw_panel, fit_text, wrap_text,
)

CONTROL_CARDS = (
    ("steer", "LÁI TÀU", "Di lòng bàn tay để lái. Tì khuỷu tay lên bàn cho đỡ mỏi.", "WASD"),
    ("focus", "NÉ CHẬM", "Nắm tay để bay chậm và hiện điểm va chạm khi né đạn.", "SHIFT"),
    ("skill", "KỸ NĂNG NỘ", "Chụm ngón cái và trỏ, giữ 0,5 giây khi thanh Nộ đầy.", "K"),
    ("rest", "NGHỈ TAY", "Bỏ tay khỏi khung để tạm dừng. Đưa tay lên để đếm 3–2–1.", "ESC"),
)
WEAPON_CARDS = {
    "plasma": ("Quét đông", "Đạn nổ lan"),
    "laser": ("Diệt boss", "Tia xuyên liên tục"),
    "homing": ("An toàn, tự đuổi", "7 tên lửa xoắn ốc"),
    "lightning": ("Nhảy dây chuyền", "Nhảy 8 mục tiêu"),
}
ITEM_CARDS = (
    ("heal", "HỒI MÁU", f"Hồi {config.HEAL_AMOUNT[GameMode.CAMPAIGN]} HP. Hỏa ngục: {config.HEAL_AMOUNT[GameMode.INFERNO]} HP."),
    ("shield", "KHIÊN", f"Bất tử {config.SHIELD_TICKS[GameMode.CAMPAIGN] / config.TICK_RATE:g} giây. Húc chết địch thường."),
    ("upgrade_plasma", "PLASMA", "Đạn tỏa rộng để quét bầy."),
    ("upgrade_laser", "LASER", "Tia đạn mạnh để diệt boss."),
    ("upgrade_homing", "HOMING", "Tên lửa tự đuổi mục tiêu."),
    ("upgrade_lightning", "TIA SÉT", "Đánh dây chuyền qua nhiều địch."),
    ("upgrade_universal", "UNIVERSAL", "Nâng cấp súng đang cầm."),
    ("upgrade_drone", "DRONE", "Ải 3: drone tự ngắm bắn. Ải 9: drone hộ vệ bắn hạ đạn địch."),
    ("upgrade_burn", "THIÊU ĐỐT", f"Đạn gây cháy {config.BURN_DAMAGE_PER_SECOND} HP/s. Thưởng ải 7."),
)


def _grid(area: pygame.Rect, cols: int, rows: int, gap_x: int, gap_y: int) -> tuple[pygame.Rect, ...]:
    w = (area.width - (cols - 1) * gap_x) // cols
    h = (area.height - (rows - 1) * gap_y) // rows
    return tuple(pygame.Rect(area.x + col * (w + gap_x), area.y + row * (h + gap_y), w, h)
                 for row in range(rows) for col in range(cols))


def _paragraph(surface, assets, text, pos, width, *, size=16, line_height=21, color=SECONDARY, role="body") -> int:
    x, y = pos
    for line in wrap_text(assets, text, size, width, role=role):
        surface.blit(assets.text(line, size, color, role=role), (x, y))
        y += line_height
    return y


def draw_controls(surface, assets, body: pygame.Rect, seconds: float) -> None:
    for box, (action, label, description, key) in zip(_grid(body, 2, 2, 20, 16), CONTROL_CARDS):
        draw_panel(surface, box, ACCENT)
        draw_hand_demo(surface, pygame.Rect(box.x + 10, box.y + 22, 148, box.height - 34), action, seconds)
        x = box.x + 170
        width = box.right - 16 - x
        surface.blit(fit_text(assets, label, 22, ACCENT, width, role="ui"), (x, box.y + 18))
        _paragraph(surface, assets, description, (x, box.y + 59), width)
        y = box.bottom - 47
        surface.blit(assets.text("BÀN PHÍM", 14, MUTED, role="label"), (x, y - 19))
        label = assets.text(key, 15, (11, 20, 30), role="ui")
        keycap = pygame.Rect(x, y, label.get_width() + 18, 27)
        pygame.draw.rect(surface, TEXT, keycap, border_radius=4)
        surface.blit(label, label.get_rect(center=keycap.center))


def draw_weapons(surface, assets, body: pygame.Rect, previews) -> None:
    area = pygame.Rect(body.x, body.y, body.width, body.height - 48)
    line_color = (40, 61, 76)
    for box, (weapon, (purpose, upgrade)) in zip(_grid(area, 2, 2, 20, 16), WEAPON_CARDS.items()):
        draw_panel(surface, box, ACCENT)
        preview = pygame.Rect(box.x + 14, box.centery - 55, 150, 110)
        draw_panel(surface, preview.inflate(4, 4))
        previews[weapon].draw(surface, assets, preview)
        x = preview.right + 16
        right = box.right - 16
        width = right - x
        # Mọi dòng dựng sẵn rồi xếp dọc với khoảng cách đều, cả khối căn giữa theo chiều dọc của thẻ.
        damage_label = assets.text("SÁT THƯƠNG GỐC", 13, MUTED, role="label")
        damage_value = assets.text(str(config.WEAPON_BASE_DAMAGE[weapon]), 17, TEXT, role="ui")
        lines = [
            (assets.text(config.WEAPON_NAMES[weapon], 23, ACCENT, role="ui"), 0),
            (fit_text(assets, purpose, 15, SECONDARY, width, role="body"), 1),
            (None, 9),                                                  # đường kẻ
            ("damage", 9),
            (assets.text("DẠNG CẤP 6", 13, MUTED, role="label"), 10),
            (fit_text(assets, upgrade, 15, TEXT, width, role="body"), 2),
            (assets.text("KỸ NĂNG NỘ", 13, MUTED, role="label"), 10),
            (fit_text(assets, config.SKILL_NAMES[weapon].upper(), 16, TEXT, width, role="ui"), 2),
        ]
        heights = {None: 1, "damage": max(damage_label.get_height(), damage_value.get_height())}
        total = sum(gap + heights.get(img, 0) if not isinstance(img, pygame.Surface) else gap + img.get_height()
                    for img, gap in lines)
        y = box.centery - total // 2
        for img, gap in lines:
            y += gap
            if img is None:
                pygame.draw.line(surface, line_color, (x, y), (right, y))
                y += 1
            elif img == "damage":
                h = heights["damage"]
                surface.blit(damage_label, damage_label.get_rect(midleft=(x, y + h // 2)))
                surface.blit(damage_value, damage_value.get_rect(midright=(right, y + h // 2)))
                y += h
            else:
                surface.blit(img, (x, y))
                y += img.get_height()

    pickup = "Nhặt cùng loại: lên cấp (tối đa 6) · Khác loại: đổi súng, về cấp 1"
    blit_center(surface, assets.text(pickup, 15, TEXT, role="body"), body.bottom - 42)
    fire = "Tự động bắn mặc định. Khi tắt: giơ ngón trỏ hoặc giữ Space / J."
    blit_center(surface, assets.text(fire, 15, MUTED, role="body"), body.bottom - 18)


def draw_items(surface, assets, body: pygame.Rect, seconds: float) -> None:
    grid = pygame.Rect(body.x, body.y, body.width, 352)
    for i, (box, (kind, title, description)) in enumerate(zip(_grid(grid, 3, 3, 12, 12), ITEM_CARDS)):
        draw_panel(surface, box)
        draw_item_icon(surface, assets, kind, box.x + 34, box.centery, t=seconds + i * .07, size=1.1)
        x = box.x + 69
        width = box.right - 11 - x
        surface.blit(fit_text(assets, title, 18, TEXT, width, role="ui"), (x, box.y + 16))
        _paragraph(surface, assets, description, (x, box.y + 46), width, size=15, line_height=18)

    example = pygame.Rect(body.x, grid.bottom + 15, body.width, 99)
    draw_panel(surface, example, DANGER, header_height=28)
    surface.blit(assets.text("CẢNH BÁO ĐỔI SÚNG", 15, DANGER, role="label"), (example.x + 13, example.y + 3))
    mid_y = example.y + 62
    held = assets.text("Đang cầm LASER", 16, TEXT, role="body")
    surface.blit(held, held.get_rect(midleft=(example.x + 16, mid_y)))
    arrow = assets.text("→", 22, MUTED, role="label")
    surface.blit(arrow, arrow.get_rect(center=(example.x + 162, mid_y)))
    draw_item_icon(surface, assets, "upgrade_plasma", example.x + 202, mid_y, t=seconds, warn=True)
    _paragraph(surface, assets, "Hộp Plasma nháy viền đỏ kèm dấu !. Nhặt vào sẽ đổi súng và về cấp 1.",
               (example.x + 236, example.y + 41), example.width - 250, size=16)
    reward = "Phần thưởng boss (Drone, Thiêu đốt) tự bay vào tàu."
    blit_center(surface, assets.text(reward, 15, SECONDARY, role="body"), body.bottom - 23)


def draw_modes(surface, assets, body: pygame.Rect, campaign_cleared: bool) -> None:
    details = (
        (f"{LEVEL_COUNT} ải, {len(ACTS)} hồi, có cốt truyện. Chọn độ khó Dễ, Thường hoặc Khó.",
         "1 sao: qua ải · 2 sao: mất tối đa 1 mạng · 3 sao: không mất mạng nào."),
        ("Sống sót càng lâu càng tốt. Độ khó tăng dần và càng về sau càng nhiều loại địch.",
         f"Boss đổi loại sau mỗi {config.ENDLESS_BOSS_INTERVAL:g} giây."),
        (f"Mưa đạn, ít máu, không rơi khiên. Boss xuất hiện sau mỗi {config.INFERNO_BOSS_INTERVAL:g} giây.",
         "Mở khóa sau khi phá đảo Vượt ải."),
    )
    for box, mode, (description, note) in zip(_grid(body, 1, 3, 0, 16), GameMode, details):
        locked = mode is GameMode.INFERNO and not campaign_cleared
        corner = DANGER if locked else ACCENT
        draw_panel(surface, box, corner, header_height=49)
        surface.blit(assets.text(mode.label, 25, MUTED if locked else ACCENT, role="display"),
                     (box.x + 17, box.y + 7))
        if locked:
            tag = assets.text("ĐANG KHÓA", 14, DANGER, role="label")
            tag_rect = tag.get_rect(midright=(box.right - 16, box.y + 25))
            draw_lock(surface, (tag_rect.x - 16, tag_rect.centery), DANGER)
            surface.blit(tag, tag_rect)
        y = _paragraph(surface, assets, description, (box.x + 17, box.y + 65), box.width - 34, size=17)
        _paragraph(surface, assets, note, (box.x + 17, y + 9), box.width - 34, size=16, color=MUTED)


class BestiaryView:
    def __init__(self, body: pygame.Rect) -> None:
        self.body = body
        self.keys = tuple(BESTIARY)
        self.selected = 0
        height = body.height - 44
        grid = pygame.Rect(body.x, body.y + 44, 424, height)
        self.cards = _grid(grid, 3, (len(self.keys) + 2) // 3, 8, 8)[:len(self.keys)]
        x = grid.right + 16
        self.detail = pygame.Rect(x, grid.y, body.right - x, height)
        self._silhouettes: dict[tuple[str, int], pygame.Surface] = {}

    def _sprite(self, assets, name: str, box: pygame.Rect, locked: bool):
        raw = assets.raw(name)
        if raw is None:
            return None
        width = min(box.width, max(1, box.height * raw.get_width() // raw.get_height()))
        image = assets.image(name, width)
        if not locked:
            return image
        key = name, width
        if key not in self._silhouettes:
            shadow = image.copy()
            shadow.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MULT)
            self._silhouettes[key] = shadow
        return self._silhouettes[key]

    def _draw_sprite(self, surface, assets, name: str, box: pygame.Rect, locked: bool) -> None:
        sprite = self._sprite(assets, name, box, locked)
        if sprite is not None:
            surface.blit(sprite, sprite.get_rect(center=box.center))

    def draw(self, surface, assets, seen: set[str], focus: int) -> None:
        body = self.body
        surface.blit(assets.text("SỔ TAY CHIẾN ĐẤU", 25, TEXT, role="display"), (body.x, body.y - 4))
        count = assets.text(f"{len(BESTIARY.keys() & seen)} / {len(self.keys)} đã gặp", 15, MUTED, role="label")
        surface.blit(count, count.get_rect(topright=(body.right, body.y + 8)))
        for i, (box, key) in enumerate(zip(self.cards, self.keys)):
            entry = BESTIARY[key]
            locked = key not in seen
            highlighted = i in (focus, self.selected)
            fill = SELECTED_FILL if highlighted else (24, 37, 50, 238) if locked else PANEL_FILL
            draw_panel(surface, box, ACCENT if highlighted else LOCKED if locked else CORNER, fill)
            image_box = pygame.Rect(box.x + 10, box.y + 4, box.width - 20, 45)
            self._draw_sprite(surface, assets, entry.sprite, image_box, locked)
            lines = wrap_text(assets, "???" if locked else entry.name, 12, box.width - 12, role="label")
            y = box.bottom - 6 - 14 * len(lines)
            for j, label in enumerate(lines):
                blit_center(surface, assets.text(label, 13, MUTED if locked else TEXT, role="label"),
                            y + 14 * j, box.centerx)
        self._draw_detail(surface, assets, seen)

    def _draw_detail(self, surface, assets, seen: set[str]) -> None:
        key = self.keys[self.selected]
        entry = BESTIARY[key]
        locked = key not in seen
        box = self.detail
        draw_panel(surface, box, LOCKED if locked else ACCENT, header_height=33)
        x, width = box.x + 15, box.width - 30
        surface.blit(assets.text("CHƯA GẶP" if locked else "ĐÃ GẶP", 15, MUTED if locked else ACCENT, role="label"),
                     (x, box.y + 6))
        _paragraph(surface, assets, "???" if locked else entry.name, (x, box.y + 43), width,
                   size=22, line_height=25, color=TEXT, role="display")
        picture = pygame.Rect(x, box.y + 113, width, 112)
        pygame.draw.rect(surface, (23, 34, 46), picture.inflate(6, 8), border_radius=4)
        self._draw_sprite(surface, assets, entry.sprite, picture.inflate(-14, -14), locked)
        y = box.y + 250
        if locked:
            _paragraph(surface, assets, "Gặp kẻ địch này trong trận để mở mô tả và mẹo đánh.", (x, y), width)
            return
        y = _paragraph(surface, assets, entry.description, (x, y), width)
        surface.blit(assets.text("MẸO ĐÁNH", 14, ACCENT, role="label"), (x, y + 12))
        _paragraph(surface, assets, entry.tip, (x, y + 35), width, color=TEXT)
