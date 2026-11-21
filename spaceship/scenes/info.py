"""Hai màn thông tin tĩnh: Hướng dẫn chơi và Thành tựu.

Bản cũ vẽ panel rộng 840px và 860px trên màn hình 800px nên bị cắt mép;
giờ panel rộng 760px, nội dung lấy từ ``config`` để không bao giờ lệch với game.
"""
from __future__ import annotations

import pygame

from spaceship import config
from spaceship.config import WIDTH, GameMode
from spaceship.core.scene import Scene
from spaceship.entities.items import draw_item_icon
from spaceship.ui.hud import format_time
from spaceship.ui.menu_list import MenuList
from spaceship.ui.widgets import ACCENT, FRAME, MUTED, SECONDARY, TEXT, blit_center, draw_back_hint, draw_panel, fit_text

PANEL = pygame.Rect(20, 50, WIDTH - 40, 600)
BACK = pygame.Rect(WIDTH // 2 - 160, PANEL.bottom - 36, 320, 26)


class _InfoScene(Scene):
    music = "menu"

    def __init__(self, game) -> None:
        super().__init__(game)
        self.menu = MenuList(game, (BACK,), self._back)

    def _back(self, _index=0) -> None:
        from spaceship.scenes.menu import MenuScene

        self.game.change_scene(MenuScene(self.game))

    def handle_event(self, event) -> None:
        if (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE) or (
                event.type == pygame.MOUSEBUTTONDOWN and event.button == 1):
            self._back()
        else:
            self.menu.handle_event(event)

    def update(self, controls) -> None:
        self.game.starfield.update()
        self.menu.update(controls)

    def draw_frame(self, surface: pygame.Surface, title: str) -> None:
        surface.fill((0, 0, 0))
        self.game.starfield.draw(surface)
        draw_panel(surface, PANEL, header_height=64)
        blit_center(surface, self.game.assets.text(title, 36, TEXT, role="display"), PANEL.y + 8)
        draw_back_hint(surface, self.game.assets, BACK.y + 2)
        self.menu.draw_progress(surface)


class HowToPlayScene(_InfoScene):
    def draw(self, surface: pygame.Surface) -> None:
        a = self.game.assets
        self.draw_frame(surface, "HƯỚNG DẪN CHI TIẾT")
        left, right, top = PANEL.x + 25, PANEL.x + 400, PANEL.y + 80
        column_width = PANEL.right - right - 18
        pygame.draw.line(surface, FRAME, (WIDTH // 2, top), (WIDTH // 2, PANEL.bottom - 68))

        surface.blit(a.text("ĐIỀU KHIỂN", 18, ACCENT, role="ui"), (left, top))
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
            surface.blit(fit_text(a, key, 15, SECONDARY, 120, role="label"), (left, y))
            surface.blit(fit_text(a, desc, 14, TEXT, WIDTH // 2 - left - 145, role="body"), (left + 130, y))

        mode_y = top + 265
        surface.blit(a.text("CHẾ ĐỘ CHƠI", 18, ACCENT, role="ui"), (left, mode_y))
        modes = [
            ("VƯỢT ẢI", "10 ải, 3 hồi, có cốt truyện."),
            ("VÔ TẬN", f"Sống sót. Boss mỗi {config.ENDLESS_BOSS_INTERVAL:.0f}s."),
            ("HỎA NGỤC", "Mở khóa khi phá đảo Vượt ải."),
        ]
        for i, (name, desc) in enumerate(modes):
            y = mode_y + 32 + i * 27
            surface.blit(a.text(name, 15, SECONDARY, role="label"), (left, y))
            surface.blit(fit_text(a, desc, 15, TEXT, WIDTH // 2 - left - 142, role="body"), (left + 125, y))

        surface.blit(a.text("VẬT PHẨM", 18, ACCENT, role="ui"), (right, top))
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
            ("upgrade_burn", f"Đạn thiêu đốt {config.BURN_DAMAGE_PER_SECOND} HP/s (boss ải 7)"),
        ]
        for i, (kind, desc) in enumerate(items):
            y = top + 32 + i * 34
            draw_item_icon(surface, a, kind, right + 12, y + 12, size=0.8)
            surface.blit(fit_text(a, desc, 14, TEXT, column_width - 32, role="body"), (right + 32, y + 4))
        note = "Nhặt cùng loại súng: lên cấp (tối đa 6) · Khác loại: đổi súng"
        surface.blit(fit_text(a, note, 14, MUTED, column_width, role="body"), (right, top + 32 + len(items) * 34 + 6))


class AchievementsScene(_InfoScene):
    COLUMNS = (("SỐ VÁN", 290), ("QUÁI", 390), ("BOSS", 480), ("ĐIỂM CAO", 585), ("LÂU NHẤT", 690))

    def draw(self, surface: pygame.Surface) -> None:
        a = self.game.assets
        self.draw_frame(surface, "BẢNG THÀNH TỰU")
        save = self.game.save
        blit_center(surface, fit_text(a, f"KỶ LỤC CHUNG: {save.highscore}", 21, ACCENT, PANEL.width - 60, role="ui"),
                    PANEL.y + 71)
        header_y = PANEL.y + 110
        for label, cx in self.COLUMNS:
            text = a.text(label, 15, MUTED, role="label")
            surface.blit(text, (cx - text.get_width() // 2, header_y))
        for i, mode in enumerate(GameMode):
            rec = save.modes[mode]
            row = pygame.Rect(PANEL.x + 20, header_y + 35 + i * 110, PANEL.width - 40, 95)
            draw_panel(surface, row)
            name = fit_text(a, mode.label, 24, TEXT, 170, role="ui")
            surface.blit(name, name.get_rect(midleft=(row.x + 20, row.centery)))
            values = (rec.games_played, rec.total_kills, rec.total_boss_kills, rec.best_score, format_time(rec.best_time))
            for (label, cx), value in zip(self.COLUMNS, values):
                text = fit_text(a, str(value), 22, ACCENT if label == "ĐIỂM CAO" else TEXT, 74, role="ui")
                surface.blit(text, text.get_rect(center=(cx, row.centery)))
        blit_center(surface, a.text("Số quái/boss là tổng cộng dồn qua mọi ván.", 14, MUTED, role="body"),
                    PANEL.bottom - 62)
