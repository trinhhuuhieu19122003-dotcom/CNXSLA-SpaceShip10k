# Changelog

## [2.1.0-dev] – Chữ sắc nét, chuỗi hạ địch, kamikaze báo trước
- **Chữ sắc nét khi toàn màn hình** (`ui/crisp.py`): `Assets.text` trả về `TextSurface` nhớ chữ/cỡ/màu; tấm vẽ
  800x700 và tấm 2 bảng bên là `CrispSurface`. Khi phóng > 1,05 lần, chữ được ghi lại rồi vẽ lại bằng font cỡ lớn
  ngay trên ảnh đã phóng (chọn cỡ có bề rộng khớp nhất). Vật vẽ đè lên chữ thì chữ được vẽ thường trước, giữ đúng
  thứ tự (bảng Tạm dừng, Kết quả phủ lên trận). Hình ảnh vẫn phóng như cũ.
- **Hết giật hình ở menu toàn màn hình**: nền mờ 2 bên làm tối trên ảnh 40x35 trước khi phóng (trước đây làm tối
  3 triệu điểm ảnh, ~27 ms, mỗi 4 hình). Menu 1080p ~19 ms → ~10 ms mỗi hình.
- **Kamikaze báo trước**: khựng 0,5 giây "khóa mục tiêu" (thân rung, vòng đỏ co lại, vạch ngắm, tiếng bíp), rồi lao;
  chỉ bẻ lái 1°/tick trong 20 tick đầu rồi bay thẳng. Đứng yên vẫn bị đâm, né ngang kịp thì trượt.
- **Hủy đạn**: hạ boss hoặc boss sang pha mới → đạn địch trên màn thành tia sáng vàng, +5 điểm mỗi viên.
- **Chuỗi hạ địch**: hạ liên tiếp (cách nhau < 2,5 giây), mỗi 10 lần +1 bậc nhân điểm, tối đa x4; bị trúng đạn mất
  chuỗi. Hiện "CHUỖI xN" trên tàu, trên dải điểm, ở bảng trái màn rộng; màn Kết quả ghi chuỗi dài nhất.
- **Bất tử sau khi trúng đạn rút còn 0,25 giây** (trước: 0,5): bot né đạn chạy 6 ván mỗi cấu hình cho thấy 0,5 giây
  làm số mạng mất giảm ~60% ở ải 6 và ~37% ở Hỏa ngục, quá dễ. 0,25 giây vẫn chặn được "trúng cả chùm 3 viên".
- **Sát đạn (graze)**: đạn địch sượt qua trong 34 px mà không trúng → +2 điểm (nhân theo chuỗi), tia sáng nhỏ,
  tiếng "xẹt", và giữ chuỗi hạ không bị đứt. Không tính khi đang bất tử.
- **Thống kê**: lưu chuỗi hạ dài nhất của từng chế độ (`ModeRecord.best_combo`), hiện dưới Điểm cao.
- **Bảng điểm** (thẻ thứ 3 ở màn Thành tựu): 5 ván điểm cao nhất mỗi chế độ, kèm ải / thời gian, chuỗi dài nhất,
  ngày chơi (`ModeRecord.top_runs`; file lưu cũ / dữ liệu lạ vẫn nạp được).
- **3 huy hiệu mới** (tổng 21): Bậc thầy chuỗi (chuỗi 30), Luồn lách (100 lần sát đạn trong một ván), Dọn sạch
  bầu trời (hủy 30 viên đạn cùng lúc). Thẻ huy hiệu thấp hơn để đủ 7 hàng: ngày đạt / tiến độ nằm bên phải tên.
- Bảng trái màn rộng hiện số lần **sát đạn**; mất chuỗi từ 10 trở lên hiện chữ đỏ **"MẤT CHUỖI N"**.
- **Tiếng mới** (tổng hợp bằng numpy): `lock_on`, `heartbeat` (khớp nhịp viền đỏ khi máu thấp), `bullet_cancel`,
  `graze`.
