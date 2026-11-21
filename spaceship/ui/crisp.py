"""Chữ sắc nét khi phóng to (toàn màn hình, cửa sổ phóng to).

Vấn đề: cả game vẽ trên tấm 800x700 rồi phóng lên màn hình. Ở 1080p phải phóng ~1,54 lần, mà ảnh phóng
lẻ thì phải làm mượt -> chữ bị nhòe. Hình ảnh (tàu, nổ) nhòe một chút không sao, nhưng chữ nhòe rất khó chịu.

Cách giải (không phải sửa ~400 chỗ vẽ):

1. ``Assets.text`` trả về ``TextSurface``: một Surface bình thường nhưng NHỚ nó được vẽ từ chữ gì, cỡ nào,
   màu gì (``spec``).
2. Tấm vẽ chính là ``CrispSurface``. Khi bật chế độ nét, chữ blit lên nó KHÔNG được vẽ ngay mà chỉ ghi lại
   (chữ gì, ở đâu, độ trong suốt).
3. Sau khi phóng tấm 800x700 lên màn hình, các chữ đã ghi được vẽ LẠI bằng font cỡ lớn (cỡ x tỉ lệ phóng)
   ngay trên ảnh đã phóng -> nét như chữ gốc của màn hình.

Thứ tự vẽ vẫn đúng: nếu sau chữ có thứ khác đè lên (bảng Tạm dừng phủ tối lên trận, khung thông báo...),
chữ bị đè được "nướng" (vẽ thường, độ phân giải thấp) ngay trước khi vật đè lên được vẽ.
"""
from __future__ import annotations

from collections import OrderedDict
from typing import List, Optional, Tuple

import pygame

Spec = Tuple[str, int, tuple, bool, bool, Optional[str]]      # chữ, cỡ, màu, đậm, nghiêng, vai trò font
HIRES_CACHE_SIZE = 600


class TextSurface(pygame.Surface):
    """Surface chứa một dòng chữ, kèm ``spec`` để vẽ lại ở cỡ lớn hơn."""

    spec: Optional[Spec] = None

    @classmethod
    def wrap(cls, image: pygame.Surface, spec: Spec) -> "TextSurface":
        surf = cls(image.get_size(), pygame.SRCALPHA, 32)
        surf.blit(image, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)   # chép y nguyên (cộng vào nền 0)
        surf.spec = spec
        return surf


