# Changelog

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