- 27 test mới (`tests/test_crisp.py`, thêm vào `tests/test_game_feel.py`, `tests/test_storage.py`,
  `tests/test_achievements.py`), tổng 151. Chạy thử ngẫu nhiên dài
  (10 ải + Vô tận + Hỏa ngục, 1 phút mỗi chế độ, 6 cỡ cửa sổ) không lỗi.

## [2.1.0-dev] – Cảm giác đánh
- **Rung kiểu trauma** (`World.shake` / `tick_feel`): mỗi cú cộng trauma 0..1, độ lệch = 12 px × trauma², giảm dần.
  Cú nhẹ chỉ hơi nhích, hạ boss giật mạnh; thay cho rung ±8 px cố định.
- **Khựng hình (hitstop)** `World.freeze`: trúng đạn 4 tick, mất mạng 10, hạ địch to 3, hạ boss 12. Không cộng dồn;
  chữ thông báo vẫn chạy trong lúc khựng.
- **Bất tử ngắn sau khi trúng đạn** (`MERCY_TICKS` = 0,25 giây): chùm đạn sát nhau chỉ trừ máu một lần. Lúc bất tử tàu
  chỉ ẩn 1/4 thời gian (trước là 1/2) nên vẫn thấy rõ để né; vòng vàng chỉ còn sau khi hồi sinh.
- **Viền đỏ** (`ui/feel.py`): loé khi trúng đạn, đập theo nhịp tim khi máu ≤ 30%. Vẽ trước HUD.
- **Chớp sáng mờ dần** (tối đa alpha 150) thay cho trắng xóa cả màn.
- Cài đặt mới **RUNG & NHÁY MÀN HÌNH: ĐẦY ĐỦ / NHẸ / TẮT** (`settings.screen_fx`).
- 12 test mới (`tests/test_game_feel.py`), tổng 124.

## [2.1.0-dev] – Đánh bóng giao diện
- **HUD trong trận gọn 4 góc** (cửa sổ thường): dải mảnh trên cùng "ĐIỂM · ẢI · WAVE"; góc dưới trái mạng + cử chỉ
  tay + máu + Nộ (gợi ý kỹ năng khi đầy); góc dưới phải vũ khí + tăng cường. Hai ô góc **tự mờ khi tàu bay sát**.
  Bỏ nhãn lẻ "DRONE", "ĐIỀU KHIỂN: PHÍM"; thống nhất dấu "·". Thanh máu lính chỉ hiện ~1,5 giây sau khi trúng đạn.
- **Đạn địch dễ thấy**: nền trong trận tối đi ~40%, đạn địch có viền sáng.
- **Độ nét**: chữ phụ sáng hơn, chữ gợi ý tối thiểu cỡ 15; cửa sổ thường dùng bội số nguyên của 800x700 (vẽ 1:1, nét
  tuyệt đối); phóng >= 2 lần (2K/4K) nhân điểm ảnh trước rồi mới làm mượt (`app.upscale`).
- Màn Chọn ải: nút **CHƠI MỚI** tách ra góc trên phải, viền đỏ.
- Màn **Kết quả**: sao bật lên lần lượt kèm tiếng, số liệu đếm tăng dần, huy hiệu mới thành thẻ có biểu tượng.
- Màn **Tạm dừng**: thông tin ải/wave/điểm/máu + **2 thanh trượt âm lượng** (`ui/volume_sliders.py`, dùng chung với
  Cài đặt); kéo bằng tay chỉ bắt đầu khi tay nằm trên thanh trượt.
- 3 test mới, tổng 112.

## [2.1.0-dev] – Huy hiệu thành tựu & Chơi mới
- **18 huy hiệu** (`campaign/achievements.py`): qua ải, 3 sao, phá đảo, toàn sao, chu kỳ 2, đủ Sổ tay, boss ở độ khó
  Khó, trụ 5/10 phút Vô tận, 3 phút Hỏa ngục, 20 boss, 1 000 địch, 25 lần Nộ, hộ vệ chặn 100 đạn, qua ải chỉ bằng tay,
  hạ Tàu Mẹ bằng Tia Sét. Lưu kèm ngày đạt; bộ đếm cộng dồn (`counters`). Save v5.
