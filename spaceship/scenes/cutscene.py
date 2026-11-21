"""Đoạn hội thoại giữa các ải: chân dung người nói, chữ gõ máy, nhiễu sóng, radar.

Phông nền (``backdrop``): ``"radar"`` (màn hình radar - mở đầu game), tên một ảnh
nền hồi (``"bg_act2"``...) hoặc ``"ending"`` (ảnh kết thúc).

Sửa lỗi bản cũ: bấm SPACE đặt ``fade_state = "OUT"`` — trạng thái không tồn tại
(đúng phải là ``"FADE_OUT"``), nên phím tua không hoạt động. Ngoài ra mọi bộ
đếm giờ giờ chạy theo tick cố định thay vì ``pygame.time.get_ticks()``.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, List, Optional

import pygame

from spaceship.campaign import story
from spaceship.config import HEIGHT, TICK_RATE, WHITE, WIDTH
from spaceship.core.scene import Scene
from spaceship.ui.widgets import ACCENT, DANGER, MUTED, TEXT, blit_center, dim, draw_panel, fit_text, wrap_text


@dataclass(frozen=True)
class Line:
    speaker: str
    text: str
    delay: float = 1.0          # giây chờ sau khi gõ xong
    effect: Optional[str] = None
    sound: Optional[str] = None
    radar_contacts: bool = False


def make_script(lines) -> List[Line]:
    """Đổi lời thoại dạng (người nói, câu[, hiệu ứng]) trong story.py thành Line."""
    script = []
    for entry in lines:
        speaker, text = entry[0], entry[1]
        effect = entry[2] if len(entry) > 2 else None
        delay = 1.0 + len(text) / 35                       # câu dài thì chờ lâu hơn cho kịp đọc
        script.append(Line(speaker, text, delay,
                           effect="glitch" if effect == "glitch" else None,
                           sound="radar" if effect == "radar" else None,
                           radar_contacts=effect == "radar"))
    return script


INTRO_SCRIPT = tuple(make_script(story.INTROS[1]))
ENDING_SCRIPT = tuple(make_script(story.ENDING))

CHARS_PER_SECOND = 28
FADE_STEP = 5
GLITCH_CHARS = "!@#$%^&*()_+-=[]{}|;':,./<>?"
RADAR_CENTER = (WIDTH // 2, HEIGHT // 2 - 110)
RADAR_RADIUS = 140
BOX = pygame.Rect(40, HEIGHT - 210, WIDTH - 80, 160)
PORTRAIT = 130


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
    def __init__(self, game, script, next_scene: Callable[[], Scene], backdrop: str = "radar",
                 title: str = "", subtitle: str = "", music: str = "briefing") -> None:
        super().__init__(game)
        self.music = music
        self._typed = 0                 # đếm ký tự đã gõ: cứ 2 ký tự phát 1 tiếng cho đỡ dày
        self.script: List[Line] = list(script) if script and isinstance(script[0], Line) else make_script(script)
        self.next_scene = next_scene
        self.backdrop, self.title, self.subtitle = backdrop, title, subtitle
        self.index = 0
        self.typewriter = Typewriter(self.script[0].text)
        self.wait = 0
        self.ticks = 0
        self.fade_alpha = 255
        self.fade = "in"                # in | playing | out
        self.radar_angle = 0.0
        self.radar_dots: List[List[float]] = []
        self.glitch = 0
        self._announce_line()

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

    def _announce_line(self) -> None:
        line = self.line
        if line is None:
            return
        if line.sound:
            self.game.audio.play(line.sound)
        if line.effect == "glitch":
            self.game.audio.play("glitch")
        if line.radar_contacts:
            rng = self.game.rng
            cx, cy = RADAR_CENTER
            self.radar_dots = [[cx - 110 + rng.randint(0, 220), cy - 100 - rng.randint(0, 120), rng.uniform(0.6, 1.4)]
                               for _ in range(15)]

    def next_line(self) -> None:
        self.index += 1
        self.wait = 0
        if self.line is None:
            self.fade = "out"
            return
        self.typewriter = Typewriter(self.line.text)
        self._announce_line()

    # --- Logic --------------------------------------------------------------------------
    def update(self, controls) -> None:
        self.ticks += 1
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

        if self.typewriter.update() and self.line is not None:
            self._typed += 1
            if self._typed % 2:
                self.game.audio.voice(self.line.speaker)
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
        a = self.game.assets
        self._draw_backdrop(surface)
        if self.title:
            label = fit_text(a, self.title, 32, TEXT, WIDTH - 64, role="display")
            blit_center(surface, label, 38)
        if self.subtitle:
            blit_center(surface, a.text(self.subtitle, 15, MUTED, role="label"), 17)
        self._draw_dialog(surface)
        surface.blit(a.text("CLICK: TUA CÂU · SPACE / ESC: BỎ QUA", 13, MUTED, role="label"), (BOX.x, HEIGHT - 30))
        if self.fade_alpha > 0:
            dim(surface, self.fade_alpha)

    def _draw_backdrop(self, surface: pygame.Surface) -> None:
        if self.backdrop == "radar":
            surface.fill((5, 10, 15))
            self._draw_radar(surface)
            return
        image = self.game.assets.raw(self.backdrop)
        surface.fill((0, 0, 0))
        if image is None:
            return
        if self.backdrop == "ending":                       # ảnh kết thúc: căn giữa, từ từ phóng to
            k = 1.0 + min(0.08, self.ticks / 6000)
            w = int(WIDTH * k)
            h = int(image.get_height() * w / image.get_width())
            scaled = pygame.transform.smoothscale(image, (w, h))
            surface.blit(scaled, scaled.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 60)))
            return
        y = int(self.ticks * 0.4) % image.get_height()      # ảnh nền hồi: cuộn chậm, tối đi
        surface.blit(image, (0, y - image.get_height()))
        surface.blit(image, (0, y))
        dim(surface, 90)

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
        line = self.line
        color = story.SPEAKER_COLORS.get(line.speaker, TEXT) if line else ACCENT
        draw_panel(surface, BOX, color, header_height=44)
        if line is None:
            return
        a, rng = self.game.assets, self.game.rng
        tx = BOX.x + 20
        portrait = a.image(story.PORTRAITS[line.speaker], PORTRAIT) if line.speaker in story.PORTRAITS else None
        if portrait is not None:
            px, py = BOX.x + 14, BOX.y + 15
            if line.effect == "glitch" and self.glitch:                       # chân dung cũng nhiễu
                px += rng.randint(-4, 4)
            surface.blit(portrait, (px, py))
            pygame.draw.rect(surface, color, (BOX.x + 14, py, PORTRAIT, PORTRAIT), 1)
            tx = BOX.x + PORTRAIT + 32
        surface.blit(a.text(line.speaker.upper(), 22, color, role="ui"), (tx, BOX.y + 7))
        width = BOX.right - tx - 20
        rows = wrap_text(a, self.typewriter.visible, 19, width)
        for i, row in enumerate(rows[:4]):
            y = BOX.y + 50 + i * 25
            if self.glitch > 0:
                row = "".join(rng.choice(GLITCH_CHARS) if c != " " and rng.random() < 0.2 else c for c in row)
                rx, ry = rng.randint(-3, 3), rng.randint(-2, 2)
                surface.blit(fit_text(a, row, 19, DANGER, width, role="body"), (tx + rx, y + ry))
                surface.blit(fit_text(a, row, 19, ACCENT, width, role="body"), (tx - rx, y - ry))
            else:
                surface.blit(a.text(row, 19, TEXT, role="body"), (tx, y))
