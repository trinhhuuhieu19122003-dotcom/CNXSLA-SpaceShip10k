"""Bộ lọc One Euro (Casiez et al., CHI 2012) để khử rung tọa độ tay.

Ý tưởng: khi tay gần đứng yên thì lọc mạnh (hết rung), khi tay di chuyển
nhanh thì lọc nhẹ (bớt trễ). Bản cũ chỉ nội suy cố định 15% mỗi khung nên
vừa rung khi đứng yên vừa trễ khi né đạn.
Tham khảo: https://cristal.univ-lille.fr/~casiez/1euro
"""
from __future__ import annotations

import math
from typing import Optional


def _alpha(dt: float, cutoff: float) -> float:
    tau = 1.0 / (2.0 * math.pi * cutoff)
    return 1.0 / (1.0 + tau / dt)


class OneEuroFilter:
    def __init__(self, min_cutoff: float = 1.0, beta: float = 0.0, d_cutoff: float = 1.0) -> None:
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self.reset()

    def reset(self) -> None:
        self._t: Optional[float] = None
        self._x = 0.0
        self._dx = 0.0

    def __call__(self, x: float, t: float) -> float:
        """Lọc giá trị ``x`` đo tại thời điểm ``t`` (giây)."""
        if self._t is None:
            self._t, self._x, self._dx = t, x, 0.0
            return x
        dt = t - self._t
        if dt <= 0:
            return self._x
        a_d = _alpha(dt, self.d_cutoff)
        dx = (x - self._x) / dt
        self._dx = a_d * dx + (1 - a_d) * self._dx
        cutoff = self.min_cutoff + self.beta * abs(self._dx)
        a = _alpha(dt, cutoff)
        self._x = a * x + (1 - a) * self._x
        self._t = t
        return self._x
