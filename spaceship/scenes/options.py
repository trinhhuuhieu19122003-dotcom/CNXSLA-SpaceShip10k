"""Màn Cài đặt: toàn màn hình, tự động bắn, độ nhạy tay, điều khiển menu bằng tay, âm lượng, hiệu chỉnh lại tay."""
from __future__ import annotations

import pygame

from spaceship import config
from spaceship.config import WIDTH
from spaceship.core.scene import Scene
from spaceship.input.gestures import Gesture
from spaceship.ui.menu_list import MenuList
from spaceship.ui.widgets import (
    ACCENT, CORNER, FRAME, MUTED, PANEL_FILL, SECONDARY, SELECTED_FILL, TEXT, Button, blit_center, draw_panel, fit_text,
)

PANEL = pygame.Rect(60, 60, WIDTH - 120, 580)
BTN_W, BTN_H = 440, 40
BTN_TOP, BTN_STEP = 150, 50
VOLUME_STEP = 0.05
VOLUME_NOTE = "Kéo thanh bằng chuột · phím trái/phải: ±5% · chụm tay rồi di ngang để kéo."
SLIDER_LABEL_W, SLIDER_VALUE_W = 170, 64          # cột chữ bên trái / ô phần trăm bên phải của thanh trượt
#: (chữ cố định, hành động, ghi chú hiện ở cuối khung khi mục được chọn)
ROWS = (
    ("", "fullscreen", "Phủ kín màn hình. Phím tắt: F11 hoặc Alt + Enter, dùng được ở mọi màn."),
    ("", "auto_fire", "Tàu tự bắn liên tục, tay chỉ cần lái. Tắt: giơ 1 ngón trỏ / giữ Space để bắn."),
    ("", "sensitivity", "Cao = nhích tay ít đã đi xa (đỡ mỏi). Thấp = chính xác hơn, phải vung rộng hơn."),
    ("", "hand_menu", "Tắt: menu chỉ dùng phím / chuột (trong trận vẫn lái tàu bằng tay)."),
    ("", "music", VOLUME_NOTE),
    ("", "sfx", VOLUME_NOTE),
    ("HIỆU CHỈNH LẠI TAY", "calibrate", "Đặt lại tư thế nghỉ của tay (chỗ ứng với giữa màn hình)."),
    ("VỀ MENU", "menu", "Lưu tự động: mọi thay đổi có hiệu lực ngay."),
)
NOTE_Y = BTN_TOP + len(ROWS) * BTN_STEP + 8
VOLUMES = {"music": "music_volume", "sfx": "sfx_volume"}


