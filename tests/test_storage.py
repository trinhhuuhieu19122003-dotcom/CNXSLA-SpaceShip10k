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
