"""Cơ chế riêng của từng ải Hồi IV (docs/design/hoi-4.md).

Mỗi ải có thể gắn một "cơ chế" (``Level.mechanic``): một đối tượng sống suốt trận, được GameplayScene gọi ở
vài điểm cố định. Lớp cơ sở ``Mechanic`` không làm gì, nên các ải cũ chạy y như trước.

| Móc (hook) | Khi nào | Dùng cho |
|---|---|---|
| ``update(world)`` | mỗi tick, sau khi địch/đạn di chuyển | hộ tống, hố đen, Trái Tim Đàn |
| ``target_for(world, enemy)`` | khi địch cập nhật | Ký Sinh / lính cảm tử nhắm tàu cứu sinh |
| ``holds(world)`` | trước khi sang wave mới / qua ải | chờ tàu cứu sinh bay hết |
| ``radio(world, key)`` | khi có thoại theo sự kiện | thoại có số người cứu được |
| ``stars(world)`` | lúc thắng | ải 12 chấm sao theo người cứu |
| ``hud_text`` | dải trạng thái | "ĐÃ CỨU 20/40" |
| ``draw_back`` / ``draw_front`` / ``draw_overlay`` | khi vẽ | hố đen, màn tối, nhuộm đỏ |
"""
from __future__ import annotations

import math
from typing import List, Optional

import pygame

from spaceship import config
from spaceship.config import WIDTH
from spaceship.entities.enemies import Enemy, Parasite
from spaceship.systems.world import World
from spaceship.ui import glow


class Mechanic:
    hud_text = ""
    body_cover = False          # True: thân tàu người chơi chặn đạn địch (ải hộ tống)

    def update(self, world: World) -> None:
        pass

    def target_for(self, world: World, enemy):
        return world.player

    def holds(self, world: World) -> bool:
        return False

    def radio(self, world: World, key) -> Optional[list]:
        """Thoại thay cho bảng RADIO ở sự kiện ``key`` (None = dùng bảng)."""
        return None

    def stars(self, world: World) -> Optional[int]:
        return None

    def draw_back(self, surface: pygame.Surface, world: World, assets, fx: float = 1.0) -> None:
        """Vẽ ngay trên nền (dưới địch, đạn)."""

    def draw_front(self, surface: pygame.Surface, world: World, assets, fx: float = 1.0) -> None:
        """Vẽ sau địch, trước đạn địch."""

    def draw_overlay(self, surface: pygame.Surface, world: World, assets, fx: float = 1.0) -> None:
        """Vẽ sau tàu người chơi, trước HUD."""


# --- Ải 12 · Hộ tống tàu cứu sinh ----------------------------------------------------------------
LIFEBOAT_Y = 470
LIFEBOAT_SPEED = 0.8
LIFEBOAT_HP = 100
LIFEBOAT_CREW = 10
LIFEBOAT_COUNT = 4
LIFEBOAT_RAM_DAMAGE = 30
LIFEBOAT_WIDTH = 120


