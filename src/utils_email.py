"""
Модуль для поиска и извлечения email адресов из веб-страниц по ОГРН
"""

import os
import time
from pathlib import Path
from tkinter import Tk, filedialog
from typing import Optional, Tuple

import pandas as pd
import requests
from bs4 import BeautifulSoup
from loguru import logger

from src.utils import (
    extract_emails_from_text,
    get_headers,
    normalize_url,
    print_progress,
    validate_emails,
)

# Константы
DEFAULT_TIMEOUT = 20
DEFAULT_MAX_RETRIES = 3
BASE_URL_COMPANY = "https://companium.ru/id"
BASE_URL_PEOPLE = "https://companium.ru/people/inn"
OGRN_LENGTH_COMPANY = 13
OGRN_LENGTH_PEOPLE = 15
EMAIL_CLASSES = ["email", "mail", "e-mail", "contact-email", "contact-mail"]
DATA_EMAIL_ATTRS = ["data-email", "data-mail", "data-e-mail"]
UNKNOWN_COMPANY = "Неизвестная компания"


class ExtractionEmail:
    """
    Класс для извлечения email-адресов с веб-страниц компаний
    """

    def __init__(
        self,
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        """
        Инициализация класса

        Args:
            timeout: Таймаут для HTTP запросов в секундах
            max_retries: Максимальное количество повторных попыток
        """
        self.timeout = timeout
        self.max_retries = max_retries

    def _get_headers(self) -> dict[str, str]:
        """
        Генерирует HTTP заголовки для запросов

        Returns:
            Словарь с HTTP заголовками
        """

        return get_headers()

    def get_webpage_content(self, url: str, max_retries: Optional[int] = None) -> str:
        """
        Получает содержимое веб-страницы с повторными попытками

        Args:
            url: URL для загрузки
            max_retries: Максимальное количество попыток (если None, используется self.max_retries)

        Returns:
            HTML содержимое страницы или пустая строка при ошибке
        """
        if max_retries is None:
            max_retries = self.max_retries

        headers = self._get_headers()

        for attempt in range(max_retries):
            try:
                response = requests.get(url, headers=headers, timeout=self.timeout)
                response.raise_for_status()

                logger.debug(f"Успешно загружена страница: {url}")
                return response.text

            except requests.exceptions.Timeout as e:
                logger.warning(
                    f"Попытка {attempt + 1}/{max_retries} не удалась для {url}: {e}"
                )

                if attempt < max_retries - 1:
                    # Экспоненциальная задержка между попытками
                    delay = 2**attempt
                    logger.debug(f"Ожидание {delay} секунд перед повторной попыткой...")
                    time.sleep(delay)
                else:
                    logger.error(
                        f"Не удалось загрузить страницу {url} после {max_retries} попыток"
                    )
            except requests.exceptions.HTTPError:
                print("\nНе могу получить данные с сайта https://companium.ru")
                input('Пожалуйста проверте доступность сайта. Для выхода нажмите <Enter>')
                raise ValueError('Ошибка получения данных')

        return ""

    def _extract_company_name(self, soup: BeautifulSoup) -> str:
        """
        Извлекает название компании из HTML

        Args:
            soup: Объект BeautifulSoup с распарсенным HTML

        Returns:
            Название компании или "Неизвестная компания"
        """
        # Пытаемся найти название через itemprop="name"
        name_spans = soup.find_all("span", {"itemprop": "name"})
        if len(name_spans) > 2:
            company = name_spans[2].text.strip()
            if company:
                return company

        # Альтернативный способ - извлечение из title
        title = soup.find("title")
        if title:
            company = title.text.strip()
            if company:
                return company

        return UNKNOWN_COMPANY

    def _extract_emails_from_mailto_links(self, soup: BeautifulSoup) -> list[str]:
        """
        Извлекает email из ссылок mailto:

        Args:
            soup: Объект BeautifulSoup с распарсенным HTML

        Returns:
            Список найденных email-адресов
        """
        emails = []
        mailto_links = soup.select('a[href^="mailto:"]')

        for link in mailto_links:
            href = link.get("href", "")
            if isinstance(href, str) and href.startswith("mailto:"):
                email = href[7:]  # Убираем 'mailto:'
                # Удаляем параметры после email (если есть)
                email = email.split("?")[0].strip()
                if "@" in email:
                    emails.append(email)

        return emails

    def _extract_emails_from_links(self, soup: BeautifulSoup) -> list[str]:
        """
        Извлекает email из текста ссылок

        Args:
            soup: Объект BeautifulSoup с распарсенным HTML

        Returns:
            Список найденных email-адресов
        """
        emails = []
        for link in soup.find_all("a"):
            link_text = link.get_text().strip()
            if "@" in link_text and "." in link_text:
                found_emails = extract_emails_from_text(link_text)
                emails.extend(found_emails)

        return emails

    def _extract_emails_from_data_attrs(self, soup: BeautifulSoup) -> list[str]:
        """
        Извлекает email из элементов с data-атрибутами

        Args:
            soup: Объект BeautifulSoup с распарсенным HTML

        Returns:
            Список найденных email-адресов
        """
        emails = []
        selector = ", ".join([f"[{attr}]" for attr in DATA_EMAIL_ATTRS])
        for elem in soup.select(selector):
            for attr_name in DATA_EMAIL_ATTRS:
                if attr_name in elem.attrs:
                    attr_value = elem.attrs[attr_name]
                    if isinstance(attr_value, str):
                        emails.extend(extract_emails_from_text(attr_value))
                    elif isinstance(attr_value, list):
                        for value in attr_value:
                            if isinstance(value, str):
                                emails.extend(extract_emails_from_text(value))

        return emails

    def _extract_emails_from_classes(self, soup: BeautifulSoup) -> list[str]:
        """
        Извлекает email из элементов с определенными классами

        Args:
            soup: Объект BeautifulSoup с распарсенным HTML

        Returns:
            Список найденных email-адресов
        """
        emails = []
        for class_name in EMAIL_CLASSES:
            for elem in soup.select(f".{class_name}"):
                emails.extend(extract_emails_from_text(elem.get_text()))

        return emails

    @logger.catch
    def extract_emails_from_webpage(self, url: str) -> Tuple[str, list[str]]:
        """
        Извлекает email-адреса с веб-страницы

        Args:
            url: URL веб-страницы

        Returns:
            Кортеж (название компании, список email-адресов)
        """
        normalized_url = normalize_url(url)
        content = self.get_webpage_content(normalized_url)

        if not content:
            return "", []

        try:
            soup = BeautifulSoup(content, "html.parser")

            # Извлекаем название компании
            company = self._extract_company_name(soup)
            logger.debug(f"Найдена компания: {company}")

            # Собираем email из разных источников
            emails = []
            emails.extend(self._extract_emails_from_mailto_links(soup))
            emails.extend(self._extract_emails_from_links(soup))
            emails.extend(self._extract_emails_from_data_attrs(soup))
            emails.extend(self._extract_emails_from_classes(soup))

            # Ищем email в общем тексте страницы
            page_text = soup.get_text()
            emails.extend(extract_emails_from_text(page_text))

            # Валидируем и удаляем дубликаты
            valid_emails = validate_emails(emails)
            unique_emails = sorted(list(set(valid_emails)))

            logger.debug(
                f"Найдено {len(unique_emails)} уникальных email-адресов на {url}"
            )
            return company, unique_emails

        except Exception as e:
            logger.error(f"Ошибка при извлечении email с {url}: {e}")
            return "", []

    def load_excel(self, file_path: str) -> Optional[pd.DataFrame]:
        """
        Загружает данные из Excel файла

        Args:
            file_path: Путь к Excel файлу

        Returns:
            DataFrame Pandas или None при ошибке
        """
        try:
            if not os.path.exists(file_path):
                logger.error(f"Файл не найден: {file_path}")
                return None

            pd_data = pd.read_excel(file_path)
            logger.debug(f"Файл {file_path} успешно загружен, строк: {len(pd_data)}")
            return pd_data

        except Exception as e:
            logger.error(f"Ошибка при чтении файла {file_path}: {e}")
            return None

    def ogrn_to_url(self, ogrn: str | int | float) -> str:
        """
        Преобразует ОГРН в URL для запроса

        Args:
            ogrn: ОГРН компании или ИНН физического лица

        Returns:
            URL для запроса или пустая строка если формат не поддерживается
        """
        ogrn_str = str(int(float(ogrn))) if isinstance(ogrn, float) else str(ogrn)

        if len(ogrn_str) == OGRN_LENGTH_COMPANY:
            return f"{BASE_URL_COMPANY}/{ogrn_str}/contacts"

        if len(ogrn_str) == OGRN_LENGTH_PEOPLE:
            return f"{BASE_URL_PEOPLE}/{ogrn_str}"

        logger.warning(
            f"Неподдерживаемый формат ОГРН: {ogrn_str} (длина: {len(ogrn_str)})"
        )
        return ""

    def process_ogrn_list(
        self, ogrn_list: list[str | int | float], delay: float = 1.0
    ) -> list[dict[str, str]]:
        """
        Обрабатывает список ОГРН и извлекает email-адреса

        Args:
            ogrn_list: Список ОГРН для обработки
            delay: Задержка между запросами в секундах

        Returns:
            Список словарей с результатами {"name": str, "email": str}
        """
        results = []
        total = len(ogrn_list)

        for idx, ogrn in enumerate(ogrn_list, 1):
            logger.info(f"Обработка {idx}/{total}: ОГРН {ogrn}")

            print_progress(idx, total)

            url = self.ogrn_to_url(ogrn)
            if not url:
                logger.warning(f"Не удалось создать URL для ОГРН {ogrn}")
                continue

            company, emails = self.extract_emails_from_webpage(url)

            if emails:
                for email in emails:
                    results.append({"name": company, "email": email})
            else:
                results.append({"name": company, "email": ""})

            # Задержка между запросами
            if idx < total:
                time.sleep(delay)

        return results

    def save_results(self, results: list[dict[str, str]], output_path: str) -> bool:
        """
        Сохраняет результаты в Excel файл

        Args:
            results: Список словарей с результатами
            output_path: Путь для сохранения файла

        Returns:
            True если сохранение прошло успешно
        """
        if not results:
            logger.warning("Нет данных для сохранения")
            return False

        try:
            result_df = pd.DataFrame(results)
            result_df.index += 1

            # Создаем директорию если не существует
            output_dir = os.path.dirname(output_path)
            if output_dir:
                Path(output_dir).mkdir(parents=True, exist_ok=True)

            result_df.to_excel(output_path, index_label="№")
            logger.info(f"Результаты сохранены в {output_path}")
            return True

        except Exception as e:
            logger.error(f"Ошибка при сохранении результатов: {e}")
            return False


def select_file_dialog() -> Optional[str]:
    """
    Открывает диалог выбора файла

    Returns:
        Путь к выбранному файлу или None
    """
    try:
        root = Tk()
        root.withdraw()
        file_path = filedialog.askopenfilename(
            title="Выберите файл с ОГРН",
            filetypes=[("Excel files", "*.xlsx *.xls")],
        )
        root.destroy()
        return file_path if file_path else None

    except Exception as e:
        logger.error(f"Ошибка при открытии диалога выбора файла: {e}")
        return None


@logger.catch
def process(file_path: Optional[str] = None, delay: float = 1.0) -> None:
    """
    Основная функция для поиска email адресов по ОГРН

    Args:
        file_path: Путь к Excel файлу с ОГРН (если None, откроется диалог выбора)
        delay: Задержка между запросами в секундах
    """
    logger.info("Начинаем поиск email адресов из Excel файла с ОГРН")

    # Выбор файла
    if file_path is None:
        file_path = select_file_dialog()

    if not file_path:
        logger.error("Файл не выбран")
        return

    # Инициализация класса
    extractor = ExtractionEmail()

    # Загрузка данных
    data_all = extractor.load_excel(file_path)
    if data_all is None or data_all.empty:
        logger.error("Не удалось загрузить данные из файла")
        return

    # Проверка наличия столбца ОГРН
    if "ОГРН" not in data_all.columns:
        logger.error("В файле отсутствует столбец 'ОГРН'")
        return

    # Получение уникальных ОГРН
    ogrn_data = data_all["ОГРН"].dropna().unique().tolist()
    logger.info(f"Найдено {len(ogrn_data)} уникальных ОГРН для обработки")
    print(f'\nБудем искать email адреса для {len(ogrn_data)} производителей')

    # Обработка ОГРН
    results = extractor.process_ogrn_list(ogrn_data, delay=delay)

    # Сохранение результатов
    if results:
        input_dir, input_filename = os.path.split(file_path)
        output_path = os.path.join(input_dir, f"email_{input_filename}")
        extractor.save_results(results, output_path)
        print(f'Данные сохранены в файле {output_path}')
        input('Для выхода нажмите <Enter>')
    else:
        logger.warning("Не найдено ни одного email адреса")


def main() -> None:
    """Точка входа в программу"""
    process()


if __name__ == "__main__":
    main()