- Đạt trong trận: thẻ **"THÀNH TỰU MỚI"** góc phải (chung chỗ với "ĐỊCH MỚI"); màn kết quả liệt kê huy hiệu mới.
- Màn **Thành tựu** chia 2 thẻ: **Huy hiệu** (đạt: sáng vàng + ngày; chưa đạt: khóa + cách đạt + thanh tiến độ cho
  huy hiệu đếm số) và **Thống kê** (bảng cũ + chu kỳ, số lần Nộ, đạn hộ vệ chặn). Đổi thẻ bằng phím/chuột/tay.
- **CHƠI MỚI** ở màn Chọn ải: chọn 2 lần, cảnh báo đỏ; xóa sạch tiến độ như mới cài game, giữ Cài đặt, tự sao lưu
  file cũ thành `save_backup_<ngày giờ>.json`.
- 6 test mới (`tests/test_achievements.py`), tổng 109.

## [2.1.0-dev] – Bản đồ hành trình (thay màn radar)
- Đoạn hội thoại mở đầu **mọi ải** dùng **bản đồ hành trình** (`ui/journey_map.py`): 10 ải là 10 điểm sao chia
  3 cụm theo hồi; ải đã qua sáng xanh kèm sao, ải sắp chơi nhấp nháy đỏ, ải chưa tới mờ; dấu thoi đỏ ở ải có
  boss; bóng Tàu Mẹ sau ải 10. Tàu bay từ ải trước tới ải này theo đường cong. Nền là ảnh của hồi phóng to chậm
  + lưới chiến thuật. Câu "nhiều mục tiêu áp sát" làm hiện bầy chấm đỏ quây quanh điểm ải.
- Chân dung có "chất tín hiệu" theo người nói: ARIA (AI) sọc quét + thỉnh thoảng lệch dòng; Chỉ huy (ở xa) nhiễu hạt,
  chập chờn; KX-17 hình sạch.
- 1 test mới (mọi ải có bản đồ, tàu bay tới nơi, bầy chấm đỏ hiện đúng câu thoại), tổng 103.

## [2.1.0-dev] – Đạn đẹp hơn, drone có ích
- **Tia Sét** vẽ lại: quầng sáng cộng sáng, thân vàng lõi trắng, 1-2 nhánh rẽ xanh điện, rung nhấp nháy, chớp sáng ở
  điểm trúng; tồn tại lâu hơn (10 tick) nên nhìn thấy liên tục. Bão Sét và màn Hướng dẫn dùng chung kiểu mới.
- Plasma to và sáng hơn (quầng ngoài + vệt dài hơn); Laser có lõi trắng nóng; Homing có lửa đuôi phập phồng.
- **Drone** tự ngắm địch gần nhất trong tầm 420, bắn kim sáng cam ~4 phát/giây, 4 sát thương/phát (bản cũ: 1 phát/giây,
  2 sát thương, bắn thẳng) - khoảng 16 sát thương/giây; không hồi Nộ.
- **Drone thứ 2 = DRONE HỘ VỆ**: bay vòng quanh tàu, tự bắn hạ viên đạn địch gần nhất trong tầm 150 (~2 viên/giây)
  bằng tia điện xanh. Hình riêng `assets/images/drone_guard.png` (Codex vẽ: thân lục giác, 6 tấm chắn, lõi cyan),
  tự xoay chậm khi bay, lõi chớp sáng lúc bắn. Ảnh so sánh: `docs/screenshots/dan-truoc-sau.png`.

