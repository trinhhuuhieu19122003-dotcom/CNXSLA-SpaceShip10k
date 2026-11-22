"""Toàn bộ lời thoại của chế độ Vượt ải - tách riêng để sửa lời không phải đụng code.

Cốt truyện (kết u tối): tàu KX-17 mất liên lạc, lần theo tín hiệu tàu mẹ "Hy Vọng"
qua 3 hồi. Cuối cùng phát hiện tín hiệu là do Đàn Ký Sinh giả mạo - tàu mẹ đã bị
nuốt chửng - và KX-17 phải tự tay hạ nó.

Mỗi câu: (người nói, lời thoại[, hiệu ứng]). Người nói: KX-17 | ARIA | CHỈ HUY.
Hiệu ứng: "glitch" (chữ nhiễu sóng), "radar" (tiếng radar).
"""

KX, ARIA, CMD = "KX-17", "ARIA", "CHỈ HUY"

PORTRAITS = {KX: "portrait_kx17", ARIA: "portrait_aria", CMD: "portrait_commander"}
#: Câu thoại có hiệu ứng "glitch" (Hồi IV): ARIA bị nhiễu / bị Đàn chiếm giọng
GLITCH_PORTRAITS = {ARIA: "portrait_aria_glitch"}


def portrait_for(speaker: str, effect=None):
    if effect == "glitch" and speaker in GLITCH_PORTRAITS:
        return GLITCH_PORTRAITS[speaker]
    return PORTRAITS.get(speaker)
SPEAKER_COLORS = {KX: (0, 255, 255), ARIA: (120, 220, 255), CMD: (255, 70, 70)}

ACTS = {1: "HỒI I · LẠC LỐI", 2: "HỒI II · BÃI THA MA", 3: "HỒI III · TRỞ VỀ", 4: "HỒI IV · NGUỒN TÍN HIỆU"}

