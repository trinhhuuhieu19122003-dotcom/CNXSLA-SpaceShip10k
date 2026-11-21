"""Hằng số và thông số cân bằng game, gom về một chỗ để chỉnh dễ dàng.

Mọi giá trị "theo tick" ở đây tính trên bước cập nhật cố định 1/60 giây
(xem ``spaceship.app``), nên game chạy đúng tốc độ trên mọi máy.
"""
from __future__ import annotations

from enum import Enum
from pathlib import Path

# --- Màn hình & vòng lặp -----------------------------------------------------
TITLE = "Spaceship 10k"
WIDTH, HEIGHT = 800, 700
TICK_RATE = 60                     # số lần cập nhật logic mỗi giây (cố định)
TICK = 1.0 / TICK_RATE
MAX_FRAME_TIME = 0.25              # chặn "spiral of death" khi máy bị đứng hình

# --- Đường dẫn ---------------------------------------------------------------
PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = PACKAGE_DIR.parent
ASSETS_DIR = PROJECT_DIR / "assets"
IMAGES_DIR = ASSETS_DIR / "images"
AUDIO_DIR = ASSETS_DIR / "audio"

# --- Màu -----------------------------------------------------------------------
BLACK = (10, 10, 15)
WHITE = (255, 255, 255)
GRAY = (100, 100, 100)
YELLOW = (255, 255, 0)
NEON_GREEN = (57, 255, 20)
NEON_RED = (255, 0, 50)
NEON_CYAN = (0, 255, 255)
NEON_ORANGE = (255, 120, 0)
NEON_MAGENTA = (255, 0, 255)
PLASMA_COLOR = (0, 150, 255)
LASER_COLOR = (255, 50, 50)
HOMING_COLOR = (200, 0, 255)

FONT_NAMES = "tahoma,segoeui,arial,dejavusans"


class GameMode(str, Enum):
    CAMPAIGN = "CAMPAIGN"
    ENDLESS = "ENDLESS"
    INFERNO = "INFERNO"

    @property
    def label(self) -> str:
        return {"CAMPAIGN": "VƯỢT ẢI", "ENDLESS": "VÔ TẬN", "INFERNO": "HỎA NGỤC"}[self.value]

    @property
    def is_timed(self) -> bool:
        return self is not GameMode.CAMPAIGN


# --- Người chơi -------------------------------------------------------------
PLAYER_MAX_HP = 100
PLAYER_LIVES = 3
PLAYER_MAX_RAGE = 100
PLAYER_KEYBOARD_SPEED = 7          # px/tick khi điều khiển bằng phím
PLAYER_HAND_FOLLOW = 0.25          # hệ số bám theo tay mỗi tick (0..1)
PLAYER_HITBOX = 15
RESPAWN_INVINCIBLE_TICKS = 180
RAGE_PER_HIT = 5
MAX_WEAPON_LEVEL = 6
MAX_BONUS_DAMAGE = 30

WEAPON_BASE_DAMAGE = {"plasma": 6, "laser": 10, "homing": 7, "lightning": 7}
WEAPON_NAMES = {"plasma": "PLASMA", "laser": "LASER", "homing": "HOMING", "lightning": "TIA SÉT"}
PIERCING_LASER_DAMAGE = 9          # laser cấp 6 (tia xuyên thấu). Bản cũ 15 + cộng đủ bonus: hạ boss trong vài giây
PIERCING_LASER_BONUS_SHARE = 0.5   # tia cấp 6 chỉ ăn một nửa sát thương cộng thêm
PLASMA_SPLASH_RADIUS = 48          # plasma cấp 6: nổ lan
PLASMA_SPLASH_SHARE = 0.5
LIGHTNING_RANGE = 480              # tia sét tìm mục tiêu trong bán kính này (gần hết màn hình)
LIGHTNING_CHAIN_RANGE = 150        # khoảng nhảy từ địch này sang địch khác
LIGHTNING_CHAIN_DECAY = 0.85       # mỗi lần nhảy sát thương còn 85%
LIGHTNING_DAMAGE_PER_LEVEL = 3     # sét không bắn nhiều tia hơn khi lên cấp, nên tăng sát thương
DRONE_DAMAGE = 2
DRONE_COOLDOWN_TICKS = 60

