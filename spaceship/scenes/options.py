"""Màn Cài đặt: toàn màn hình, rung & nháy màn hình, tự động bắn, độ nhạy tay, điều khiển menu bằng tay, âm lượng, hiệu chỉnh lại tay."""
from __future__ import annotations

import pygame

from spaceship import config
from spaceship.config import WIDTH
from spaceship.core.scene import Scene
from spaceship.ui.menu_list import MenuList
from spaceship.ui.volume_sliders import STEP as VOLUME_STEP, VOLUMES, VolumeSliders
from spaceship.ui.widgets import FRAME, MUTED, SECONDARY, TEXT, Button, blit_center, draw_panel, fit_text

PANEL = pygame.Rect(60, 60, WIDTH - 120, 580)
BTN_W, BTN_H = 440, 40
BTN_TOP, BTN_STEP = 146, 46
VOLUME_NOTE = "Kéo thanh bằng chuột · phím trái/phải: ±5% · chụm tay rồi di ngang để kéo."
#: (chữ cố định, hành động, ghi chú hiện ở cuối khung khi mục được chọn)
ROWS = (
    ("", "fullscreen", "Phủ kín màn hình. Phím tắt: F11 hoặc Alt + Enter, dùng được ở mọi màn."),
    ("", "screen_fx", "Rung màn hình, khựng hình khi trúng đòn, chớp sáng. NHẸ / TẮT nếu thấy chóng mặt."),
    ("", "auto_fire", "Tàu tự bắn liên tục, tay chỉ cần lái. Tắt: giơ 1 ngón trỏ / giữ Space để bắn."),
    ("", "sensitivity", "Cao = nhích tay ít đã đi xa (đỡ mỏi). Thấp = chính xác hơn, phải vung rộng hơn."),
    ("", "hand_menu", "Tắt: menu chỉ dùng phím / chuột (trong trận vẫn lái tàu bằng tay)."),
    ("", "music", VOLUME_NOTE),
    ("", "sfx", VOLUME_NOTE),
    ("HIỆU CHỈNH LẠI TAY", "calibrate", "Đặt lại tư thế nghỉ của tay (chỗ ứng với giữa màn hình)."),
    ("VỀ MENU", "menu", "Lưu tự động: mọi thay đổi có hiệu lực ngay."),
)
NOTE_Y = BTN_TOP + len(ROWS) * BTN_STEP + 8


class OptionsScene(Scene):
    music = "menu"
    shows_camera = True          # nhìn ô camera để thấy vùng điều khiển thay đổi theo độ nhạy

    def __init__(self, game) -> None:
        super().__init__(game)
        x = WIDTH // 2 - BTN_W // 2
        self.buttons = [Button(text, pygame.Rect(x, BTN_TOP + i * BTN_STEP, BTN_W, BTN_H), action)
                        for i, (text, action, _note) in enumerate(ROWS)]
        self.menu = MenuList.for_buttons(game, self.buttons, self._do)
        self.sliders = VolumeSliders(game, self.buttons)      # thanh trượt âm lượng dùng chung với Tạm dừng
        self._refresh()

    _track = staticmethod(VolumeSliders.track)

    @property
    def _hand_drag(self):
        return self.sliders.hand_drag

    def _refresh(self) -> None:
        s = self.game.settings
        texts = {
            "fullscreen": f"TOÀN MÀN HÌNH: {'BẬT' if self.game.fullscreen else 'TẮT'}",
            "screen_fx": f"RUNG & NHÁY MÀN HÌNH: {config.SCREEN_FX_LABELS.get(s.screen_fx, 'ĐẦY ĐỦ')}",
            "auto_fire": f"TỰ ĐỘNG BẮN: {'BẬT' if s.auto_fire else 'TẮT'}",
            "sensitivity": f"ĐỘ NHẠY TAY: {config.HAND_SENSITIVITY_LABELS[s.sensitivity]}",
            "hand_menu": f"CHỌN MENU BẰNG TAY: {'BẬT' if s.hand_menu else 'TẮT'}",
            "music": "NHẠC NỀN",
            "sfx": "HIỆU ỨNG",
        }
        for button in self.buttons:
            button.text = texts.get(button.action, button.text)

    def _change_volume(self, action: str, step: float, wrap: bool) -> None:
        self.sliders.step(action, step, wrap)
        self._refresh()

    def handle_event(self, event) -> None:
        if self.sliders.handle_event(event, self.menu):
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.game.audio.play("ui_back")
            self._do("menu")
        else:
            self.menu.handle_event(event)

    def _do(self, action: str) -> None:
        from spaceship.scenes.calibration import CalibrationScene
        from spaceship.scenes.menu import MenuScene

        s = self.game.settings
        if action == "fullscreen":
            self.game.toggle_fullscreen()
            self._refresh()
            return
        if action == "screen_fx":
            s.cycle_screen_fx()
        elif action == "auto_fire":
            s.auto_fire = not s.auto_fire
        elif action == "sensitivity":
            s.cycle_sensitivity()
        elif action == "hand_menu":
            s.hand_menu = not s.hand_menu
        elif action in VOLUMES:
            self._change_volume(action, VOLUME_STEP, wrap=True)
            return
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
        self._refresh()                      # F11 / Alt+Enter có thể đổi toàn màn hình từ bên ngoài
        self.sliders.before_menu_update(controls, self.menu)
        self.menu.update(controls)
        self.sliders.after_menu_update(self.menu)

    def draw(self, surface: pygame.Surface) -> None:
        a = self.game.assets
        surface.fill((0, 0, 0))
        self.game.starfield.draw(surface)
        draw_panel(surface, PANEL, header_height=64)
        blit_center(surface, a.text("CÀI ĐẶT", 36, TEXT, role="display"), PANEL.y + 8)
        for i, button in enumerate(self.buttons):
            if button.action in VOLUMES:
                self.sliders.draw(surface, a, button, i == self.menu.selected)
            else:
                button.draw(surface, a, i == self.menu.selected)
        self.menu.draw_progress(surface)
        pygame.draw.line(surface, FRAME, (PANEL.x + 24, NOTE_Y - 4), (PANEL.right - 24, NOTE_Y - 4))
        note = fit_text(a, ROWS[self.menu.selected][2], 15, SECONDARY, PANEL.width - 48, role="body")
        blit_center(surface, note, NOTE_Y + 8)
        if not self.game.hand_available:
            note = "(Không có camera - các mục về tay sẽ có tác dụng khi bật camera)"
            blit_center(surface, a.text(note, 15, MUTED, role="body"), NOTE_Y + 36)
        blit_center(surface, a.text("ESC: VỀ MENU", 15, MUTED, role="label"), PANEL.bottom + 14)