class CrispSurface(pygame.Surface):
    """Tấm vẽ ghi lại chữ thay vì vẽ ngay (khi ``enabled``), để vẽ lại sắc nét sau khi phóng."""

    def setup(self) -> "CrispSurface":
        self.enabled = False
        self.records: List[tuple] = []          # (TextSurface, Rect, alpha)
        return self

    # --- Ghi / nướng ---------------------------------------------------------------------
    def begin(self, enabled: bool) -> None:
        self.bake()
        self.enabled = enabled

    def bake(self) -> None:
        """Vẽ thường mọi chữ còn đang chờ (để tấm 800x700 luôn đầy đủ: chụp màn, hiệu ứng chuyển cảnh)."""
        records = getattr(self, "records", None)
        while records:
            self._draw_record(records.pop(0))

    def _draw_record(self, record) -> None:
        image, rect, alpha = record
        old = image.get_alpha()
        image.set_alpha(alpha)
        pygame.Surface.blit(self, image, rect.topleft)
        image.set_alpha(old)

    def _bake_under(self, rect: pygame.Rect) -> None:
        keep = []
        for record in self.records:
            if record[1].colliderect(rect):
                self._draw_record(record)        # vẽ chữ trước, vật mới sẽ đè lên đúng thứ tự
            else:
                keep.append(record)
        self.records = keep

    # --- Chuyển chữ từ tấm phụ sang tấm chính ---------------------------------------------------
    def take(self, rect: pygame.Rect, target) -> List[tuple]:
        """Tấm phụ (vd. ô HUD góc) sắp được dán lên ``target``. Nếu ``target`` đang ghi chữ: lấy các chữ trong
        ``rect`` ra để chuyển sang (gọi ``put`` SAU khi dán); nếu không: vẽ thường chúng vào tấm phụ luôn."""
        inside = [r for r in getattr(self, "records", []) if rect.contains(r[1])]
        if not inside:
            return []
        self.records = [r for r in self.records if r not in inside]
        if getattr(target, "enabled", False):
            return inside
        for record in inside:
            self._draw_record(record)
        return []

    def put(self, records: List[tuple], alpha: int = 255, offset: Tuple[int, int] = (0, 0)) -> None:
        """Nhận chữ từ tấm phụ, nhân thêm độ trong suốt của tấm phụ khi dán."""
        for image, rect, a in records:
            base = 255 if a is None else a
            self.records.append((image, rect.move(offset), round(base * alpha / 255)))

    # --- Ghi đè các lệnh vẽ ----------------------------------------------------------------
    def blit(self, source, dest, area=None, special_flags=0):
        if getattr(self, "enabled", False):
            spec = getattr(source, "spec", None)
            if spec is not None and area is None and not special_flags:
                rect = pygame.Rect(int(dest[0]), int(dest[1]), *source.get_size())
                if self.get_clip().contains(rect):
                    self.records.append((source, rect, source.get_alpha()))
                    return rect.copy()
            if self.records:
                if area is not None:
                    size = pygame.Rect(area).size
                else:
                    size = source.get_size()
                self._bake_under(pygame.Rect(int(dest[0]), int(dest[1]), *size))
        return super().blit(source, dest, area, special_flags)

    def fill(self, color, rect=None, special_flags=0):
        if getattr(self, "records", None):
            if rect is None:
                if special_flags:
                    self.bake()                  # phủ tối / nhuộm cả màn: chữ cũng phải bị phủ
                else:
                    self.records.clear()         # tô kín: chữ cũ bị xóa hẳn
            else:
                self._bake_under(pygame.Rect(rect))
        return super().fill(color, rect, special_flags)

    # --- Vẽ lại sắc nét ----------------------------------------------------------------
    def draw_crisp(self, target: pygame.Surface, assets, scale_x: float, scale_y: float,
                   region: Optional[pygame.Rect] = None, offset: Tuple[int, int] = (0, 0)) -> None:
        """Vẽ các chữ đã ghi lên ``target`` (ảnh đã phóng). ``region``: chỉ lấy chữ nằm trong vùng này của tấm
        vẽ (bảng trái / phải ở màn rộng), toạ độ tính từ góc vùng."""
        if not getattr(self, "records", None):
            return
        ox, oy = region.topleft if region is not None else (0, 0)
        for image, rect, alpha in self.records:
            if region is not None and not region.contains(rect):
                continue
            hires = crisp_text(assets, image.spec, scale_y, rect.width * scale_x)
            if hires is None:
                continue
            cx = (rect.centerx - ox) * scale_x + offset[0]
            cy = (rect.centery - oy) * scale_y + offset[1]
            hires.set_alpha(alpha)
            target.blit(hires, hires.get_rect(center=(round(cx), round(cy))))
            hires.set_alpha(None)


_hires: "OrderedDict[tuple, pygame.Surface]" = OrderedDict()


def crisp_text(assets, spec: Spec, scale: float, width: Optional[float] = None) -> Optional[pygame.Surface]:
    """Chữ vẽ ở cỡ ~``size x scale`` (có cache). Font cỡ lớn không rộng đúng tỉ lệ với cỡ nhỏ (do làm tròn nét),
    nên thử vài cỡ quanh đó và chọn cỡ có bề rộng gần ``width`` nhất: chữ canh trái/phải không bị lệch."""
    text, size, color, bold, italic, role = spec
    target = round(width) if width else None
    key = (spec, round(scale * 100), target)
    image = _hires.get(key)
    if image is None:
        big = max(1, round(size * scale))
        if target:
            sizes = [s for s in (big - 2, big - 1, big, big + 1) if s >= 1]
            big = min(sizes, key=lambda s: abs(assets.font(s, bold, italic, role=role).size(text)[0] - target))
        image = assets.font(big, bold, italic, role=role).render(text, True, color)
        _hires[key] = image
        if len(_hires) > HIRES_CACHE_SIZE:
            _hires.popitem(last=False)
    else:
        _hires.move_to_end(key)
    return image


def make_crisp(size: Tuple[int, int]) -> CrispSurface:
    """Tấm vẽ cùng định dạng điểm ảnh với cửa sổ (nhanh như ``Surface.convert()``)."""
    display = pygame.display.get_surface()
    surf = CrispSurface(size, 0, display) if display is not None else CrispSurface(size)
    return surf.setup()