# --- Kỹ năng Nộ (mỗi súng một kiểu, thay cho Nuke dùng chung) -------------------------
SKILL_LASER_TICKS = 180            # Đại Pháo: tia khổng lồ 3 giây
SKILL_LASER_DPS = 150
SKILL_LASER_WIDTH = 90
SKILL_PLASMA_DAMAGE = 45           # Vòng Plasma: nổ vòng quanh tàu, xóa đạn địch
SKILL_PLASMA_RADIUS = 420
SKILL_HOMING_MISSILES = 20         # Mưa Tên Lửa
SKILL_HOMING_DAMAGE = 14
SKILL_LIGHTNING_STRIKES = 3        # Bão Sét: đánh mọi địch trên màn 3 lần
SKILL_LIGHTNING_DAMAGE = 16
SKILL_NAMES = {"laser": "ĐẠI PHÁO", "plasma": "VÒNG PLASMA", "homing": "MƯA TÊN LỬA", "lightning": "BÃO SÉT"}

# --- Kẻ địch -------------------------------------------------------------------
KAMIKAZE_SPEED = 8                 # bản cũ: 15 px/tick, gần như không né được
BURN_DAMAGE_PER_SECOND = 6         # bản cũ: 1.5/s, gần như vô dụng
ENEMY_BULLET_DAMAGE = {"normal": 15}
ENEMY_BULLET_DAMAGE_DEFAULT = 25
COLLISION_DAMAGE = 20
HEAVY_COLLISION_DAMAGE = 30        # va vào boss / thiên thạch

# --- Điểm số -------------------------------------------------------------------
SCORE_ENEMY = 10
SCORE_METEOR = 20
SCORE_BOSS_PER_STAGE = 250         # bản cũ: boss chỉ +10 như lính thường
SCORE_WRECK = 30

# --- Vật phẩm -------------------------------------------------------------------
HEAL_AMOUNT = {GameMode.CAMPAIGN: 30, GameMode.ENDLESS: 30, GameMode.INFERNO: 5}
SHIELD_TICKS = {GameMode.CAMPAIGN: 180, GameMode.ENDLESS: 180, GameMode.INFERNO: 60}
RANDOM_DROP_CHANCE = {GameMode.ENDLESS: 0.45, GameMode.INFERNO: 0.20}
ITEM_PICKUP_RADIUS = 30

# --- Độ khó (chọn ở màn Chọn ải) -----------------------------------------------
DIFFICULTIES = ("easy", "normal", "hard")
DIFFICULTY_LABELS = {"easy": "DỄ", "normal": "THƯỜNG", "hard": "KHÓ"}
DIFFICULTY_HP = {"easy": 0.75, "normal": 1.0, "hard": 1.35}         # máu địch
DIFFICULTY_FIRE = {"easy": 0.7, "normal": 1.0, "hard": 1.4}         # tốc độ bắn của địch
DIFFICULTY_DROPS = {"easy": 1.3, "normal": 1.0, "hard": 0.7}        # tỉ lệ rơi đồ

# --- Chế độ chơi ---------------------------------------------------------------
ENDLESS_BOSS_INTERVAL = 60.0       # giây (thật, nhờ bước cập nhật cố định)
INFERNO_BOSS_INTERVAL = 45.0

