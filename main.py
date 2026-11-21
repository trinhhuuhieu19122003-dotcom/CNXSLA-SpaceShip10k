"""Giữ tương thích với cách chạy cũ: ``python main.py``.

Code thật nằm trong package ``spaceship/`` — xem ``python -m spaceship --help``.
"""
from spaceship.__main__ import main

if __name__ == "__main__":
    main()
