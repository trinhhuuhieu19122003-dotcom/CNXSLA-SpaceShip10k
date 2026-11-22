"""Dữ liệu 15 ải của chế độ Vượt ải (4 hồi; Hồi IV mở sau khi phá đảo ải 10).

Mỗi ải = danh sách wave, mỗi wave = danh sách sự kiện ``(tick, hàm_sinh_địch)``.
Wave sau chỉ bắt đầu khi đã diệt hết địch của wave trước. Muốn thêm/sửa ải:
chỉ cần sửa dữ liệu ở đây, không đụng tới logic.

| Ải | Tên | Điểm mới |
|---|---|---|
| 1 | Vành đai Mất Tín Hiệu | Làm quen |
| 2 | Mưa Thiên Thạch | Thiên thạch, kamikaze |
| 3 | Ổ Phục Kích | BOSS 1 -> Drone |
| 4 | Bãi Xác Tàu | Ký Sinh, xác tàu (núp được), súng Tia Sét |
| 5 | Tinh vân Đỏ | Sương mù, Lính Khiên |
| 6 | Tổ Đàn | Kẻ Đẻ Trứng, mini-boss Tổ Mẹ |
| 7 | Lõi Tinh vân | BOSS 2 -> Thiêu đốt |
| 8 | Trạm Tiền Tiêu | Pháo tháp, tàu đồng minh bị nhiễm |
| 9 | Hạm Đội Hộ Tống | Mini-boss Tàu Hộ Tống -> Drone thứ hai |
| 10 | Tàu Mẹ | BOSS CUỐI (phá đảo: mở Hỏa ngục) |
| 11 | Tiếng Vọng | Hồi IV: Bóng KX lặp lại đường bay của bạn |
| 12 | Khoang Ngủ Đông | Hộ tống 4 tàu cứu sinh, sao theo số người cứu |
| 13 | Giếng Trọng Lực | Hố đen kéo tàu, đạn bay cong, mini-boss Mắt Bão |
| 14 | Tín Hiệu Câm | Màn tối (đạn soi đường), mini-boss Kẻ Nghe |
| 15 | Trái Tim Đàn | BOSS CUỐI THẬT: 3 pha, tàu ma, ARIA chọn |

Hồi IV mở sau khi qua ải 10; cơ chế riêng từng ải nằm ở systems/mechanics.py (``Level.mechanic``).
Thiết kế: docs/design/hoi-4.md.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple

from spaceship import config
from spaceship.config import WIDTH
from spaceship.entities.enemies import Breeder, Enemy, InfectedAlly, Meteor, Parasite, ShadowKX, ShieldBug, Turret, Wreck
from spaceship.systems.spawning import formation

Event = Tuple[int, Callable]
FRONT_Y, BACK_Y = 200, 50            # vị trí dọc của hàng trước / hàng sau cùng trong đội hình lính
Wave = List[Event]


# --- "Ngôn ngữ" mô tả wave ---------------------------------------------------------------------
def grunts(stage: int, wave: int, at: int = 0, kamikaze: float = 0.0, style: str = "single") -> List[Event]:
    """Đội hình lính thường lấy từ bảng đội hình gốc của game (formation).

    Lính bay vào LẦN LƯỢT (hàng trước trước, từ giữa ra hai bên), cách nhau ``ENTRY_STAGGER_TICKS``,
    thay vì cả đội hình hiện ra cùng một lúc."""
    positions, dx = formation(stage, wave)
    order = sorted(positions, key=lambda p: (-p[1], abs(p[0]), p[0]))
    # Hàng trước ở y=FRONT_Y, các hàng sau nén vào trong màn hình (đội hình 5 hàng không nằm ngoài mép trên)
    depth = max(1, -min(py for _px, py in positions))
    squeeze = min(1.0, (FRONT_Y - BACK_Y) / depth)
    events = []
    for i, (px, py) in enumerate(order):
        def spawn(world, px=px, py=py):
            e = Enemy(world.hp_mult, stage=stage, rng=world.rng, kamikaze_chance=kamikaze)
            e.style = style
            e.x = max(30, min(WIDTH - 30, WIDTH // 2 + px))
            e.y = -40
            e.target_y = FRONT_Y + py * squeeze
            e.dx = dx * world.rng.choice([-1, 1]) if dx else e.dx
            world.enemies.append(e)
        events.append((at + i * config.ENTRY_STAGGER_TICKS, spawn))
    return events


def swarm(count: int, at: int = 0, every: int = 10, side: Optional[str] = None) -> List[Event]:
    """Bầy Ký Sinh lao xuống lần lượt (side: "left" | "right" | None = rải khắp)."""
    events = []
    for i in range(count):
        def spawn(world, i=i):
            if side == "left":
                x = world.rng.randint(80, 300)
            elif side == "right":
                x = world.rng.randint(WIDTH - 300, WIDTH - 80)
            else:
                x = world.rng.randint(80, WIDTH - 80)
            world.enemies.append(Parasite(world.hp_mult, x, rng=world.rng))
        events.append((at + i * every, spawn))
    return events


def _placed(cls, xs, y: int, at: int = 0, every: int = 0) -> List[Event]:
    return [(at + i * every, lambda world, x=x: world.enemies.append(cls(world.hp_mult, x, y, rng=world.rng)))
            for i, x in enumerate(xs)]


def shields(xs, y: int = 190, at: int = 0, every: int = 20) -> List[Event]:
    return _placed(ShieldBug, xs, y, at, every)


def breeders(xs, y: int = 160, at: int = 0, every: int = 40) -> List[Event]:
    return _placed(Breeder, xs, y, at, every)


def turrets(xs, y: int = 130, at: int = 0, every: int = 30) -> List[Event]:
    return _placed(Turret, xs, y, at, every)


def allies(count: int, at: int = 0, every: int = 40, y: int = 200) -> List[Event]:
    xs = [int(WIDTH * (i + 1) / (count + 1)) for i in range(count)]
    return _placed(InfectedAlly, xs, y, at, every)


def meteors(count: int, at: int = 0, every: int = 30) -> List[Event]:
    return [(at + i * every, lambda world: world.enemies.append(Meteor(world.hp_mult, rng=world.rng)))
            for i in range(count)]


def wreck(x: int, variant: int = 1, at: int = 0, carries: Optional[str] = None) -> List[Event]:
    return [(at, lambda world: world.enemies.append(Wreck(world.hp_mult, x, rng=world.rng, variant=variant,
                                                          carries=carries)))]


def shadows(delays, at: int = 0, every: int = 30) -> List[Event]:
    """Bóng KX (Hồi IV): mỗi con trễ một nhịp ``delays`` giây so với đường bay của bạn, xếp hàng trên cùng."""
    return [(at + i * every,
             lambda world, d=d, i=i: world.enemies.append(ShadowKX(world.hp_mult, d, row=i, rng=world.rng)))
            for i, d in enumerate(delays)]


def lifeboat(at: int = 0) -> List[Event]:
    """Ải 12: thả một tàu cứu sinh bay ngang qua màn (cần cơ chế "escort")."""
    return [(at, lambda world: world.mechanic.launch(world))]


def wave(*parts: List[Event]) -> Wave:
    return sorted((e for part in parts for e in part), key=lambda e: e[0])


# --- Định nghĩa ải -------------------------------------------------------------------------------
@dataclass(frozen=True)
class Level:
    number: int
    act: int
    name: str
    background: str
    difficulty: float
    waves: Tuple[Wave, ...]
    boss: Optional[str] = None             # khóa trong BOSS_SPECS
    reward: Optional[str] = None           # phần thưởng khi hạ boss (tự bay vào tàu)
    meteor_rate: float = 0.0               # xác suất mỗi tick có thiên thạch bay ngang
    wreck_every: int = 0                   # cứ N tick lại trôi xuống một xác tàu
    fog: bool = False
    mechanic: Optional[str] = None         # cơ chế riêng Hồi IV (systems/mechanics.py)
    hint: str = field(default="", compare=False)

    @property
    def title(self) -> str:
        return f"ẢI {self.number} · {self.name}"


LEVELS: Tuple[Level, ...] = (
    # ===== HỒI I · LẠC LỐI =====
    Level(1, 1, "VÀNH ĐAI MẤT TÍN HIỆU", "bg_act1", 1.0, (
        wave(grunts(1, 1)),
        wave(grunts(1, 2)),
        wave(grunts(1, 3)),
        wave(grunts(1, 4)),
    ), hint="Làm quen điều khiển"),
    Level(2, 1, "MƯA THIÊN THẠCH", "bg_act1", 1.05, (
        wave(grunts(1, 5, kamikaze=0.2)),
        wave(grunts(2, 1, kamikaze=0.25)),
        wave(grunts(2, 3, kamikaze=0.25), meteors(2, at=60, every=90)),
        wave(meteors(8, every=28), grunts(1, 2, at=120)),
        wave(grunts(2, 4, kamikaze=0.3)),
    ), meteor_rate=0.006, hint="Thiên thạch, kamikaze"),
    Level(3, 1, "Ổ PHỤC KÍCH", "bg_act1", 1.1, (
        wave(grunts(1, 5, kamikaze=0.2)),
        wave(grunts(2, 2, kamikaze=0.3, style="pink")),
    ), boss="crab", reward="upgrade_drone", hint="Boss: Kẻ Nuốt Drone"),

    # ===== HỒI II · BÃI THA MA =====
    Level(4, 2, "BÃI XÁC TÀU", "bg_act2", 1.2, (
        wave(swarm(10, every=14), wreck(250, 1, at=30)),
        wave(grunts(2, 1, kamikaze=0.2), swarm(6, at=90, every=16, side="left")),
        wave(wreck(400, 1, carries="upgrade_lightning"), grunts(1, 3, at=60), swarm(8, at=200, every=12)),
        wave(swarm(10, every=12, side="left"), swarm(10, at=60, every=12, side="right"), wreck(560, 2, at=40)),
        wave(grunts(2, 4, kamikaze=0.25, style="pink"), swarm(8, at=150, every=12)),
    ), wreck_every=520, hint="Ký Sinh, xác tàu, súng Tia Sét"),
    Level(5, 2, "TINH VÂN ĐỎ", "bg_act2", 1.3, (
        wave(shields([250, 550]), grunts(1, 2, at=60)),
        wave(swarm(12, every=12), shields([400], at=80)),
        wave(grunts(2, 3, kamikaze=0.2), shields([200, 600], at=120)),
        wave(shields([160, 400, 640]), swarm(10, at=140, every=10)),
        wave(grunts(2, 5, style="pink"), shields([300, 500], at=150)),
    ), fog=True, hint="Sương mù, Lính Khiên"),
    Level(6, 2, "TỔ ĐÀN", "bg_act2", 1.4, (
        wave(breeders([280, 520]), swarm(8, at=60, every=14)),
        wave(breeders([200, 400, 600]), shields([400], at=120)),
        wave(grunts(2, 6, style="pink"), breeders([400], at=100), swarm(10, at=160, every=10)),
    ), boss="nest", reward="upgrade_universal", hint="Mini-boss: Tổ Mẹ"),
    Level(7, 2, "LÕI TINH VÂN", "bg_act2", 1.5, (
        wave(grunts(3, 1, style="triple"), shields([250, 550], at=80)),
        wave(breeders([250, 550]), grunts(2, 4, at=100, kamikaze=0.25)),
    ), boss="spider", reward="upgrade_burn", hint="Boss: Lõi Tinh vân"),

    # ===== HỒI III · TRỞ VỀ =====
    Level(8, 3, "TRẠM TIỀN TIÊU", "bg_act3", 1.6, (
        wave(turrets([200, 600]), grunts(2, 1, at=60)),
        wave(allies(4)),
        wave(turrets([150, 400, 650]), allies(2, at=120)),
        wave(swarm(16, every=8), turrets([300, 500], at=60)),
        wave(allies(6, every=30), shields([250, 550], at=120)),
    ), hint="Pháo tháp, tàu đồng minh bị nhiễm"),
    Level(9, 3, "HẠM ĐỘI HỘ TỐNG", "bg_act3", 1.7, (
        wave(allies(5, every=30), turrets([200, 600], at=60)),
        wave(grunts(3, 4, style="triple"), allies(3, at=120)),
    ), boss="cruiser", reward="upgrade_drone", hint="Mini-boss: Tàu Hộ Tống"),
    Level(10, 3, "TÀU MẸ", "bg_act3", 1.8, (
        wave(turrets([150, 650]), allies(4, at=60)),
        wave(breeders([250, 550]), shields([400], at=60), swarm(10, at=120, every=10)),
    ), boss="mothership", hint="BOSS CUỐI"),
    # ===== HỒI IV · NGUỒN TÍN HIỆU (mở sau khi qua ải 10) =====
    Level(11, 4, "TIẾNG VỌNG", "bg_act4", 1.9, (
        wave(grunts(3, 1), shadows([2], at=120)),
        wave(swarm(14, every=8), shadows([2], at=40)),
        wave(shields([250, 550]), shadows([2, 3], at=60, every=40)),
        wave(grunts(3, 4, kamikaze=0.3), allies(2, at=90)),
        wave(shadows([2, 3, 4], every=40), turrets([200, 600], at=90)),
    ), hint="Bóng KX: Đàn đang học cách bạn lái"),
    Level(12, 4, "KHOANG NGỦ ĐÔNG", "bg_act4", 1.9, (
        wave(lifeboat(), grunts(3, 2, at=30)),
        wave(lifeboat(), swarm(12, at=90, every=14)),
        wave(lifeboat(), breeders([250, 550], at=60), grunts(3, 3, at=120, kamikaze=0.4)),
        wave(lifeboat(), turrets([40, 760], at=60), allies(3, at=120)),
    ), mechanic="escort", hint="Hộ tống 4 tàu cứu sinh (40 người)"),
    Level(13, 4, "GIẾNG TRỌNG LỰC", "bg_blackhole", 2.0, (
        wave(grunts(3, 2)),
        wave(swarm(16, every=8), meteors(3, at=40, every=60)),
        wave(shields([200, 400, 600]), grunts(3, 3, at=90, kamikaze=0.3)),
        wave(turrets([200, 600]), allies(2, at=60)),
    ), boss="storm_eye", reward="upgrade_universal", mechanic="gravity", hint="Hố đen kéo tàu · Mini-boss: Mắt Bão"),
    Level(14, 4, "TÍN HIỆU CÂM", "bg_act4", 2.0, (
        wave(grunts(3, 3)),
        wave(swarm(9, side="left", every=10), swarm(9, at=40, side="right", every=10)),
        wave(breeders([250, 550]), shadows([2, 3, 4], at=60, every=40)),
        wave(turrets([150, 400, 650])),
    ), boss="listener", mechanic="dark", hint="Màn tối: bắn để soi đường · Mini-boss: Kẻ Nghe"),
    Level(15, 4, "TRÁI TIM ĐÀN", "bg_heart", 2.1, (
        wave(grunts(3, 4, kamikaze=0.3), shields([200, 600], at=60), shadows([2, 3], at=150, every=40)),
        wave(breeders([250, 550]), turrets([150, 650], at=60), swarm(12, at=120, every=10)),
    ), boss="swarm_heart", mechanic="heart", hint="BOSS CUỐI THẬT"),
)

LEVEL_COUNT = len(LEVELS)
#: Ải cuối của mạch chính (Hồi I-III): qua ải này là "phá đảo" - mở Hỏa ngục và Hồi IV.
MAIN_LEVELS = 10


def get_level(number: int) -> Level:
    return LEVELS[number - 1]


def default_loadout(number: int) -> dict:
    """Trang bị khi vào thẳng một ải từ màn Chọn ải (đã "đi qua" các ải trước theo truyện)."""
    return {
        "weapon": "laser",
        "level": min(4, 1 + (number - 1) // 2),
        "bonus_damage": 0,
        "drones": (1 if number > 3 else 0) + (1 if number > 9 else 0),   # Hồi IV: đủ 2 drone
        "burn": number > 7,
    }
