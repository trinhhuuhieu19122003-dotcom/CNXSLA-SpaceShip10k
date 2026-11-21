"""Màn chơi chính. Scene này chỉ ĐIỀU PHỐI: thứ tự cập nhật nằm trong ``update``,
còn quy tắc cụ thể ở ``systems/`` và hình vẽ ở ``entities/``."""
from __future__ import annotations

from collections import deque
from typing import Optional

import pygame

from spaceship.campaign import achievements
from spaceship.campaign.achievements import RunStats
from spaceship.campaign.bestiary import BESTIARY, BestiaryEntry
from spaceship.campaign.levels import LEVEL_COUNT, default_loadout, get_level
from spaceship.campaign.story import RADIO
from spaceship import config
from spaceship.config import HEIGHT, TICK, TICK_RATE, WIDTH, GameMode
from spaceship.core.scene import Scene
from spaceship.core.storage import GameResult
from spaceship.entities.enemies import Boss, Breeder, Enemy, InfectedAlly, Meteor, Parasite, ShieldBug, Turret, Wreck
from spaceship.input.hand_tracker import PREVIEW_SIZE
from spaceship.systems import attacks, combat, weapons
from spaceship.systems.spawning import create_director
from spaceship.systems.world import World
from spaceship.ui import feel, sidebar
from spaceship.ui.hud import ENCOUNTER_HEIGHT, Toast, draw_banner, draw_boss_bar, draw_encounter, draw_hud, draw_radio

DEFAULT_BACKGROUND = {GameMode.ENDLESS: "bg_act2", GameMode.INFERNO: "bg_act3"}
BG_SCROLL = 0.6                     # px/tick
FOG_BAND = 470                      # sương mù chỉ phủ phần trên màn hình (chỗ địch đứng)
ENCOUNTER_TICKS = 3 * TICK_RATE
ENEMY_KEYS = {
    Parasite: "parasite", ShieldBug: "shield", Breeder: "breeder", Turret: "turret",
    InfectedAlly: "ally", Meteor: "meteor", Wreck: "wreck",
}


def enemy_key(enemy) -> Optional[str]:
    if isinstance(enemy, Boss):
        return enemy.kind
    if isinstance(enemy, Enemy):
        return "kamikaze" if enemy.kamikaze else "grunt"
    return ENEMY_KEYS.get(type(enemy))