class Lifeboat:
    """Tàu cứu sinh: bay ngang từ mép trái sang mép phải, không có khiên, chở 10 người ngủ đông."""

    is_lifeboat = True
    rx, ry = 50, 22

    def __init__(self, number: int) -> None:
        self.number = number
        self.x, self.y = -70.0, float(LIFEBOAT_Y)
        self.hp = self.max_hp = LIFEBOAT_HP
        self.age = 0
        self.hit_flash = 0
        self.saved = False

    @property
    def dead(self) -> bool:
        return self.hp <= 0

    @property
    def gone(self) -> bool:
        return self.dead or self.saved

    def contains(self, x: float, y: float, margin: float = 0.0) -> bool:
        dx = (x - self.x) / (self.rx + margin)
        dy = (y - self.y) / (self.ry + margin)
        return dx * dx + dy * dy < 1.0

    def update(self) -> None:
        self.age += 1
        self.x += LIFEBOAT_SPEED
        self.y = LIFEBOAT_Y + math.sin(self.age / 40) * 6          # dập dềnh nhẹ
        if self.hit_flash > 0:
            self.hit_flash -= 1
        if self.x > WIDTH + 70:
            self.saved = True

    def draw(self, surface: pygame.Surface, assets) -> None:
        x, y = int(self.x), int(self.y)
        glow.add(surface, glow.orb((60, 120, 160), 26, core=0.0, halo=1.3), (x, y))
        sprite = assets.image("lifeboat", LIFEBOAT_WIDTH)
        if sprite is not None:
            surface.blit(sprite, sprite.get_rect(center=(x, y)))
            if self.hit_flash > 0:
                white = assets.silhouette("lifeboat", LIFEBOAT_WIDTH)
                if white is not None:
                    white.set_alpha(40 * self.hit_flash)
                    surface.blit(white, white.get_rect(center=(x, y)))
        else:
            pygame.draw.ellipse(surface, (220, 230, 240), (x - 45, y - 18, 90, 36), 2)
        if (self.age // 20) % 2 == 0:                                  # đèn hiệu nhấp nháy ở đuôi
            glow.add(surface, glow.orb((255, 255, 255), 3, core=1.0), (x - 50, y - 2))
        w = 70                                                         # thanh máu luôn hiện
        bx, by = x - w // 2, y - 38
        pygame.draw.rect(surface, (10, 20, 26), (bx - 1, by - 1, w + 2, 6))
        k = max(0.0, self.hp / self.max_hp)
        color = (90, 230, 140) if k > 0.5 else ((255, 200, 70) if k > 0.25 else (255, 80, 80))
        pygame.draw.rect(surface, color, (bx, by, int(w * k), 4))


class Escort(Mechanic):
    """Ải 12: mỗi wave một tàu cứu sinh. Wave sau và "qua ải" chờ tàu đang bay về tới nơi (hoặc nổ).

    * Đạn địch trúng tàu cứu sinh trừ máu như trúng tàu bạn; địch đâm vào trừ 30.
    * Thân tàu bạn che được: đạn trúng bạn trước thì không tới được nó (xử lý đạn của bạn chạy trước).
    * Ký Sinh và lính cảm tử nhắm tàu cứu sinh thay vì nhắm bạn.
    * Chấm sao theo số người cứu; mất cả 4 tàu là thua.
    """

    body_cover = True

    def __init__(self) -> None:
        self.boats: List[Lifeboat] = []
        self.launched = 0
        self.rescued = 0
        self.lost = 0

    @property
    def hud_text(self) -> str:
        return f"ĐÃ CỨU {self.rescued}/{LIFEBOAT_COUNT * LIFEBOAT_CREW}"

    def launch(self, world: World) -> None:
        self.launched += 1
        self.boats.append(Lifeboat(self.launched))
        world.play("radar")

    def holds(self, world: World) -> bool:
        return bool(self.boats)

    def _alive(self) -> List[Lifeboat]:
        return [b for b in self.boats if not b.gone and b.x > 0]

    def target_for(self, world: World, enemy):
        if isinstance(enemy, Parasite) or (isinstance(enemy, Enemy) and enemy.kamikaze):
            boats = self._alive()
            if boats:
                return min(boats, key=lambda b: abs(b.x - enemy.x) + abs(b.y - enemy.y))
        return world.player

    def update(self, world: World) -> None:
        for boat in self.boats:
            boat.update()
        for bullet in list(world.enemy_bullets):                     # đạn địch trúng tàu cứu sinh
            for boat in self.boats:
                if not boat.gone and boat.contains(bullet.x, bullet.y, 4):
                    world.enemy_bullets.remove(bullet)
                    self._hurt(world, boat, config.ENEMY_BULLET_DAMAGE.get(bullet.kind,
                                                                             config.ENEMY_BULLET_DAMAGE_DEFAULT))
                    world.sparks(bullet.x, bullet.y, (255, 220, 200), 3)
                    break
        for enemy in list(world.enemies):                            # địch đâm vào: nổ, không được điểm
            if enemy.is_boss or enemy.is_obstacle or enemy.is_meteor:
                continue
            for boat in self.boats:
                if not boat.gone and boat.contains(enemy.x, enemy.y, enemy.radius * 0.6):
                    world.enemies.remove(enemy)
                    world.play("explode_small")
                    world.explode(enemy.x, enemy.y, 0.8)
                    self._hurt(world, boat, LIFEBOAT_RAM_DAMAGE)
                    break
        for boat in self.boats:
            if boat.saved:
                self.rescued += LIFEBOAT_CREW
                world.announce(f"ĐÃ CỨU {self.rescued}/{LIFEBOAT_COUNT * LIFEBOAT_CREW}", 1.5)
                world.play("pickup")
            elif boat.dead:
                self.lost += 1
                world.play("explode_big")
                world.explode(boat.x, boat.y, 1.6)
                world.say("ARIA", f"Mất chiếc số {boat.number}. Mười người.")
        self.boats = [b for b in self.boats if not b.gone]
        if self.lost >= LIFEBOAT_COUNT and not world.outcome:
            world.outcome = "defeat"

    def _hurt(self, world: World, boat: Lifeboat, damage: float) -> None:
        boat.hp -= damage
        boat.hit_flash = 4

    def stars(self, world: World) -> Optional[int]:
        """≥ 10 người = 1 sao · ≥ 30 = 2 sao · 40/40 = 3 sao."""
        total = LIFEBOAT_COUNT * LIFEBOAT_CREW
        return 3 if self.rescued >= total else (2 if self.rescued >= 30 else 1)

    def radio(self, world: World, key) -> Optional[list]:
        if key != ("clear", 0):
            return None
        total = LIFEBOAT_COUNT * LIFEBOAT_CREW
        lines = [("ARIA", f"Đã cứu {self.rescued} trên {total} người.")]
        if self.rescued >= total:
            lines.append(("KX-17", "Tất cả. Lần này không bỏ lại ai."))
        else:
            lines.append(("KX-17", "Không đủ. Nhưng là hy vọng."))
        return lines

    def draw_front(self, surface: pygame.Surface, world: World, assets, fx: float = 1.0) -> None:
        for boat in self.boats:
            boat.draw(surface, assets)


MECHANICS = {"escort": Escort}


def create_mechanic(level) -> Optional[Mechanic]:
    kind = getattr(level, "mechanic", None) if level is not None else None
    return MECHANICS[kind]() if kind in MECHANICS else None


