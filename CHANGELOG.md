# Changelog

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
