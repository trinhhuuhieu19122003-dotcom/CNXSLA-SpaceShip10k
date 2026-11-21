"""Hiệu chỉnh tư thế nghỉ của tay.

Người chơi tì khuỷu tay lên bàn, để tay ở chỗ thoải mái nhất rồi giữ yên.
Vị trí đó thành TÂM màn hình; vùng điều khiển nhỏ được dựng quanh nó, nên
không phải giơ tay cao ngang mặt như bản cũ.
"""
from __future__ import annotations

import math
from collections import deque
from typing import Callable

import pygame

from spaceship import config
from spaceship.config import GRAY, HEIGHT, NEON_CYAN, NEON_GREEN, WHITE, WIDTH, YELLOW
from spaceship.core.scene import Scene
from spaceship.input.hand_tracker import TrackerState
from spaceship.ui.widgets import blit_center

PREVIEW = (400, 300)
STARTUP_TIMEOUT_TICKS = 8 * config.TICK_RATE     # camera mở quá lâu -> bỏ qua
DONE_TICKS = int(0.8 * config.TICK_RATE)
WINDOW = int(0.5 * config.TICK_RATE)             # xét độ "đứng yên" trong 0.5 giây gần nhất


class CalibrationScene(Scene):
    music = "menu"

    def __init__(self, game, next_scene: Callable[[], Scene]) -> None:
        super().__init__(game)
        self.next_scene = next_scene
        self.samples: deque = deque(maxlen=WINDOW)
        self.still_ticks = 0
        self.ticks = 0
        self.done_ticks = 0
        self.detected = False

    @property
    def hold_ticks(self) -> int:
        return int(config.CALIBRATION_HOLD_SECONDS * config.TICK_RATE)

    @property
    def progress(self) -> float:
        return 1.0 if self.done_ticks else min(1.0, self.still_ticks / self.hold_ticks)

    def handle_event(self, event) -> None:
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_ESCAPE):
            self._finish(skipped=True)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            self._finish(skipped=True)

    def _finish(self, skipped: bool = False) -> None:
        self.game.calibrated = True
        self.game.change_scene(self.next_scene())

    def update(self, controls) -> None:
        self.ticks += 1
        self.game.starfield.update()
        tracker = self.game.tracker
        if tracker is None or tracker.state in (TrackerState.UNAVAILABLE, TrackerState.STOPPED):
            return self._finish(skipped=True)
        if tracker.state == TrackerState.STARTING:
            if self.ticks > STARTUP_TIMEOUT_TICKS:
                self._finish(skipped=True)
            return
        if self.done_ticks:
            self.done_ticks += 1
            if self.done_ticks > DONE_TICKS:
                self._finish()
            return

        reading = tracker.reading
        self.detected = reading.detected
        if not reading.detected:
            self.samples.clear()
            self.still_ticks = 0
            return
        self.samples.append((reading.raw_x, reading.raw_y))
        xs, ys = [p[0] for p in self.samples], [p[1] for p in self.samples]
        still = max(xs) - min(xs) < config.CALIBRATION_STILL and max(ys) - min(ys) < config.CALIBRATION_STILL
        self.still_ticks = self.still_ticks + 1 if still else 0
        if self.still_ticks >= self.hold_ticks:
            settings = self.game.settings
            settings.hand_center = (round(sum(xs) / len(xs), 3), round(sum(ys) / len(ys), 3))
            settings.save()
            self.game.controls.apply_settings()
            self.done_ticks = 1
            self.game.audio.play("beep")

    # --- Vẽ -----------------------------------------------------------------------------
    def draw(self, surface: pygame.Surface) -> None:
        a = self.game.assets
        surface.fill((0, 0, 0))
        self.game.starfield.draw(surface)
        blit_center(surface, a.text("HIỆU CHỈNH TAY", 36, YELLOW), 30)
        lines = ("Tì khuỷu tay lên bàn, để bàn tay ở tư thế THOẢI MÁI nhất",
                 "trước camera, rồi giữ yên khoảng 2 giây.",
                 "Chỗ đó sẽ là giữa màn hình - chỉ cần nhích tay một gang là lái hết màn.")
        for i, line in enumerate(lines):
            blit_center(surface, a.text(line, 16, WHITE, bold=False), 82 + i * 24)

        box = pygame.Rect(WIDTH // 2 - PREVIEW[0] // 2, 165, *PREVIEW)
        image = self.game.camera_surface(PREVIEW)
        if image is not None:
            surface.blit(image, box)
        else:
            pygame.draw.rect(surface, (15, 20, 28), box)
            blit_center(surface, a.text(self.game.tracker.message if self.game.tracker else "", 16, GRAY), box.centery - 8)
        pygame.draw.rect(surface, NEON_CYAN, box, 2)

        self._draw_progress(surface, (WIDTH // 2, box.bottom + 70))
        if self.done_ticks:
            status, color = "XONG! Đã lưu tư thế nghỉ", NEON_GREEN
        elif not self.detected:
            status, color = "Chưa thấy tay - đưa bàn tay vào khung hình", GRAY
        elif self.still_ticks:
            status, color = "Giữ yên...", YELLOW
        else:
            status, color = "Tay đang di chuyển - giữ yên một chút", WHITE
        blit_center(surface, a.text(status, 18, color), box.bottom + 120)
        blit_center(surface, a.text("SPACE / ENTER: bỏ qua, dùng vị trí cũ", 14, GRAY, bold=False), HEIGHT - 34)

    def _draw_progress(self, surface: pygame.Surface, center) -> None:
        r = 30
        pygame.draw.circle(surface, (40, 45, 55), center, r, 6)
        if self.progress > 0:
            rect = pygame.Rect(center[0] - r, center[1] - r, r * 2, r * 2)
            start = math.pi / 2
            pygame.draw.arc(surface, NEON_GREEN if self.done_ticks else YELLOW, rect,
                            start - self.progress * 2 * math.pi, start, 6)
