# Ghi công tài nguyên

## Âm thanh & nhạc (nhánh 2.x)

Toàn bộ âm thanh mới đều dùng giấy phép **CC0** (public domain): không bắt buộc ghi công, nhưng vẫn ghi để
tôn trọng tác giả. Các file đã được cắt, chuẩn hóa âm lượng và đổi sang `.ogg` cho nhẹ.

| Dùng cho | Nguồn | Tác giả | Giấy phép |
|---|---|---|---|
| Tiếng súng, nổ, va chạm, khiên | [Sci-Fi Sounds](https://opengameart.org/content/sci-fi-sounds) | Kenney (kenney.nl) | CC0 |
| Tiếng giao diện (di chuyển, chọn, quay lại) | [Interface Sounds](https://opengameart.org/content/interface-sounds) | Kenney (kenney.nl) | CC0 |
| Nhặt đồ, lên cấp, kỹ năng Nộ, tia sét | [63 Digital sound effects](https://opengameart.org/content/63-digital-sound-effects-lasers-phasers-space-etc) | Kenney (kenney.nl) | CC0 |
| Nhạc đoạn hội thoại, Hồi II, Hồi III, đoạn kết, tiếng chiến thắng | [Dark Sci-Fi Audio Pack](https://opengameart.org/content/dark-sci-fi-audio-pack) | SRG774 | CC0 |
| Nhạc Hồi I | [Space Battle](https://opengameart.org/content/space-battle) | MintoDog | CC0 |
| Nhạc trận cuối (Tàu Mẹ) | [Boss Battle (loop)](https://opengameart.org/content/boss-battle-loop) | Pro Sensory | CC0 |

**Tự tổng hợp bằng code** (`spaceship/core/audio.py`, numpy): còi báo động boss, tiếng gõ chữ riêng của từng
nhân vật (KX-17, ARIA, Chỉ huy), tiếng mở bộ đàm, radar, nhiễu sóng.

**Giữ từ bản gốc thời đại học:** `menu_music.mp3` (menu) và `game_music.mp3` (trận boss thường, chế độ Vô tận).

## Font chữ

- [Chakra Petch](https://fonts.google.com/specimen/Chakra+Petch) và [Exo 2](https://fonts.google.com/specimen/Exo+2),
  giấy phép SIL Open Font License 1.1 (xem `assets/fonts/`).

## Hình ảnh

- Hình minh họa mới (kẻ địch, boss, chân dung, ảnh nền các hồi, ảnh kết) được tạo bằng công cụ tạo ảnh AI qua Codex.
- Các hình còn lại từ bản gốc (nhánh `main`).
