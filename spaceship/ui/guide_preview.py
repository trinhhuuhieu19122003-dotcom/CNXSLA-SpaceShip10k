"""Minh họa cử chỉ và hộp thử đạn riêng của Hướng dẫn."""
from __future__ import annotations

import math
from dataclasses import dataclass

import pygame

from spaceship import config
from spaceship.entities.projectiles import Bullet
from spaceship.input.gestures import HAND_CONNECTIONS
from spaceship.systems.weapons import LightningArc
from spaceship.ui import glow
from spaceship.ui.widgets import ACCENT, DANGER, TEXT, draw_progress_ring

OPEN = (
    (.50, .95), (.38, .85), (.28, .75), (.22, .64), (.17, .55),
    (.40, .55), (.38, .40), (.37, .30), (.36, .21),
    (.50, .53), (.50, .36), (.50, .25), (.50, .15),
    (.59, .55), (.61, .40), (.62, .30), (.63, .22),
    (.67, .60), (.71, .49), (.73, .42), (.75, .35),
)


def _fist_pose():
    pose = list(OPEN)
    for mcp in (5, 9, 13, 17):
        x, y = pose[mcp]
        pose[mcp + 1:mcp + 4] = ((x, y - .08), (x + .01, y - .03), (x + .01, y + .03))
    pose[2:5] = ((.33, .74), (.40, .66), (.47, .61))
    return tuple(pose)


FIST = _fist_pose()
PINCH = tuple(
    {2: (.30, .72), 3: (.29, .60), 4: (.31, .51), 6: (.36, .42), 7: (.33, .46), 8: (.32, .51)}.get(i, point)
    for i, point in enumerate(OPEN)
)


def _ease(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3 - 2 * value)


