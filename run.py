#!/usr/bin/env python3
"""
Скрипт для запуска Email Extractor
"""

import sys
import os
from pathlib import Path

# Добавляем src в путь для импорта
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.main import main

if __name__ == "__main__":
    main()
