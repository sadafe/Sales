#!/usr/bin/env python3
"""
Скрипт для запуска Email Extractor
"""

import sys
from pathlib import Path

# Добавляем src в путь для импорта
sys.path.insert(0, str(Path(__file__).parent / "src"))

import curses
import sys

from loguru import logger

from src.main_probe import main
from src.utils import setup_logging


def run_main():
    logger.remove()

    if len(sys.argv) > 1 and sys.argv[1] == "-log":
        setup_logging(log_level="TRACE", log_file="app.log")

    # Запускаем curses приложение
    curses.wrapper(main)


if __name__ == "__main__":
    run_main()
