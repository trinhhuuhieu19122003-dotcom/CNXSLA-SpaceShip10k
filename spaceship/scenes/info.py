"""Hướng dẫn chơi theo thẻ và bảng Thành tựu."""
from __future__ import annotations

import pygame

from spaceship import config
from spaceship.config import WIDTH, GameMode
from spaceship.core.scene import Scene
from spaceship.campaign import achievements
from spaceship.campaign.bestiary import BESTIARY
from spaceship.campaign.levels import LEVEL_COUNT
from spaceship.ui import glow, guide
from spaceship.ui.guide_preview import WeaponPreview
from spaceship.ui.hud import format_time
from spaceship.ui.menu_list import MenuList
from spaceship.ui.widgets import (
    ACCENT, FRAME, LOCKED, MUTED, SECONDARY, SELECTED_FILL, TEXT, Button,
    blit_center, dim, draw_back_hint, draw_lock, draw_panel, draw_star, fit_text,
)

PANEL = pygame.Rect(20, 50, WIDTH - 40, 600)
BACK = pygame.Rect(WIDTH // 2 - 160, PANEL.bottom - 36, 320, 26)
GUIDE_BODY = pygame.Rect(40, 135, WIDTH - 80, 509)
GUIDE_BACK = pygame.Rect(GUIDE_BODY.right - 126, 667, 126, 27)
TAB_NAMES = ("ĐIỀU KHIỂN", "VŨ KHÍ", "VẬT PHẨM", "KẺ ĐỊCH", "CHẾ ĐỘ CHƠI")
CONTROLS, WEAPONS, ITEMS, ENEMIES = range(4)


class _InfoScene(Scene):
    music = "menu"

    def __init__(self, game) -> None:
        super().__init__(game)
        self.menu = MenuList(game, (BACK,), self._back)

    def _back(self, _index=0) -> None:
        from spaceship.scenes.menu import MenuScene

        self.game.audio.play("ui_back")
        self.game.change_scene(MenuScene(self.game))

    def handle_event(self, event) -> None:
        if (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE) or (
                event.type == pygame.MOUSEBUTTONDOWN and event.button == 1):
            self._back()
        else:
            self.menu.handle_event(event)

    def update(self, controls) -> None:
        self.game.starfield.update()
        self.menu.update(controls)

    def draw_frame(self, surface: pygame.Surface, title: str) -> None:
        surface.fill((0, 0, 0))
        self.game.starfield.draw(surface)
        draw_panel(surface, PANEL, header_height=64)
        blit_center(surface, self.game.assets.text(title, 36, TEXT, role="display"), PANEL.y + 8)
        draw_back_hint(surface, self.game.assets, BACK.y + 2)
        self.menu.draw_progress(surface)


class HowToPlayScene(_InfoScene):
    def __init__(self, game) -> None:
        super().__init__(game)
        self.tab = CONTROLS
        self.ticks = 0
        self.book = guide.BestiaryView(GUIDE_BODY)
        self.previews = {weapon: WeaponPreview(weapon) for weapon in guide.WEAPON_CARDS}
        self._background = game.assets.image("bg_act1", WIDTH)
        self.back = Button("ESC · VỀ MENU", GUIDE_BACK, "back", 14)

        x = GUIDE_BODY.x - 14            # chữ căn giữa ô (lề 14px) -> chữ thẻ đầu thẳng mép nội dung
        font = game.assets.font(17, role="ui")
        self.tabs = []
        for label in TAB_NAMES:
            w = font.size(label)[0] + 29
            self.tabs.append(pygame.Rect(x, 75, w, 37))
            x += w + 4
        self.menu = MenuList(game, self._navigation_rects(), self._activate)

    def _navigation_rects(self) -> tuple[pygame.Rect, ...]:
        cards = self.book.cards if self.tab == ENEMIES else ()
        return (*self.tabs, *cards, GUIDE_BACK)

    def _activate(self, index: int) -> None:
        if index < len(TAB_NAMES):
            change_rows = (self.tab == ENEMIES) != (index == ENEMIES)
            self.tab = index
            if change_rows:
                self.menu.set_rects(self._navigation_rects(), selected=index)
        elif index < len(self.menu.rects) - 1:
            self.book.selected = index - len(TAB_NAMES)
        else:
            self._back()

    def handle_event(self, event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._back()
                return
            if event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                step = 1 if event.key == pygame.K_RIGHT else -1
                index = (self.tab + step) % len(TAB_NAMES)
                self.menu.select(index)
                self._activate(index)
                return
            if self.tab == ENEMIES and event.key in (pygame.K_UP, pygame.K_DOWN):
                # ↑ ↓ duyệt hết lưới; ← → vẫn dành riêng cho đổi thẻ.
                entries = (self.tab, *range(len(TAB_NAMES), len(self.menu.rects)))
                selected = self.menu.selected if self.menu.selected in entries else self.tab
                step = 1 if event.key == pygame.K_DOWN else -1
                self.menu.select(entries[(entries.index(selected) + step) % len(entries)])
                return
        self.menu.handle_event(event)

    def _book_focused(self) -> bool:
        return self.tab == ENEMIES and len(TAB_NAMES) <= self.menu.selected < len(self.menu.rects) - 1

    def update(self, controls) -> None:
        self.ticks += 1
        if self.tab == WEAPONS:
            for preview in self.previews.values():
                preview.update()
        super().update(controls)

    def draw(self, surface: pygame.Surface) -> None:
        a = self.game.assets
        surface.fill((5, 9, 16))
        if self._background is not None:
            surface.blit(self._background, self._background.get_rect(center=surface.get_rect().center))
            dim(surface, 75)
        surface.blit(a.text("HƯỚNG DẪN", 31, TEXT, role="display"), (GUIDE_BODY.x, 24))
        self._draw_tabs(surface, a)
        seconds = self.ticks * config.TICK
        if self.tab == CONTROLS:
            guide.draw_controls(surface, a, GUIDE_BODY, seconds)
        elif self.tab == WEAPONS:
            guide.draw_weapons(surface, a, GUIDE_BODY, self.previews)
        elif self.tab == ITEMS:
            guide.draw_items(surface, a, GUIDE_BODY, seconds)
        elif self.tab == ENEMIES:
            focus = self.menu.selected - len(TAB_NAMES) if self._book_focused() else -1
            self.book.draw(surface, a, self.game.save.seen_enemies, focus)
        else:
            guide.draw_modes(surface, a, GUIDE_BODY, self.game.save.campaign_cleared)
        self._draw_footer(surface, a)
        rect = self.menu.rects[self.menu.selected]
        progress_center = (rect.right - 10, rect.top + 13) if self._book_focused() else (rect.right - 11, rect.centery)
        if self.menu.selected == len(self.menu.rects) - 1:
            progress_center = (rect.right + 13, rect.centery)
        self.menu.draw_progress(surface, progress_center)

    def _draw_tabs(self, surface, assets) -> None:
        y = self.tabs[0].bottom
        pygame.draw.line(surface, FRAME, (GUIDE_BODY.x, y), (GUIDE_BODY.right, y))
        for index, (label, rect) in enumerate(zip(TAB_NAMES, self.tabs)):
            active = self.tab == index
            focused = self.menu.selected == index
            title = assets.text(label, 17, ACCENT if active or focused else MUTED, role="ui")
            spot = title.get_rect(center=rect.center)
            if focused and not active:
                pygame.draw.rect(surface, SELECTED_FILL[:3], spot.inflate(16, 8), border_radius=3)
            surface.blit(title, spot)
            if active:
                pygame.draw.line(surface, ACCENT, (spot.x, y - 2), (spot.right, y - 2), 3)

    def _draw_footer(self, surface, assets) -> None:
        y = GUIDE_BACK.centery
        pygame.draw.rect(surface, (8, 13, 21), (0, 660, WIDTH, 40))
        pygame.draw.line(surface, FRAME, (0, 660), (WIDTH, 660))
        hint = "← → / DI TAY: ĐỔI THẺ · CHỤM TAY: CHỌN"
        if self.tab == ENEMIES:
            hint = "← →: ĐỔI THẺ · ↑ ↓: CHỌN Ô · ENTER / CHỤM TAY: XEM"
        text = assets.text(hint, 15, MUTED, role="label")
        surface.blit(text, text.get_rect(midleft=(GUIDE_BODY.x, y)))
        page = assets.text(f"trang {self.tab + 1} / {len(TAB_NAMES)}", 14, SECONDARY, role="label")
        surface.blit(page, page.get_rect(midright=(GUIDE_BACK.x - 20, y)))
        self.back.draw(surface, assets, self.menu.selected == len(self.menu.rects) - 1)




def draw_badge_icon(surface: pygame.Surface, icon: str, center, color, r: int = 20) -> None:
    """Biểu tượng huy hiệu vẽ bằng hình khối (không cần ảnh): vòng tròn + ký hiệu."""
    x, y = center
    pygame.draw.circle(surface, (12, 20, 30), center, r)
    pygame.draw.circle(surface, color, center, r, 2)
    k = r / 20
    if icon == "star":
        draw_star(surface, center, int(11 * k), True, color=color)
    elif icon == "skull":
        pygame.draw.circle(surface, color, (x, y - 2), int(9 * k), 2)
        for dx in (-4, 4):
            pygame.draw.circle(surface, color, (x + int(dx * k), y - 3), max(1, int(2 * k)))
        pygame.draw.line(surface, color, (x - 5 * k, y + 8 * k), (x + 5 * k, y + 8 * k), 2)
    elif icon == "bolt":
        pygame.draw.polygon(surface, color, [(x + 3 * k, y - 12 * k), (x - 6 * k, y + 2 * k), (x - 1 * k, y + 2 * k),
                                             (x - 3 * k, y + 12 * k), (x + 6 * k, y - 2 * k), (x + 1 * k, y - 2 * k)])
    elif icon == "shield":
        pygame.draw.polygon(surface, color, [(x, y - 11 * k), (x + 9 * k, y - 6 * k), (x + 7 * k, y + 5 * k),
                                             (x, y + 11 * k), (x - 7 * k, y + 5 * k), (x - 9 * k, y - 6 * k)], 2)
    elif icon == "clock":
        pygame.draw.circle(surface, color, center, int(10 * k), 2)
        pygame.draw.line(surface, color, center, (x, y - 7 * k), 2)
        pygame.draw.line(surface, color, center, (x + 5 * k, y + 2 * k), 2)
    elif icon == "book":
        pygame.draw.rect(surface, color, (x - 10 * k, y - 8 * k, 9 * k, 16 * k), 2)
        pygame.draw.rect(surface, color, (x + 1 * k, y - 8 * k, 9 * k, 16 * k), 2)
    elif icon == "hand":
        pygame.draw.circle(surface, color, (x, y + 4 * k), int(6 * k), 2)
        for i, dx in enumerate((-6, -2, 2, 6)):
            pygame.draw.line(surface, color, (x + dx * k, y), (x + dx * k * 1.2, y - (9 + (i % 3)) * k), 2)
    elif icon == "loop":
        pygame.draw.arc(surface, color, (x - 10 * k, y - 10 * k, 20 * k, 20 * k), 0.6, 5.6, 2)
        pygame.draw.polygon(surface, color, [(x + 9 * k, y - 9 * k), (x + 11 * k, y - 1 * k), (x + 3 * k, y - 4 * k)])
    elif icon == "flag":
        pygame.draw.line(surface, color, (x - 7 * k, y - 11 * k), (x - 7 * k, y + 11 * k), 2)
        pygame.draw.polygon(surface, color, [(x - 6 * k, y - 11 * k), (x + 9 * k, y - 6 * k), (x - 6 * k, y - 1 * k)])
    else:  # fist
        pygame.draw.rect(surface, color, (x - 8 * k, y - 7 * k, 16 * k, 14 * k), 2, border_radius=4)
        for dx in (-4, 0, 4):
            pygame.draw.line(surface, color, (x + dx * k, y - 7 * k), (x + dx * k, y - 1 * k), 1)


ACH_TABS = ("HUY HIỆU", "THỐNG KÊ", "BẢNG ĐIỂM")
ACH_BACK = pygame.Rect(WIDTH // 2 - 130, PANEL.bottom - 40, 260, 30)
BADGE_AREA = pygame.Rect(PANEL.x + 20, PANEL.y + 122, PANEL.width - 40, 418)
BADGE_COLOR = (255, 210, 90)


class AchievementsScene(Scene):
    """Thành tựu: thẻ HUY HIỆU (lưới huy hiệu, đạt/chưa đạt, cách đạt, ngày đạt, tiến độ), thẻ THỐNG KÊ và
    thẻ BẢNG ĐIỂM (5 ván điểm cao nhất mỗi chế độ)."""

    music = "menu"
    COLUMNS = (("SỐ VÁN", 290), ("QUÁI", 390), ("BOSS", 480), ("ĐIỂM CAO", 585), ("LÂU NHẤT", 690))

    def __init__(self, game) -> None:
        super().__init__(game)
        self.tab = 0
        font = game.assets.font(18, role="ui")
        widths = [font.size(self._tab_label(i))[0] + 40 for i in range(len(ACH_TABS))]
        x = WIDTH // 2 - (sum(widths) + 12) // 2
        self.tabs = []
        for w in widths:
            self.tabs.append(pygame.Rect(x, PANEL.y + 74, w, 34))
            x += w + 12
        self.menu = MenuList(game, (*self.tabs, ACH_BACK), self._activate)

    def _tab_label(self, index: int) -> str:
        if index == 0:
            return f"HUY HIỆU {len(self.game.save.achievements)}/{len(achievements.ACHIEVEMENTS)}"
        return ACH_TABS[index]

    def _activate(self, index: int) -> None:
        if index < len(self.tabs):
            self.tab = index
        else:
            self._back()

    def _back(self) -> None:
        from spaceship.scenes.menu import MenuScene

        self.game.audio.play("ui_back")
        self.game.change_scene(MenuScene(self.game))

    def handle_event(self, event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._back()
        elif event.type == pygame.KEYDOWN and event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_TAB):
            self.tab = (self.tab + (-1 if event.key == pygame.K_LEFT else 1)) % len(self.tabs)
            self.menu.select(self.tab)
            self.game.audio.play("ui_move")
        else:
            self.menu.handle_event(event)

    def update(self, controls) -> None:
        self.game.starfield.update()
        self.menu.update(controls)

    # --- Vẽ -----------------------------------------------------------------------------
    def draw(self, surface: pygame.Surface) -> None:
        a = self.game.assets
        surface.fill((0, 0, 0))
        self.game.starfield.draw(surface)
        draw_panel(surface, PANEL, header_height=64)
        blit_center(surface, a.text("THÀNH TỰU", 36, TEXT, role="display"), PANEL.y + 8)
        y = self.tabs[0].bottom
        pygame.draw.line(surface, FRAME, (PANEL.x + 20, y), (PANEL.right - 20, y))
        for i, rect in enumerate(self.tabs):
            active, focused = i == self.tab, i == self.menu.selected
            title = a.text(self._tab_label(i), 18, ACCENT if active or focused else MUTED, role="ui")
            spot = title.get_rect(center=rect.center)
            if focused and not active:
                pygame.draw.rect(surface, SELECTED_FILL[:3], spot.inflate(16, 8), border_radius=3)
            surface.blit(title, spot)
            if active:
                pygame.draw.line(surface, ACCENT, (spot.x, y - 2), (spot.right, y - 2), 3)
        if self.tab == 0:
            self._draw_badges(surface, a)
        elif self.tab == 1:
            self._draw_stats(surface, a)
        else:
            self._draw_board(surface, a)
        back_focused = self.menu.selected == len(self.tabs)
        label = a.text("ESC · VỀ MENU", 15, ACCENT if back_focused else MUTED, role="label")
        surface.blit(label, label.get_rect(center=ACH_BACK.center))
        self.menu.draw_progress(surface)

    def _progress(self, key: str):
        s = self.game.save
        totals = {
            "boss_hunter": (sum(r.total_boss_kills for r in s.modes.values()), 20),
            "thousand": (sum(r.total_kills for r in s.modes.values()), 1000),
            "rage": (s.counters.get("skills", 0), 25),
            "guardian": (s.counters.get("guard_blocks", 0), 100),
            "bestiary": (len(s.seen_enemies & set(BESTIARY)), len(BESTIARY)),
            "all_stars": (s.total_stars, LEVEL_COUNT * 3),
        }
        return totals.get(key)

    def _draw_badges(self, surface, a) -> None:
        cols, gap = 3, 8
        items = achievements.ACHIEVEMENTS
        rows = (len(items) + cols - 1) // cols
        w = (BADGE_AREA.width - gap * (cols - 1)) // cols
        h = (BADGE_AREA.height - gap * (rows - 1)) // rows
        earned = self.game.save.achievements
        for i, item in enumerate(items):
            row, col = divmod(i, cols)
            card = pygame.Rect(BADGE_AREA.x + col * (w + gap), BADGE_AREA.y + row * (h + gap), w, h)
            got = item.key in earned
            draw_panel(surface, card, BADGE_COLOR if got else (40, 61, 76))
            color = BADGE_COLOR if got else LOCKED
            center = (card.x + 30, card.centery)
            if got:
                glow.add(surface, glow.orb(glow.scale(BADGE_COLOR, 0.45), 16, core=0.0), center)
            draw_badge_icon(surface, item.icon, center, color)
            if not got:
                draw_lock(surface, (center[0] + 15, center[1] + 15), MUTED)
            tx = card.x + 60
            width = card.right - 12 - tx
            # Thẻ thấp (7 hàng): ngày đạt / tiến độ nằm bên phải dòng tên, thanh tiến độ sát đáy thẻ.
            footer, progress = "", None
            if got:
                y, m, d = (earned[item.key].split("-") + ["", "", ""])[:3]
                footer = f"{d}.{m}.{y[2:]}"                    # ngày đạt (màu vàng = đã đạt), ngắn để tên đủ chỗ
            elif self._progress(item.key) is not None:
                cur, goal = self._progress(item.key)
                footer, progress = f"{min(cur, goal)}/{goal}", min(1, cur / goal)
            tag_w = 0
            if footer:
                tag = a.text(footer, 10, BADGE_COLOR if got else MUTED, role="label")
                tag_w = tag.get_width() + 6
                surface.blit(tag, (card.right - 10 - tag.get_width(), card.y + 9))
            name = fit_text(a, item.name, 15, TEXT if got else SECONDARY, width - tag_w, role="ui")
            surface.blit(name, (tx, card.y + 5))
            how = fit_text(a, item.how, 12, SECONDARY if got else MUTED, width, role="body")
            surface.blit(how, (tx, card.y + 25))
            if progress is not None:
                bar = pygame.Rect(tx, card.bottom - 7, width, 3)
                pygame.draw.rect(surface, (30, 38, 50), bar)
                pygame.draw.rect(surface, SECONDARY, (bar.x, bar.y, bar.w * progress, bar.h))

    def _draw_board(self, surface, a) -> None:
        """5 ván điểm cao nhất của mỗi chế độ, mỗi chế độ một cột."""
        save = self.game.save
        top = PANEL.y + 126
        width = (PANEL.width - 40 - 2 * 12) // 3
        for i, mode in enumerate(GameMode):
            col = pygame.Rect(PANEL.x + 20 + i * (width + 12), top, width, 400)
            draw_panel(surface, col, header_height=40)
            surface.blit(a.text(mode.label.upper(), 18, ACCENT, role="ui"), (col.x + 14, col.y + 9))
            runs = save.modes[mode].top_runs
            if not runs:
                blit_center(surface, a.text("Chưa có ván nào", 15, MUTED, role="body"), col.y + 70, x=col.centerx)
                continue
            for rank, run in enumerate(runs):
                y = col.y + 52 + rank * 69
                rank_color = BADGE_COLOR if rank == 0 else (SECONDARY if rank < 3 else MUTED)
                surface.blit(a.text(f"{rank + 1}.", 18, rank_color, role="display"), (col.x + 14, y))
                score = fit_text(a, f"{run['score']:,}".replace(",", " "), 22, ACCENT if rank == 0 else TEXT,
                                 width - 60, role="display")
                surface.blit(score, (col.x + 44, y - 2))
                where = f"Ải {run['level']}" if run.get("level") else format_time(run.get("time", 0))
                bits = [where]
                if run.get("combo", 0) >= 2:
                    bits.append(f"chuỗi {run['combo']}")
                date = str(run.get("date", ""))
                if len(date) == 10:                                  # yyyy-mm-dd -> dd/mm
                    bits.append(f"{date[8:10]}/{date[5:7]}")
                detail = fit_text(a, " · ".join(bits), 14, SECONDARY, width - 58, role="label")
                surface.blit(detail, (col.x + 44, y + 28))
                if rank < len(runs) - 1:
                    pygame.draw.line(surface, FRAME, (col.x + 14, y + 58), (col.right - 14, y + 58))
        note = "Mỗi chế độ giữ 5 ván điểm cao nhất · chuỗi = chuỗi hạ liên tiếp dài nhất trong ván."
        blit_center(surface, fit_text(a, note, 14, MUTED, PANEL.width - 50, role="body"), PANEL.bottom - 64)

    def _draw_stats(self, surface, a) -> None:
        save = self.game.save
        blit_center(surface, fit_text(a, f"KỶ LỤC CHUNG: {save.highscore}", 21, ACCENT, PANEL.width - 60, role="ui"),
                    PANEL.y + 128)
        header_y = PANEL.y + 166
        for label, cx in self.COLUMNS:
            text = a.text(label, 15, MUTED, role="label")
            surface.blit(text, (cx - text.get_width() // 2, header_y))
        for i, mode in enumerate(GameMode):
            rec = save.modes[mode]
            row = pygame.Rect(PANEL.x + 20, header_y + 30 + i * 100, PANEL.width - 40, 86)
            draw_panel(surface, row)
            name = fit_text(a, mode.label, 24, TEXT, 170, role="ui")
            surface.blit(name, name.get_rect(midleft=(row.x + 20, row.centery)))
            values = (rec.games_played, rec.total_kills, rec.total_boss_kills, rec.best_score, format_time(rec.best_time))
            for (label, cx), value in zip(self.COLUMNS, values):
                text = fit_text(a, str(value), 22, ACCENT if label == "ĐIỂM CAO" else TEXT, 74, role="ui")
                surface.blit(text, text.get_rect(center=(cx, row.centery)))
                if label == "ĐIỂM CAO" and rec.best_combo >= 2:          # chuỗi hạ dài nhất, ngay dưới điểm cao
                    combo = fit_text(a, f"chuỗi {rec.best_combo}", 13, SECONDARY, 80, role="label")
                    surface.blit(combo, combo.get_rect(center=(cx, row.centery + 24)))
        extra = (f"Chu kỳ đã phá đảo: {len(save.cycle_history)} · Kỹ năng Nộ đã dùng: {save.counters.get('skills', 0)}"
                 f" · Đạn hộ vệ đã chặn: {save.counters.get('guard_blocks', 0)}")
        blit_center(surface, fit_text(a, extra, 14, SECONDARY, PANEL.width - 50, role="body"), PANEL.bottom - 78)
        blit_center(surface, a.text("Số quái/boss là tổng cộng dồn qua mọi ván.", 14, MUTED, role="body"),
                    PANEL.bottom - 58)
