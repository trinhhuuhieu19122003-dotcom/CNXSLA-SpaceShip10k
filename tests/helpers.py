"""Tiện ích dùng chung cho test: chạy pygame không cần màn hình/loa thật."""
import os
import tempfile

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
os.environ.setdefault("SPACESHIP_SAVE_DIR", tempfile.mkdtemp(prefix="spaceship-test-"))

import pygame  # noqa: E402

pygame.init()
