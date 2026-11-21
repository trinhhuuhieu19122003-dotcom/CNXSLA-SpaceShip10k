"""Hai màn thông tin tĩnh: Hướng dẫn chơi và Thành tựu.

Bản cũ vẽ panel rộng 840px và 860px trên màn hình 800px nên bị cắt mép;
giờ panel rộng 760px, nội dung lấy từ ``config`` để không bao giờ lệch với game.
"""
from __future__ import annotations

import pygame

from spaceship import config
from spaceship.config import (
    HOMING_COLOR,
    NEON_CYAN,
    NEON_GREEN,
    NEON_ORANGE,
    NEON_RED,
    WHITE,
    WIDTH,
    YELLOW,
    GameMode,
)
from spaceship.core.scene import Scene
from spaceship.entities.items import draw_item_icon
from spaceship.ui.hud import format_time
from spaceship.ui.widgets import blit_center, draw_back_hint, draw_panel

PANEL = pygame.Rect(20, 50, WIDTH - 40, 600)


class _InfoScene(Scene):
    music = "menu"

    def handle_event(self, event) -> None:
        from spaceship.scenes.menu import MenuScene

        back = (event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_RETURN)) or \
               (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1)
        if back:
            self.game.change_scene(MenuScene(self.game))

    def update(self, controls) -> None:
        self.game.starfield.update()

    def draw_frame(self, surface: pygame.Surface, title: str) -> None:
        surface.fill((0, 0, 0))
        self.game.starfield.draw(surface)
        draw_panel(surface, PANEL)
        blit_center(surface, self.game.assets.text(title, 36, YELLOW), PANEL.y + 15)
        draw_back_hint(surface, self.game.assets, PANEL.bottom - 32)


class HowToPlayScene(_InfoScene):
    def draw(self, surface: pygame.Surface) -> None:
        a = self.game.assets
        self.draw_frame(surface, "HƯỚNG DẪN CHI TIẾT")
        left, right, top = PANEL.x + 25, PANEL.x + 400, PANEL.y + 80

        surface.blit(a.text("[ ĐIỀU KHIỂN ]", 18, NEON_CYAN), (left, top))
        controls = [
            ("Lòng bàn tay", "Lái tàu, tì khuỷu tay lên bàn"),
            ("Tự động bắn", "Tàu tự bắn (tắt trong Cài đặt)"),
            ("Chụm cái + trỏ", "Giữ 0,5 giây: kỹ năng Nộ"),
            ("Nắm tay", "Né chậm, hiện điểm va chạm"),
            ("Bỏ tay xuống", "Tự tạm dừng để nghỉ tay"),
            ("Phím", "WASD · J bắn · K Nộ · Shift né"),
            ("ESC · F11 · C", "Dừng · toàn màn hình · camera"),
        ]
        for i, (key, desc) in enumerate(controls):
            y = top + 32 + i * 27
            surface.blit(a.text(key, 15, YELLOW), (left, y))
            surface.blit(a.text(desc, 14, WHITE, bold=False), (left + 130, y))

        mode_y = top + 265
        surface.blit(a.text("[ CHẾ ĐỘ CHƠI ]", 18, NEON_ORANGE), (left, mode_y))
        modes = [
            ("VƯỢT ẢI", "10 ải, 3 hồi, có cốt truyện.", NEON_CYAN),
            ("VÔ TẬN", f"Sống sót. Boss mỗi {config.ENDLESS_BOSS_INTERVAL:.0f}s.", NEON_GREEN),
            ("HỎA NGỤC", "Mở khóa khi phá đảo Vượt ải.", NEON_RED),
        ]
        for i, (name, desc, color) in enumerate(modes):
            y = mode_y + 32 + i * 27
            surface.blit(a.text(name, 15, color), (left, y))
            surface.blit(a.text(desc, 15, WHITE, bold=False), (left + 125, y))

        surface.blit(a.text("[ VẬT PHẨM ]", 18, NEON_ORANGE), (right, top))
        dmg = config.WEAPON_BASE_DAMAGE
        heal = config.HEAL_AMOUNT[GameMode.CAMPAIGN]
        shield = config.SHIELD_TICKS[GameMode.CAMPAIGN] / config.TICK_RATE
        items = [
            ("heal", f"Hồi {heal} máu"),
            ("shield", f"Khiên bảo vệ {shield:.0f} giây"),
            ("upgrade_plasma", f"Plasma {dmg['plasma']} · tỏa rộng · Nộ: Vòng Plasma"),
            ("upgrade_laser", f"Laser {dmg['laser']} · diệt boss · Nộ: Đại Pháo"),
            ("upgrade_homing", f"Homing {dmg['homing']} · tự đuổi · Nộ: Mưa Tên Lửa"),
            ("upgrade_lightning", f"Tia Sét {dmg['lightning']} · nhảy dây · Nộ: Bão Sét"),
            ("upgrade_universal", "Nâng cấp súng đang dùng"),
            ("upgrade_drone", "Drone (boss ải 3 · ải 9: drone 2)"),
            ("upgrade_burn", f"Đạn cháy {config.BURN_DAMAGE_PER_SECOND} HP/s (boss ải 7)"),
        ]
        for i, (kind, desc) in enumerate(items):
            y = top + 32 + i * 34
            draw_item_icon(surface, a, kind, right + 12, y + 12, size=0.8)
            surface.blit(a.text(desc, 13, WHITE, bold=False), (right + 32, y + 4))
        note = "Nhặt cùng loại súng: lên cấp (tối đa 6) · Khác loại: đổi súng"
        surface.blit(a.text(note, 13, HOMING_COLOR, bold=False), (right, top + 32 + len(items) * 34 + 6))


class AchievementsScene(_InfoScene):
    MODE_COLORS = {GameMode.CAMPAIGN: NEON_CYAN, GameMode.ENDLESS: HOMING_COLOR, GameMode.INFERNO: NEON_RED}
    COLUMNS = (("SỐ VÁN", 290), ("QUÁI", 390), ("BOSS", 480), ("ĐIỂM CAO", 585), ("LÂU NHẤT", 690))

    def draw(self, surface: pygame.Surface) -> None:
        a = self.game.assets
        self.draw_frame(surface, "BẢNG THÀNH TỰU")
        save = self.game.save
        blit_center(surface, a.text(f"KỶ LỤC CHUNG: {save.highscore}", 20, YELLOW), PANEL.y + 65)
        header_y = PANEL.y + 110
        for label, cx in self.COLUMNS:
            text = a.text(label, 15, NEON_ORANGE)
            surface.blit(text, (cx - text.get_width() // 2, header_y))
        for i, mode in enumerate(GameMode):
            rec = save.modes[mode]
            row = pygame.Rect(PANEL.x + 20, header_y + 35 + i * 110, PANEL.width - 40, 95)
            color = self.MODE_COLORS[mode]
            pygame.draw.rect(surface, (20, 25, 35), row, border_radius=6)
            pygame.draw.rect(surface, color, row, 1, border_radius=6)
            surface.blit(a.text(mode.label, 24, color), (row.x + 20, row.centery - 15))
            values = (rec.games_played, rec.total_kills, rec.total_boss_kills, rec.best_score, format_time(rec.best_time))
            for (label, cx), value in zip(self.COLUMNS, values):
                text = a.text(str(value), 22, YELLOW if label == "ĐIỂM CAO" else WHITE)
                surface.blit(text, (cx - text.get_width() // 2, row.centery - 12))
        blit_center(surface, a.text("Số quái/boss là TỔNG CỘNG DỒN qua mọi ván.", 14, (150, 150, 160), bold=False),
                    PANEL.bottom - 62)
