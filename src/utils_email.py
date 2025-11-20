"""
Поиск и извлечение email адресов
"""

import os
import random
import time
from tkinter import Tk, filedialog

import pandas as pd
import requests
from bs4 import BeautifulSoup
from loguru import logger

from utils import (
    extract_emails_from_text,
    get_random_user_agent,
    normalize_url,
    validate_emails,
)

# Константы
DEFAULT_TIMEOUT = 20


class ExtractionEmail:
    def __init__(self) -> None:
        pass

    def get_webpage_content(self, url: str, max_retries: int = 3) -> str:
        """
        Получает содержимое веб-страницы с повторными попытками

        Args:
            url: URL для загрузки
            max_retries: Максимальное количество попыток

        Returns:
            HTML содержимое страницы или "" при ошибке
        """

        headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "priority": "u=0, i",
            "sec-ch-ua": '"Chromium";v="130", "Google Chrome";v="130", "Not?A_Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-origin",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "user-agent": get_random_user_agent(),
        }

        # Добавляем случайные заголовки для большей уникальности
        if random.random() > 0.5:
            headers["Sec-Fetch-Dest"] = "document"
            headers["Sec-Fetch-Mode"] = "navigate"
            headers["Sec-Fetch-Site"] = "cross-site"
            headers["Sec-Fetch-User"] = "?1"

        timeout = DEFAULT_TIMEOUT

        for attempt in range(max_retries):
            try:
                # Выбираем случайный прокси если доступны

                response = requests.get(url, headers=headers, timeout=timeout)
                response.raise_for_status()

                logger.debug(f"Успешно загружена страница: {url}")
                return response.text
            # TODO: написать обработчик капчи
            except requests.exceptions.RequestException as e:
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

        return ""

    @logger.catch
    def extract_emails_from_webpage(self, url: str) -> tuple[str, list[str]]:
        """
        Извлекает email-адреса с веб-страницы

        :param url: адрес url
        :type url: str
        :return: возвращает название компании и привязанные email
        :rtype: tuple[str, list[str]]
        """

        emails = []
        company = ""
        normalized_url = normalize_url(url)
        content = self.get_webpage_content(normalized_url)

        if not content:
            return company, emails

        try:
            # Используем BeautifulSoup для парсинга HTML
            soup = BeautifulSoup(content, "html.parser")

            # Извлекаем название компании со страницы
            name_spans = soup.find_all("span", {"itemprop": "name"})
            if len(name_spans) > 2:
                company = name_spans[2].text.strip()
            else:
                # Альтернативный способ извлечения названия
                title = soup.find("title")
                if title:
                    company = title.text.strip()
                else:
                    company = "Неизвестная компания"
            logger.debug(f"Найдена компания {company}")

            # 1. Извлекаем email из ссылок mailto:
            mailto_links = soup.select('a[href^="mailto:"]')
            for link in mailto_links:
                href = link.get("href", "")
                if isinstance(href, str) and href.startswith("mailto:"):
                    email = href[7:]  # Убираем 'mailto:'
                    # Удаляем параметры после email (если есть)
                    email = email.split("?")[0]
                    if "@" in email:
                        emails.append(email)

            # 2. Ищем email в тексте ссылок
            for link in soup.find_all("a"):
                link_text = link.get_text().strip()
                if "@" in link_text and "." in link_text:
                    found_emails = extract_emails_from_text(link_text)
                    emails.extend(found_emails)

            # 3. Ищем в элементах с атрибутом data-email или похожими
            for elem in soup.select("[data-email], [data-mail], [data-e-mail]"):
                for attr_name in ["data-email", "data-mail", "data-e-mail"]:
                    if attr_name in elem.attrs:
                        emails.extend(extract_emails_from_text(elem[attr_name]))

            # 4. Ищем в элементах с классами, которые могут содержать email
            email_classes = ["email", "mail", "e-mail", "contact-email", "contact-mail"]
            for class_name in email_classes:
                for elem in soup.select(f".{class_name}"):
                    emails.extend(extract_emails_from_text(elem.get_text()))

            # 5. Ищем email в общем тексте страницы
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
            return company, []

    def load_excel(self, name: str) -> pd.DataFrame | None:
        """
        Загрузка данных из excel файла

        :param name: имя файла
        :return: DataFrame Pandas или None при ошибке
        :rtype: pd.DataFrame | None
        """
        try:
            pd_data = pd.read_excel(name)
            logger.debug(f"Файл {name} успешно загружен")
            return pd_data
        except Exception as e:
            logger.error(f"Ошибка при чтении файла {name}: {e}")
            return None

    def to_url(self, ints) -> str:
        """
        Приведение url из ОГРН

        :param ints: Данные из DataFrame номер ОГРН
        :return: Приведенное url
        :rtype: str
        """
        url = ""
        i = str(ints)

        if len(i) == 13:
            # https://companium.ru/id/<13-значное>/contacts
            url = f"https://companium.ru/id/{i}/contacts"

        if len(i) == 15 and i:
            # https://companium.ru/people/inn/<15-значное>
            url = f"https://companium.ru/people/inn/{i}"

        return url

@logger.catch
def process():
    """
    Основная программа поиска email адресов по ОГРН
    """
    print("Ищет email адреса из excel файла с ОГРН")
    root = Tk()
    root.withdraw()
    input_file = filedialog.askopenfilename(
        title="Выберите файл с ОГРН",
        filetypes=[("Excel files", "*.xlsx *.xls")]
    )
    if not input_file:
        logger.error("Файл не выбран")
        return

    list_email = ExtractionEmail()
    data_all = list_email.load_excel(input_file)
    if data_all is None or data_all.empty:
        logger.error("Не удалось загрузить данные из файла")
        return

    if 'ОГРН' not in data_all.columns:
        logger.error("В файле отсутствует столбец 'ОГРН'")
        return

    ogrn_data = set(data_all['ОГРН'].dropna())  # Убираем NaN и дубликаты
    results = []  # Список словарей для лучшей структуры

    for ogrn in ogrn_data:
        url = list_email.to_url(str(int(ogrn)))
        if not url:
            continue
        company, emails = list_email.extract_emails_from_webpage(url)
        if emails:
            for email in emails:
                results.append({"name": company, "email": email})
        else:
            results.append({"name": company, "email": ""})

    if results:
        result_df = pd.DataFrame(results)
        result_df.index += 1

        name_f, name_s = os.path.split(input_file)
        output_path = os.path.join(name_f, f"email_{name_s}")
        result_df.to_excel(output_path, index_label='№')
        logger.info(f"Результаты сохранены в {output_path}")
    else:
        logger.warning("Не найдено ни одного email адреса")


def main():
    process()


if __name__ == "__main__":
    main()