## [2.1.0-dev] – Nhịp sóng: thả địch có nhịp, hết "ồ ạt"
- Lính trong đội hình **bay vào lần lượt** (Galaga), nhanh rồi chậm dần; **không bắn khi đang bay vào** và chờ
  0,75 giây sau khi tới chỗ. Đội hình nhiều hàng được nén vào trong màn hình.
- **Ngân sách đe dọa** (`THREAT_CAP` theo hồi, +1 mỗi chu kỳ): đủ thì địch tiếp theo xếp hàng chờ.
- **Nghỉ giữa wave** 1,8 giây, sau mỗi 2 wave nghỉ 3,3 giây.
- **Trần đạn** của lính; boss chỉ gọi thêm lính khi xung quanh còn ít.
- Lính **trôi xuống tối đa tới giữa màn**, đứng quá 14 giây thì **rút lui** lên trên (không còn kẹt vì vài con sót).
- **Vô tận / Hỏa ngục** viết lại theo nhịp *dồn lên -> cao trào -> thả lỏng* (AI Director của Left 4 Dead):
  thả từng tốp có hình dạng, ngân sách tăng theo phút có trần; mất nhiều máu thì được nghỉ sớm; hạ boss được nghỉ.
- Ải 4: wave Ký Sinh dày nhất giảm từ 28 xuống 20 con, thả so le.
- Đo bằng bot: Vô tận trung bình 46 -> 7 địch trên màn; Hỏa ngục tối đa 255 -> 17 địch. Chi tiết, nguồn tham khảo
  và cách chỉnh số: `docs/design/nhip-song.md`. 8 test mới (`tests/test_pacing.py`), tổng 101.

## [2.1.0-dev] – Vòng lặp tín hiệu & thanh trượt âm lượng
- **Chu kỳ mới (New Game+)**: phá đảo xong, màn Chọn ải có nút "CHU KỲ 2" (chọn 2 lần để xác nhận). Ải về 1, sao
  của chu kỳ mới tính lại từ 0; Sổ tay, kỷ lục, thống kê và Hỏa ngục được giữ. Mỗi chu kỳ địch +25% máu, bắn
  nhanh hơn 12%. Save v4 (`cycle`, `cycle_complete`, `cycle_history`); save cũ đã phá đảo được mở chu kỳ 2 ngay.
- Cốt truyện: đoạn kết thêm đuôi "tín hiệu tàu mẹ lại vang lên"; từ chu kỳ 2, mở đầu ải 1 có thoại KX-17 nhận ra
  mọi thứ đang lặp lại. Số chu kỳ hiện ở menu, màn Chọn ải, hội thoại, bảng bên và HUD.
- Cài đặt: **Nhạc nền / Hiệu ứng thành thanh trượt** - bấm-kéo chuột, phím trái/phải ±5%, chụm tay rồi di ngang.
- 5 test mới (`tests/test_cycle.py`, thanh trượt bằng tay), tổng 93.

## [2.1.0-dev] – Âm thanh
- Viết lại `core/audio.py`: 25 hiệu ứng CC0 (Kenney, SRG774) thay cho 2 tiếng cũ; giới hạn số tiếng phát chồng và
  khoảng nghỉ tối thiểu cho từng tiếng; tiếng lặp nhiều có 3 cao độ ngẫu nhiên (RNG riêng, không làm lệch trận).
- Gắn tiếng cho mọi sự kiện: bắn theo từng súng, trúng đạn, nổ nhỏ/lớn/boss, bị thương, khiên chặn đạn, nhặt đồ,
  lên cấp, **đổi súng mất cấp** (tiếng "hụt"), Nộ đầy, 4 kỹ năng Nộ, boss đổi pha, qua ải, thắng/thua, menu.
- Tiếng tổng hợp bằng numpy: **còi báo động boss**, **giọng gõ chữ riêng** cho KX-17 / ARIA / Chỉ huy trong đoạn hội
  thoại, tiếng mở bộ đàm khi có thoại trong trận.
