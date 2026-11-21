"""Đoạn hội thoại mở đầu chế độ Vượt ải (radar + chữ gõ máy + nhiễu tín hiệu).

Sửa lỗi bản cũ: bấm SPACE đặt ``fade_state = "OUT"`` — trạng thái không tồn tại
(đúng phải là ``"FADE_OUT"``), nên phím tua không hoạt động. Ngoài ra mọi bộ
đếm giờ giờ chạy theo tick cố định thay vì ``pygame.time.get_ticks()``.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, List, Optional

import pygame

from spaceship.config import GRAY, HEIGHT, TICK_RATE, WHITE, WIDTH
from spaceship.core.scene import Scene


@dataclass(frozen=True)
class Line:
    speaker: str
    text: str
    delay: float = 1.0          # giây chờ sau khi gõ xong
    effect: Optional[str] = None
    sound: Optional[str] = None
    radar_contacts: bool = False


INTRO_SCRIPT = (
    Line("KX-17", "KX-17 gọi tàu mẹ... lặp lại...", 1.5),
    Line("SYSTEM", "---tín hiệu--- mất --- kết nối---", 1.5, effect="glitch"),
    Line("KX-17", "Chết tiệt... mất liên lạc hoàn toàn.", 1.5),
    Line("SYSTEM", "Cảnh báo: Phát hiện nhiều mục tiêu.", 1.5, sound="radar", radar_contacts=True),
    Line("KX-17", "...Bị lộ rồi.", 1),
    Line("SYSTEM", "Kẻ địch đang tiếp cận.", 1),
    Line("KX-17", "Không còn đường lui... chiến thôi.", 2),
)

CHARS_PER_SECOND = 25
FADE_STEP = 5
GLITCH_CHARS = "!@#$%^&*()_+-=[]{}|;':,./<>?░▒▓█"
RADAR_CENTER = (WIDTH // 2, HEIGHT // 2 - 100)
RADAR_RADIUS = 150


class Typewriter:
    def __init__(self, text: str) -> None:
        self.text = text
        self.progress = 0.0

    @property
    def visible(self) -> str:
        return self.text[: int(self.progress)]

    @property
    def done(self) -> bool:
        return self.progress >= len(self.text)

    def update(self) -> bool:
        """Trả về True nếu vừa hiện thêm một ký tự khác khoảng trắng (để phát tiếng bíp)."""
        if self.done:
            return False
        before = int(self.progress)
        self.progress = min(len(self.text), self.progress + CHARS_PER_SECOND / TICK_RATE)
        after = int(self.progress)
        return after > before and self.text[after - 1] != " "

    def finish(self) -> None:
        self.progress = len(self.text)


class CutsceneScene(Scene):
    music = "menu"

    def __init__(self, game, script, next_scene: Callable[[], Scene]) -> None:
        super().__init__(game)
        self.script: List[Line] = list(script)
        self.next_scene = next_scene
        self.index = 0
        self.typewriter = Typewriter(self.script[0].text)
        self.wait = 0
        self.fade_alpha = 255
        self.fade = "in"                # in | playing | out
        self.radar_angle = 0.0
        self.radar_dots: List[List[float]] = []
        self.glitch = 0

    @property
    def line(self) -> Optional[Line]:
        return self.script[self.index] if self.index < len(self.script) else None

    # --- Điều khiển -------------------------------------------------------------------
    def handle_event(self, event) -> None:
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_SPACE, pygame.K_ESCAPE, pygame.K_RETURN):
            self.skip()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.fade == "playing":
            if not self.typewriter.done:
                self.typewriter.finish()
            else:
                self.next_line()

    def skip(self) -> None:
        self.fade = "out"

    def next_line(self) -> None:
        self.index += 1
        self.wait = 0
        line = self.line
        if line is None:
            self.fade = "out"
            return
        self.typewriter = Typewriter(line.text)
        if line.sound:
            self.game.audio.play(line.sound)
        if line.effect == "glitch":
            self.game.audio.play("glitch")
        if line.radar_contacts:
            rng = self.game.rng
            self.radar_dots = [[WIDTH // 2 - 150 + rng.randint(0, 300), HEIGHT // 2 - 200 - rng.randint(0, 200),
                                rng.uniform(1.0, 2.5)] for _ in range(15)]

    # --- Logic --------------------------------------------------------------------------
    def update(self, controls) -> None:
        if self.fade == "in":
            self.fade_alpha = max(0, self.fade_alpha - FADE_STEP)
            if self.fade_alpha == 0:
                self.fade = "playing"
            return
        if self.fade == "out":
            self.fade_alpha = min(255, self.fade_alpha + FADE_STEP * 2)
            if self.fade_alpha >= 255:
                self.game.change_scene(self.next_scene())
            return

        if self.typewriter.update():
            self.game.audio.play("beep")
        self.radar_angle += 0.05
        for dot in self.radar_dots:
            dot[1] += dot[2]
        line = self.line
        if line and line.effect == "glitch" and self.game.rng.random() < 0.2:
            self.glitch = 5
        if self.glitch > 0:
            self.glitch -= 1
        if self.typewriter.done:
            self.wait += 1
            if line is None or self.wait > line.delay * TICK_RATE:
                self.next_line()

    # --- Vẽ -----------------------------------------------------------------------------
    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((5, 10, 15))
        self._draw_radar(surface)
        self._draw_dialog(surface)
        surface.blit(self.game.assets.text("CLICK: TUA CÂU · SPACE/ESC: BỎ QUA", 14, GRAY), (10, 10))
        if self.fade_alpha > 0:
            veil = pygame.Surface((WIDTH, HEIGHT))
            veil.set_alpha(self.fade_alpha)
            surface.blit(veil, (0, 0))

    def _draw_radar(self, surface: pygame.Surface) -> None:
        cx, cy = RADAR_CENTER
        r = RADAR_RADIUS
        sweep = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        cone = [(cx, cy)] + [(cx + r * math.cos(self.radar_angle - math.radians(i * 2)),
                              cy + r * math.sin(self.radar_angle - math.radians(i * 2))) for i in range(30)]
        pygame.draw.polygon(sweep, (0, 255, 0, 30), cone)
        pygame.draw.circle(surface, (0, 50, 0), (cx, cy), r)
        surface.blit(sweep, (0, 0))
        pygame.draw.circle(surface, (0, 200, 0), (cx, cy), r, 2)
        pygame.draw.circle(surface, (0, 100, 0), (cx, cy), r * 2 // 3, 1)
        pygame.draw.circle(surface, (0, 100, 0), (cx, cy), r // 3, 1)
        pygame.draw.line(surface, (0, 100, 0), (cx - r, cy), (cx + r, cy), 1)
        pygame.draw.line(surface, (0, 100, 0), (cx, cy - r), (cx, cy + r), 1)
        end = (cx + r * math.cos(self.radar_angle), cy + r * math.sin(self.radar_angle))
        pygame.draw.line(surface, (0, 255, 0), (cx, cy), end, 3)
        sweep_angle = self.radar_angle % (2 * math.pi)
        for x, y, _ in self.radar_dots:
            if math.hypot(x - cx, y - cy) >= r - 2:
                continue
            ang = math.atan2(y - cy, x - cx) % (2 * math.pi)
            if abs(sweep_angle - ang) < 0.2:
                pygame.draw.circle(surface, WHITE, (int(x), int(y)), 6)
            pygame.draw.circle(surface, (255, 0, 0), (int(x), int(y)), 4)

    def _draw_dialog(self, surface: pygame.Surface) -> None:
        box = pygame.Rect(WIDTH // 2 - 300, HEIGHT - 200, 600, 150)
        pygame.draw.rect(surface, (10, 20, 20), box)
        for i in range(0, box.height, 4):
            pygame.draw.line(surface, (0, 50, 50), (box.x, box.y + i), (box.right, box.y + i), 1)
        pygame.draw.rect(surface, (0, 255, 255), box, 2)
        pygame.draw.line(surface, WHITE, box.topleft, (box.x + 20, box.y), 4)
        pygame.draw.line(surface, WHITE, box.topleft, (box.x, box.y + 20), 4)
        line = self.line
        if line is None:
            return
        assets, rng = self.game.assets, self.game.rng
        ally = line.speaker == "KX-17"
        surface.blit(assets.text(line.speaker, 24, (0, 255, 255) if ally else (255, 50, 50)), (box.x + 20, box.y + 15))
        text = self.typewriter.visible
        if self.glitch > 0:
            text = "".join(rng.choice(GLITCH_CHARS) if c != " " and rng.random() < 0.2 else c for c in text)
            rx, ry = rng.randint(-3, 3), rng.randint(-3, 3)
            surface.blit(assets.text(text, 20, (255, 0, 0)), (box.x + 20 + rx, box.y + 60 + ry))
            surface.blit(assets.text(text, 20, (0, 255, 255)), (box.x + 20 - rx, box.y + 60 - ry))
        else:
            surface.blit(assets.text(text, 20, (0, 255, 0) if ally else (255, 100, 100)), (box.x + 20, box.y + 60))
