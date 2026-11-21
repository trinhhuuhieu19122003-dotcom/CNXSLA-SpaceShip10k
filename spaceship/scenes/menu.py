"""Menu chính với bố cục của Tín hiệu cuối cùng."""
from __future__ import annotations

import math

import pygame

from spaceship.campaign.levels import LEVEL_COUNT
from spaceship.config import HEIGHT, WIDTH, GameMode
from spaceship.core.scene import Scene
from spaceship.ui import glow
from spaceship.ui.menu_list import MenuList
from spaceship.ui.widgets import ACCENT, DANGER, FRAME, LOCKED, MUTED, SECONDARY, TEXT, draw_lock, draw_star, fit_text

MENU_ITEMS = (
    ("VƯỢT ẢI", "10 ải · 3 hồi · có cốt truyện", GameMode.CAMPAIGN),
    ("VÔ TẬN", "Sống sót càng lâu càng tốt", GameMode.ENDLESS),
    ("HỎA NGỤC", "Mưa đạn · ít hồi máu · boss dồn dập", GameMode.INFERNO),
    ("THÀNH TỰU", "Xem kỷ lục và thống kê các chế độ", "achievements"),
    ("HƯỚNG DẪN", "Cách điều khiển, vũ khí và vật phẩm", "how_to_play"),
    ("CÀI ĐẶT", "Tự động bắn và hiệu chỉnh tay", "options"),
    ("THOÁT", "Rời trò chơi", "quit"),
)
SHORTCUTS = {pygame.K_1: GameMode.CAMPAIGN, pygame.K_2: GameMode.ENDLESS, pygame.K_3: GameMode.INFERNO}
LEFT = 48
LOGO_X = LEFT + 6
ROW_TOP, ROW_STEP, ROW_HEIGHT, ROW_WIDTH = 300, 50, 46, 365
FOOTER_HEIGHT = 40
SHIP_CENTER = (605, 465)
SHIP_WIDTH, SHIP_ANGLE = 256, 9
LOCK_FEEDBACK_TICKS = 16
# THOÁT phải chọn 2 lần: tay thả lỏng đặt trên bàn hay trỏ vào mục cuối (THOÁT) và dễ bị đọc nhầm thành
# "chụm tay", khiến game tự tắt sau vài giây.
QUIT_CONFIRM_TICKS = 180


def _fade_right(size, color, opacity: int) -> pygame.Surface:
    width, height = size
    ramp = pygame.Surface((width, 1), pygame.SRCALPHA)
    for x in range(width):
        ramp.set_at((x, 0), (*color, round(opacity * (1 - x / (width - 1)) ** 1.3)))
    return pygame.transform.scale(ramp, (width, height))


def _tracked_text(assets, text, size, color, spacing, role) -> pygame.Surface:
    glyphs = [assets.text(char, size, color, role=role) for char in text]
    w = sum(glyph.get_width() for glyph in glyphs) + spacing * (len(glyphs) - 1)
    line = pygame.Surface((w, glyphs[0].get_height()), pygame.SRCALPHA)
    x = 0
    for glyph in glyphs:
        line.blit(glyph, (x, 0))
        x += glyph.get_width() + spacing
    return line


def _ink_rect(image: pygame.Surface, x: int, y: int) -> pygame.Rect:
    ink = image.get_bounding_rect()
    return image.get_rect(topleft=(x - ink.x, y - ink.y))


