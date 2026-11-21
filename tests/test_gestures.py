import unittest

from tests import helpers  # noqa: F401
from spaceship.input.filters import OneEuroFilter
from spaceship.input.gestures import (
    FINGERS, Gesture, GestureDebouncer, Point, classify, map_to_zone, palm_center,
)


def make_hand(up=()):
    """Bàn tay giả 21 điểm: cổ tay ở (0.5, 0.9), ngón duỗi thì đầu ngón ở xa, ngón gập thì đầu ngón lùi về."""
    pts = [Point(0.5, 0.9)] * 21
    pts = list(pts)
    for i, (name, (mcp, pip, tip)) in enumerate(FINGERS.items()):
        x = 0.35 + i * 0.1
        pts[mcp] = Point(x, 0.70)
        pts[pip] = Point(x, 0.55)
        pts[tip] = Point(x, 0.35) if name in up else Point(x, 0.68)
    pts[1], pts[2], pts[3], pts[4] = Point(0.3, 0.8), Point(0.25, 0.75), Point(0.22, 0.72), Point(0.2, 0.7)
    return pts


class ClassifyTest(unittest.TestCase):
    def test_point_three_open_fist(self):
        self.assertEqual(classify(make_hand({"index"})), Gesture.POINT)
        self.assertEqual(classify(make_hand({"index", "middle", "ring"})), Gesture.THREE)
        self.assertEqual(classify(make_hand(set(FINGERS))), Gesture.OPEN)
        self.assertEqual(classify(make_hand()), Gesture.FIST)

    def test_too_few_points(self):
        self.assertEqual(classify([Point(0, 0)] * 5), Gesture.NONE)

    def test_rotated_hand_still_point(self):
        # Xoay bàn tay 90 độ: bản cũ so toạ độ y nên nhận sai, bản mới dựa trên khoảng cách
        rotated = [Point(1 - p.y, p.x) for p in make_hand({"index"})]
        self.assertEqual(classify(rotated), Gesture.POINT)


class GeometryTest(unittest.TestCase):
    def test_palm_center_is_inside_hand(self):
        c = palm_center(make_hand())
        self.assertTrue(0.3 < c.x < 0.7 and 0.6 < c.y < 0.9)

    def test_map_to_zone_scales_and_clamps(self):
        zone = (0.2, 0.2, 0.8, 0.8)
        mid = map_to_zone(Point(0.5, 0.5), zone)
        self.assertAlmostEqual(mid.x, 0.5)
        self.assertAlmostEqual(mid.y, 0.5)
        self.assertEqual(map_to_zone(Point(0.0, 1.0), zone), Point(0.0, 1.0))
        self.assertAlmostEqual(map_to_zone(Point(0.35, 0.2), zone).x, 0.25)


class DebouncerTest(unittest.TestCase):
    def test_needs_stable_frames(self):
        d = GestureDebouncer(frames=3)
        self.assertEqual(d.update(Gesture.POINT), Gesture.NONE)
        self.assertEqual(d.update(Gesture.POINT), Gesture.NONE)
        self.assertEqual(d.update(Gesture.POINT), Gesture.POINT)
        self.assertEqual(d.update(Gesture.FIST), Gesture.POINT)   # một khung nhiễu không đổi kết quả
        d.reset()
        self.assertEqual(d.stable, Gesture.NONE)


class OneEuroTest(unittest.TestCase):
    def test_smooths_jitter_but_follows_motion(self):
        f = OneEuroFilter(min_cutoff=1.0, beta=0.0)
        noisy = [0.5 + (0.02 if i % 2 else -0.02) for i in range(60)]
        out = [f(x, i / 30) for i, x in enumerate(noisy)]
        self.assertLess(max(out[30:]) - min(out[30:]), 0.04)
        f.reset()
        self.assertEqual(f(0.9, 0.0), 0.9)


if __name__ == "__main__":
    unittest.main()
