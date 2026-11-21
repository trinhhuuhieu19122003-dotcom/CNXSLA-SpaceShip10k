"""Điểm khởi chạy: ``python -m spaceship [--no-camera] [--camera N] [--fullscreen]``.

Mở từ lối tắt (``pythonw.exe``, không có cửa sổ dòng lệnh) thì không có chỗ in log: log và lỗi được ghi vào
``spaceship.log`` cạnh file save, và nếu game gặp lỗi thì hiện hộp thoại báo kèm đường dẫn file log.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from spaceship import __version__, config


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="spaceship", description="SpaceShip 10K - bắn phi thuyền điều khiển bằng tay")
    parser.add_argument("--no-camera", action="store_true", help="tắt webcam, chỉ chơi bằng bàn phím")
    parser.add_argument("--camera", type=int, default=config.CAMERA_INDEX, metavar="N", help="chỉ số webcam (mặc định 0)")
    parser.add_argument("--fullscreen", action="store_true", help="mở toàn màn hình (mặc định: theo Cài đặt)")
    parser.add_argument("--fps", type=int, default=60, help="giới hạn khung hình vẽ (logic luôn 60 tick/giây)")
    parser.add_argument("--seed", type=int, default=None, help="cố định ngẫu nhiên (để tái hiện lỗi)")
    parser.add_argument("--debug", action="store_true", help="in log chi tiết")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser.parse_args(argv)


def _windowless() -> bool:
    """Chạy bằng pythonw (từ lối tắt): không có console để in."""
    return sys.stderr is None or sys.stdout is None


def _log_path() -> Path:
    from spaceship.core.storage import default_save_path

    return default_save_path().parent / "spaceship.log"


def _redirect_output() -> Path:
    path = _log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    stream = open(path, "w", encoding="utf-8", buffering=1)  # noqa: SIM115 - mở suốt thời gian chạy game
    sys.stdout = sys.stderr = stream
    return path


def _show_error(message: str) -> None:
    if sys.platform == "win32":
        import ctypes

        ctypes.windll.user32.MessageBoxW(None, message, "SpaceShip 10K", 0x10)


def main(argv=None) -> None:
    args = parse_args(argv)
    log_file = _redirect_output() if _windowless() else None
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s" if log_file else
                        "%(levelname)s %(name)s: %(message)s", force=True)
    try:
        from spaceship.app import Game

        Game(camera=not args.no_camera, camera_index=args.camera,
             fullscreen=True if args.fullscreen else None,
             fps=max(30, args.fps), seed=args.seed).run()
    except Exception:
        if log_file is None:
            raise
        logging.exception("Game dừng vì lỗi")
        _show_error(f"Game gặp lỗi và phải dừng.\n\nChi tiết ở file:\n{log_file}")


if __name__ == "__main__":
    main()