- Nhạc: đoạn hội thoại, **mỗi hồi một bài**, trận boss dùng **nhạc gốc thời đại học**, Tàu Mẹ có nhạc trận cuối,
  đoạn kết có nhạc riêng; Hỏa ngục hết im lặng. Đổi bài nhỏ dần rồi to dần; nhạc tự nhỏ lại khi có thoại/tạm dừng.
- Cài đặt thêm **Nhạc nền** và **Hiệu ứng** (0–100%, lưu trong `settings.json`); đếm ngược 3-2-1 có tiếng tích.
- Hai bài nhạc gốc được giảm âm lượng cho đều với nhạc mới; bỏ `laser.mp3`, `explosion.mp3` cũ (vẫn còn ở `main`).
- Thêm `CREDITS.md`; 10 test mới (`tests/test_audio.py`), tổng 77.

### Sửa lỗi khi chơi thử thật
- Game tự tắt sau vài giây: tay đặt trên bàn trỏ vào mục THOÁT và bị đọc nhầm thành chụm tay. THOÁT giờ phải
  chọn 2 lần (lần đầu hiện "THOÁT?", tự hủy sau 3 giây).
- Cài đặt thêm **Chọn menu bằng tay: Bật/Tắt** (lưu `hand_menu` trong `settings.json`). Tắt thì menu chỉ dùng
  phím/chuột, trong trận vẫn lái tàu bằng tay.
- **Toàn màn hình** thành một mục trong Cài đặt (lưu `fullscreen`), thêm phím tắt Alt + Enter bên cạnh F11.
  Màn hình rộng hơn khung 800x700 thì hai bên được phủ bằng chính khung hình làm mờ thay cho dải đen.
- Windows: bật DPI awareness để màn hình phóng to 125%/150% không kéo giãn cửa sổ làm nhòe chữ; cửa sổ thường
  tự chọn cỡ ~85% chiều cao màn hình.
- **Màn rộng phủ kín** (toàn màn hình 16:9, cửa sổ phóng to): trong trận, khung = bảng trái + chiến trường 800x700
  + bảng phải. Bảng trái: ải, điểm, thời gian, máu, Nộ, vũ khí, tăng cường, mạng. Bảng phải: ô camera tay, cử chỉ,
  lời thoại kèm chân dung. Chiến trường chỉ còn thanh boss nên thoáng hẳn; tầm vung tay và cân bằng không đổi.
  Hai bảng vẽ lại 30 lần/giây để tiết kiệm. Các màn menu giữ khung giữa + nền mờ.
- Cài đặt gọn lại: chỉ hiện ghi chú của mục đang chọn.
- **Chơi bằng icon**: `Tao loi tat.bat` tạo lối tắt SpaceShip 10K (icon riêng) trên Desktop + Start menu, chạy bằng
  `pythonw` nên không hiện cửa sổ dòng lệnh; log ghi vào `spaceship.log`, lỗi hiện hộp thoại. Cửa sổ game có icon; App ID riêng (`IamSoftware.SpaceShip10K`, gắn cả vào lối tắt) để
  Taskbar hiện icon game thay vì icon Python.
- Hướng dẫn · Vũ khí: 4 thẻ dùng chung bố cục nhãn/giá trị, khối chữ căn giữa, không còn dòng dính nhau;
  ô thẻ được trỏ căn giữa chữ.
- `requirements.txt` chỉ dùng ASCII: pip cũ trên Windows đọc theo cp1252 và báo `UnicodeDecodeError`.

## [2.1.0-dev] – Màn Hướng dẫn mới & Sổ tay chiến đấu
- Màn Hướng dẫn chia **5 thẻ**: Điều khiển · Vũ khí · Vật phẩm · Kẻ địch · Chế độ chơi; đổi thẻ bằng ←/→,
  chuột hoặc di tay + chụm tay.
