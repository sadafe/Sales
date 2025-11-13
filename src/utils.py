"""
Утилиты для Email Extractor
"""
import re
import random
import time
from loguru import logger
from proxy_information import ProxyInformation
import requests
import urllib.error
import urllib.request
import socket
from typing import List, Optional, Dict, Any
from pathlib import Path
import yaml
from fake_useragent import UserAgent


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None):
    """
    Настраивает логирование для приложения с помощью loguru

    Args:
        log_level: Уровень логирования
        log_file: Путь к файлу логов

    Returns:
        None (настраивает глобальный логгер loguru)
    """
    from loguru import logger

    # Очищаем существующие обработчики
    logger.remove()

    # Добавляем обработчик для консоли
    logger.add(
        lambda msg: print(msg, end=""),
        level=log_level.upper(),
        format="{time:YYYY-MM-DD HH:mm:ss} - {level} - {message}",
        colorize=True
    )

    # Обработчик для файла
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        logger.add(
            log_path,
            level=log_level.upper(),
            format="{time:YYYY-MM-DD HH:mm:ss} - {level} - {message}",
            rotation="1 MB",
            retention="7 days",
            encoding='utf-8'
        )


def load_config(config_path: str = "config/config.yaml") -> Dict[str, Any]:
    """
    Загружает конфигурацию из YAML файла

    Args:
        config_path: Путь к файлу конфигурации

    Returns:
        Словарь с конфигурацией
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        if not isinstance(config, dict):
            logger.error(
                "Конфигурация не является словарем: %s", type(config))
            return {}
        return config or {}
    except FileNotFoundError:
        logger.error("Файл конфигурации не найден: %s", config_path)
        return {}
    except yaml.YAMLError as e:
        logger.error("Ошибка при чтении конфигурации: %s", e)
        return {}
    except Exception as e:
        logger.error("Неожиданная ошибка при загрузке конфигурации: %s", e)
        return {}


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
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (iPad; CPU OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
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
    if not url.startswith(('http://', 'https://')):
        return 'https://' + url
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
    email_pattern = r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b'
    emails = re.findall(email_pattern, text)

    # Фильтруем только валидные email
    return validate_emails(emails)


def norm_dict_url(proxy_list: List[str]) -> List[Dict[str, str]]:
    ''' приведение списка прокси к словарю

    Args:
        proxy_file: список прокси

    Returns:
        Список словарей с прокси

    '''
    proxies = []
    lines = proxy_list
    for line in lines:
        if line and not line.startswith('#'):
            # Поддерживаем разные форматы прокси
            if '://' in line:
                http_line = line
                https_line = line.replace('https://', 'http://', 1)
                proxies.append({'http': http_line, 'https': https_line})
            else:
                # Если указан только IP:PORT, добавляем протокол
                proxies.append({
                    'http': f'http://{line}',
                    'https': f'https://{line}'
                })
    return proxies


def proxy_from_url(url: str) -> List[Dict[str, str]]:
    """
    Загружает список прокси из интернета

    Args:
        url: ссылка на файл с прокси

    Returns:
        Список прокси
    """
    lines = []
    try:
        response = requests.get(url, timeout=10)
        lines = response.text.split()
    except:
        return []
    return norm_dict_url(lines)


def searh_russia(dict_json):
    '''
    Возвращает список русских прокси
    
    Args:
        Json: список с прокси

    Returns:
        Список прокси
    '''
    list_russia = []

    for lin in dict_json:
        try:
            if lin['location']['country'] == 'Russia':
                add_url = norm_dict_url([f"{lin['ip']}:{lin['port']}"])
                list_russia.extend(add_url)
        except Exception as e:
            logger.error('Ошибка в поиске русских прокси %s', e)
    return list_russia


def load_proxies(proxy_file: str) -> List[Dict[str, str]]:
    """
    Загружает список прокси из файла

    Args:
        proxy_file: Путь к файлу с прокси

    Returns:
        Список прокси
    """
    lines = []
    try:
        with open(proxy_file, 'r', encoding='utf-8') as f:
            lines = [line.rstrip() for line in f]

    except FileNotFoundError:
        logger.warning("Файл прокси %s не найден", proxy_file)
    except Exception as e:
        logger.error("Ошибка при загрузке прокси: %s", e)

    return norm_dict_url(lines)


def load_proxies_generator(proxy_file: str):
    """
    Генератор прокси из файла для обработки без загрузки всего файла в память

    Args:
        proxy_file: Путь к файлу с прокси

    Yields:
        Словарь прокси
    """
    try:
        with open(proxy_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.rstrip()
                if line and not line.startswith('#'):
                    # Поддерживаем разные форматы прокси
                    if '://' in line:
                        http_line = line
                        https_line = line.replace('https://', 'http://', 1)
                        yield {'http': http_line, 'https': https_line}
                    else:
                        # Если указан только IP:PORT, добавляем протокол
                        yield {
                            'http': f'http://{line}',
                            'https': f'https://{line}'
                        }
    except FileNotFoundError:
        logger.warning("Файл прокси %s не найден", proxy_file)
    except Exception as e:
        logger.error("Ошибка при загрузке прокси: %s", e)


def is_bad_proxy(pip):
    try:
        proxy_handler = urllib.request.ProxyHandler({'http': pip})
        opener = urllib.request.build_opener(proxy_handler)
        opener.addheaders = [('User-agent', 'Mozilla/5.0')]
        urllib.request.install_opener(opener)
        # change the URL to test here
        req = urllib.request.Request('https://www.example.com')
        sock = urllib.request.urlopen(req)
    except urllib.error.HTTPError as e:
        print('Error code: ', e.code)
        return e.code
    except Exception as detail:
        logger.error("ERROR: %s", detail)
        return True
    return False


def is_proxy(pip):
    checker = ProxyInformation()
    proxy_info = checker.check_proxy(pip['http'].split('//')[1])

    if isinstance(proxy_info, dict):
        return proxy_info.get('status', False)
    return False


def is_good_proxy(proxy_file):
    socket.setdefaulttimeout(120)
    proxy_list = proxy_file
    for current_proxy in proxy_list[:]:
        if is_bad_proxy(current_proxy['http']) or not is_proxy(current_proxy):
            proxy_list.remove(current_proxy)

    return proxy_list


def get_random_proxy(proxies: List[Dict[str, str]]) -> Optional[Dict[str, str]]:
    """
    Возвращает случайный прокси из списка

    Args:
        proxies: Список прокси

    Returns:
        Случайный прокси или None
    """
    if not proxies:
        return None
    return random.choice(proxies)


def read_urls_from_file(file_path: str) -> List[str]:
    """
    Читает URL из файла, по одному URL на строку

    Args:
        file_path: Путь к файлу с URL

    Returns:
        Список URL
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            result: List[str] = []
            for raw_line in f:
                line = raw_line.strip()
                if not line:
                    continue

                # Если строка уже выглядит как URL — оставляем как есть (с нормализацией)
                if line.startswith(
                        ('http://', 'https://')) or '://' in line or line.startswith('www.'):
                    result.append(normalize_url(line))
                    continue

                # Ожидаем формат: "число,число"
                if ',' in line:
                    first, second = line.split(',', 1)
                    first = first.strip().strip('"\'')
                    second = second.strip().strip('"\'')

                    # Берем только цифры на всякий случай
                    first_digits = re.sub(r'\D', '', first)
                    second_digits = re.sub(r'\D', '', second)

                    if len(first_digits) == 13:
                        # https://companium.ru/id/<13-значное>/contacts
                        url = f"https://companium.ru/id/{first_digits}/contacts"
                        result.append(url)
                        continue

                    if len(first_digits) == 15 and second_digits:
                        # https://companium.ru/people/inn/<число_после_запятой>
                        url = f"https://companium.ru/people/inn/{second_digits}"
                        result.append(url)
                        continue

                # Если формат не распознан — логируем и пропускаем
                logger.warning(
                    "Строка не распознана как валидная запись CSV: %s", line)

            return result
    except FileNotFoundError:
        logger.error("Файл с URL не найден: %s", file_path)
        return []
    except Exception as e:
        logger.error("Ошибка при чтении файла с URL: %s", e)
        return []


