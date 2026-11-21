"""Nối các màn hình với nhau: hiệu chỉnh tay (nếu cần) -> hội thoại -> vào trận."""
from __future__ import annotations

from typing import Optional

from spaceship.campaign import story
from spaceship.campaign.levels import get_level
from spaceship.config import GameMode


def _with_calibration(game, make_scene) -> None:
    from spaceship.scenes.calibration import CalibrationScene

    game.change_scene(CalibrationScene(game, make_scene) if game.needs_calibration() else make_scene())


def start_level(game, number: int, loadout: Optional[dict] = None) -> None:
    """Vào ải ``number`` của Vượt ải: đoạn hội thoại mở đầu rồi vào trận."""
    from spaceship.scenes.cutscene import CutsceneScene
    from spaceship.scenes.gameplay import GameplayScene

    level = get_level(number)

    def play():
        return GameplayScene(game, GameMode.CAMPAIGN, number, loadout)

    def intro():
        backdrop = "radar" if number == 1 else level.background
        return CutsceneScene(game, story.INTROS[number], play, backdrop=backdrop,
                             title=level.title, subtitle=story.ACTS[level.act])

    _with_calibration(game, intro)


def start_survival(game, mode: GameMode) -> None:
    from spaceship.scenes.gameplay import GameplayScene

    _with_calibration(game, lambda: GameplayScene(game, mode))
