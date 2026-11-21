"""Lớp cơ sở cho mỗi màn hình (scene) của game.

Mỗi scene tách rõ 3 việc theo mẫu chuẩn của pygame:
``handle_event`` (sự kiện), ``update`` (logic, chạy đúng 60 lần/giây),
``draw`` (vẽ, chạy mỗi khung hình).
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Tuple

import pygame

if TYPE_CHECKING:
    from spaceship.app import Game
    from spaceship.input.controls import ControlState


class Scene:
    #: Khóa bản nhạc nền scene muốn phát ("menu", "game") hoặc None để tắt nhạc.
    music: Optional[str] = None
    #: Có hiện ô xem trước camera ở góc màn hình không.
    shows_camera: bool = False
    #: Màn hình rộng: có vẽ 2 bảng thông tin hai bên khung 800x700 không (xem ``draw_sidebars``).
    sidebars: bool = False

    def __init__(self, game: "Game") -> None:
        self.game = game

    def on_enter(self) -> None:
        """Gọi mỗi khi scene trở thành scene hiện tại."""

    def handle_event(self, event: pygame.event.Event) -> None:
        """Xử lý một sự kiện pygame (chuột, phím...)."""

    def update(self, controls: "ControlState") -> None:
        """Cập nhật logic một bước cố định (1/60 giây)."""

    def draw(self, surface: pygame.Surface) -> None:
        """Vẽ lên màn hình ảo kích thước WIDTH x HEIGHT."""

    def draw_sidebars(self, surface: pygame.Surface, left: pygame.Rect, right: pygame.Rect) -> None:
        """Vẽ 2 bảng bên (chỉ gọi khi ``sidebars`` và cửa sổ đủ rộng; lúc đó ``game.wide_layout`` = True)."""

    def screen_offset(self) -> Tuple[int, int]:
        """Độ lệch khi đưa màn hình ảo ra cửa sổ (dùng cho hiệu ứng rung)."""
        return 0, 0
