import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests import helpers  # noqa: F401
from spaceship.config import GameMode
from spaceship.core.storage import GameResult, SaveData


class StorageTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.path = self.dir / "save.json"

    def load(self):
        return SaveData.load(self.path, legacy_dirs=(self.dir,))

    def test_stats_are_cumulative(self):
        data = self.load()
        data.record(GameResult(GameMode.ENDLESS, score=100, kills=10, boss_kills=1, survival_time=30))
        data.record(GameResult(GameMode.ENDLESS, score=50, kills=5, boss_kills=0, survival_time=90))
        again = self.load()
        rec = again.modes[GameMode.ENDLESS]
        self.assertEqual((rec.games_played, rec.total_kills, rec.total_boss_kills), (2, 15, 1))
        self.assertEqual((rec.best_score, rec.best_time), (100, 90))
        self.assertEqual(again.highscore, 100)

    def test_best_combo_is_kept_and_old_saves_load(self):
        data = self.load()
        data.record(GameResult(GameMode.ENDLESS, 100, 10, 1, 30, best_combo=24))
        data.record(GameResult(GameMode.ENDLESS, 50, 5, 0, 30, best_combo=7))
        self.assertEqual(self.load().modes[GameMode.ENDLESS].best_combo, 24)
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        for record in raw["modes"].values():
            record.pop("best_combo")                       # file lưu cũ chưa có trường này
        self.path.write_text(json.dumps(raw), encoding="utf-8")
        self.assertEqual(self.load().modes[GameMode.ENDLESS].best_combo, 0)

    def test_top_runs_keep_best_five_and_survive_bad_data(self):
        data = self.load()
        for score in (300, 900, 100, 700, 500, 800, 0):
            data.record(GameResult(GameMode.INFERNO, score, 5, 0, 60, best_combo=score // 100))
        runs = self.load().modes[GameMode.INFERNO].top_runs
        self.assertEqual([r["score"] for r in runs], [900, 800, 700, 500, 300])   # ván 0 điểm không ghi
        self.assertEqual(runs[0]["combo"], 9)
        self.assertEqual(len(runs[0]["date"]), 10)
        data.record(GameResult(GameMode.CAMPAIGN, 50, 5, 0, 60, victory=True, level=3))
        self.assertEqual(self.load().modes[GameMode.CAMPAIGN].top_runs[0]["level"], 3)
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        raw["modes"][GameMode.INFERNO.value]["top_runs"] = ["rác", {"x": 1}, {"score": 5}]
        self.path.write_text(json.dumps(raw), encoding="utf-8")
        loaded = self.load()
        self.assertTrue(all(isinstance(r, dict) and "score" in r for m in loaded.modes.values() for r in m.top_runs))

    def test_new_record_flag(self):
        data = self.load()
        self.assertTrue(data.record(GameResult(GameMode.CAMPAIGN, 10, 1, 0, 5)))
        self.assertFalse(data.record(GameResult(GameMode.CAMPAIGN, 5, 1, 0, 5)))

    def test_first_sighting_writes_once_and_round_trips(self):
        data = self.load()
        with patch.object(data, "save", wraps=data.save) as write:
            self.assertTrue(data.mark_seen("parasite"))
            self.assertFalse(data.mark_seen("parasite"))
            write.assert_called_once()
        self.assertEqual(json.loads(self.path.read_text(encoding="utf-8"))["campaign"]["seen_enemies"], ["parasite"])
        again = self.load()
        self.assertEqual(again.seen_enemies, {"parasite"})
        self.assertFalse(again.mark_seen("parasite"))

    def test_older_campaign_save_has_empty_bestiary(self):
        self.path.write_text(json.dumps({"highscore": 100, "campaign": {"unlocked_level": 4, "level_stars": {"1": 3}}}))
        data = self.load()
        self.assertEqual(data.seen_enemies, set())
        self.assertEqual((data.highscore, data.unlocked_level, data.total_stars), (100, 4, 3))

    def test_corrupt_file_is_backed_up(self):
        self.path.write_text("{not json", encoding="utf-8")
        data = self.load()
        self.assertEqual(data.highscore, 0)
        self.assertTrue(self.path.with_suffix(".bak").exists())

    def test_imports_legacy_files(self):
        (self.dir / "highscore.txt").write_text("3430")
        (self.dir / "stats.json").write_text(json.dumps({"INFERNO": {"kills": 7, "boss_kills": 2, "score": 9790}}))
        data = self.load()
        self.assertEqual(data.highscore, 9790)   # bản cũ 2 file lệch nhau → lấy số lớn nhất
        self.assertEqual(data.modes[GameMode.INFERNO].total_kills, 7)
        self.assertTrue(self.path.exists())


if __name__ == "__main__":
    unittest.main()
