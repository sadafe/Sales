"""
Утилиты
"""

import random
import re
from pathlib import Path
from tkinter import Tk, filedialog
from typing import Dict, List, Optional

from fake_useragent import UserAgent
from loguru import logger


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None):
    """
    Настраивает логирование для приложения с помощью loguru

    Args:
        log_level: Уровень логирования
        log_file: Путь к файлу логов

    Returns:
        None (настраивает глобальный логгер loguru)
    """

    # Очищаем существующие обработчики
    logger.remove()

    # Обработчик для файла
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        logger.add(log_path, level=log_level.upper(), encoding="utf-8")


def is_valid_email(email: str) -> bool:
    """
    Проверяет валидность email-адреса

    Args:
        email: Email-адрес для проверки

    Returns:
        True если email валидный
    """
    if not email or not isinstance(email, str):
        return False

    # Более строгая проверка email
    pattern = r"^[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*@(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$"
    return bool(re.match(pattern, email))


def validate_emails(emails: List[str]) -> List[str]:
    """
    Фильтрует только валидные email-адреса

    Args:
        emails: Список email-адресов

    Returns:
        Список валидных email-адресов
    """
    return [email for email in emails if is_valid_email(email)]


def get_random_user_agent() -> str:
    """
    Возвращает случайный User-Agent

    Returns:
        Строка с User-Agent
    """
    try:
        ua = UserAgent()
        return ua.random
    except Exception:
        # Fallback список User-Agent
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (iPad; CPU OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1",
        ]
        return random.choice(user_agents)


def normalize_url(url: str) -> str:
    """
    Нормализует URL, добавляя протокол если необходимо

    Args:
        url: URL для нормализации

    Returns:
        Нормализованный URL
    """
    if not url:
        return url

    url = url.strip()
    if not url.startswith(("http://", "https://")):
        return "https://" + url
    return url


def extract_emails_from_text(text: str) -> List[str]:
    """
    Извлекает email-адреса из текста с помощью регулярных выражений

    Args:
        text: Текст для поиска email-адресов

    Returns:
        Список найденных email-адресов
    """
    if not text:
        return []

    # Улучшенное регулярное выражение для поиска email
    email_pattern = r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b"
    emails = re.findall(email_pattern, text)

    # Фильтруем только валидные email
    return validate_emails(emails)


def norm_dict_url(proxy_list: List[str]) -> List[Dict[str, str]]:
    """приведение списка прокси к словарю

    Args:
        proxy_file: список прокси

    Returns:
        Список словарей с прокси

    """
    proxies = []
    lines = proxy_list
    for line in lines:
        if line and not line.startswith("#"):
            # Поддерживаем разные форматы прокси
            if "://" in line:
                http_line = line
                https_line = line.replace("https://", "http://", 1)
                proxies.append({"http": http_line, "https": https_line})
            else:
                # Если указан только IP:PORT, добавляем протокол
                proxies.append({"http": f"http://{line}", "https": f"https://{line}"})
    return proxies


def print_progress(current: int, total: int, prefix: str = "Прогресс") -> None:
    """
    Выводит прогресс выполнения

    Args:
        current: Текущий элемент
        total: Общее количество элементов
        prefix: Префикс для вывода
    """
    if total == 0:
        return

    percentage = (current / total) * 100
    bar_length = 30
    filled_length = int(bar_length * current // total)
    baris = "█" * filled_length + "-" * (bar_length - filled_length)

    print(
        f"\r{prefix}: |{baris}| {current}/{total} ({percentage:.1f}%)",
        end="",
        flush=True,
    )

    if current == total:
        print()  # Новая строка в конце

def get_path():
    # Выбор пути для сохранения файлов через диалог
    root = Tk()
    root.withdraw()  # Скрываем основное окно
    output_dir = filedialog.askdirectory(title="Выберите папку для сохранения файлов")
    if not output_dir:
        output_dir = "."
    return output_dir