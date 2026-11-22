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
    cover_radius = 0            # > 0: thân tàu người chơi (bán kính này) chặn đạn địch - ải hộ tống

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

    def on_boss_defeated(self, world: World, boss) -> None:
        """Boss của ải vừa bị hạ (trước khi đếm ngược qua ải)."""

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

    cover_radius = 34           # cỡ thân + cánh tàu

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


# --- Ải 13 · Giếng trọng lực ---------------------------------------------------------------------
WELL_START = (400.0, 260.0)
WELL_RIM = 40                       # chạm vành: mất 30 máu, bị hất ra
WELL_RIM_DAMAGE = 30
WELL_DRIFT = 150                    # biên độ trôi ngang
WELL_PULL_FAR, WELL_PULL_NEAR = 0.6, 2.2   # px/tick kéo tàu bạn: ở xa / sát vành
WELL_PULL_RANGE = 520
WELL_BULLET_G = 0.06                # gia tốc kéo đạn (px/tick²), giảm dần ngoài 120 px
WELL_SWIRL = 0.7                    # tỉ lệ lực xoáy (vuông góc) so với lực hút: đạn bay cong thành cánh quạt
WELL_PULSE_PERIOD = 240             # wave 4: 4 giây một nhịp đập ...
WELL_PULSE_BOSS = 180               # ... Mắt Bão pha 2: 3 giây
WELL_PULSE_WARN = 60                # vòng sáng co lại 1 giây ...
WELL_PULSE_STRONG = 60              # ... rồi lực hút gấp đôi 1 giây
WELL_COLOR = (255, 150, 70)
WELL_EDGE = (170, 110, 255)


