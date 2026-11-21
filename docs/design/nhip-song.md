# Nhịp sóng: cách game thả địch

Bản 2.1 đầu tiên thả địch "ồ ạt". Một bot chơi tự động đo được:

- 15–18 lính hiện ra cùng một khoảnh khắc ở ải 2–5.
- Lính vừa tới chỗ là bắn ngay.
- Chế độ Vô tận trung bình 46 địch trên màn.
- Chế độ Hỏa ngục có lúc 255 địch và 1 381 viên đạn.

Tài liệu này mô tả luật mới và chỉ chỗ chỉnh số.

## Bốn nguyên tắc (và lấy từ đâu)

| Nguyên tắc | Cách làm trong game | Nguồn tham khảo |
|---|---|---|
| **Bay vào lần lượt, không bắn khi đang vào** | Lính trong đội hình bay vào từng con, cách nhau `ENTRY_STAGGER_TICKS`. Hàng trước vào trước, từ giữa ra hai bên. Lính bay nhanh rồi chậm dần khi tới chỗ, và chỉ bắn sau khi đã tới được `ARRIVAL_GRACE_TICKS`. | Galaga: lúc đang bay vào thì địch chưa bắn. *Anatomy of a Shmup*: không để địch vừa xuất hiện đã bắn ngay. |
| **Trần mật độ ("ngân sách đe dọa")** | Mỗi loại địch tính một mức điểm (`threat`). Khi tổng điểm trên màn đạt `THREAT_CAP` thì đồng hồ wave dừng lại, địch tiếp theo xếp hàng chờ. | Wave Manager chia một wave thành nhiều "pulse". |
| **Có lúc nghỉ** | Nghỉ `WAVE_BREATH_TICKS` giữa các wave. Sau mỗi 2 wave thì nghỉ `WAVE_LONG_BREATH_TICKS`. Vô tận và Hỏa ngục đi theo vòng *dồn lên → cao trào → thả lỏng*. | AI Director của Left 4 Dead (Build Up / Sustain Peak / Peak Fade / Relax). Hướng dẫn thiết kế R-Type: nghỉ ngắn sau đoạn căng. |
| **Trần đạn** | Đạn của lính trên màn vượt `ENEMY_BULLET_CAP` thì lính tạm ngừng bắn. Đạn boss không bị giới hạn. Boss chỉ gọi thêm lính khi xung quanh còn ít lính. | Luôn chừa đường né. |

Thêm một luật nữa: **rút lui**. Lính đứng trong đội hình quá `RETREAT_AFTER_TICKS` (khoảng 14 giây) mà chưa bị hạ thì ngừng bắn và bay ngược lên khỏi màn hình. Nhờ vậy không ai phải đi săn từng con sót lại, nhất là khi lái bằng tay.

## Điểm đe dọa của từng loại địch

| Địch | Điểm |
|---|---|
| Lính, lính cảm tử | 1 |
| Ký Sinh | 0,75 |
| Lính Khiên, Pháo tháp, Tàu đồng minh bị nhiễm | 2 |
| Kẻ Đẻ Trứng | 3 |
| Boss, thiên thạch, xác tàu | không tính |

Trần theo hồi: **Hồi I là 9, Hồi II là 12, Hồi III là 14**. Mỗi chu kỳ của Vòng lặp tín hiệu cộng thêm 1.

## Vô tận và Hỏa ngục

Đây là phiên bản rút gọn của AI Director (`SurvivalDirector`, thông số trong `PACING`):

| | Vô tận | Hỏa ngục |
|---|---|---|
| Dồn lên (thả từng tốp 3–5 lính, bầy Ký Sinh, Lính Khiên...) | 18 giây | 15 giây |
| Cao trào (giữ nguyên, không thả thêm) | 4 giây | 4 giây |
| Thả lỏng (không thả tốp mới cho tới khi màn gần sạch) | ít nhất 6 giây | ít nhất 4 giây |
| Ngân sách đe dọa | 7, cộng 2 mỗi phút, tối đa 18 | 12, cộng 3 mỗi phút, tối đa 26 |
| Mất ≥ chừng này máu khi đang dồn lên thì được nghỉ sớm | 35% | 45% |

Khi đang có boss, ngân sách chỉ còn 4. Hạ boss xong thì được một nhịp thả lỏng.

## Trước và sau (bot chơi, 4 phút mỗi chế độ)

| | Địch tối đa cùng lúc | Số địch hiện ra trong 1 khoảnh khắc | Đạn tối đa |
|---|---|---|---|
| Ải 2 – trước → sau | 18 → 9 | 18 → 1 | 18 → 12 |
| Ải 4 – trước → sau | 28 → 16 | 15 → 2 | 14 → 13 |
| Vô tận – trước → sau | 74 → 16 (trung bình 46 → 7) | 7 → 2 | 87 → 27 |
| Hỏa ngục – trước → sau | 255 → 17 | 6 → 1 | 1 381 → 286 (phần lớn là đạn boss) |

## Muốn chỉnh

Tất cả số liệu nằm ở cuối `spaceship/config.py` (mục *Nhịp sóng*) và trong `PACING` ở `spaceship/systems/spawning.py`. Ví dụ:

- Thấy vẫn dày quá: giảm `THREAT_CAP`.
- Thấy chán vì nghỉ lâu: giảm `WAVE_BREATH_TICKS`.
- Muốn lính đứng lâu hơn mới rút: tăng `RETREAT_AFTER_TICKS`.

Sửa xong chạy `python -m unittest discover -s tests -t .`. Các test trong `tests/test_pacing.py` sẽ báo nếu bạn vô tình làm hỏng luật.