- Thẻ Điều khiển vẽ **bàn tay 21 điểm có chuyển động** (lái, nắm tay né chậm, chụm tay tung Nộ, bỏ tay để nghỉ).
- Thẻ Vũ khí có **khung bắn thử** cho từng súng; số liệu lấy thẳng từ `config` nên không lệch khi cân bằng lại.
- Thẻ Vật phẩm minh họa luật cảnh báo đổi súng (hộp nháy đỏ + "!").
- **Sổ tay chiến đấu** (`campaign/bestiary.py`, 15 mục): chưa gặp thì hiện bóng đen "???", gặp lần đầu trong
  trận thì mở khóa, lưu vào `save.json` (`seen_enemies`) và hiện thẻ **"ĐỊCH MỚI"** 3 giây, không dừng game.
- 9 test mới (`tests/test_guide.py`, `tests/test_storage.py`), tổng 67. Thực hiện bởi Codex, Claude rà soát.

## [2.1.0-dev] – Giao diện mới
- Đóng gói font **Chakra Petch** (tiêu đề, nút, nhãn) và **Exo 2** (chữ mô tả, lời thoại), giấy phép SIL OFL;
  `Assets.font(role=...)` theo vai trò, thiếu file thì lùi về font hệ thống.
- **Menu chính mới**: logo + phụ đề "Tín hiệu cuối cùng", danh sách mục căn trái, ảnh tàu và Tàu Mẹ làm nền,
  một màu chủ đạo cyan; Hỏa ngục hiện ổ khóa khi chưa phá đảo.
- **Điều khiển menu không cần chuột** (`ui/menu_list.py`): phím mũi tên/Enter, di tay để chọn + chụm tay để vào
  (có vòng tiến trình); áp dụng cho Menu, Chọn ải, Cài đặt, Tạm dừng, Kết quả. Lần chụm dùng cho menu không
  kích hoạt kỹ năng Nộ khi quay lại trận.
- Khung dùng chung kiểu sci-fi (góc ngoặc sáng, dải tiêu đề) cho mọi màn phụ, HUD, hội thoại.
- Chuyển cảnh mờ đen 0,25 giây (chỉ ở lớp vẽ, logic đổi scene ngay).
- 12 test mới (`tests/test_ui.py`, điều hướng menu bằng phím/tay). Thực hiện bởi Codex, Claude rà soát.

## [2.1.0-dev] – Vũ khí, 10 ải, cốt truyện (giai đoạn 3–5)
### Vũ khí
- Thêm súng **Tia Sét** (nhảy dây chuyền, xuyên khiên Lính Khiên); rơi từ ải 4 (xác tàu của phi đội).
- Mỗi súng một **kỹ năng Nộ** riêng thay cho Nuke dùng chung: Đại Pháo, Vòng Plasma, Mưa Tên Lửa, Bão Sét.
- Cấp 6 tối thượng: Plasma nổ lan, Homing 7 tên lửa; **Laser cấp 6 giảm sức mạnh** (15 → 9, nửa sát thương cộng thêm).
- Homing được tăng sức (4 → 7, bắn nhanh hơn) để không lép vế khi đánh boss. Kỹ năng Nộ không tự hồi Nộ.
- **Drone thứ hai** (bay bên trái). Phần thưởng boss **tự bay vào tàu**, không rơi mất; có cả ở Vô tận/Hỏa ngục.
- Giữ nguyên luật "ăn súng khác loại thì về cấp 1" (cố ý).

### Màn chơi
- Vượt ải từ 3 stage thành **10 ải / 3 hồi**, dữ liệu ải tách riêng (`campaign/levels.py`).
- 6 loại địch mới: Ký Sinh, Lính Khiên (chặn đạn bắn thẳng), Kẻ Đẻ Trứng, Pháo tháp (vạch đỏ cảnh báo),
  tàu đồng minh bị nhiễm, xác tàu (núp được).
- Boss theo bảng thông số: Kẻ Nuốt Drone, Lõi Tinh vân, mini-boss Tổ Mẹ & Tàu Hộ Tống, boss cuối Tàu Mẹ (3 pha).
  Thanh máu boss lớn trên đầu màn hình, có vạch chia pha.