# --- Điều khiển bằng tay -------------------------------------------------------
CAMERA_INDEX = 0
CAMERA_SIZE = (640, 480)
# Vùng điều khiển = một ô NHỎ trong khung camera, đặt quanh "tư thế nghỉ" của tay
# (đo ở màn Hiệu chỉnh). Chỉ cần nhích tay ~1 gang là tàu đi hết màn hình,
# khuỷu tay tì lên bàn được -> đỡ mỏi ("gorilla arm").
HAND_DEFAULT_CENTER = (0.5, 0.62)  # chưa hiệu chỉnh: hơi thấp, ngang ngực
HAND_SENSITIVITY = {"low": 0.24, "medium": 0.18, "high": 0.13}  # nửa bề ngang vùng (tỉ lệ khung camera)
HAND_SENSITIVITY_LABELS = {"low": "THẤP", "medium": "VỪA", "high": "CAO"}
HAND_ZONE_ASPECT = 1.15            # cao/rộng của vùng, bù tỉ lệ camera 4:3 so với màn 800x700
CALIBRATION_HOLD_SECONDS = 1.5     # giữ yên tay bao lâu để chốt tư thế nghỉ
CALIBRATION_STILL = 0.03           # dao động tối đa (tỉ lệ khung) vẫn tính là "đứng yên"
PINCH_RATIO = 0.4                  # chụm: khoảng cách đầu ngón cái-trỏ < 0.4 x cỡ lòng bàn tay
PINCH_HOLD_SECONDS = 0.5           # giữ chụm bao lâu thì tung kỹ năng Nộ
HAND_PAUSE_SECONDS = 1.5           # mất tay quá lâu -> tự tạm dừng
RESUME_COUNTDOWN_SECONDS = 1.8     # đếm 3-2-1 trước khi chơi tiếp
FOCUS_HAND_SPEED = 3.5             # né chậm: tốc độ tối đa (px/tick) khi lái bằng tay
FOCUS_KEYBOARD_SPEED = 3.0         # né chậm bằng phím Shift
ONE_EURO_MIN_CUTOFF = 0.9          # nhỏ hơn = mượt hơn khi tay đứng yên
ONE_EURO_BETA = 4.0                # lớn hơn = ít trễ hơn khi tay di chuyển nhanh
GESTURE_STABLE_FRAMES = 3          # cử chỉ phải giữ ổn định N khung mới được nhận
HAND_LOST_TIMEOUT = 0.35           # giây: quá thời gian này mới coi là mất tay
HAND_LANDMARKER_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/latest/hand_landmarker.task"
)

# --- Vòng lặp tín hiệu (chu kỳ mới sau khi phá đảo) ---------------------------------------------
#: mỗi chu kỳ sau: địch thêm 25% máu và bắn nhanh hơn 12% (chu kỳ 2 = x1.25 / x1.12, chu kỳ 3 = x1.5 / x1.24...)
CYCLE_HP_STEP = 0.25
CYCLE_FIRE_STEP = 0.12

# --- Nhịp sóng (pacing): tránh cảnh địch "ồ ạt" ----------------------------------------------------
#: Lính trong một đội hình bay vào lần lượt (Galaga), cách nhau chừng này tick.
ENTRY_STAGGER_TICKS = 7
#: Tới vị trí rồi phải chờ chừng này tick mới được bắn: không bị bắn ngay khi địch vừa xuất hiện.
ARRIVAL_GRACE_TICKS = 45
#: Lính trôi xuống chậm nhưng dừng ở đây: nửa dưới màn hình là chỗ của người chơi.
FORMATION_FLOOR = 360
#: Lính ở đội hình quá lâu mà chưa bị hạ thì rút lui (bay lên khỏi màn): trận không bị "kẹt" vì vài con sót.
RETREAT_AFTER_TICKS = 840
#: "Ngân sách đe dọa" cùng lúc trên màn (lính = 1, Ký Sinh = 0,75, Lính Khiên/Pháo/Tàu nhiễm = 2, Đẻ Trứng = 3).
#: Đủ ngân sách thì địch tiếp theo xếp hàng chờ. Theo hồi; mỗi chu kỳ Vòng lặp +1.
THREAT_CAP = {1: 9, 2: 12, 3: 14}
THREAT_CAP_PER_CYCLE = 1
#: Nghỉ giữa các wave; sau mỗi 2 wave nghỉ dài hơn.
WAVE_BREATH_TICKS = 110
WAVE_LONG_BREATH_TICKS = 200
#: Trần đạn của lính thường (đạn boss không bị giới hạn): quá thì lính tạm ngừng bắn.
ENEMY_BULLET_CAP = {GameMode.CAMPAIGN: 45, GameMode.ENDLESS: 55, GameMode.INFERNO: 100}
