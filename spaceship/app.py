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
from spaceship.core.settings import Settings
from spaceship.core.storage import SaveData
from spaceship.entities.effects import Starfield
from spaceship.input.controls import ControlHub
from spaceship.input.gestures import Gesture
from spaceship.input.hand_tracker import PREVIEW_SIZE, HandTracker, TrackerState
from spaceship.ui.widgets import MUTED, fit_text

log = logging.getLogger(__name__)


def enable_dpi_awareness() -> None:
    """Windows đang phóng to giao diện 125%/150% sẽ tự "kéo giãn" cửa sổ game như một tấm ảnh,
    làm chữ mờ nhòe. Báo cho Windows biết game tự lo việc co giãn để được vẽ nét ở độ phân giải thật."""
    import sys

    if sys.platform != "win32":
        return
    try:
        import ctypes

        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)      # Windows 8.1+: theo từng màn hình
        except (AttributeError, OSError):
            ctypes.windll.user32.SetProcessDPIAware()           # Windows cũ hơn
    except Exception as exc:  # noqa: BLE001 - chỉ là cải thiện hiển thị, lỗi thì bỏ qua
        log.debug("Không bật được DPI awareness: %s", exc)


MOUSE_EVENTS = (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION)
SCENE_FADE_SECONDS = 0.25