- Ảnh nền cuộn theo từng hồi, sương mù ở Tinh vân Đỏ.
- Màn **Chọn ải**: sao 1–3, khóa/mở ải, **độ khó Dễ/Thường/Khó**; tiến độ lưu trong save.json.
- Vô tận: càng lâu càng nhiều loại địch, boss đổi loại. Hỏa ngục **mở khóa khi phá đảo**.

### Cốt truyện
- Toàn bộ lời thoại ở `campaign/story.py`: hội thoại trước mỗi ải có **chân dung** KX-17 / ARIA / Chỉ huy,
  thoại ngay trong trận (không dừng game), kết thúc u tối có ảnh riêng.
- 19 ảnh mới (địch, boss, chân dung, nền, ảnh kết) do Codex tạo, đã thu nhỏ + nén; xóa watermark ở boss3.png.

## [2.1.0-dev] – Hình ảnh phát sáng (giai đoạn 2)
- Đạn vẽ lại kiểu neon (cộng màu, quầng sáng cache sẵn): Plasma là quả cầu năng lượng có vệt mờ,
  Laser là vệt sáng, Laser cấp 6 là **một dải tia liền từ mũi tàu**, Homing có lửa đuôi + vệt khói.
- Đạn địch **viền tối + lõi sáng**, toàn tông nóng (đỏ/hồng/tím/cam) để không lẫn với đạn mình.
- Lóe sáng đầu nòng, quầng sáng động cơ; địch **nháy trắng** khi trúng; tia lửa theo màu súng.
- Vụ nổ: chớp sáng + sóng xung kích + mảnh cháy + tia lửa; boss nổ dây chuyền; Nuke nổ to.
- Hộp vật phẩm mới: lục giác phát sáng, **mỗi loại một hình**; hộp súng khác súng đang cầm
  **nháy viền đỏ + dấu "!"**.
- HUD mới: thanh máu chia ô đổi màu, thanh Nộ sáng nhấp nháy khi đầy, ô súng có 6 vạch cấp.

## [2.1.0-dev] – Điều khiển tay đỡ mỏi (giai đoạn 1)
- **Hiệu chỉnh tư thế nghỉ**: giữ yên tay ~2 giây, chỗ đó thành giữa màn hình; vùng điều khiển nhỏ quanh đó
  (tì khuỷu tay, nhích tay một gang là đi hết màn hình). Lưu lại cho lần sau.
- **Độ nhạy tay** Thấp / Vừa / Cao; **tự động bắn** (mặc định bật) — cả hai trong màn **Cài đặt** mới.
- Cử chỉ mới: **chụm ngón cái + trỏ** giữ 0,5 giây = kỹ năng Nộ (thay cho giơ 3 ngón dễ nhận nhầm);
  **nắm tay** = né chậm, hiện đúng điểm va chạm. Phím: Shift = né chậm.
- **Bỏ tay xuống là tự tạm dừng**; đưa tay lên lại tự đếm 3‑2‑1. Mọi lần chơi tiếp đều có đếm ngược.
- HUD có chỉ báo cử chỉ + vòng tròn đầy dần khi giữ chụm ngón, cảnh báo khi sắp mất tay.

## [2.0.0] – 2026-11-21 · Đại tu

### Kiến trúc
- Tách `main.py` (991 dòng) + `entities.py` + `ui.py` + `vision.py` + `settings.py` thành package
  `spaceship/` gồm `core/`, `input/`, `entities/`, `systems/`, `scenes/`, `ui/` (xem `docs/ARCHITECTURE.md`).
- Mỗi màn hình là một `Scene`; vòng lặp *fixed timestep* 60 tick/giây; màn hình ảo 800×700 co giãn giữ tỉ lệ.
- Mọi con số cân bằng gom về `config.py`. Bỏ toàn bộ `except:` trống, thay bằng log rõ ràng.
- `assets/images` + `assets/audio` thay cho `graphics/` + `audio/` (tên file sạch, không còn `.wav.mp3`).
- Thêm 31 test tự động (`python -m unittest discover -s tests -t .`).