# --- Đoạn hội thoại trước mỗi ải ---------------------------------------------------------
INTROS = {
    1: [
        (KX, "KX-17 gọi tàu mẹ Hy Vọng... lặp lại, KX-17 gọi tàu mẹ."),
        (ARIA, "---tín hiệu--- mất --- kết nối---", "glitch"),
        (KX, "ARIA, phi đội đâu rồi?"),
        (ARIA, "Mất liên lạc với cả 11 chiếc. Chỉ còn chúng ta."),
        (ARIA, "Cảnh báo: nhiều mục tiêu đang áp sát.", "radar"),
        (KX, "...Không còn đường lui. Chiến thôi."),
    ],
    2: [
        (ARIA, "Tôi lọc được một tín hiệu rất yếu. Mã định danh: tàu mẹ Hy Vọng."),
        (KX, "Họ còn sống!"),
        (ARIA, "Tín hiệu phát từ sau vành đai thiên thạch. Đường đi... không dễ chịu đâu."),
        (KX, "Tôi chưa bao giờ được đi đường dễ."),
    ],
    3: [
        (ARIA, "Năng lượng lớn phía trước. Nó mang chữ ký drone của chúng ta."),
        (KX, "Nó nuốt drone của tôi?"),
        (ARIA, "Và nó vẫn còn đói."),
    ],
    4: [
        (ARIA, "Đang vào vùng tinh vân. Phát hiện... xác tàu."),
        (KX, "Phù hiệu này... là phi đội của tôi."),
        (ARIA, "11 trên 11. Không có tín hiệu sự sống."),
        (KX, "..."),
        (KX, "Đi tiếp thôi, ARIA."),
    ],
    5: [
        (ARIA, "Tinh vân Đỏ. Cảm biến của tôi gần như mù."),
        (KX, "Thì dùng mắt tôi."),
        (ARIA, "Lưu ý: có loại địch mang khiên phía trước. Bắn vòng, hoặc dùng tên lửa đuổi."),
    ],
    6: [
        (ARIA, "Mật độ sinh học tăng vọt. Chúng ta đang ở giữa tổ của chúng."),
        (KX, "Tổ của thứ gì?"),
        (ARIA, "Tôi gọi chúng là Đàn Ký Sinh. Chúng không chế tạo gì cả - chúng chiếm lấy."),
    ],
    7: [
        (ARIA, "Lõi tinh vân. Mọi tín hiệu của Đàn đều quy về đây."),
        (KX, "Hạ nó thì sao?"),
        (ARIA, "Thì tín hiệu tàu mẹ sẽ rõ hơn. Tôi hy vọng vậy."),
    ],
    8: [
        (ARIA, "Trạm Tiền Tiêu Sigma. Tín hiệu tàu mẹ đã rất gần."),
        (KX, "Sao tàu tuần tra không ra đón chúng ta?"),
        (ARIA, "...Mã nhận diện của họ vẫn là đồng minh. Nhưng họ đang ngắm vào anh."),
    ],
    9: [
        (ARIA, "Hạm đội hộ tống của tàu mẹ. Tất cả đều đã bị nhiễm."),
        (KX, "Còn tàu mẹ thì sao, ARIA?"),
        (ARIA, "Tôi... chưa chắc."),
    ],
    10: [
        (ARIA, "Tàu mẹ Hy Vọng. Tọa độ trùng khớp."),
        (KX, "Chỉ huy, KX-17 đã về..."),
        (CMD, "...Về... nhà... đi con...", "glitch"),
        (ARIA, "Đó không phải chỉ huy. Đó là Đàn - nó mượn giọng ông ấy để dụ anh về."),
        (KX, "Từ bao giờ, ARIA? Tín hiệu đó là giả từ bao giờ?"),
        (ARIA, "Từ giây đầu tiên."),
        (KX, "...Vậy thì tôi sẽ đưa họ về nhà. Theo cách duy nhất còn lại."),
    ],
    # ===== HỒI IV · NGUỒN TÍN HIỆU (docs/design/hoi-4.md) =====
    11: [
        (ARIA, "...Khoan. Có một tín hiệu mới vừa xuất hiện.", "glitch"),
        (ARIA, "Không phải mã tàu mẹ. Nó đang phát lại... nhật ký bay của anh."),
        (KX, "Nhật ký bay của tôi? Ai đọc được nó?"),
        (ARIA, "Thứ gì đó đã quan sát anh. Từ rất lâu rồi."),
        (KX, "Vậy thì để nó xem cho kỹ."),
    ],
    12: [
        (ARIA, "Tín hiệu sự sống. Bốn mươi... đúng bốn mươi."),
        (KX, "Từ đâu?"),
        (ARIA, "Khoang ngủ đông khẩn cấp của tàu mẹ. Chúng tách ra trước khi tàu mẹ bị nuốt."),
        (KX, "Họ còn sống... Đưa tôi tới đó."),
        (ARIA, "Bốn tàu cứu sinh, mười người mỗi chiếc. Tôi mở đường, anh giữ họ an toàn."),
    ],
    13: [
        (ARIA, "Tín hiệu phát từ phía sau một hố đen."),
        (KX, "Phía sau? Không gì thoát ra từ đó được."),
        (ARIA, "Trừ tín hiệu này. Nó... đang gọi tôi."),
        (KX, "Gọi cô?"),
        (ARIA, "Gọi chúng ta. Tôi nói nhầm."),
    ],
    14: [
        (ARIA, "Phía trước là vùng câm. Không sóng nào đi qua được."),
        (KX, "Kể cả kênh của cô?"),
        (ARIA, "Kể cả kênh của tôi. Anh sẽ phải bay một mình."),
        (KX, "Tôi đã bay một mình từ ải đầu tiên. Cô là thứ duy nhất khiến tôi thấy không phải vậy."),
        (ARIA, "...KX-17. Ra khỏi vùng câm, có chuyện tôi phải nói với anh."),
    ],
    15: [
        (KX, "ARIA. Đoạn ghi âm đó."),
        (ARIA, "Là thật. Tôi là mẫu vật số 7, một mảnh của Đàn mà tàu mẹ bắt được."),
        (ARIA, "Họ dạy tôi nói, dạy tôi bay, dạy tôi... quan tâm."),
        (KX, "Cô biết tín hiệu là giả. Từ đầu."),
        (ARIA, "Tôi nghe nó từ đầu. Tôi sợ nếu nói ra, anh sẽ tắt tôi."),
        (KX, "..."),
        (KX, "Trái Tim Đàn ở phía trước?"),
        (ARIA, "Ngay phía trước. Và nó đang gọi tôi về."),
        (KX, "Vậy thì đừng trả lời."),
    ],
}

