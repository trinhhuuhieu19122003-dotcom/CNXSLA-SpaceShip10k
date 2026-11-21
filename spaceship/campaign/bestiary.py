"""Dữ liệu Sổ tay chiến đấu, theo thứ tự hiển thị trong lưới."""
from dataclasses import dataclass


@dataclass(frozen=True)
class BestiaryEntry:
    name: str
    sprite: str
    description: str
    tip: str


BESTIARY = {
    "grunt": BestiaryEntry(
        "LÍNH ĐÀN", "enemy",
        "Lính tiền tuyến của Đàn Ký Sinh. Bay vào đội hình rồi bắn thẳng vào bạn.",
        "Đứng yên là chết: luôn di chuyển ngang.",
    ),
    "kamikaze": BestiaryEntry(
        "LÍNH CẢM TỬ", "enemy",
        "Lính bị thương nặng sẽ lao thẳng vào tàu.",
        "Hạ dứt điểm, đừng bỏ dở khi chúng còn ít máu.",
    ),
    "parasite": BestiaryEntry(
        "KÝ SINH", "parasite",
        "Nhỏ, nhanh, bay lượn sóng theo bầy. Không bắn, chỉ lao vào.",
        "Plasma và Tia Sét quét bầy hiệu quả nhất.",
    ),
    "shield": BestiaryEntry(
        "LÍNH KHIÊN", "shield_enemy",
        "Khiên phía trước chặn mọi viên đạn bắn thẳng.",
        "Đánh từ bên hông, hoặc dùng Homing / Tia Sét.",
    ),
    "breeder": BestiaryEntry(
        "KẺ ĐẺ TRỨNG", "breeder",
        "Liên tục đẻ Ký Sinh; chết thì vỡ ra thêm 4 con.",
        "Hạ sớm, và chuẩn bị đón bầy con.",
    ),
    "turret": BestiaryEntry(
        "PHÁO THÁP", "turret_base",
        "Đứng yên, kẻ vạch đỏ khóa mục tiêu rồi mới bắn laser.",
        "Thấy vạch đỏ thì bước ra khỏi đường thẳng đó.",
    ),
    "ally": BestiaryEntry(
        "TÀU ĐỒNG MINH BỊ NHIỄM", "infected_ally",
        "Từng là phi đội tuần tra của tàu mẹ. Lượn nhanh, bắn đôi.",
        "Canh nhịp lượn của chúng mà bắn.",
    ),
    "meteor": BestiaryEntry(
        "THIÊN THẠCH", "meteor",
        "Đá trôi trong vành đai. Va vào rất đau.",
        "Bắn vỡ để lấy điểm, thỉnh thoảng rơi đồ.",
    ),
    "wreck": BestiaryEntry(
        "XÁC TÀU", "wreck_1",
        "Xác phi đội của KX-17, trôi giữa tinh vân. Chặn được đạn địch.",
        "Núp sau xác tàu khi mưa đạn.",
    ),
    "crab": BestiaryEntry(
        "KẺ NUỐT DRONE (BOSS)", "boss",
        "Kẻ đã nuốt drone của KX-17.",
        "Pha cuối bắn thêm laser đôi: đứng lệch khỏi tâm.",
    ),
    "octopus": BestiaryEntry(
        "LÍNH GÁC TINH VÂN (BOSS)", "boss2",
        "Chỉ xuất hiện ở chế độ Vô tận.",
        "Pha 2 bắn tỉa: đổi hướng liên tục.",
    ),
    "nest": BestiaryEntry(
        "TỔ MẸ (MINI-BOSS)", "nest_mother",
        "Tổ sinh học khổng lồ, thả Ký Sinh liên tục kèm vòng đạn xoay.",
        "Dọn bầy bằng kỹ năng Nộ rồi dồn sát thương.",
    ),
    "spider": BestiaryEntry(
        "LÕI TINH VÂN (BOSS)", "boss3",
        "Trái tim của tinh vân, có khiên và hồi khiên khi đổi pha.",
        "Laser phá khiên nhanh nhất.",
    ),
    "cruiser": BestiaryEntry(
        "TÀU HỘ TỐNG (MINI-BOSS)", "escort_cruiser",
        "Tàu chiến hộ tống tàu mẹ, đã bị nhiễm. Xuất kích tàu nhiễm.",
        "Hạ các tàu nhiễm nó thả ra trước.",
    ),
    "mothership": BestiaryEntry(
        "TÀU MẸ HY VỌNG (BOSS CUỐI)", "mothership_boss",
        "Ngôi nhà mà KX-17 tìm kiếm suốt hành trình.",
        "Pha 3: con mắt bắn laser tím theo bạn, luôn di chuyển.",
    ),
}