### Sửa lỗi
- **Game chạy chậm theo tốc độ webcam** → camera + MediaPipe chạy ở luồng riêng.
- **Không có webcam thì không chơi được** → luôn có điều khiển bàn phím; camera lỗi chỉ hiện thông báo.
- **MediaPipe ≥ 0.10.31 làm game crash** (`mp.solutions` bị xóa) → hỗ trợ cả `HandLandmarker` (Tasks API).
- Đạn địch bay lên trên không bao giờ bị xóa (càng chơi càng giật) → dọn đủ 4 mép màn hình.
- Phím SPACE ở cutscene không tua được (gán nhầm trạng thái `"OUT"`).
- Bảng Hướng dẫn (840px) và Thành tựu (860px) tràn khỏi màn hình 800px.
- Ảnh sprite 16:9 bị ép thành hình vuông → giữ đúng tỉ lệ, cắt viền trong suốt.
- Tham chiếu tới 5 ảnh nền không tồn tại (`background_space`, `nebula_*`...) → bỏ.
- Thống kê chỉ lưu khi phá kỷ lục, `highscore.txt` lệch `stats.json` → một file `save.json`
  cộng dồn, ghi an toàn (atomic), lưu ở thư mục người dùng thay vì trong repo; tự nhập dữ liệu cũ.
- Nuke giết địch: thiên thạch không được điểm, logic "địch chết" lặp 4 nơi lệch nhau → gom về `kill_enemy`.
- Tia laser của Drone trúng một địch ở nhiều tick liên tiếp (sát thương bị nhân lên) → xuyên thấu nhưng mỗi địch trúng 1 lần.
- Font được tạo lại mỗi lần vẽ → cache.

### Cân bằng
- Hạ Boss: +10 điểm → **+250 × stage**.
- Thiêu đốt: 1.5 → **6 HP/giây** (bản cũ gần như vô dụng).
- Kamikaze lao tới: 15 → **8 px/tick** (bản cũ gần như không thể né).
- Vô tận/Hỏa ngục: vật phẩm rơi ngẫu nhiên giờ có đủ Laser/Homing/Universal (bản cũ chỉ Plasma).
- Bám tay: 0.15 → 0.25, cộng vùng điều khiển thu nhỏ (không phải với tay ra sát mép camera).

### Điều khiển bằng tay
- Vị trí tàu theo **tâm lòng bàn tay** thay vì cổ tay, có lọc rung One Euro.
- Nhận dạng ngón duỗi theo **khoảng cách** tới cổ tay (đúng cả khi xoay tay), thay vì so toạ độ y.
- Cử chỉ phải giữ ổn định 3 khung hình mới tính (hết bắn nhầm do nháy cử chỉ).
- Mất tay < 0.35 giây thì giữ vị trí cũ (không giật tàu).
- Ô xem camera vẽ trong cửa sổ game (bỏ cửa sổ OpenCV riêng), phím C để ẩn/hiện.

### Thêm mới
- Màn **Kết quả** có thống kê ván, nút Chơi lại; HUD hiện cấp súng, khiên, Drone/Thiêu đốt.
- Phím tắt 1/2/3 chọn chế độ; ESC/P tạm dừng; tự tạm dừng khi rời cửa sổ.
- Tham số dòng lệnh `--no-camera`, `--camera N`, `--fullscreen`, `--fps`, `--seed`, `--debug`.

### Loại bỏ
- Code chết: `upgrade_spread`, loại địch `asteroid` (không bao giờ xuất hiện).
- File rác khỏi repo: `__pycache__/`, `highscore.txt`, `stats.json`.

## [1.0.0]
- Phiên bản đồ án môn Công nghệ xử lý ảnh (Anos2003, Tabisan805).