class GravityWell(Mechanic):
    """Ải 13: hố đen ở nửa trên màn kéo tàu bạn, đạn (cả của bạn và của địch) và địch về tâm.

    * Kéo tàu 0,6 px/tick khi ở xa, tối đa 2,2 px/tick khi sát vành; chạm vành mất 30 máu và bị hất ra.
    * Đạn bay cong (hút + xoáy) - bắn vòng qua Lính Khiên được; đạn rơi vào vành thì mất.
    * Địch bị hút vào vành thì tan biến: không được điểm, nhưng cũng không mất chuỗi.
    * Từ wave 4: hố đen đập theo nhịp (vòng sáng co lại 1 giây báo trước, rồi lực hút gấp đôi 1 giây).
    * Mắt Bão nằm ngay tâm và trôi theo hố đen; pha 2 đập nhịp 3 giây, mỗi nhịp gọi 4 Ký Sinh từ vành.
    """

    def __init__(self) -> None:
        self.x, self.y = WELL_START
        self.t = 0
        self.pulse_t = 0
        self.just_pulsed = False         # tick bắt đầu lực hút mạnh (Mắt Bão gọi Ký Sinh đúng lúc này)
        self.swallowed = 0
        self._period = 1

    # --- Trạng thái ----------------------------------------------------------------------------
    def _boss(self, world: World):
        return next((e for e in world.enemies if e.is_boss and e.kind == "storm_eye"), None)

    def pulse_period(self, world: World) -> int:
        boss = self._boss(world)
        if boss is not None and boss.hp_ratio < 0.5:
            return WELL_PULSE_BOSS
        return WELL_PULSE_PERIOD if world.wave >= 4 or boss is not None else 0

    @property
    def warning(self) -> float:
        """0..1 trong 1 giây báo trước (vòng sáng co lại); 0 nếu không."""
        if self.pulse_t <= 0:
            return 0.0
        phase = self.pulse_t % self._period
        start = self._period - WELL_PULSE_WARN - WELL_PULSE_STRONG
        return (phase - start) / WELL_PULSE_WARN if start <= phase < start + WELL_PULSE_WARN else 0.0

    @property
    def strong(self) -> bool:
        if self.pulse_t <= 0:
            return False
        return self.pulse_t % self._period >= self._period - WELL_PULSE_STRONG

    def strength(self, world: World) -> float:
        base = 0.7 if world.wave <= 1 and self._boss(world) is None else 1.0     # wave 1: hút nhẹ để làm quen
        return base * (2.0 if self.strong else 1.0)

    # --- Mỗi tick ------------------------------------------------------------------------------
    def update(self, world: World) -> None:
        self.t += 1
        if world.wave >= 2 or self._boss(world) is not None:                     # wave 1 đứng yên
            self.x = WELL_START[0] + math.sin(self.t / 360) * WELL_DRIFT
        period = self.pulse_period(world)
        self._period = max(1, period)
        was_strong = self.strong
        self.pulse_t = self.pulse_t + 1 if period else 0
        self.just_pulsed = self.strong and not was_strong
        if self.just_pulsed:
            world.play("boss_phase")
            world.shake(4)
        k = self.strength(world)
        self._pull_player(world, k)
        self._bend_bullets(world, k)
        self._pull_enemies(world, k)
        boss = self._boss(world)
        if boss is not None:
            boss.dx = 0
            boss.x = self.x
            if boss.y >= self.y - 1:
                boss.y = self.y
            if boss.hp_ratio < 0.5 and self.just_pulsed:
                self._spawn_parasites(world)

    def _unit(self, x: float, y: float):
        dx, dy = self.x - x, self.y - y
        d = math.hypot(dx, dy) or 1e-6
        return dx / d, dy / d, d

    def _pull_player(self, world: World, k: float) -> None:
        from spaceship.systems import combat

        p = world.player
        ux, uy, d = self._unit(p.x, p.y)
        near = max(0.0, 1 - d / WELL_PULL_RANGE) ** 2
        pull = (WELL_PULL_FAR + (WELL_PULL_NEAR - WELL_PULL_FAR) * near) * k
        p.x = max(20, min(WIDTH - 20, p.x + ux * pull))
        p.y = max(50, min(config.HEIGHT - 50, p.y + uy * pull))
        if d < WELL_RIM + 14:                                        # chạm vành: hất ra ngoài + mất máu
            p.x = max(20, min(WIDTH - 20, self.x - ux * (WELL_RIM + 90)))
            p.y = max(50, min(config.HEIGHT - 50, self.y - uy * (WELL_RIM + 90)))
            world.particles.append(_ring(self.x, self.y, WELL_COLOR, WELL_RIM + 60))
            if not p.shield_active and p.invincible_timer <= 0:
                combat.damage_player(world, WELL_RIM_DAMAGE)

    def _bend_bullets(self, world: World, k: float) -> None:
        g = WELL_BULLET_G * k
        keep = []
        for b in world.enemy_bullets:
            ux, uy, d = self._unit(b.x, b.y)
            if d < WELL_RIM and not getattr(b, "from_well", False):
                continue                                             # rơi vào hố đen
            if b.kind not in ("laser", "purple_laser"):
                a = g * min(1.0, 120 / d)
                b.dx += (ux - uy * WELL_SWIRL) * a
                b.dy += (uy + ux * WELL_SWIRL) * a
            keep.append(b)
        world.enemy_bullets[:] = keep
        keep = []
        for b in world.bullets:
            ux, uy, d = self._unit(b.x, b.y)
            if d < WELL_RIM:
                world.sparks(b.x, b.y, WELL_EDGE, 1)
                continue
            if b.kind != "homing" and not b.is_piercing_laser:
                a = g * 1.4 * min(1.0, 120 / d)
                b.dx += (ux - uy * WELL_SWIRL) * a
                b.vy -= (uy + ux * WELL_SWIRL) * a                   # vy dương = bay lên
            keep.append(b)
        world.bullets[:] = keep

    def _pull_enemies(self, world: World, k: float) -> None:
        for e in list(world.enemies):
            if e.is_boss or e.is_obstacle or getattr(e, "ai", None) == "turret" or e.y < 0:
                continue
            grace = getattr(e, "well_grace", 0)
            if grace > 0:                                            # vừa chui ra từ vành: chưa bị hút lại
                e.well_grace = grace - 1
                continue
            ux, uy, d = self._unit(e.x, e.y)
            pull = (0.35 + 1.2 * max(0.0, 1 - d / 400) ** 2) * k
            e.x += ux * pull
            e.y += uy * pull
            if hasattr(e, "base_x"):
                e.base_x += ux * pull
            if d < WELL_RIM + e.radius * 0.5:                       # bị nuốt: không điểm, không mất chuỗi
                world.enemies.remove(e)
                self.swallowed += 1
                world.burst(e.x, e.y, WELL_EDGE, 8, speed_scale=0.4)
                world.particles.append(_ring(self.x, self.y, WELL_EDGE, WELL_RIM + 24))

    def _spawn_parasites(self, world: World) -> None:
        if sum(isinstance(e, Parasite) for e in world.enemies) >= 20:
            return
        for i in range(4):
            ang = math.radians(30 + i * 40)                          # nửa dưới vành
            p = Parasite(world.hp_mult, self.x + math.cos(ang) * (WELL_RIM + 50),
                         self.y + math.sin(ang) * (WELL_RIM + 50), rng=world.rng)
            p.well_grace = 45
            world.enemies.append(p)
        world.particles.append(_ring(self.x, self.y, WELL_EDGE, WELL_RIM + 70))

    # --- Vẽ ----------------------------------------------------------------------------------------
    def draw_back(self, surface: pygame.Surface, world: World, assets, fx: float = 1.0) -> None:
        x, y = self.x, self.y
        spin = self.t * 0.02
        boost = 1.0 + (0.5 if self.strong else 0.0)
        glow.add(surface, glow.soft_halo(glow.scale(WELL_EDGE, 0.55 if self.strong else 0.38), 150), (x, y))
        for i, (r, color, k) in enumerate(((118, WELL_EDGE, 0.35), (88, WELL_COLOR, 0.55), (62, (255, 220, 160), 0.8))):
            rect = pygame.Rect(0, 0, int(r * 2), int(r * 1.25))           # đĩa bồi tụ nghiêng (elip)
            rect.center = (int(x), int(y))
            for j in range(3):
                a0 = spin * (1.4 - i * 0.3) + j * 2.1
                pygame.draw.arc(surface, glow.scale(color, k * boost), rect, a0, a0 + 1.3, 3)
        pygame.draw.circle(surface, (0, 0, 0), (int(x), int(y)), WELL_RIM)  # lõi đen: hút cả ánh sáng
        pygame.draw.circle(surface, glow.scale(WELL_COLOR, 0.9 * boost), (int(x), int(y)), WELL_RIM, 2)
        warn = self.warning
        if warn > 0:                                                  # vòng sáng co lại: sắp hút mạnh
            r = int(WELL_RIM + 260 * (1 - warn))
            c = glow.scale((255, 230, 180), 0.4 + 0.6 * warn)
            pygame.draw.circle(surface, glow.scale(WELL_COLOR, 0.4), (int(x), int(y)), r + 3, 6)
            pygame.draw.circle(surface, c, (int(x), int(y)), r, 2)
        if self.strong and fx > 0:
            for i in range(6):                                        # vệt sáng bị hút vào
                a = spin * 3 + i * math.pi / 3
                r0 = 200 - (self.t * 6 + i * 30) % 160
                sx, sy = x + math.cos(a) * r0, y + math.sin(a) * r0 * 0.7
                glow.glow_line(surface, glow.scale(WELL_EDGE, 0.7), (sx, sy),
                               (x + math.cos(a) * (r0 - 26), y + math.sin(a) * (r0 - 26) * 0.7), 2)


