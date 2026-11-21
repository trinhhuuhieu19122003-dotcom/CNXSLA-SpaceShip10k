"""Màn chơi chính. Scene này chỉ ĐIỀU PHỐI: thứ tự cập nhật nằm trong ``update``,
còn quy tắc cụ thể ở ``systems/`` và hình vẽ ở ``entities/``."""
from __future__ import annotations

from typing import Optional

import pygame

from spaceship.campaign.levels import LEVEL_COUNT, default_loadout, get_level
from spaceship.campaign.story import RADIO
from spaceship.config import TICK, WHITE, WIDTH, GameMode
from spaceship.core.scene import Scene
from spaceship.core.storage import GameResult
from spaceship.systems import attacks, combat, weapons
from spaceship.systems.spawning import create_director
from spaceship.systems.world import World
from spaceship.ui.hud import draw_banner, draw_hud, draw_radio

DEFAULT_BACKGROUND = {GameMode.ENDLESS: "bg_act2", GameMode.INFERNO: "bg_act3"}
BG_SCROLL = 0.6                     # px/tick
FOG_BAND = 470                      # sương mù chỉ phủ phần trên màn hình (chỗ địch đứng)


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

    def __init__(self, game, mode: GameMode, level_number: Optional[int] = None, loadout: Optional[dict] = None) -> None:
        super().__init__(game)
        self.mode = mode
        self.music = None if mode is GameMode.INFERNO else "game"
        self.level_number = level_number or 1
        self.level = get_level(self.level_number) if mode is GameMode.CAMPAIGN else None
        self.world = World(mode=mode, rng=game.rng, preset=game.settings.difficulty, level=self.level)
        if self.level is not None:
            self.world.difficulty = self.level.difficulty
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

        if self.director.paused:                      # tên ải đang hiện: chỉ cho lái tàu
            self.director.update(w)
            p.move(controls)
            p.tick_timers()
            return

        w.survival_time += TICK
        self.director.update(w)
        if w.outcome:
            return self._finish()

        p.move(controls)
        p.tick_timers()
        if controls.fire and weapons.fire_player(w):
            w.play("laser")
        p.fire_drone(w.bullets)
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
        combat.apply_burn(w)
        combat.resolve_body_collisions(w)
        combat.reap_dead(w)
        for item in w.items:
            item.update(p)
        combat.collect_items(w)
        for fx in (*w.particles, *w.damage_numbers):
            fx.update()
        combat.cleanup(w)

        if w.screen_shake > 0:
            w.screen_shake -= 1
        if w.flash > 0:
            w.flash -= 1
        self._flush_sounds()
        if w.outcome:
            self._finish()

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
        from spaceship.scenes.cutscene import ENDING_SCRIPT, CutsceneScene
        from spaceship.scenes.result import ResultScene

        self.finished = True
        self._flush_sounds()
        w = self.world
        victory = w.outcome == "victory"
        result = GameResult(mode=self.mode, score=w.score, kills=w.kills, boss_kills=w.boss_kills,
                            survival_time=w.survival_time, victory=victory)
        new_record = self.game.save.record(result)
        game = self.game
        if self.level is None:
            return game.change_scene(ResultScene(game, self, result, new_record))
        stars = self.stars if victory else 0
        if victory:
            game.save.record_level(self.level_number, stars, LEVEL_COUNT)

        def result_scene(ending: bool = False):
            return ResultScene(game, self, result, new_record, level=self.level_number, stars=stars,
                               loadout=self.loadout(), ending=ending)

        if victory and self.level_number == LEVEL_COUNT:          # phá đảo -> đoạn kết
            game.change_scene(CutsceneScene(game, ENDING_SCRIPT, lambda: result_scene(ending=True),
                                            backdrop="ending", title="KẾT THÚC"))
        else:
            game.change_scene(result_scene())

    # --- Vẽ -----------------------------------------------------------------------------
    def screen_offset(self):
        if self.world.screen_shake > 0:
            return self.game.rng.randint(-8, 8), self.game.rng.randint(-8, 8)
        return 0, 0

    def _draw_background(self, surface: pygame.Surface) -> None:
        bg = self.game.assets.raw(self.background)
        if bg is None:
            surface.fill((0, 0, 0))
            return
        h = bg.get_height()
        y = int(self.bg_offset) % h
        surface.blit(bg, (0, y - h))
        surface.blit(bg, (0, y))

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
        draw_hud(surface, assets, w, self.controls, self.director)
        draw_radio(surface, assets, w)
        draw_banner(surface, assets, w, self.director)
        if w.flash > 0:
            surface.fill(WHITE)