class OptionsScene(Scene):
    music = "menu"
    shows_camera = True          # nhìn ô camera để thấy vùng điều khiển thay đổi theo độ nhạy

    def __init__(self, game) -> None:
        super().__init__(game)
        x = WIDTH // 2 - BTN_W // 2
        self.buttons = [Button(text, pygame.Rect(x, BTN_TOP + i * BTN_STEP, BTN_W, BTN_H), action)
                        for i, (text, action, _note) in enumerate(ROWS)]
        self.menu = MenuList.for_buttons(game, self.buttons, self._do)
        self._mouse_drag: str | None = None   # đang kéo thanh trượt nào bằng chuột
        self._hand_drag: str | None = None    # ... bằng tay (chụm + di ngang)
        self._refresh()

    # --- Thanh trượt âm lượng ------------------------------------------------------------
    @staticmethod
    def _track(button: Button) -> pygame.Rect:
        r = button.rect
        return pygame.Rect(r.x + SLIDER_LABEL_W, r.centery - 3, r.width - SLIDER_LABEL_W - SLIDER_VALUE_W, 6)

    def _set_volume(self, action: str, value: float, *, save: bool) -> None:
        s = self.game.settings
        key = VOLUMES[action]
        value = min(1.0, max(0.0, round(value * 20) / 20))          # bước 5%
        changed = abs(getattr(s, key) - value) > 1e-6
        setattr(s, key, value)
        self.game.audio.set_volumes(s.music_volume, s.sfx_volume)
        if changed and action == "sfx":
            self.game.audio.play("ui_move")                          # nghe thử ngay mức vừa chỉnh
        if save:
            s.save()

    def _set_from_x(self, button: Button, x: int, *, save: bool = False) -> None:
        track = self._track(button)
        self._set_volume(button.action, (x - track.x) / track.width, save=save)

    def _draw_slider(self, surface, assets, button: Button, selected: bool) -> None:
        value = getattr(self.game.settings, VOLUMES[button.action])
        r = button.rect
        draw_panel(surface, r, ACCENT if selected else CORNER, SELECTED_FILL if selected else PANEL_FILL)
        color = ACCENT if selected else TEXT
        label = fit_text(assets, button.text, 20, color, SLIDER_LABEL_W - 28, role="ui")
        surface.blit(label, label.get_rect(midleft=(r.x + 20, r.centery)))
        track = self._track(button)
        pygame.draw.rect(surface, (30, 38, 50), track, border_radius=3)
        filled = pygame.Rect(track.x, track.y, round(track.width * value), track.height)
        pygame.draw.rect(surface, ACCENT if selected else SECONDARY, filled, border_radius=3)
        knob = (track.x + round(track.width * value), track.centery)
        dragging = button.action in (self._mouse_drag, self._hand_drag)
        pygame.draw.circle(surface, (11, 20, 30), knob, 11 if dragging else 9)
        pygame.draw.circle(surface, ACCENT if selected else TEXT, knob, 11 if dragging else 9, 3)
        percent = assets.text(f"{round(value * 100)}%", 18, color, role="ui")
        surface.blit(percent, percent.get_rect(midright=(r.right - 16, r.centery)))

    def _refresh(self) -> None:
        s = self.game.settings
        texts = {
            "fullscreen": f"TOÀN MÀN HÌNH: {'BẬT' if self.game.fullscreen else 'TẮT'}",
            "auto_fire": f"TỰ ĐỘNG BẮN: {'BẬT' if s.auto_fire else 'TẮT'}",
            "sensitivity": f"ĐỘ NHẠY TAY: {config.HAND_SENSITIVITY_LABELS[s.sensitivity]}",
            "hand_menu": f"CHỌN MENU BẰNG TAY: {'BẬT' if s.hand_menu else 'TẮT'}",
            "music": "NHẠC NỀN",
            "sfx": "HIỆU ỨNG",
        }
        for button in self.buttons:
            button.text = texts.get(button.action, button.text)

    def _change_volume(self, action: str, step: float, wrap: bool) -> None:
        s = self.game.settings
        value = getattr(s, VOLUMES[action]) + step
        if wrap and value > 1.0 + 1e-6:
            value = 0.0
        self._set_volume(action, value, save=True)
        self._refresh()

    def _slider_at(self, pos):
        if pos is None:
            return None
        return next((b for b in self.buttons if b.action in VOLUMES and b.rect.collidepoint(pos)), None)

    def handle_event(self, event) -> None:
        action = self.buttons[self.menu.selected].action
        if event.type == pygame.MOUSEBUTTONDOWN and getattr(event, "button", 0) == 1 and self._slider_at(event.pos):
            button = self._slider_at(event.pos)                  # bấm vào thanh trượt: nhảy tới chỗ bấm, bắt đầu kéo
            self.menu.select(self.buttons.index(button))
            self._mouse_drag = button.action
            self._set_from_x(button, event.pos[0])
            return
        if event.type == pygame.MOUSEMOTION and self._mouse_drag and event.pos is not None:
            button = next(b for b in self.buttons if b.action == self._mouse_drag)
            self._set_from_x(button, event.pos[0])
            return
        if event.type == pygame.MOUSEBUTTONUP and self._mouse_drag:
            self._mouse_drag = None
            self.game.settings.save()
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.game.audio.play("ui_back")
            self._do("menu")
        elif event.type == pygame.KEYDOWN and event.key in (pygame.K_LEFT, pygame.K_RIGHT) and action in VOLUMES:
            self._change_volume(action, VOLUME_STEP if event.key == pygame.K_RIGHT else -VOLUME_STEP, wrap=False)
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
        if action == "auto_fire":
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
        selected = self.buttons[self.menu.selected]
        pinching = controls.gesture is Gesture.PINCH and controls.target is not None
        if self.game.settings.hand_menu and pinching and (self._hand_drag or selected.action in VOLUMES):
            # Chụm tay trên thanh trượt = nắm núm kéo ngang (không tính là "bấm" mục)
            self.game.menu_pinch_consumed = True
            self._hand_drag = self._hand_drag or selected.action
            self._set_from_x(selected, controls.target[0])
        elif self._hand_drag:
            self._hand_drag = None
            self.game.settings.save()
        self.menu.update(controls)
        if self._hand_drag:
            self.menu.progress = 0.0

    def draw(self, surface: pygame.Surface) -> None:
        a = self.game.assets
        surface.fill((0, 0, 0))
        self.game.starfield.draw(surface)
        draw_panel(surface, PANEL, header_height=64)
        blit_center(surface, a.text("CÀI ĐẶT", 36, TEXT, role="display"), PANEL.y + 8)
        for i, button in enumerate(self.buttons):
            if button.action in VOLUMES:
                self._draw_slider(surface, a, button, i == self.menu.selected)
            else:
                button.draw(surface, a, i == self.menu.selected)
        self.menu.draw_progress(surface)
        pygame.draw.line(surface, FRAME, (PANEL.x + 24, NOTE_Y - 4), (PANEL.right - 24, NOTE_Y - 4))
        note = fit_text(a, ROWS[self.menu.selected][2], 15, SECONDARY, PANEL.width - 48, role="body")
        blit_center(surface, note, NOTE_Y + 8)
        if not self.game.hand_available:
            note = "(Không có camera - các mục về tay sẽ có tác dụng khi bật camera)"
            blit_center(surface, a.text(note, 14, MUTED, role="body"), NOTE_Y + 36)
        blit_center(surface, a.text("ESC: VỀ MENU", 14, MUTED, role="label"), PANEL.bottom + 14)