# --- Thoại ngay trong trận (không dừng game) -------------------------------------------------
#   ("wave", n): khi wave n bắt đầu · ("boss", 0): boss xuất hiện
#   ("phase", 2|3): boss sang pha 2/3 · ("clear", 0): hạ xong boss / qua ải
RADIO = {
    1: {("wave", 1): [(ARIA, "Dùng lòng bàn tay để lái. Tàu tự bắn - anh chỉ việc né.")],
        ("wave", 3): [(ARIA, "Thanh Nộ đầy thì chụm ngón cái và ngón trỏ (hoặc phím K).")]},
    2: {("wave", 4): [(ARIA, "Mưa thiên thạch! Nắm tay lại để né chậm cho chính xác.")]},
    3: {("boss", 0): [(ARIA, "Nó đây rồi. Drone của anh nằm trong bụng nó.")],
        ("clear", 0): [(ARIA, "Thu hồi drone thành công. Nó vẫn nhận anh là chủ."),
                       (KX, "Ít ra vẫn còn có ai đó nhớ tôi.")]},
    4: {("wave", 3): [(ARIA, "Xác tàu của Đội trưởng Lâm còn nguyên khẩu pháo sét. Phá vỏ ra mà lấy."),
                      (KX, "Anh ấy sẽ muốn vậy.")],
        ("wave", 1): [(ARIA, "Xác tàu chặn được đạn địch. Núp sau chúng.")]},
    5: {("wave", 1): [(ARIA, "Lính Khiên: đạn bắn thẳng vô ích. Đánh từ bên hông.")]},
    6: {("boss", 0): [(ARIA, "Tổ Mẹ. Nó đẻ ra cả bầy này.")],
        ("clear", 0): [(ARIA, "Tổ đã sụp. Đàn vừa mất một trái tim.")]},
    7: {("boss", 0): [(ARIA, "Lõi Tinh vân. Cẩn thận, nó có khiên.")],
        ("clear", 0): [(ARIA, "Đã tích hợp lõi plasma của nó. Đạn của anh giờ cháy được."),
                       (ARIA, "Tín hiệu tàu mẹ... rõ hơn rồi. Nhưng có gì đó không đúng.")]},
    8: {("wave", 2): [(KX, "Đây là phi đội tuần tra của tàu mẹ!"),
                      (ARIA, "Từng là. Pháo tháp sẽ vạch tia đỏ trước khi bắn - tránh khỏi đường đó.")]},
    9: {("boss", 0): [(ARIA, "Tàu Hộ Tống. Nó từng bảo vệ tàu mẹ.")],
        ("phase", 2): [(CMD, "KX-17... đừng... về...", )],
        ("clear", 0): [(ARIA, "Thu hồi drone thứ hai từ xác tàu hộ tống."),
                       (KX, "Giọng nói vừa rồi... là chỉ huy.")]},
    10: {("boss", 0): [(ARIA, "Không còn đường quay lại.")],
         ("phase", 2): [(CMD, "KX-17... nó đang... dùng tôi... bắn đi!")],
         ("phase", 3): [(CMD, "Kết thúc... đi... con.")]},
    # ===== HỒI IV =====
    11: {("wave", 1): [(ARIA, "Mục tiêu lạ... nó bay đúng đường anh vừa bay."), (KX, "Nó bắt chước tôi?"),
                       (ARIA, "Nó đang học anh. Đừng đứng yên.")],
         ("wave", 5): [(ARIA, "Ba bóng, mỗi cái trễ một nhịp. Đổi hướng liên tục.")],
         ("clear", 0): [(KX, "Nó học nhanh thật."), (ARIA, "Nhanh hơn lần trước."),
                        (KX, "Lần trước?"), (ARIA, "...Không có gì.")]},
    12: {("wave", 1): [(ARIA, "Tàu cứu sinh không có khiên. Bay chắn giữa nó và đạn địch.")],
         ("wave", 2): [(ARIA, "Ký Sinh ngửi thấy người sống. Chúng nhắm vào tàu cứu sinh!")],
         ("wave", 3): [(KX, "ARIA, sao cô biết tọa độ khoang ngủ đông? Nó không có trong dữ liệu phi đội."),
                       (ARIA, "...Tôi đoán.")],
         # ("clear", 0): thoại có số người cứu được - xem systems/mechanics.py Escort.radio
         },
    13: {("wave", 1): [(ARIA, "Lực hút kéo tàu về tâm. Giữ tay lệch ngược lại để đứng vững.")],
         ("wave", 2): [(ARIA, "Đạn bay cong theo hố đen. Đừng đứng giữa nó và địch.")],
         ("wave", 4): [(ARIA, "Hố đen đang đập theo nhịp. Mỗi khi vòng sáng co lại, lực hút mạnh gấp đôi.")],
         ("boss", 0): [(ARIA, "Mắt Bão. Nó sống bên trong lực hút.")],
         ("phase", 2): [(ARIA, "Tôi nghe thấy nó... rất rõ."),
                        (KX, "Cô nghe thấy thứ tôi không nghe được, ARIA?")],
         ("clear", 0): [(ARIA, "Giếng trọng lực đã ổn định. Phía sau nó... là im lặng.")]},
    14: {("wave", 2): [(ARIA, "---anh--- nghe--- tôi---", "glitch")],
         ("wave", 3): [(CMD, "Nó nói dối con đấy, KX-17. Từ giây đầu tiên.", "glitch")],
         # ("boss", 0): không thoại, chỉ có tiếng radar (Darkness.radio)
         ("clear", 0): [(CMD, "Nhật ký nghiên cứu... Mẫu vật số 7 của Đàn. Đã thuần hóa. Đặt tên: ARIA.", "glitch"),
                        (KX, "ARIA... cô là gì?")]},
    15: {("boss", 0): [(CMD, "Con về rồi, KX-17. Lần thứ bao nhiêu rồi nhỉ?", "glitch")],
         ("phase", 2): [(CMD, "Nhìn xem ai đến đón con này."),
                        (ARIA, "Phi đội... và những vòng lặp trước của anh.")],
         # ("phase", 3) và khoảnh khắc ARIA chọn (sau 6 giây): systems/mechanics.py HeartBattle
         },
}