class MenuScene(Scene):
    music = "menu"

    def __init__(self, game) -> None:
        super().__init__(game)
        assets = game.assets
        self.ticks = 0
        self.lock_feedback = 0
        self.quit_armed = 0             # > 0: đã chọn THOÁT một lần, chờ chọn lần nữa
        rows = [pygame.Rect(LEFT, ROW_TOP + i * ROW_STEP, ROW_WIDTH, ROW_HEIGHT) for i in range(len(MENU_ITEMS))]
        self.menu = MenuList(game, rows, self._activate)
        self._row_light = _fade_right((ROW_WIDTH, ROW_HEIGHT), ACCENT, 47)
        self._backdrop = self._make_backdrop()
        self._title = _tracked_text(assets, "SPACESHIP", 70, TEXT, 4, "display")
        self._number = assets.text("10K", 96, ACCENT, role="display")
        self._halo = glow.glyph_halo(self._number)
        self._subtitle = _tracked_text(assets, "TÍN HIỆU CUỐI CÙNG", 14, DANGER, 3, "label")

        player = assets.image("player", SHIP_WIDTH)
        self._player = pygame.transform.rotozoom(player, SHIP_ANGLE, 1) if player is not None else None
        self._engines = (
            tuple(pygame.Vector2(SHIP_WIDTH * side * 0.087, player.get_height() * 0.42).rotate(-SHIP_ANGLE)
                  for side in (-1, 1)) if player is not None else ()
        )
        self._engine_glow = glow.soft_halo(glow.scale(ACCENT, 0.55), 36)

    def _make_backdrop(self) -> pygame.Surface:
        assets = self.game.assets
        canvas = pygame.Surface((WIDTH, HEIGHT)).convert()
        canvas.fill((7, 11, 18))
        background = assets.image("bg_act3", WIDTH)
        if background is not None:
            canvas.blit(background, background.get_rect(center=canvas.get_rect().center))
        mothership = assets.image("mothership_boss", 580)
        if mothership is not None:
            ghost = mothership.copy()
            ghost.set_alpha(76)
            canvas.blit(ghost, ghost.get_rect(center=(644, 178)))
        canvas.blit(_fade_right((WIDTH, HEIGHT), (5, 8, 13), 242), (0, 0))
        return canvas

    def handle_event(self, event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in SHORTCUTS:
                self._start(SHORTCUTS[event.key])
                return
            if event.key == pygame.K_ESCAPE:
                self.menu.select(0)
                return
        self.menu.handle_event(event)

    def _activate(self, index: int) -> None:
        from spaceship.scenes.info import AchievementsScene, HowToPlayScene
        from spaceship.scenes.options import OptionsScene

        action = MENU_ITEMS[index][2]
        if isinstance(action, GameMode):
            self._start(action)
        elif action == "quit":
            if self.quit_armed:
                self.game.quit()
            else:
                self.quit_armed = QUIT_CONFIRM_TICKS
        else:
            scene = {"achievements": AchievementsScene, "how_to_play": HowToPlayScene, "options": OptionsScene}[action]
            self.game.change_scene(scene(self.game))

    def _start(self, mode: GameMode) -> None:
        from spaceship.scenes.flow import start_survival
        from spaceship.scenes.level_select import LevelSelectScene

        if mode is GameMode.CAMPAIGN:
            self.game.change_scene(LevelSelectScene(self.game))
        elif mode is GameMode.INFERNO and not self.game.save.campaign_cleared:
            self.lock_feedback = LOCK_FEEDBACK_TICKS
            self.game.audio.play("ui_back")
        else:
            start_survival(self.game, mode)

    def update(self, controls) -> None:
        self.ticks += 1
        self.lock_feedback = max(0, self.lock_feedback - 1)
        self.menu.update(controls)
        if self.quit_armed and MENU_ITEMS[self.menu.selected][2] != "quit":
            self.quit_armed = 0                       # rời khỏi mục THOÁT thì hủy
        self.quit_armed = max(0, self.quit_armed - 1)

    def _draw_ship(self, surface: pygame.Surface) -> None:
        if self._player is None:
            return
        x, y = SHIP_CENTER
        y += round(8 * math.sin(self.ticks / 39))
        for engine in self._engines:
            glow.add(surface, self._engine_glow, (x + engine.x, y + engine.y))
        surface.blit(self._player, self._player.get_rect(center=(x, y)))

    def _draw_status(self, surface: pygame.Surface) -> None:
        a, save = self.game.assets, self.game.save
        stars = a.text(f"{save.total_stars} / {LEVEL_COUNT * 3}", 15, TEXT, role="label")
        star_value = stars.get_rect(midright=(WIDTH - 26, 31))
        surface.blit(stars, star_value)
        draw_star(surface, (star_value.x - 13, star_value.centery), 8, True)
        score = fit_text(a, f"KỶ LỤC {save.highscore}", 15, SECONDARY, 234, role="label")
        surface.blit(score, score.get_rect(midright=(star_value.x - 33, star_value.centery)))

    def _draw_entries(self, surface: pygame.Surface) -> None:
        a = self.game.assets
        for index, (text, description, action) in enumerate(MENU_ITEMS):
            rect = self.menu.rects[index]
            selected = index == self.menu.selected
            locked = action is GameMode.INFERNO and not self.game.save.campaign_cleared
            if selected:
                surface.blit(self._row_light, rect)
                pygame.draw.rect(surface, ACCENT, (rect.x, rect.y, 3, rect.height))
            offset = round(4 * math.sin(self.lock_feedback * 1.5) * self.lock_feedback / LOCK_FEEDBACK_TICKS) if locked else 0
            x = rect.x + 20 + offset
            color = LOCKED if locked else (ACCENT if selected else TEXT)
            if action == "quit" and self.quit_armed:
                text, description, color = "THOÁT?", "Chọn lần nữa để thoát (tự hủy sau 3 giây)", DANGER
            label = a.text(text, 25, color, role="ui")
            label_rect = label.get_rect(midleft=(x, rect.y + 16 if selected else rect.centery))
            surface.blit(label, label_rect)
            if locked:
                lock_x = label_rect.right + 14
                draw_lock(surface, (lock_x, label_rect.centery), DANGER if self.lock_feedback else LOCKED)
                if not selected:
                    note = a.text("phá đảo để mở", 14, LOCKED, role="body")
                    surface.blit(note, note.get_rect(midleft=(lock_x + 15, label_rect.centery)))
                description = "phá đảo để mở"
            if selected:
                note = a.text(description, 15, MUTED if locked else SECONDARY, role="body")
                surface.blit(note, note.get_rect(midleft=(x, rect.y + 36)))
        self.menu.draw_progress(surface)

    def draw(self, surface: pygame.Surface) -> None:
        surface.blit(self._backdrop, (0, 0))
        self._draw_ship(surface)
        self._draw_status(surface)
        surface.blit(self._title, _ink_rect(self._title, LOGO_X, 82))
        number_rect = _ink_rect(self._number, LOGO_X, 154)
        glow.add(surface, self._halo, number_rect.center)
        surface.blit(self._number, number_rect)
        surface.blit(self._subtitle, _ink_rect(self._subtitle, LOGO_X + 1, 247))
        pygame.draw.line(surface, DANGER, (LOGO_X, 273), (LOGO_X + 93, 273), 2)

        self._draw_entries(surface)
        y = HEIGHT - FOOTER_HEIGHT
        pygame.draw.rect(surface, (8, 13, 21), (0, y, WIDTH, FOOTER_HEIGHT))
        pygame.draw.line(surface, FRAME, (0, y), (WIDTH, y))
        a = self.game.assets
        controls = a.text("↑↓ / DI TAY: CHỌN · ENTER / CHỤM TAY: VÀO · ESC: QUAY LẠI", 14, MUTED, role="label")
        surface.blit(controls, controls.get_rect(midleft=(27, y + FOOTER_HEIGHT // 2)))
        version = a.text("v2.1", 13, MUTED, role="label")
        surface.blit(version, version.get_rect(midright=(WIDTH - 26, y + FOOTER_HEIGHT // 2)))