# --- Ải 14 · Màn tối ----------------------------------------------------------------------------
DARK_ALPHA = 238                    # độ tối phủ chiến trường
DARK_PLAYER_LIGHT = 150             # vòng sáng quanh tàu
DARK_BULLET_LIGHT = 38              # mỗi viên đạn của bạn soi một vòng nhỏ
DARK_SKILL_TICKS = 180              # kỹ năng Nộ: soi sáng toàn màn 3 giây
DARK_FADE = 24


def light_texture(radius: int) -> pygame.Surface:
    """Lỗ sáng: kênh alpha 0 ở tâm, tăng dần tới 255 ở mép (dán bằng BLEND_RGBA_MIN lên lớp tối)."""
    key = ("light", radius)
    if key not in _light_cache:
        s = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        s.fill((0, 0, 0, 255))
        for r in range(radius, 0, -2):
            t = r / radius
            pygame.draw.circle(s, (0, 0, 0, int(255 * min(1.0, t ** 1.8))), (radius, radius), r)
        _light_cache[key] = s
    return _light_cache[key]


_light_cache: dict = {}


class Darkness(Mechanic):
    """Ải 14 "Tín Hiệu Câm": cả chiến trường tối; chỉ sáng quanh tàu bạn và quanh đạn bạn bắn (bắn là soi đường).

    Công bằng: đạn địch, vạch cảnh báo của Pháo tháp, vòng đỏ của lính cảm tử, quầng tím của Bóng KX và tai phát
    sáng của Kẻ Nghe luôn hiện (vẽ đè lên lớp tối). Kỹ năng Nộ soi sáng toàn màn 3 giây. ARIA im lặng: ô LIÊN LẠC
    chỉ còn nhiễu sóng."""

    radio_static = True

    def radio(self, world: World, key) -> Optional[list]:
        if key == ("boss", 0):
            world.play("radar")
            return []
        return None

    def __init__(self) -> None:
        self.t = 0
        self.lit = 0                     # > 0: kỹ năng Nộ đang soi sáng toàn màn
        self._skills_seen = 0
        self._layer = None

    def update(self, world: World) -> None:
        self.t += 1
        if world.skills_used != self._skills_seen:                  # vừa tung kỹ năng Nộ: soi sáng 3 giây
            self._skills_seen = world.skills_used
            self.lit = DARK_SKILL_TICKS
        elif self.lit > 0:
            self.lit -= 1
        boss = next((e for e in world.enemies if e.is_boss and e.kind == "listener"), None)
        if boss is not None and boss.arrived:                       # Kẻ Nghe lượn trong tối
            boss.free_flight = True
            boss.dx = 0
            boss.x = WIDTH / 2 + math.sin(self.t / 150) * 250
            boss.y = 170 + math.sin(self.t / 97) * 55
        if boss is not None and boss.hp_ratio < 0.5:
            self._decoys(world, boss)
        elif boss is None:
            for e in [e for e in world.enemies if getattr(e, "decoy", False)]:
                world.enemies.remove(e)

    def _decoys(self, world: World, boss) -> None:
        from spaceship.entities.enemies import ListenerDecoy

        decoys = [e for e in world.enemies if isinstance(e, ListenerDecoy)]
        if not decoys and (boss.decoy_cooldown <= 0):
            for side in (-1, 1):
                world.enemies.append(ListenerDecoy(boss, side))
            world.play("glitch")
            boss.decoy_cooldown = 300                               # bị phá hết thì 5 giây sau tách lại
        elif not decoys:
            boss.decoy_cooldown -= 1

    @property
    def darkness(self) -> float:
        """1 = tối hẳn, 0 = sáng hẳn (đang soi bằng kỹ năng Nộ: sáng dần lên rồi tối dần lại)."""
        if self.lit <= 0:
            return 1.0
        elapsed = DARK_SKILL_TICKS - self.lit
        if elapsed < DARK_FADE:
            return 1 - elapsed / DARK_FADE
        if self.lit < DARK_FADE:
            return 1 - self.lit / DARK_FADE
        return 0.0

    def lights(self, world: World) -> List[tuple]:
        p = world.player
        out = [(p.x, p.y, DARK_PLAYER_LIGHT)]
        for b in world.bullets:
            out.append((b.x, b.y, DARK_BULLET_LIGHT + (14 if b.kind == "plasma" else 0)))
        from spaceship.entities.effects import Flash
        from spaceship.systems.weapons import LightningArc
        for fx in world.particles:
            if isinstance(fx, Flash) and fx.radius >= 14:
                out.append((fx.x, fx.y, int(fx.radius * 2.5)))
            elif isinstance(fx, LightningArc):                       # tia sét soi rộng nhất
                for x, y in fx.points[::2]:
                    out.append((x, y, 70))
        for e in world.enemies:
            if getattr(e, "charging", False):                        # Kẻ Nghe đang phát sáng tai: lộ diện
                out.append((e.x, e.y, 120))
        return out

    def draw_front(self, surface: pygame.Surface, world: World, assets, fx: float = 1.0) -> None:
        dark = self.darkness
        if dark > 0:
            size = surface.get_size()
            if self._layer is None or self._layer.get_size() != size:
                self._layer = pygame.Surface(size, pygame.SRCALPHA)
            layer = self._layer
            layer.fill((0, 0, 0, int(DARK_ALPHA * dark)))
            for x, y, r in self.lights(world):
                r = max(8, int(r) // 4 * 4)
                tex = light_texture(r)
                layer.blit(tex, (int(x) - r, int(y) - r), special_flags=pygame.BLEND_RGBA_MIN)
            surface.blit(layer, (0, 0))
        for e in world.enemies:                                      # dấu hiệu nguy hiểm luôn hiện
            if hasattr(e, "draw_telegraph"):
                e.draw_telegraph(surface)
            elif hasattr(e, "draw_halo"):
                e.draw_halo(surface)


# --- Ải 15 · Trái Tim Đàn ------------------------------------------------------------------------
HEART_GHOST_GAP = 180               # đợt tàu ma thứ hai sau 3 giây
HEART_SHIELD_REGEN = 1 / 600        # còn tàu ma: hồi khiên (phần của khiên tối đa) mỗi tick
HEART_CHOICE_TICKS = 6 * 60         # pha 3: 6 giây sau thì ARIA cắt kết nối
HEART_ARMOR = 0.25                  # lõi bọc giáp: chỉ nhận 25% sát thương
HEART_EXPOSED = 2.0                 # lõi lộ ra: nhận 200%
HEART_FRENZY = 1.5                  # sau khi lộ lõi: bắn dồn dập gấp rưỡi
HEART_MIN_PHASE_TICKS = 10 * 60     # pha 1, 2 kéo dài ít nhất 10 giây (Nộ liên tục không "đốt" mất cả pha)
HEART_PHASE_FLOOR = {1: 0.67, 2: 0.34}
CALL_TO_ACTION = "CHỤM TAY · ĐẠI PHÁO"


class HeartBattle(Mechanic):
    """Ải 15: Trái Tim Đàn 3 pha.

    * Pha 2 "Ký ức": gọi 11 tàu ma (chữ V, 2 đợt 6 + 5) và Bóng KX của "các vòng trước" (số chu kỳ + 0, tối
      đa 4). Còn tàu ma trên màn thì boss hồi khiên.
    * Pha 3 "ARIA": màn nhuộm đỏ, boss nói bằng giọng ARIA, lõi bọc giáp (25% sát thương). Sau 6 giây ARIA
      cắt kết nối: hủy mọi đạn địch, hết đỏ, lõi lộ ra (200%), thanh Nộ đầy ngay, kỹ năng Nộ kế tiếp là ĐẠI
      PHÁO dù đang cầm súng gì; boss bắn dồn dập gấp rưỡi cho tới khi chết.
    * Hạ boss bằng Đại pháo sau khoảnh khắc đó: huy hiệu TÔI CHỌN ANH.
    """

    def __init__(self) -> None:
        self.phase = 1
        self.t = 0
        self.ghost_at: List[int] = []    # tick sẽ thả đợt tàu ma
        self.red_since = None            # tick bắt đầu pha 3 (màn đỏ)
        self.chosen = False              # ARIA đã cắt kết nối
        self.chose_you = False           # kết liễu bằng Đại pháo sau khoảnh khắc đó
        self.call_to_action = False      # đang hiện "CHỤM TAY · ĐẠI PHÁO"
        self.phase_started = 0
        self.met = False

    def _boss(self, world: World):
        return next((e for e in world.enemies if e.is_boss and e.kind == "swarm_heart"), None)

    def update(self, world: World) -> None:
        self.t += 1
        boss = self._boss(world)
        if boss is None:
            return
        if not self.met:                                              # boss vừa xuất hiện: pha 1 bắt đầu
            self.met = True
            self.phase_started = self.t
        floor = HEART_PHASE_FLOOR.get(self.phase)
        if floor is not None and self.t - self.phase_started < HEART_MIN_PHASE_TICKS:
            boss.hp = max(boss.hp, boss.max_hp * floor)               # chưa đủ 10 giây: chưa sang pha sau
        if boss.phase != self.phase:
            self.phase = boss.phase
            self.phase_started = self.t
            if self.phase == 2:
                self.ghost_at = [self.t + 30, self.t + 30 + HEART_GHOST_GAP]
                self._shadows_of_past(world)
            elif self.phase == 3 and self.red_since is None:
                self.red_since = self.t
                boss.damage_mult = HEART_ARMOR
                world.play("glitch")
        for at in [a for a in self.ghost_at if a <= self.t]:
            self.ghost_at.remove(at)
            self._ghosts(world, boss, 6 if len(self.ghost_at) else 5)
        if any(getattr(e, "ai", None) == "ghost" for e in world.enemies) and boss.max_shield > 0:
            boss.shield_hp = min(boss.max_shield, boss.shield_hp + boss.max_shield * HEART_SHIELD_REGEN)
        if self.red_since is not None and not self.chosen and self.t - self.red_since >= HEART_CHOICE_TICKS:
            self._aria_chooses(world, boss)
        if self.call_to_action and world.skills_used != self._skills_at_choice:
            self.call_to_action = False

    def on_boss_defeated(self, world: World, boss) -> None:
        if boss.kind == "swarm_heart":
            if self.chosen and _cannon_active(world):                # kết liễu bằng Đại pháo: TÔI CHỌN ANH
                self.chose_you = True
            self.call_to_action = False
            for e in [e for e in world.enemies if getattr(e, "ai", None) in ("ghost", "shadow")]:
                world.enemies.remove(e)                               # ký ức tan theo Trái Tim Đàn
                world.burst(e.x, e.y, (200, 200, 230), 6, speed_scale=0.5)

    def _ghosts(self, world: World, boss, count: int) -> None:
        from spaceship.entities.enemies import ghost_v

        cx = max(220, min(WIDTH - 220, world.player.x))
        world.enemies.extend(ghost_v(world.hp_mult, count, cx, 290 if count == 6 else 320, rng=world.rng))
        world.play("radar")

    def _shadows_of_past(self, world: World) -> None:
        from spaceship.entities.enemies import ShadowKX

        count = max(1, min(4, world.cycle))                          # người chơi lâu năm gặp cả "quá khứ"
        for i in range(count):
            world.enemies.append(ShadowKX(world.hp_mult, 2 + i * 0.7, row=i, rng=world.rng))

    def _aria_chooses(self, world: World, boss) -> None:
        self.chosen = True
        world.cancel_enemy_bullets()
        boss.damage_mult = HEART_EXPOSED
        boss.fire_speed = HEART_FRENZY
        boss.sprite = "swarm_heart_core"
        boss.attack_cooldown = 90                                     # một nhịp thở trước cơn bắn dồn dập
        p = world.player
        p.rage = p.max_rage
        world.forced_skill = "laser"
        self.call_to_action = True
        self._skills_at_choice = world.skills_used
        world.flash = 6
        world.shake(14)
        world.freeze(8)
        world.play("rage_full")
        world.radio.clear()
        world.say("ARIA", "Không. Tôi chọn anh.", 3.0)
        world.say("ARIA", "Đã cắt kết nối. Lõi của nó lộ rồi. Tôi dồn hết năng lượng cho anh: chụm tay đi!", 5.0)

    def radio(self, world: World, key) -> Optional[list]:
        if key == ("phase", 3):                                       # 2 câu đầu; 2 câu sau ở _aria_chooses
            world.radio.clear()                                       # cắt thoại cũ: khoảnh khắc này phải nghe ngay
            return [("ARIA", "Về... với... Đàn...", "glitch"), ("KX-17", "ARIA!")]
        return None

    @property
    def red(self) -> bool:
        return self.red_since is not None and not self.chosen

    def draw_overlay(self, surface: pygame.Surface, world: World, assets, fx: float = 1.0) -> None:
        if self.red:                                                  # pha 3: màn nhuộm đỏ (đập theo nhịp)
            beat = 0.5 + 0.5 * math.sin(self.t / 9)
            tint = _tint_layer(surface.get_size())
            tint.set_alpha(int(50 + 40 * beat * (fx if fx > 0 else 0.3)))
            surface.blit(tint, (0, 0))
        if self.call_to_action:
            k = 0.75 + 0.25 * math.sin(self.t / 5)
            label = assets.text(CALL_TO_ACTION, 46, (255, int(200 * k), 90), role="display")
            y = config.HEIGHT // 2 + 40
            shade = pygame.Surface((WIDTH, label.get_height() + 26), pygame.SRCALPHA)
            shade.fill((0, 0, 0, 140))
            surface.blit(shade, (0, y - 13))
            surface.blit(label, (WIDTH // 2 - label.get_width() // 2, y))
            hint = assets.text("ARIA dồn hết năng lượng cho anh · phím K", 16, (255, 230, 200), role="label")
            surface.blit(hint, (WIDTH // 2 - hint.get_width() // 2, y + label.get_height() + 2))


def _cannon_active(world: World) -> bool:
    from spaceship.systems.weapons import LaserCannon

    return any(isinstance(s, LaserCannon) for s in world.skills)


_tint_cache: dict = {}


def _tint_layer(size) -> pygame.Surface:
    if size not in _tint_cache:
        s = pygame.Surface(size)
        s.fill((150, 0, 20))
        _tint_cache[size] = s
    return _tint_cache[size]


def _ring(x, y, color, radius):
    from spaceship.entities.effects import Shockwave
    return Shockwave(x, y, color, max_radius=radius, life=16)


MECHANICS = {"escort": Escort, "gravity": GravityWell, "dark": Darkness, "heart": HeartBattle}


def create_mechanic(level) -> Optional[Mechanic]:
    kind = getattr(level, "mechanic", None) if level is not None else None
    return MECHANICS[kind]() if kind in MECHANICS else None


