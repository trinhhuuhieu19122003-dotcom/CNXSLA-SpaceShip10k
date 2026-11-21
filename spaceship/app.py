"""Lớp ``Game``: cửa sổ, vòng lặp chính, chuyển scene, phím toàn cục.

Vòng lặp dùng mô hình *fixed timestep*: logic luôn chạy đúng 60 bước/giây
bất kể máy nhanh hay chậm, còn việc vẽ chạy nhanh nhất có thể (giới hạn bởi
``--fps``). Đây là cách sửa gốc rễ lỗi "game chạy chậm theo webcam" của bản cũ.
"""
from __future__ import annotations

import logging
import random
import time
from typing import Optional, Tuple

import pygame

from spaceship import config
from spaceship.core.assets import Assets
from spaceship.core.audio import Audio
from spaceship.core.scene import Scene
from spaceship.core.storage import SaveData
from spaceship.entities.effects import Starfield
from spaceship.input.controls import ControlHub
from spaceship.input.hand_tracker import PREVIEW_SIZE, HandTracker, TrackerState

log = logging.getLogger(__name__)

MOUSE_EVENTS = (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION)


class Game:
    def __init__(self, *, camera: bool = True, camera_index: int = config.CAMERA_INDEX,
                 fullscreen: bool = False, fps: int = 60, seed: Optional[int] = None,
                 save: Optional[SaveData] = None) -> None:
        pygame.init()
        pygame.display.set_caption(config.TITLE)
        self.fullscreen = fullscreen
        self.window = self._create_window()
        self.screen = pygame.Surface((config.WIDTH, config.HEIGHT)).convert()
        self.clock = pygame.time.Clock()
        self.fps = fps

        self.rng = random.Random(seed)
        self.assets = Assets()
        self.audio = Audio()
        self.save = save or SaveData.load()
        self.starfield = Starfield(rng=self.rng)
        self.tracker = HandTracker(camera_index).start() if camera else None
        self.controls = ControlHub(self.tracker)
        self.show_camera = True
        self.mouse_pos: Optional[Tuple[int, int]] = None

        self.running = False
        self.scene: Optional[Scene] = None
        self._pending: Optional[Scene] = None

    # --- Cửa sổ & toạ độ ---------------------------------------------------------------
    def _create_window(self) -> pygame.Surface:
        if self.fullscreen:
            return pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        return pygame.display.set_mode((config.WIDTH, config.HEIGHT), pygame.RESIZABLE)

    def toggle_fullscreen(self) -> None:
        self.fullscreen = not self.fullscreen
        self.window = self._create_window()

    def _viewport(self) -> Tuple[float, int, int]:
        """(tỉ lệ, lề trái, lề trên) để đặt màn hình ảo 800x700 giữa cửa sổ (letterbox)."""
        ww, wh = self.window.get_size()
        scale = min(ww / config.WIDTH, wh / config.HEIGHT)
        return scale, (ww - int(config.WIDTH * scale)) // 2, (wh - int(config.HEIGHT * scale)) // 2

    def to_virtual(self, pos) -> Optional[Tuple[int, int]]:
        scale, ox, oy = self._viewport()
        if scale <= 0:
            return None
        return int((pos[0] - ox) / scale), int((pos[1] - oy) / scale)

    # --- Scene ------------------------------------------------------------------------
    def change_scene(self, scene: Scene) -> None:
        """Đổi scene ở cuối tick hiện tại (an toàn kể cả khi gọi giữa ``update``)."""
        self._pending = scene

    def _apply_pending_scene(self) -> None:
        if self._pending is None:
            return
        self.scene, self._pending = self._pending, None
        self.audio.play_music(self.scene.music)
        self.scene.on_enter()

    def quit(self) -> None:
        self.running = False

    # --- Vòng lặp -----------------------------------------------------------------------
    def _handle_global(self, event) -> bool:
        """Phím dùng ở mọi màn hình. Trả về True nếu đã xử lý."""
        if event.type == pygame.QUIT:
            self.quit()
            return True
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_F11:
                self.toggle_fullscreen()
                return True
            if event.key == pygame.K_c:
                self.show_camera = not self.show_camera
                return True
        return False

    def _dispatch_events(self) -> None:
        for event in pygame.event.get():
            if self._handle_global(event):
                continue
            if event.type in MOUSE_EVENTS:
                attrs = dict(event.dict)
                attrs["pos"] = self.to_virtual(event.pos)
                event = pygame.event.Event(event.type, attrs)
            self.scene.handle_event(event)
            self._apply_pending_scene()

    def step(self) -> None:
        """Một bước logic cố định (dùng cả cho test headless)."""
        self.scene.update(self.controls.poll())
        self._apply_pending_scene()

    def render(self) -> None:
        self.scene.draw(self.screen)
        scale, ox, oy = self._viewport()
        dx, dy = self.scene.screen_offset()
        size = (int(config.WIDTH * scale), int(config.HEIGHT * scale))
        self.window.fill((0, 0, 0))
        frame = self.screen if size == self.screen.get_size() else pygame.transform.smoothscale(self.screen, size)
        self.window.blit(frame, (ox + int(dx * scale), oy + int(dy * scale)))
        if self.scene.shows_camera:
            self._draw_camera_overlay()
        pygame.display.flip()

    def _draw_camera_overlay(self) -> None:
        if self.tracker is None or not self.show_camera:
            return
        ww = self.window.get_width()
        x = ww - PREVIEW_SIZE[0] - 10
        frame = self.tracker.preview()
        if frame is not None:
            image = pygame.image.frombuffer(frame.tobytes(), PREVIEW_SIZE, "RGB")
            self.window.blit(image, (x, 10))
            pygame.draw.rect(self.window, config.NEON_CYAN, (x, 10, *PREVIEW_SIZE), 1)
            label = f"{self.tracker.backend_name} · {self.tracker.fps:.0f} fps"
        elif self.tracker.state == TrackerState.UNAVAILABLE:
            label = f"Không có camera: {self.tracker.message} · dùng bàn phím"
        else:
            label = self.tracker.message
        text = self.assets.text(label, 12, config.GRAY, bold=False)
        self.window.blit(text, (ww - text.get_width() - 10, 10 + PREVIEW_SIZE[1] + 4))

    def run(self, first_scene: Optional[Scene] = None) -> None:
        from spaceship.scenes.menu import MenuScene

        self.change_scene(first_scene or MenuScene(self))
        self._apply_pending_scene()
        self.running = True
        accumulator, last = 0.0, time.perf_counter()
        try:
            while self.running:
                now = time.perf_counter()
                accumulator += min(now - last, config.MAX_FRAME_TIME)
                last = now
                pos = pygame.mouse.get_pos() if pygame.mouse.get_focused() else None
                self.mouse_pos = self.to_virtual(pos) if pos else None
                self._dispatch_events()
                while accumulator >= config.TICK and self.running:
                    self.step()
                    accumulator -= config.TICK
                if self.running:
                    self.render()
                self.clock.tick(self.fps)
        finally:
            self.shutdown()

    def shutdown(self) -> None:
        if self.tracker is not None:
            self.tracker.stop()
        pygame.quit()
