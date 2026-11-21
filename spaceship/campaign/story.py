"""Toàn bộ lời thoại của chế độ Vượt ải - tách riêng để sửa lời không phải đụng code.

Cốt truyện (kết u tối): tàu KX-17 mất liên lạc, lần theo tín hiệu tàu mẹ "Hy Vọng"
qua 3 hồi. Cuối cùng phát hiện tín hiệu là do Đàn Ký Sinh giả mạo - tàu mẹ đã bị
nuốt chửng - và KX-17 phải tự tay hạ nó.

Mỗi câu: (người nói, lời thoại[, hiệu ứng]). Người nói: KX-17 | ARIA | CHỈ HUY.
Hiệu ứng: "glitch" (chữ nhiễu sóng), "radar" (tiếng radar).
"""

KX, ARIA, CMD = "KX-17", "ARIA", "CHỈ HUY"

PORTRAITS = {KX: "portrait_kx17", ARIA: "portrait_aria", CMD: "portrait_commander"}
SPEAKER_COLORS = {KX: (0, 255, 255), ARIA: (120, 220, 255), CMD: (255, 70, 70)}

ACTS = {1: "HỒI I · LẠC LỐI", 2: "HỒI II · BÃI THA MA", 3: "HỒI III · TRỞ VỀ"}

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