class Game:
    def __init__(self, *, camera: bool = True, camera_index: int = config.CAMERA_INDEX,
                 fullscreen: Optional[bool] = None, fps: int = 60, seed: Optional[int] = None,
                 save: Optional[SaveData] = None, settings: Optional[Settings] = None) -> None:
        enable_dpi_awareness()
        pygame.init()
        pygame.display.set_caption(config.TITLE)
        self.save = save or SaveData.load()
        self.settings = settings or Settings.load()
        # None = theo lựa chọn đã lưu trong Cài đặt; True/False = ép (tham số --fullscreen, test)
        self.fullscreen = self.settings.fullscreen if fullscreen is None else fullscreen
        self.window = self._create_window()
        self._backdrop: Optional[pygame.Surface] = None     # ảnh mờ lấp 2 bên khi màn hình rộng
        self._backdrop_frame = 0
        self.screen = pygame.Surface((config.WIDTH, config.HEIGHT)).convert()
        self.clock = pygame.time.Clock()
        self.fps = fps

        self.rng = random.Random(seed)
        self.assets = Assets()
        self.audio = Audio(music_volume=self.settings.music_volume, sfx_volume=self.settings.sfx_volume)
        self.starfield = Starfield(rng=self.rng)
        self.tracker = HandTracker(camera_index).start() if camera else None
        self.controls = ControlHub(self.tracker, self.settings)
        self.show_camera = True
        self.calibrated = False         # đã hiệu chỉnh tay trong lần mở game này chưa
        self.mouse_pos: Optional[Tuple[int, int]] = None

        self.running = False
        self.scene: Optional[Scene] = None
        self._pending: Optional[Scene] = None
        self.menu_pinch_consumed = False
        self._presented: Optional[Tuple[pygame.Surface, int]] = None
        self._fade_from: Optional[pygame.Surface] = None
        self._fade_started: Optional[float] = None
        self._fade_overlay: Optional[pygame.Surface] = None

    # --- Cửa sổ & toạ độ ---------------------------------------------------------------
    def _create_window(self) -> pygame.Surface:
        if self.fullscreen:
            return pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        return pygame.display.set_mode(self._windowed_size(), pygame.RESIZABLE)

    @staticmethod
    def _windowed_size() -> Tuple[int, int]:
        """Cửa sổ thường: phóng theo màn hình (cao ~85%) để không bị bé trên màn độ phân giải cao."""
        try:
            desk_w, desk_h = pygame.display.get_desktop_sizes()[0]
        except (pygame.error, IndexError, AttributeError):
            return config.WIDTH, config.HEIGHT
        scale = min(desk_h * 0.85 / config.HEIGHT, desk_w * 0.9 / config.WIDTH)
        if scale <= 1.05:
            return config.WIDTH, config.HEIGHT
        return int(config.WIDTH * scale), int(config.HEIGHT * scale)

    def toggle_fullscreen(self) -> None:
        self.set_fullscreen(not self.fullscreen)

    def set_fullscreen(self, on: bool) -> None:
        """Bật/tắt toàn màn hình và nhớ lựa chọn cho lần mở sau."""
        if on != self.fullscreen:
            self.fullscreen = on
            self.window = self._create_window()
            self._backdrop = None
        if self.settings.fullscreen != on:
            self.settings.fullscreen = on
            self.settings.save()

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

    # --- Camera ------------------------------------------------------------------------
    @property
    def hand_available(self) -> bool:
        """Có webcam đang (hoặc sắp) hoạt động không."""
        return self.tracker is not None and self.tracker.state in (TrackerState.STARTING, TrackerState.RUNNING)

    def needs_calibration(self) -> bool:
        return self.hand_available and not self.calibrated

    def camera_surface(self, size: Optional[Tuple[int, int]] = None) -> Optional[pygame.Surface]:
        if self.tracker is None:
            return None
        frame = self.tracker.preview()
        if frame is None:
            return None
        image = pygame.image.frombuffer(frame.tobytes(), PREVIEW_SIZE, "RGB")
        return pygame.transform.smoothscale(image, size) if size else image

    # --- Scene ------------------------------------------------------------------------
    def change_scene(self, scene: Scene) -> None:
        """Đổi scene ở cuối tick hiện tại (an toàn kể cả khi gọi giữa ``update``)."""
        self._pending = scene

    def _apply_pending_scene(self) -> None:
        if self._pending is None:
            return
        if self._presented is not None:
            source, darkness = self._presented
            self._fade_from = source.copy()
            self._darken(self._fade_from, darkness)
        self._fade_started = time.perf_counter()
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
            alt_enter = event.key == pygame.K_RETURN and getattr(event, "mod", 0) & pygame.KMOD_ALT
            if event.key == pygame.K_F11 or alt_enter:
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
        # Lần chụm đã dùng cho menu không kích hoạt kỹ năng khi trở lại trận.
        controls = self.controls.poll(allow_pinch_skill=not self.menu_pinch_consumed)
        if controls.gesture not in (Gesture.NONE, Gesture.PINCH):
            self.menu_pinch_consumed = False
        self.scene.update(controls)
        self._apply_pending_scene()
        self.audio.update()

    def render(self) -> None:
        self.scene.draw(self.screen)
        source, darkness = self._transition_frame()
        scale, ox, oy = self._viewport()
        dx, dy = self.scene.screen_offset() if source is self.screen else (0, 0)
        size = (int(config.WIDTH * scale), int(config.HEIGHT * scale))
        self._draw_backdrop(source, size)
        frame = source if size == source.get_size() else pygame.transform.smoothscale(source, size)
        self.window.blit(frame, (ox + int(dx * scale), oy + int(dy * scale)))
        if ox > 0 or oy > 0:                                 # viền mảnh tách khung game khỏi nền mờ
            pygame.draw.rect(self.window, (40, 61, 76), (ox - 1, oy - 1, size[0] + 2, size[1] + 2), 1)
        if self.scene.shows_camera and source is self.screen:
            self._draw_camera_overlay()
        self._darken(self.window, darkness)
        self._presented = source, darkness
        pygame.display.flip()

    def _draw_backdrop(self, source: pygame.Surface, size: Tuple[int, int]) -> None:
        """Màn hình rộng hơn khung game 800x700: thay 2 dải đen bằng chính khung hình được làm mờ,
        tối đi, phủ kín cửa sổ (giống video dọc phát trên màn hình ngang)."""
        ww, wh = self.window.get_size()
        if size[0] >= ww - 1 and size[1] >= wh - 1:
            self.window.fill((0, 0, 0))
            return
        self._backdrop_frame += 1
        if self._backdrop is None or self._backdrop.get_size() != (ww, wh) or self._backdrop_frame % 4 == 0:
            tiny = pygame.transform.smoothscale(source, (40, 35))
            cover = max(ww / config.WIDTH, wh / config.HEIGHT)
            big = pygame.transform.smoothscale(tiny, (int(config.WIDTH * cover) + 2, int(config.HEIGHT * cover) + 2))
            big.fill((95, 95, 108), special_flags=pygame.BLEND_MULT)
            self._backdrop = pygame.Surface((ww, wh)).convert()
            self._backdrop.blit(big, big.get_rect(center=(ww // 2, wh // 2)))
        self.window.blit(self._backdrop, (0, 0))

    def _darken(self, surface: pygame.Surface, darkness: int) -> None:
        if not darkness:
            return
        if self._fade_overlay is None or self._fade_overlay.get_size() != surface.get_size():
            self._fade_overlay = pygame.Surface(surface.get_size()).convert()
            self._fade_overlay.fill((0, 0, 0))
        self._fade_overlay.set_alpha(darkness)
        surface.blit(self._fade_overlay, (0, 0))

    def _transition_frame(self) -> Tuple[pygame.Surface, int]:
        if self._fade_started is None:
            return self.screen, 0
        progress = (time.perf_counter() - self._fade_started) / SCENE_FADE_SECONDS
        if progress >= 1:
            self._fade_from, self._fade_started = None, None
            return self.screen, 0
        if self._fade_from is None:
            return self.screen, round(255 * (1 - progress))
        if progress < 0.5:
            return self._fade_from, round(510 * progress)
        return self.screen, round(510 * (1 - progress))

    def _draw_camera_overlay(self) -> None:
        if self.tracker is None or not self.show_camera:
            return
        ww = self.window.get_width()
        x = ww - PREVIEW_SIZE[0] - 10
        image = self.camera_surface()
        if image is not None:
            self.window.blit(image, (x, 10))
            pygame.draw.rect(self.window, config.NEON_CYAN, (x, 10, *PREVIEW_SIZE), 1)
            label = f"{self.tracker.backend_name} · {self.tracker.fps:.0f} fps"
        elif self.tracker.state == TrackerState.UNAVAILABLE:
            label = f"Không có camera: {self.tracker.message} · dùng bàn phím"
        else:
            label = self.tracker.message
        text = fit_text(self.assets, label, 12, MUTED, max(1, ww - 20), role="label")
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
