#!/usr/bin/env python3
"""
Скрипт для запуска Email Extractor
"""

import sys
import os
from pathlib import Path

# Добавляем src в путь для импорта
sys.path.insert(0, str(Path(__file__).parent / "src"))

import curses
import sys
from src.main import main
from src.utils import setup_logging
from loguru import logger

if __name__ == "__main__":
    # Настраиваем логирование
    setup_logging(log_level="INFO")

    # Проверка аргументов командной строки для логирования в файл
    if len(sys.argv) > 1 and sys.argv[1] == "-log":
        logger.add("app.log", rotation="1 MB", retention="7 days", level="INFO")

    # Запускаем curses приложение
    curses.wrapper(main)