def save_emails_to_file(emails: List[str], output_file: str) -> bool:
    """
    Сохраняет email-адреса в файл

    Args:
        emails: Список email-адресов
        output_file: Путь к выходному файлу

    Returns:
        True если сохранение прошло успешно
    """
    try:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            for email in emails:
                f.write(email + '\n')

        logger.info("Сохранено %s email-адресов в файл: %s",
                      len(emails), output_file)
        return True

    except Exception as e:
        logger.error("Ошибка при сохранении email-адресов: %s", e)
        return False


def format_duration(seconds: float) -> str:
    """
    Форматирует продолжительность в читаемый вид

    Args:
        seconds: Количество секунд

    Returns:
        Отформатированная строка времени
    """
    if seconds < 60:
        return f"{seconds:.1f} сек"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f} мин"
    else:
        hours = seconds / 3600
        return f"{hours:.1f} ч"


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
    baris = '█' * filled_length + '-' * (bar_length - filled_length)

    print(f'\r{prefix}: |{baris}| {current}/{total} ({percentage:.1f}%)',
          end='', flush=True)

    if current == total:
        print()  # Новая строка в конце


class ExtractionStats:
    """Класс для отслеживания статистики извлечения"""

    def __init__(self):
        self.start_time = time.time()
        self.total_urls = 0
        self.successful_extractions = 0
        self.failed_extractions = 0
        self.total_emails_found = 0
        self.categories = {}

    def add_category(self, category: str, urls_count: int):
        """Добавляет категорию для отслеживания"""
        self.categories[category] = {
            'urls': urls_count,
            'successful': 0,
            'failed': 0,
            'emails': 0
        }

    def update_extraction(self, category: str, success: bool, emails_count: int = 0):
        """Обновляет статистику извлечения"""
        if success:
            self.successful_extractions += 1
            self.total_emails_found += emails_count
            if category in self.categories:
                self.categories[category]['successful'] += 1
                self.categories[category]['emails'] += emails_count
        else:
            self.failed_extractions += 1
            if category in self.categories:
                self.categories[category]['failed'] += 1

    def get_duration(self) -> float:
        """Возвращает продолжительность выполнения"""
        return time.time() - self.start_time

    def print_summary(self):
        """Выводит сводную статистику"""
        duration = self.get_duration()

        print(f"\n{'='*50}")
        print("СТАТИСТИКА ИЗВЛЕЧЕНИЯ EMAIL-АДРЕСОВ")
        print(f"{'='*50}")
        print(f"Время выполнения: {format_duration(duration)}")
        print(f"Всего URL обработано: {self.total_urls}")
        print(f"Успешных извлечений: {self.successful_extractions}")
        print(f"Неудачных извлечений: {self.failed_extractions}")
        print(f"Всего найдено email-адресов: {self.total_emails_found}")

        if self.categories:
            print("\nСтатистика по категориям:")
            for category, stats in self.categories.items():
                success_rate = (
                    stats['successful'] / stats['urls'] * 100) if stats['urls'] > 0 else 0
                print(
                    f"  {category}: {stats['successful']}/{stats['urls']} ({success_rate:.1f}%) - {stats['emails']} email")

        print(f"{'='*50}")