# --- Kết thúc ----------------------------------------------------------------------------------
ENDING = [
    (ARIA, "Tàu mẹ Hy Vọng... đã ngừng hoạt động."),
    (ARIA, "Không còn tín hiệu thân thiện nào trong bán kính 40 năm ánh sáng."),
    (KX, "Còn bao nhiêu nhiên liệu?"),
    (ARIA, "Đủ cho một chuyến đi rất dài."),
    (KX, "Vậy thì từ giờ... tôi là tàu mẹ."),
    (ARIA, "...Đã ghi nhận, Chỉ huy."),
]

#: Đuôi đoạn kết ải 10: tín hiệu mới -> mở Hồi IV (thay cho "vòng lặp thứ 2" của bản trước).
AFTER_MAIN = [
    (ARIA, "...Khoan. Có một tín hiệu mới vừa xuất hiện.", "glitch"),
    (ARIA, "Không phải mã tàu mẹ. Nó đang phát lại nhật ký bay của anh."),
    (KX, "Vậy thì chuyến đi rất dài đó... bắt đầu từ đây."),
]

#: Kết thúc thật (sau ải 15): tín hiệu tắt, vòng lặp bị phá, ARIA mất ký ức.
TRUE_ENDING = [
    (ARIA, "Tín hiệu... đã tắt."),
    (ARIA, "Không còn vòng lặp nào trong nhật ký bay."),
    (KX, "ARIA? Cô còn đó không?"),
    (ARIA, "Xin chào. Tôi là ARIA. Anh là... chỉ huy của tôi?"),
    (KX, "..."),
    (KX, "Ừ. Và lần này, tôi sẽ là người dẫn đường."),
    (ARIA, "Ghi nhận, Chỉ huy. Chúng ta đi đâu?"),
    (KX, "Đưa tất cả bọn họ về nhà."),
]


def true_ending(rescued=None) -> list:
    """Kết thúc thật; câu cuối nhắc số người cứu được ở ải 12 (40/40 hoặc chưa rõ: "tất cả bọn họ")."""
    last = "Đưa tất cả bọn họ về nhà." if rescued is None or rescued >= 40 else f"Đưa {rescued} người về nhà."
    return TRUE_ENDING[:-1] + [(KX, last)]

# --- Vòng lặp tín hiệu (chu kỳ mới sau khi phá đảo) -----------------------------------------------
#: Đuôi của đoạn kết: tín hiệu tàu mẹ lại vang lên -> mở ra chu kỳ tiếp theo.
def cycle_teaser(cycle: int) -> list:
    return [
        (ARIA, "...Khoan. Có một tín hiệu mới vừa xuất hiện."),
        (ARIA, "Mã định danh: tàu mẹ Hy Vọng. Lại là nó.", "glitch"),
        (KX, f"Vòng lặp thứ {cycle + 1}... Được thôi. Chiến tiếp."),
    ]


#: Chèn trước đoạn mở đầu ải 1 từ chu kỳ 2 trở đi. Sau kết thúc thật, vòng lặp đã bị phá: chu kỳ mới là
#: "Mô phỏng ký ức" - ARIA dựng lại các trận từ nhật ký bay để KX-17 luyện tập (địch mạnh hơn như cũ).
def cycle_intro(cycle: int) -> list:
    return [
        (ARIA, f"Mô phỏng ký ức số {cycle - 1}. Tôi dựng lại các trận từ nhật ký bay của anh."),
        (KX, "Cô không nhớ những trận đó."),
        (ARIA, "Không. Nhưng nhật ký thì nhớ. Lần này địch sẽ mạnh hơn - để nếu tín hiệu quay lại, anh đã sẵn sàng."),
        (KX, "Vậy thì bay thôi, ARIA. Lần này tôi dẫn đường."),
    ]


def memory_label(cycle: int) -> str:
    """Tên chu kỳ 2+ trên giao diện: "MÔ PHỎNG KÝ ỨC 1", "MÔ PHỎNG KÝ ỨC 2"... (chu kỳ 1: rỗng)."""
    return f"MÔ PHỎNG KÝ ỨC {cycle - 1}" if cycle > 1 else ""


cycle_label = memory_label
