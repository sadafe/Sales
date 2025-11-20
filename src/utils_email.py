"""
Поиск и извлечение email адресов
"""

import json
import os
import random
import time
from tkinter import Tk, filedialog

import pandas as pd
import requests
from bs4 import BeautifulSoup
from icecream import ic
from loguru import logger

from utils import (
    extract_emails_from_text,
    get_random_user_agent,
    normalize_url,
    validate_emails,
)


class ExtrationEmail:
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

        timeout = 20  # магическое число !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

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
            company = soup.find_all("span", {"itemprop": "name"})[2].text
            logger.debug(f"Найдена компания {company}")

            # 1. Извлекаем email из ссылок mailto:
            mailto_links = soup.select('a[href^="mailto:"]')
            for link in mailto_links:
                href = link.get("href", "")
                if href.startswith("mailto:"):
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

    def load_excel(self, name):
        """
        Загрузка данных из excel файла

        :param name: имя файла
        :return: DataFrame Pandas
        :rtype: pd.DataFrame
        """
        pd_data = pd.DataFrame
        try:
            pd_data = pd.read_excel(name)
        except Exception as e:
            logger.error(f"Ощибка при чтении файла {name} - {e}")

        return pd_data

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
    output_file = filedialog.askopenfilename(
        title="Выберите файл",
    )
    if not output_file:
        output_file = "."

    list_email = ExtrationEmail()
    emails = []
    data_all = list_email.load_excel(output_file)
    data = set(data_all['ОГРН'])
    for url in data:
        copm, email_comp = list_email.extract_emails_from_webpage(list_email.to_url(url))
        if len(email_comp) == 0:
            emails.append([copm, ''])
        for em in email_comp:
            emails.append([copm, em])


    ic(emails)
    json_pd = pd.DataFrame(emails, columns=['name', 'emails'])
    json_pd.index += 1

    name_f, name_s = os.path.split(output_file)

    json_pd.to_excel(f'{name_f}/email_{name_s}', index_label='№')


def main():
    process()


if __name__ == "__main__":
    main()
