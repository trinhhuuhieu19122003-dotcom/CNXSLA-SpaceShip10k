"""Tạm dừng: vẽ đè lên màn chơi đang đóng băng.

Hai lý do dừng:
- ``manual``: bấm ESC/P hoặc rời cửa sổ.
- ``hand``: đang lái bằng tay mà bỏ tay xuống -> dừng để nghỉ tay.
  Đưa tay vào khung lại là tự đếm 3-2-1 rồi chơi tiếp, không cần bấm gì.
Chơi tiếp luôn có đếm ngược để người chơi kịp đặt tay/ngón vào vị trí.
"""
from __future__ import annotations

import math

import pygame

from spaceship import config
from spaceship.config import HEIGHT, WIDTH
from spaceship.core.scene import Scene
from spaceship.input.gestures import Gesture
from spaceship.ui.menu_list import MenuList
from spaceship.ui.volume_sliders import VolumeSliders
from spaceship.ui.widgets import ACCENT, MUTED, SECONDARY, TEXT, Button, blit_center, dim, draw_panel, fit_text

BTN_W, BTN_H = 400, 46
BTN_STEP = 56
PANEL = pygame.Rect(WIDTH // 2 - 230, 110, 460, 470)
HAND_BACK_TICKS = int(0.3 * config.TICK_RATE)    # tay phải xuất hiện ổn định 0.3 giây


class PauseScene(Scene):
    shows_camera = True
    sidebars = True                  # màn rộng: giữ 2 bảng bên của trận đang dừng

    def __init__(self, game, gameplay, reason: str = "manual") -> None:
        super().__init__(game)
        self.gameplay = gameplay
        self.reason = reason
        self.music = gameplay.music                  # giữ nguyên nhạc, không phát lại từ đầu
        self.countdown = 0                           # > 0: đang đếm ngược (tick còn lại)
        self.hand_seen_ticks = 0
        self._auto_resume = False
        x = WIDTH // 2 - BTN_W // 2
        top = PANEL.y + (176 if reason == "hand" else 128)
        rows = (("TIẾP TỤC", "resume"), ("NHẠC NỀN", "music"), ("HIỆU ỨNG", "sfx"), ("QUAY LẠI MENU", "menu"))
        self.buttons = [Button(text, pygame.Rect(x, top + i * BTN_STEP, BTN_W, BTN_H), action)
                        for i, (text, action) in enumerate(rows)]
        self.menu = MenuList.for_buttons(game, self.buttons, self._do)
        self.sliders = VolumeSliders(game, self.buttons)           # chỉnh âm lượng ngay khi tạm dừng

    @property
    def counting(self) -> bool:
        return self.countdown > 0

    def handle_event(self, event) -> None:
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_p):
            if self.counting:
                self._cancel_countdown()
            else:
                self._do("resume")
        elif not self.counting and not self.sliders.handle_event(event, self.menu):
            self.menu.handle_event(event)

    def _do(self, action: str) -> None:
        from spaceship.scenes.menu import MenuScene

        if action in ("music", "sfx"):                 # Enter / chụm giữ trên thanh trượt: +5%
            self.sliders.step(action, 0.05, wrap=True)
            return
        if action == "resume":
            self.countdown = int(config.RESUME_COUNTDOWN_SECONDS * config.TICK_RATE)
            self._auto_resume = False
            self.game.audio.play("ui_move")
        else:
            self.game.change_scene(MenuScene(self.game))

    def _cancel_countdown(self) -> None:
        self.countdown = 0
        self.hand_seen_ticks = 0
        self._auto_resume = False

    def _count_number(self) -> int:
        total = config.RESUME_COUNTDOWN_SECONDS * config.TICK_RATE
        return max(1, math.ceil(self.countdown / total * 3))

    def update(self, controls) -> None:
        self.game.audio.duck()                       # nhạc nhỏ lại khi tạm dừng
        pinching = controls.gesture is Gesture.PINCH
        if self.counting and self._auto_resume and pinching and controls.target is not None:
            # Một lần chụm chủ ý có thể ngắt đếm tự động để dùng menu.
            if not self.game.menu_pinch_consumed:
                self._cancel_countdown()
        if not self.counting:
            self.sliders.before_menu_update(controls, self.menu)
        self.menu.update(controls, enabled=not self.counting)
        self.sliders.after_menu_update(self.menu)
        hand_visible = controls.gesture is not Gesture.NONE
        if self.reason == "hand" and not self.counting:
            self.hand_seen_ticks = self.hand_seen_ticks + 1 if hand_visible and not pinching else 0
            if self.hand_seen_ticks >= HAND_BACK_TICKS:
                self._do("resume")
                self._auto_resume = True
        if self.counting:
            if self.reason == "hand" and not hand_visible and controls.hand_absent > 0.5:
                self._cancel_countdown()
                return
            before = self._count_number()
            self.countdown -= 1
            if self.countdown and self._count_number() != before:
                self.game.audio.play("ui_move")
            if self.countdown == 0:
                self.game.change_scene(self.gameplay)

    # --- Vẽ -----------------------------------------------------------------------------
    def draw_sidebars(self, surface, left, right) -> None:
        self.gameplay.draw_sidebars(surface, left, right)

    def draw(self, surface: pygame.Surface) -> None:
        a = self.game.assets
        self.gameplay.draw(surface)
        dim(surface)
        panel = PANEL if self.counting else PANEL.copy()
        if not self.counting:                         # khung ôm vừa nội dung
            panel.height = self.buttons[-1].rect.bottom + 58 - PANEL.y
        draw_panel(surface, panel, header_height=68)
        if self.counting:
            total = config.RESUME_COUNTDOWN_SECONDS * config.TICK_RATE
            number = max(1, math.ceil(self.countdown / total * 3))
            blit_center(surface, a.text("TIẾP TỤC", 36, TEXT, role="display"), PANEL.y + 10)
            blit_center(surface, a.text(str(number), 112, ACCENT, role="display"), HEIGHT // 2 - 104)
            blit_center(surface, a.text("Chuẩn bị...", 20, SECONDARY, role="body"), HEIGHT // 2 + 62)
            return
        title = "NGHỈ TAY" if self.reason == "hand" else "TẠM DỪNG"
        blit_center(surface, a.text(title, 40, TEXT, role="display"), PANEL.y + 8)
        info = fit_text(a, self._info_line(), 16, SECONDARY, PANEL.width - 40, role="label")
        blit_center(surface, info, PANEL.y + 82)
        if self.reason == "hand":
            blit_center(surface, a.text("Đưa tay vào khung camera để chơi tiếp", 18, ACCENT, role="body"), PANEL.y + 116)
            blit_center(surface, a.text("(game sẽ tự đếm 3-2-1)", 15, MUTED, role="body"), PANEL.y + 144)
        for i, button in enumerate(self.buttons):
            if button.action in ("music", "sfx"):
                self.sliders.draw(surface, a, button, i == self.menu.selected)
            else:
                button.draw(surface, a, i == self.menu.selected)
        self.menu.draw_progress(surface)
        hint = "ESC / P: CHƠI TIẾP · TRÁI/PHẢI: CHỈNH ÂM LƯỢNG"
        blit_center(surface, a.text(hint, 14, MUTED, role="label"), panel.bottom - 30)

    def _info_line(self) -> str:
        """Đang ở đâu trong trận: ải/chế độ, wave, điểm, máu."""
        play, w = self.gameplay, self.gameplay.world
        where = play.level.title if play.level is not None else play.mode.label.upper()
        progress = play.director.progress_text
        parts = [where, progress, f"ĐIỂM {w.score}", f"MÁU {max(0, round(w.player.hp))}/{w.player.max_hp}"]
        return "  ·  ".join(p for p in parts if p)