def draw_hand_demo(surface: pygame.Surface, rect: pygame.Rect, action: str, seconds: float) -> None:
    pose, blend, progress = OPEN, 0.0, 0.0
    dx, dy, angle = 0.0, 0.0, 0.0
    size = 150
    if action == "steer":
        sway = math.sin(seconds * 2.6)
        dx, angle = 11 * sway, 6 * sway
    elif action == "focus":
        pose, blend = FIST, (1 - math.cos(seconds * math.tau / 2.8)) / 2
    elif action == "skill":
        pose = PINCH
        phase = seconds % 2.8
        blend = _ease(phase / .65) * _ease((2.25 - phase) / .55)
        if .65 <= phase < 1.7:
            progress = min(1.0, (phase - .65) / config.PINCH_HOLD_SECONDS)
    elif action == "rest":
        size = 116
        dy = 119 * (1 - math.cos(seconds * math.tau / 3.8)) / 2

    wrist = pygame.Vector2(OPEN[0])
    points = []
    for start, end in zip(OPEN, pose):
        x, y = wrist + (pygame.Vector2(start).lerp(end, blend) - wrist).rotate(angle)
        points.append((round(rect.centerx + (x - .5) * size + dx), round(rect.y + y * size + dy)))

    clip = surface.get_clip()
    surface.set_clip(clip.clip(rect))
    try:
        if action == "rest":
            camera_box = pygame.Rect(rect.x + 1, rect.y + 1, rect.width - 2, 121)
            pygame.draw.rect(surface, DANGER, camera_box, 1)
            x, y = camera_box.right - 18, camera_box.y + 20
            pygame.draw.lines(surface, config.NEON_ORANGE, False, ((x - 5, y), (x, y + 5), (x + 5, y)), 2)
        ink = glow.scale(ACCENT, .55) if action == "rest" and dy > 65 else ACCENT
        for a, b in HAND_CONNECTIONS:
            glow.glow_line(surface, ink, points[a], points[b], 2)
        for point in points:
            glow.add(surface, glow.soft_halo(glow.scale(ink, .45), 7), point)
            pygame.draw.circle(surface, TEXT, point, 2)
        if action == "skill":
            thumb, index = points[4], points[8]
            center = ((thumb[0] + index[0]) // 2, (thumb[1] + index[1]) // 2)
            draw_progress_ring(surface, center, 13, progress, color=config.NEON_ORANGE)
    finally:
        surface.set_clip(clip)


ARENA_SIZE = (300, 220)
SHIP_POS = (150, 190)
FIRE_FROM = (SHIP_POS[0], 166)
SHOT_INTERVALS = {"plasma": 10, "laser": 9, "homing": 15, "lightning": 12}


@dataclass
class _Target:
    x: int
    y: int
    flash: int = 0

    @property
    def center(self) -> tuple[int, int]:
        return self.x, self.y


class WeaponPreview:
    """Đạn và mục tiêu chỉ tồn tại trong ô minh họa."""

    def __init__(self, weapon: str) -> None:
        self.weapon = weapon
        self.targets = [_Target(66, 56), _Target(150, 37), _Target(234, 56)]
        self.bullets: list[Bullet] = []
        self.arcs: list[LightningArc] = []
        self._arena = pygame.Surface(ARENA_SIZE)
        self._step = 0
        self._ticks = 0
        self._fire()

    def _fire(self) -> None:
        if self.weapon == "lightning":
            start = FIRE_FROM
            for target in (self.targets[1], self.targets[0], self.targets[2]):
                ax, ay = start
                dx, dy = target.x - ax, target.y - ay
                points = [start]
                for i in range(1, 5):
                    nudge = 9 * math.sin(self._step + i * 2.3)
                    points.append((ax + dx * i / 5 + nudge, ay + dy * i / 5 - nudge))
                points.append(target.center)
                self.arcs.append(LightningArc(points, life=8, width=2))
                target.flash = 7
                start = target.center
            return

        targets = self.targets if self.weapon != "laser" else [self.targets[self._step // SHOT_INTERVALS["laser"] % 3]]
        for i, target in enumerate(targets):
            angle = math.degrees(math.atan2(FIRE_FROM[1] - target.y, target.x - FIRE_FROM[0]))
            if self.weapon == "homing":
                angle += (-10, 4, 10)[i]
            self.bullets.append(Bullet(*FIRE_FROM, self.weapon, angle, level=3))

    def update(self) -> None:
        self._ticks += 1
        if self._ticks % 2:
            return
        self._step += 1
        for target in self.targets:
            target.flash = max(0, target.flash - 1)
        for arc in self.arcs:
            arc.update()
        self.arcs[:] = [arc for arc in self.arcs if arc.alive]
        moving = []
        for bullet in self.bullets:
            before = (round(bullet.x), round(bullet.y))
            bullet.update(self.targets)
            after = (round(bullet.x), round(bullet.y))
            hit = next((t for t in self.targets if pygame.Rect(t.x - 11, t.y - 11, 22, 22).clipline(before, after)), None)
            if hit is not None:
                hit.flash = 6
            elif self._arena.get_rect().collidepoint(after):
                moving.append(bullet)
        self.bullets[:] = moving
        if self._step % SHOT_INTERVALS[self.weapon] == 0:
            self._fire()

    def draw(self, surface: pygame.Surface, assets, rect: pygame.Rect) -> None:
        arena = self._arena
        arena.fill((8, 15, 24))
        for x in range(30, ARENA_SIZE[0], 30):
            pygame.draw.line(arena, (19, 31, 43), (x, 0), (x, ARENA_SIZE[1]))
        for y in range(30, ARENA_SIZE[1], 30):
            pygame.draw.line(arena, (19, 31, 43), (0, y), (ARENA_SIZE[0], y))
        ship = assets.image("player", 68)
        if ship is not None:
            arena.blit(ship, ship.get_rect(center=SHIP_POS))
        for target in self.targets:
            glow.add(arena, glow.orb(DANGER, 6, core=.4, halo=.45), target.center)
            pygame.draw.circle(arena, DANGER, target.center, 14 - target.flash if target.flash else 11, 2)
        for bullet in self.bullets:
            bullet.draw(arena)
        for arc in self.arcs:
            arc.draw(arena)

        clip = surface.get_clip()
        surface.set_clip(clip.clip(rect))
        try:
            surface.blit(pygame.transform.smoothscale(arena, rect.size), rect)
        finally:
            surface.set_clip(clip)
