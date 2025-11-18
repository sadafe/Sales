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

if __name__ == "__main__":
    # Проверка аргументов командной строки для логирования в файл

    # logger.disable("")
    logger.remove()
    # print(logger._core.handlers)
    input("tur")

    if len(sys.argv) > 1 and sys.argv[1] == "-log":
        setup_logging(log_level="DEBUG", log_file="app.log")

    # Запускаем curses приложение
    curses.wrapper(main)
