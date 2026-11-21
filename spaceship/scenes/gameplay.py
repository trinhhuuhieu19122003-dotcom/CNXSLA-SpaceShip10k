"""Màn chơi chính. Scene này chỉ ĐIỀU PHỐI: thứ tự cập nhật nằm trong ``update``,
còn quy tắc cụ thể ở ``systems/`` và hình vẽ ở ``entities/``."""
from __future__ import annotations

import math

import pygame

from spaceship.config import HEIGHT, NEON_CYAN, TICK, WHITE, WIDTH, GameMode
from spaceship.core.scene import Scene
from spaceship.core.storage import GameResult
from spaceship.entities.projectiles import NukeMissile
from spaceship.systems import attacks, combat
from spaceship.systems.spawning import create_director
from spaceship.systems.world import World
from spaceship.ui.hud import draw_hud

NUKE_TRAIL_COLORS = ((255, 0, 0), (255, 100, 0), (100, 200, 255))


class GameplayScene(Scene):
    shows_camera = True

    def __init__(self, game, mode: GameMode) -> None:
        super().__init__(game)
        self.mode = mode
        self.music = None if mode is GameMode.INFERNO else "game"
        self.world = World(mode=mode, rng=game.rng)
        if mode is GameMode.INFERNO:
            self.world.difficulty = 2.0
        self.director = create_director(mode)
        self.control_source = "keyboard"
        self.finished = False

    # --- Sự kiện ------------------------------------------------------------------------
    def handle_event(self, event) -> None:
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_p):
            self.pause()
        elif event.type == pygame.WINDOWFOCUSLOST:
            self.pause()

    def pause(self) -> None:
        from spaceship.scenes.pause import PauseScene

        if not self.finished:
            self.game.change_scene(PauseScene(self.game, self))

    # --- Logic --------------------------------------------------------------------------
    def update(self, controls) -> None:
        if self.finished:
            return
        w, p = self.world, self.world.player
        self.control_source = controls.source
        self.game.starfield.update()

        if self.director.paused:                      # chữ "STAGE n" đang hiện: chỉ cho lái tàu
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
        if controls.fire and p.fire(w.bullets):
            w.play("laser")
        p.fire_drone(w.bullets)
        if controls.nuke and p.rage_full:
            w.nukes.append(NukeMissile(p.x, p.y))
            p.rage = 0

        self._update_nukes()
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
            item.update()
        combat.collect_items(w)
        for fx in (*w.particles, *w.damage_numbers):
            fx.update()
        combat.cleanup(w)

        if w.screen_shake > 0:
            w.screen_shake -= 1
        if w.flash > 0:
            w.flash -= 1
        for sound in w.sounds:
            self.game.audio.play(sound)
        w.sounds.clear()
        if w.outcome:
            self._finish()

    def _update_nukes(self) -> None:
        w = self.world
        for nuke in list(w.nukes):
            nuke.update()
            if w.rng.random() < 0.4:                  # vệt lửa đuôi tên lửa
                back = nuke.heading + math.pi
                particle_x, particle_y = nuke.x + math.cos(back) * 20, nuke.y + math.sin(back) * 20
                w.burst(particle_x, particle_y, w.rng.choice(NUKE_TRAIL_COLORS), 1, speed_scale=0.2)
            if nuke.exploded:
                combat.detonate_nuke(w, nuke)
                w.nukes.remove(nuke)

    def _finish(self) -> None:
        from spaceship.scenes.result import ResultScene

        self.finished = True
        w = self.world
        for sound in w.sounds:
            self.game.audio.play(sound)
        w.sounds.clear()
        result = GameResult(mode=self.mode, score=w.score, kills=w.kills, boss_kills=w.boss_kills,
                            survival_time=w.survival_time, victory=w.outcome == "victory")
        new_record = self.game.save.record(result)
        self.game.change_scene(ResultScene(self.game, self, result, new_record))

    # --- Vẽ -----------------------------------------------------------------------------
    def screen_offset(self):
        if self.world.screen_shake > 0:
            return self.game.rng.randint(-8, 8), self.game.rng.randint(-8, 8)
        return 0, 0

    def draw(self, surface: pygame.Surface) -> None:
        w, assets = self.world, self.game.assets
        surface.fill((0, 0, 0))
        self.game.starfield.draw(surface, inferno=self.mode is GameMode.INFERNO)
        for item in w.items:
            item.draw(surface, assets)
        for particle in w.particles:
            particle.draw(surface)
        for bullet in w.bullets:
            bullet.draw(surface)
        for bullet in w.enemy_bullets:
            bullet.draw(surface)
        for enemy in w.enemies:
            enemy.draw(surface, assets)
        for nuke in w.nukes:
            nuke.draw(surface, assets)
        for number in w.damage_numbers:
            number.draw(surface, assets)
        if not self.finished or w.outcome == "victory":
            w.player.draw(surface, assets)
        draw_hud(surface, assets, w, self.control_source)

        banner = self.director.banner_text
        if banner:
            text = assets.text(banner, 60, NEON_CYAN)
            surface.blit(text, (WIDTH // 2 - text.get_width() // 2, HEIGHT // 2 - 50))
        if w.flash > 0:
            surface.fill(WHITE)
