"""Màn Cài đặt: tự động bắn, độ nhạy tay, hiệu chỉnh lại tay."""
from __future__ import annotations

import pygame

from spaceship import config
from spaceship.config import GRAY, NEON_CYAN, NEON_GREEN, WHITE, WIDTH, YELLOW
from spaceship.core.scene import Scene
from spaceship.ui.widgets import Button, blit_center, draw_panel

PANEL = pygame.Rect(60, 60, WIDTH - 120, 580)
BTN_W, BTN_H = 420, 50


class OptionsScene(Scene):
    music = "menu"
    shows_camera = True          # nhìn ô camera để thấy vùng điều khiển thay đổi theo độ nhạy

    def __init__(self, game) -> None:
        super().__init__(game)
        x = WIDTH // 2 - BTN_W // 2
        self.buttons = [
            Button("", pygame.Rect(x, 170, BTN_W, BTN_H), NEON_CYAN, "auto_fire", 22),
            Button("", pygame.Rect(x, 285, BTN_W, BTN_H), NEON_CYAN, "sensitivity", 22),
            Button("HIỆU CHỈNH LẠI TAY", pygame.Rect(x, 400, BTN_W, BTN_H), NEON_GREEN, "calibrate", 22),
            Button("VỀ MENU", pygame.Rect(x, 515, BTN_W, BTN_H), GRAY, "menu", 22),
        ]
        self._refresh()

    def _refresh(self) -> None:
        s = self.game.settings
        self.buttons[0].text = f"TỰ ĐỘNG BẮN: {'BẬT' if s.auto_fire else 'TẮT'}"
        self.buttons[1].text = f"ĐỘ NHẠY TAY: {config.HAND_SENSITIVITY_LABELS[s.sensitivity]}"

    def handle_event(self, event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._do("menu")
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for button in self.buttons:
                if button.hovered(event.pos):
                    self._do(button.action)

    def _do(self, action: str) -> None:
        from spaceship.scenes.calibration import CalibrationScene
        from spaceship.scenes.menu import MenuScene

        s = self.game.settings
        if action == "auto_fire":
            s.auto_fire = not s.auto_fire
        elif action == "sensitivity":
            s.cycle_sensitivity()
        elif action == "calibrate":
            self.game.change_scene(CalibrationScene(self.game, lambda: OptionsScene(self.game)))
            return
        else:
            self.game.change_scene(MenuScene(self.game))
            return
        s.save()
        self.game.controls.apply_settings()
        self._refresh()

    def update(self, controls) -> None:
        self.game.starfield.update()

    def draw(self, surface: pygame.Surface) -> None:
        a = self.game.assets
        surface.fill((0, 0, 0))
        self.game.starfield.draw(surface)
        draw_panel(surface, PANEL)
        blit_center(surface, a.text("CÀI ĐẶT", 36, YELLOW), PANEL.y + 18)
        notes = {
            0: "Tàu tự bắn liên tục, tay chỉ cần lái. Tắt: giơ 1 ngón trỏ / giữ Space để bắn.",
            1: "Cao = nhích tay ít đã đi xa (đỡ mỏi). Thấp = chính xác hơn, phải vung rộng hơn.",
            2: "Đặt lại tư thế nghỉ của tay (chỗ ứng với giữa màn hình).",
        }
        for i, button in enumerate(self.buttons):
            button.draw(surface, a, self.game.mouse_pos)
            if i in notes:
                blit_center(surface, a.text(notes[i], 14, WHITE, bold=False), button.rect.bottom + 12)
        if not self.game.hand_available:
            blit_center(surface, a.text("(Không có camera - các mục về tay sẽ có tác dụng khi bật camera)", 13, GRAY, bold=False),
                        PANEL.y + 72)
        blit_center(surface, a.text("ESC: VỀ MENU", 14, GRAY), PANEL.bottom + 14)
