"""Điểm khởi chạy: ``python -m spaceship [--no-camera] [--camera N] [--fullscreen]``."""
from __future__ import annotations

import argparse
import logging

from spaceship import __version__, config


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="spaceship", description="SpaceShip 10K - bắn phi thuyền điều khiển bằng tay")
    parser.add_argument("--no-camera", action="store_true", help="tắt webcam, chỉ chơi bằng bàn phím")
    parser.add_argument("--camera", type=int, default=config.CAMERA_INDEX, metavar="N", help="chỉ số webcam (mặc định 0)")
    parser.add_argument("--fullscreen", action="store_true", help="mở toàn màn hình")
    parser.add_argument("--fps", type=int, default=60, help="giới hạn khung hình vẽ (logic luôn 60 tick/giây)")
    parser.add_argument("--seed", type=int, default=None, help="cố định ngẫu nhiên (để tái hiện lỗi)")
    parser.add_argument("--debug", action="store_true", help="in log chi tiết")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser.parse_args(argv)


def main(argv=None) -> None:
    args = parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    from spaceship.app import Game

    Game(camera=not args.no_camera, camera_index=args.camera, fullscreen=True if args.fullscreen else None,
         fps=max(30, args.fps), seed=args.seed).run()


if __name__ == "__main__":
    main()
