# Hồi IV · Nguồn Tín Hiệu

Bản thiết kế đầy đủ (lời thoại, wave, mẫu đạn boss, câu hỏi đã chốt) nằm trong tài liệu sống
"SpaceShip10K · Hồi IV · Nguồn Tín Hiệu (thiết kế)" trên Claude. File này là bản tóm tắt để đọc cùng code.

## Mạch truyện

5 ải mới (11–15), mở sau khi qua ải 10. Trả lời hai câu hỏi còn bỏ ngỏ: ai phát tín hiệu giả, và vì sao mọi thứ
lặp lại. Cuối hồi là **kết thúc thật**: tín hiệu tắt, vòng lặp bị phá, ARIA mất ký ức, KX-17 thành người dẫn đường.

- Cú lật 1 (ải 14): ARIA được tạo từ "mẫu vật số 7" của Đàn, nghe được tín hiệu từ đầu nhưng giấu.
- Cú lật 2 (ải 15): Trái Tim Đàn ghi lại mỗi trận và phát lại tín hiệu để dụ KX-17 đánh lại từ đầu (vòng lặp).

| Ải | Tên | Cảm giác | Cơ chế mới | Boss |
|---|---|---|---|---|
| 11 | Tiếng Vọng | Bất an | Bóng KX lặp lại đường bay của bạn 2 giây trước | — |
| 12 | Khoang Ngủ Đông | Hy vọng | Hộ tống 4 tàu cứu sinh (40 người), sao theo số người cứu | — |
| 13 | Giếng Trọng Lực | Mất kiểm soát | Hố đen kéo tàu, đạn bay cong, nhịp hút | Mắt Bão (mini) |
| 14 | Tín Hiệu Câm | Cô độc | Màn tối, đạn bạn soi đường, ARIA im lặng | Kẻ Nghe (mini) |
| 15 | Trái Tim Đàn | Bùng nổ | Boss 3 pha: giọng Chỉ huy → phi đội ma + Bóng KX → ARIA chọn | Trái Tim Đàn |

## Quyết định đã chốt (2026-11-21)

1. Ải 12 chấm sao theo số người cứu: ≥ 10 = 1 sao, ≥ 30 = 2 sao, 40/40 = 3 sao.
2. Mất cả 4 tàu cứu sinh = thất bại, chơi lại ải.
3. Cuối game ARIA mất ký ức.
4. Đòn kết liễu bằng Đại pháo không bắt buộc; dùng thì được huy hiệu TÔI CHỌN ANH.
5. Chu kỳ 2+ đổi tên "Mô phỏng ký ức", chỉ mở sau kết thúc thật; ai đang chơi chu kỳ 2 giữ nguyên tiến độ.
6. Tên ải, boss, lời thoại theo tài liệu thiết kế.
7. Làm theo 6 đợt, khung chơi được trước.

## Tiến độ

| Đợt | Nội dung | Trạng thái |
|---|---|---|
| 1 | Khung: dữ liệu 5 ải (địch tạm), toàn bộ thoại mở đầu, màn Chọn ải 3 hàng (Hồi IV hiện "???" tới khi phá đảo), bản đồ hành trình riêng, đoạn kết ải 10 mở Hồi IV, kết thúc thật sau ải 15, ảnh tạm | Xong |
| 2 | Bóng KX: lặp lại x của tàu 2/3/4 giây trước, bắn thẳng xuống mỗi 0,8 giây bằng màu súng của bạn; ải 11 (5 wave theo thiết kế), ải 14 wave 3, ải 15 wave 1 | Xong |
| 3 | Hộ tống: 4 tàu cứu sinh (máu 100, bay ngang y≈470, 0,8 px/tick), mỗi wave 1 tàu và wave sau chờ tàu bay xong; Ký Sinh + lính cảm tử nhắm tàu cứu sinh; thân tàu bạn che đạn (kể cả lúc bất tử); "ĐÃ CỨU N/40"; sao theo người cứu; mất cả 4 = thua; nhớ số người cứu cho câu cuối kết thúc thật | Xong |
| 4 | Hố đen trôi ngang kéo tàu (0,6 → 2,2 px/tick), đạn hai phía bay cong (hút + xoáy), địch bị nuốt không điểm, chạm vành -30 máu + hất ra, wave 4 đập nhịp (báo 1 giây, hút gấp đôi 1 giây); Mắt Bão ngồi giữa hố đen, xoắn 8 tia, pha 2 nhịp 3 giây gọi 4 Ký Sinh | Xong |
| 5 | Màn tối + Kẻ Nghe | Chưa |
| 6 | Trái Tim Đàn 3 pha, khoảnh khắc ARIA, 3 huy hiệu, "Mô phỏng ký ức" | Chưa |

## Ghi chú kỹ thuật (đợt 2-6)

- `systems/mechanics.py`: mỗi ải Hồi IV gắn một "cơ chế" (`Level.mechanic`), do `LevelDirector` tạo và gọi
  `update` mỗi tick; GameplayScene gọi các móc vẽ (`draw_back` / `draw_front` / `draw_overlay`), `stars`,
  `hud_text`. Ải không có cơ chế chạy y như cũ.
- `Player.x_history` (4 giây) cho Bóng KX; ảnh `shadow_kx`, `ghost_ship` dựng từ sprite tàu (`Assets.DERIVED`).
- `SaveData.rescued`: số người cứu ở lần qua ải 12 gần nhất, dùng cho câu cuối `story.true_ending()`.

## Ghi chú kỹ thuật (đợt 1)

- `campaign/levels.py`: `LEVEL_COUNT = 15`, `MAIN_LEVELS = 10`. Qua ải 10 → `campaign_cleared` (mở Hỏa ngục, Hồi IV);
  qua ải 15 → `cycle_complete` (mở chu kỳ mới). `SaveData.record_level(number, stars, last, main)`.
- Save cũ đã qua ải 10 trong chu kỳ hiện tại được mở luôn ải 11 khi nạp.
- `core/assets.py` `PLACEHOLDERS`: ảnh Hồi IV chưa có file thì dùng tạm ảnh cũ; thả file thật vào `assets/images/` là
  game tự dùng (bg_act4, bg_blackhole, bg_heart, lifeboat, storm_eye, listener, swarm_heart, swarm_heart_core,
  portrait_aria_glitch).
- Boss mới (`storm_eye`, `listener`, `swarm_heart`) đã có thông số trong `BOSS_SPECS` nhưng tạm mượn kiểu đánh của boss
  cũ trong `BOSS_PATTERNS` cho tới đợt làm riêng. Nhạc `act4` tạm là nhạc Hồi III.
- Thoại trong trận của ải 11, 12, 15 đang là bản tạm khớp với địch tạm; đổi sang bản trong tài liệu khi có cơ chế.