class Fog:
    """Sương mù Tinh vân Đỏ: những đám mây đỏ thẫm trôi chậm, che bớt tầm nhìn."""

    def __init__(self, rng) -> None:
        tile = pygame.Surface((WIDTH, FOG_BAND), pygame.SRCALPHA)
        for _ in range(26):
            r = rng.randint(50, 120)
            color = (rng.randint(70, 110), rng.randint(5, 20), rng.randint(25, 45), rng.randint(70, 120))
            pygame.draw.circle(tile, color, (rng.randint(0, WIDTH), rng.randint(0, FOG_BAND)), r)
        small = pygame.transform.smoothscale(tile, (WIDTH // 8, FOG_BAND // 8))
        self.tile = pygame.transform.smoothscale(small, (WIDTH, FOG_BAND))
        self.offset = 0.0

    def update(self) -> None:
        self.offset = (self.offset + 0.4) % FOG_BAND

    def draw(self, surface: pygame.Surface) -> None:
        surface.set_clip(pygame.Rect(0, 0, WIDTH, FOG_BAND))
        y = int(self.offset)
        surface.blit(self.tile, (0, y - FOG_BAND))
        surface.blit(self.tile, (0, y))
        surface.set_clip(None)


class GameplayScene(Scene):
    shows_camera = True
    sidebars = True

    def __init__(self, game, mode: GameMode, level_number: Optional[int] = None, loadout: Optional[dict] = None) -> None:
        super().__init__(game)
        self.mode = mode
        self.level_number = level_number or 1
        self.level = get_level(self.level_number) if mode is GameMode.CAMPAIGN else None
        self.world = World(mode=mode, rng=game.rng, preset=game.settings.difficulty, level=self.level)
        if self.level is not None:
            self.world.difficulty = self.level.difficulty
            self.world.cycle = game.save.cycle
            self._apply_loadout(loadout or default_loadout(self.level_number))
        elif mode is GameMode.INFERNO:
            self.world.difficulty = 2.0
        radio = RADIO.get(self.level_number) if self.level is not None else None
        self.director = create_director(mode, self.level, radio)
        self.background = self.level.background if self.level is not None else DEFAULT_BACKGROUND.get(mode, "bg_act1")
        self.bg_offset = 0.0
        self.fog = Fog(game.rng) if self.level is not None and self.level.fog else None
        self.controls = None            # ControlState gần nhất (để HUD vẽ chỉ báo cử chỉ)
        self.finished = False
        self._encounters: deque = deque()          # thẻ góc phải: ĐỊCH MỚI / THÀNH TỰU MỚI
        self._encounter_ticks = 0
        self.run = RunStats(mode, level=self.level_number if self.level is not None else None,
                            preset=game.settings.difficulty)
        self.new_achievements: list = []
        self._run_ticks = 0
        # Âm thanh: nhạc theo hồi, đổi sang nhạc boss; tiếng báo Nộ đầy / boss đổi pha / bộ đàm
        self.music = self._base_music()
        self._boss_track: Optional[str] = None
        self._boss_phases: dict[int, int] = {}
        self._rage_was_full = self.world.player.rage_full
        self._heartbeat = -1
        self._radio_line = None
        game.controls.reset_hand_mode()

    def _apply_loadout(self, loadout: dict) -> None:
        p = self.world.player
        p.weapon = loadout.get("weapon", "laser")
        p.level = loadout.get("level", 1)
        p.bonus_damage = loadout.get("bonus_damage", 0)
        p.drones = loadout.get("drones", 0)
        p.burn_unlocked = loadout.get("burn", False)

    def loadout(self) -> dict:
        """Trang bị mang sang ải sau (khi bấm "Ải tiếp theo")."""
        p = self.world.player
        return {"weapon": p.weapon, "level": p.level, "bonus_damage": p.bonus_damage,
                "drones": p.drones, "burn": p.burn_unlocked}

    # --- Sự kiện ------------------------------------------------------------------------
    def handle_event(self, event) -> None:
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_p):
            self.pause()
        elif event.type == pygame.WINDOWFOCUSLOST:
            self.pause()

    def pause(self, reason: str = "manual") -> None:
        from spaceship.scenes.pause import PauseScene

        if not self.finished:
            self.game.change_scene(PauseScene(self.game, self, reason))

    # --- Logic --------------------------------------------------------------------------
    def update(self, controls) -> None:
        if self.finished:
            return
        w, p = self.world, self.world.player
        self.controls = controls
        if controls.hand_lost:                        # bỏ tay xuống -> nghỉ tay
            return self.pause("hand")
        self.game.starfield.update()
        self.bg_offset += BG_SCROLL
        if self.fog is not None:
            self.fog.update()
        w.tick_messages()
        self._tick_encounter_notice()
        if w.hitstop > 0:          # khựng hình: địch, đạn, tàu đứng yên vài tick; chữ thông báo vẫn chạy
            w.hitstop -= 1
            w.tick_feel()
            self._update_audio()
            self._flush_sounds()
            return

        if self.director.paused:                      # tên ải đang hiện: chỉ cho lái tàu
            self.director.update(w)
            p.move(controls)
            p.tick_timers()
            w.tick_feel()
            self._discover_enemies()
            self._update_audio()
            self._flush_sounds()
            return

        w.survival_time += TICK
        self._track_run(controls)
        self.director.update(w)
        if w.outcome:
            return self._finish()

        p.move(controls)
        p.tick_timers()
        if controls.fire and weapons.fire_player(w):
            w.play(f"fire_{p.weapon}")
        p.fire_drone(w.bullets, w.enemies)
        weapons.update_guard(w)
        if controls.nuke and p.rage_full:
            weapons.trigger_skill(w)
        weapons.update_skills(w)

        for bullet in w.bullets:
            bullet.update(w.enemies, w.spawn_particle)
        combat.resolve_player_bullets(w)
        for bullet in w.enemy_bullets:
            bullet.update(p)
        combat.resolve_enemy_bullets(w)
        attacks.run_enemy_ai(w)
        self._discover_enemies()                 # kể cả địch bị hạ ngay khi vừa lọt vào màn
        combat.apply_burn(w)
        combat.resolve_body_collisions(w)
        combat.reap_dead(w)
        self._discover_enemies()                 # Ký Sinh nở khi Kẻ Đẻ Trứng bị hạ
        for item in w.items:
            item.update(p)
        combat.collect_items(w)
        for fx in (*w.particles, *w.damage_numbers):
            fx.update()
        combat.cleanup(w)

        w.tick_combo()
        w.tick_feel()
        self._update_audio()
        self._flush_sounds()
        if w.outcome:
            self._finish()

    @property
    def encounter(self) -> Optional[BestiaryEntry]:
        return self._encounters[0] if self._encounters else None

    def _tick_encounter_notice(self) -> None:
        if self._encounter_ticks:
            self._encounter_ticks -= 1
            if not self._encounter_ticks:
                self._encounters.popleft()
        if self._encounters and not self._encounter_ticks:
            self._encounter_ticks = ENCOUNTER_TICKS

    # --- Huy hiệu ------------------------------------------------------------------------
    def _sync_run(self) -> None:
        w, run = self.world, self.run
        run.time, run.kills, run.boss_kills = w.survival_time, w.kills, w.boss_kills
        run.skills, run.guard_blocks = w.skills_used, w.guard_blocks

    def _track_run(self, controls) -> None:
        run = self.run
        if controls is not None:
            if controls.source == "hand":
                run.hand_ticks += 1
            elif controls.move_x or controls.move_y:
                run.keyboard_used = True
        for boss in self.world.defeated_bosses:
            if boss.kind == "mothership" and self.world.player.weapon == "lightning":
                run.mother_by_lightning = True
        self._run_ticks += 1
        if self._run_ticks % TICK_RATE == 0:              # kiểm tra huy hiệu mỗi giây
            self._sync_run()
            self._announce_achievements(achievements.evaluate(self.game.save, run))

    def _record_achievements(self, cleared: bool, stars: int) -> None:
        """Cuối ván: cộng bộ đếm vào file lưu rồi xét huy hiệu lần cuối (màn kết quả sẽ liệt kê)."""
        save, run = self.game.save, self.run
        self._sync_run()
        run.cleared, run.stars = cleared, stars
        save.add_counters(skills=run.skills, guard_blocks=run.guard_blocks)
        run.recorded = True
        save.save()
        self.new_achievements += achievements.evaluate(save, run)

    def _announce_achievements(self, unlocked) -> None:
        for achievement in unlocked:
            self.new_achievements.append(achievement)
            self._encounters.append(Toast("THÀNH TỰU MỚI", achievement.name, achievement.how))
            self.world.play("level_up")
        if self._encounters and not self._encounter_ticks:
            self._encounter_ticks = ENCOUNTER_TICKS

    def _discover_enemies(self) -> None:
        save = self.game.save
        if not BESTIARY.keys() <= save.seen_enemies:
            for enemy in self.world.enemies:
                if enemy.y <= 0:
                    continue
                key = enemy_key(enemy)
                if key is not None and key in BESTIARY and save.mark_seen(key):
                    self._encounters.append(BESTIARY[key])
        if self._encounters and not self._encounter_ticks:
            self._encounter_ticks = ENCOUNTER_TICKS

    def draw_sidebars(self, surface: pygame.Surface, left: pygame.Rect, right: pygame.Rect) -> None:
        assets = self.game.assets
        sidebar.draw_status_panel(surface, assets, left, self.world, self.director)
        sidebar.draw_control_panel(surface, assets, right, self.game, self.world, self.controls)

    def _encounter_y(self) -> int:
        if self.game.wide_layout:
            return 60 if any(e.is_boss for e in self.world.enemies) else 14
        boss = any(e.is_boss for e in self.world.enemies)
        y = (84 if boss else 44) + (72 if self.world.radio else 0)
        if self.game.tracker is not None and self.game.show_camera:
            below_preview = self.game.to_virtual((0, PREVIEW_SIZE[1] + 32))
            if below_preview is not None:
                y = max(y, below_preview[1])
        return min(y, HEIGHT - ENCOUNTER_HEIGHT - 14)

    # --- Âm thanh -------------------------------------------------------------------------
    def _base_music(self) -> str:
        if self.level is not None:
            return f"act{self.level.act}"
        return "act3" if self.mode is GameMode.INFERNO else "game"

    def _boss_music(self, bosses) -> str:
        if self.mode is GameMode.INFERNO or any(b.kind == "mothership" for b in bosses):
            return "final_boss"
        return "game"                              # nhạc gốc thời đại học cho trận boss

    def _update_audio(self) -> None:
        w, audio = self.world, self.game.audio
        bosses = w.bosses
        if bosses:
            self._boss_track = self._boss_music(bosses)
        elif self.level is None:
            self._boss_track = None                # Vô tận/Hỏa ngục: hạ boss xong về nhạc nền
        track = self._boss_track or self._base_music()
        if track != self.music:
            self.music = track
            audio.play_music(track)
        for boss in bosses:
            before = self._boss_phases.setdefault(boss.id, boss.phase)
            if boss.phase != before:
                self._boss_phases[boss.id] = boss.phase
                w.play("boss_phase")
        p = w.player
        if 0 < p.hp <= p.max_hp * config.LOW_HP_RATIO and not w.outcome:    # máu thấp: tim đập theo viền đỏ
            beat = int(w.survival_time * feel.LOW_HP_BEATS_PER_SECOND)
            if beat != self._heartbeat:
                self._heartbeat = beat
                w.play("heartbeat")
        if w.player.rage_full and not self._rage_was_full:
            w.play("rage_full")
        self._rage_was_full = w.player.rage_full
        line = w.radio[0] if w.radio else None
        if line is not None:
            audio.duck()
            if line is not self._radio_line:
                audio.voice(line.speaker, "radio")
        self._radio_line = line

    def _flush_sounds(self) -> None:
        for sound in self.world.sounds:
            self.game.audio.play(sound)
        self.world.sounds.clear()

    @property
    def stars(self) -> int:
        """1 sao: qua ải · 2 sao: mất tối đa 1 mạng · 3 sao: không mất mạng nào."""
        lost = self.world.lives_lost
        return 3 if lost == 0 else (2 if lost <= 1 else 1)

    def _finish(self) -> None:
        from spaceship.campaign import story
        from spaceship.scenes.cutscene import ENDING_SCRIPT, CutsceneScene, make_script
        from spaceship.scenes.result import ResultScene

        self.finished = True
        self._flush_sounds()
        w = self.world
        victory = w.outcome == "victory"
        result = GameResult(mode=self.mode, score=w.score, kills=w.kills, boss_kills=w.boss_kills,
                            survival_time=w.survival_time, victory=victory)
        new_record = self.game.save.record(result)
        game = self.game
        stars = self.stars if victory and self.level is not None else 0
        cycle = game.save.cycle                                   # trước khi ghi (đoạn kết nói về chu kỳ vừa xong)
        if victory and self.level is not None:
            game.save.record_level(self.level_number, stars, LEVEL_COUNT)
        self._record_achievements(victory and self.level is not None, stars)
        if self.level is None:
            return game.change_scene(ResultScene(game, self, result, new_record))

        def result_scene(ending: bool = False):
            return ResultScene(game, self, result, new_record, level=self.level_number, stars=stars,
                               loadout=self.loadout(), ending=ending)

        if victory and self.level_number == LEVEL_COUNT:          # phá đảo -> đoạn kết
            script = list(ENDING_SCRIPT) + make_script(story.cycle_teaser(cycle))
            game.change_scene(CutsceneScene(game, script, lambda: result_scene(ending=True),
                                            backdrop="ending", title="KẾT THÚC",
                                            music="ending"))
        else:
            game.change_scene(result_scene())

    # --- Vẽ -----------------------------------------------------------------------------
    @property
    def fx_scale(self) -> float:
        """Cài đặt "Rung & nháy màn hình": 1 = đầy đủ, 0,4 = nhẹ, 0 = tắt."""
        return config.SCREEN_FX_SCALE.get(getattr(self.game.settings, "screen_fx", "full"), 1.0)

    def screen_offset(self):
        """Rung kiểu trauma: độ lệch = MAX * trauma² (cú nhẹ hơi nhích, cú nặng giật mạnh)."""
        amount = config.SHAKE_MAX_OFFSET * self.world.trauma ** 2 * self.fx_scale
        if amount < 0.5:
            return 0, 0
        rng = self.game.rng
        return round(rng.uniform(-amount, amount)), round(rng.uniform(-amount, amount))

    def _draw_background(self, surface: pygame.Surface) -> None:
        bg = self._dark_background()
        if bg is None:
            surface.fill((0, 0, 0))
            return
        h = bg.get_height()
        y = int(self.bg_offset) % h
        surface.blit(bg, (0, y - h))
        surface.blit(bg, (0, y))

    BG_BRIGHTNESS = (150, 150, 158)            # nền trong trận tối đi ~40% để đạn/địch nổi bật

    def _dark_background(self) -> Optional[pygame.Surface]:
        if getattr(self, "_bg_dark", None) is None:
            bg = self.game.assets.raw(self.background)
            if bg is None:
                return None
            self._bg_dark = bg.copy()
            self._bg_dark.fill(self.BG_BRIGHTNESS, special_flags=pygame.BLEND_MULT)
        return self._bg_dark

    def draw(self, surface: pygame.Surface) -> None:
        w, assets = self.world, self.game.assets
        self._draw_background(surface)
        self.game.starfield.draw(surface, inferno=self.mode is GameMode.INFERNO)
        for item in w.items:
            item.draw(surface, assets, w.player.weapon)
        for particle in w.particles:
            particle.draw(surface)
        for bullet in w.bullets:
            bullet.draw(surface)
        for enemy in w.enemies:
            enemy.draw(surface, assets)
        if self.fog is not None:
            self.fog.draw(surface)
        for bullet in w.enemy_bullets:               # đạn địch vẽ SAU sương mù: luôn nhìn thấy để né
            bullet.draw(surface)
        weapons.draw_skills(surface, w)
        for number in w.damage_numbers:
            number.draw(surface, assets)
        if not self.finished or w.outcome == "victory":
            w.player.draw(surface, assets)
        feel.draw_vignette(surface, w, self.fx_scale)   # trước HUD: chữ trên HUD không bị nhuộm đỏ
        if self.game.wide_layout:                    # HUD nằm ở 2 bảng bên; chiến trường chỉ giữ thanh boss
            draw_boss_bar(surface, assets, w, y=30)
        else:
            draw_hud(surface, assets, w, self.controls, self.director)
            draw_radio(surface, assets, w)
        draw_banner(surface, assets, w, self.director)
        if self.encounter is not None:
            draw_encounter(surface, assets, self.encounter, self._encounter_y())
        feel.draw_flash(surface, w, self.fx_scale)
