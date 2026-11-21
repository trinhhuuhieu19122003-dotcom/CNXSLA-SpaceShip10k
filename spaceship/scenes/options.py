"""Màn Cài đặt: tự động bắn, độ nhạy tay, hiệu chỉnh lại tay."""
from __future__ import annotations

import pygame

from spaceship import config
from spaceship.config import WIDTH
from spaceship.core.scene import Scene
from spaceship.ui.menu_list import MenuList
from spaceship.ui.widgets import MUTED, SECONDARY, TEXT, Button, blit_center, draw_panel, fit_text

PANEL = pygame.Rect(60, 60, WIDTH - 120, 580)
BTN_W, BTN_H = 420, 50
NOTES = (
    "Tàu tự bắn liên tục, tay chỉ cần lái. Tắt: giơ 1 ngón trỏ / giữ Space để bắn.",
    "Cao = nhích tay ít đã đi xa (đỡ mỏi). Thấp = chính xác hơn, phải vung rộng hơn.",
    "Đặt lại tư thế nghỉ của tay (chỗ ứng với giữa màn hình).",
)


class OptionsScene(Scene):
    music = "menu"
    shows_camera = True          # nhìn ô camera để thấy vùng điều khiển thay đổi theo độ nhạy

    def __init__(self, game) -> None:
        super().__init__(game)
        x = WIDTH // 2 - BTN_W // 2
        self.buttons = [
            Button("", pygame.Rect(x, 170, BTN_W, BTN_H), "auto_fire"),
            Button("", pygame.Rect(x, 285, BTN_W, BTN_H), "sensitivity"),
            Button("HIỆU CHỈNH LẠI TAY", pygame.Rect(x, 400, BTN_W, BTN_H), "calibrate"),
            Button("VỀ MENU", pygame.Rect(x, 515, BTN_W, BTN_H), "menu"),
        ]
        self.menu = MenuList.for_buttons(game, self.buttons, self._do)
        self._refresh()

    def _refresh(self) -> None:
        s = self.game.settings
        self.buttons[0].text = f"TỰ ĐỘNG BẮN: {'BẬT' if s.auto_fire else 'TẮT'}"
        self.buttons[1].text = f"ĐỘ NHẠY TAY: {config.HAND_SENSITIVITY_LABELS[s.sensitivity]}"

    def handle_event(self, event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._do("menu")
        else:
            self.menu.handle_event(event)

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
        self.menu.update(controls)

    def draw(self, surface: pygame.Surface) -> None:
        a = self.game.assets
        surface.fill((0, 0, 0))
        self.game.starfield.draw(surface)
        draw_panel(surface, PANEL, header_height=64)
        blit_center(surface, a.text("CÀI ĐẶT", 36, TEXT, role="display"), PANEL.y + 8)
        for i, button in enumerate(self.buttons):
            button.draw(surface, a, i == self.menu.selected)
            if i < len(NOTES):
                note = fit_text(a, NOTES[i], 15, SECONDARY, PANEL.width - 48, role="body")
                blit_center(surface, note, button.rect.bottom + 10)
        self.menu.draw_progress(surface)
        if not self.game.hand_available:
            note = "(Không có camera - các mục về tay sẽ có tác dụng khi bật camera)"
            blit_center(surface, a.text(note, 14, MUTED, role="body"), PANEL.y + 75)
        blit_center(surface, a.text("ESC: VỀ MENU", 14, MUTED, role="label"), PANEL.bottom + 14)
