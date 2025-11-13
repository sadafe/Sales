#!
"""Программа загружает с сайта zakupki.gov.ru по КТРУ характеристики товаров, работ, услуг"""

import os
import re
from tkinter import filedialog
from tkinter import Tk

import pandas as pd
import requests
from bs4 import BeautifulSoup

KTRU_PATTERN = r"\d{2}\.\d{2}\.\d{2}\.\d{3}-\d{8}"


def validate_ktru(ktru: str) -> bool:
    """Валидация формата КТРУ"""
    return bool(re.match(KTRU_PATTERN, ktru))


class ZakupkiProcessor:
    """
    Класс для парсинга и записи данных со страниц zakupki.gov.ru
    """

    BASE_URL = "https://zakupki.gov.ru"
    MAX_RETRIES = 3
    HEADERS = {
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
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    }

    def __init__(self, ktru: str = ""):
        """
        Инициализируем класс и запрашиваем у пользователя номер КТРУ

        Args:
            ktru: номер КТРУ формата XX.XX.XX.XXX-XXXXXXXX

        """
        while not validate_ktru(ktru):
            if ktru:
                print(
                    "Неверный формат КТРУ. Ожидается формат XX.XX.XX.XXX-XXXXXXXX. Попробуйте снова."
                )
            ktru = input("введите КТРУ вида 26.20.15.000-00000024: ")
        self.ktru = ktru

    def load_url(self, base_ktru: str, retries: int = 3) -> str:
        """
        Загрузка данных со страницы в интернете с повторными попытками

        Args:
            base_ktru: Относительный URL для загрузки
            retries: Количество повторных попыток

        Returns:
            HTML-содержимое страницы
        """
        ktru_url = f"{self.BASE_URL}{base_ktru}"

        for attempt in range(retries + 1):
            try:
                response = requests.get(
                    ktru_url, headers=self.HEADERS, timeout=10, verify=True
                )
                response.raise_for_status()
                return response.text
            except requests.RequestException as e:
                if attempt == retries:
                    raise RuntimeError(
                        f"Не удалось загрузить страницу после {retries} попыток: {e}"
                    )
                print(f"Попытка {attempt + 1} неудачна, повторяю: {e}")
        raise RuntimeError("Неожиданная ошибка")

    def _clean_text(self, element) -> str:
        """Очистка строковых данных от нечитаемых символов и пробелов"""
        return (
            element.get_text(strip=True)
            .replace("\xa0", "")
            .replace("  ", "")
            .replace("\n", "")
        )

    def get_ktru_version(self) -> str:
        """
        Получение версии КТРУ с основной страницы

        Returns:
            Версия КТРУ
        """
        ktru_url = f"/epz/ktru/ktruCard/ktru-description.html?itemId={self.ktru}"
        html_content = self.load_url(ktru_url)
        soup = BeautifulSoup(html_content, "html.parser")
        version_input = soup.find("input", {"id": "ktruItemVersionId"})
        if not version_input or not hasattr(version_input, "get"):
            raise ValueError("Не удалось найти версию КТРУ на странице")
        value = version_input.get("value")
        if not value:
            raise ValueError("Версия КТРУ пуста")
        return str(value)

    def process_data(self) -> None:
        """
        Парсинг данных КТРУ и сохранение в файлы
        """
        ktru_version = self.get_ktru_version()
        url = f"/epz/ktru/ktruCard/ktru-part-description.html?itemVersionId={ktru_version}&page=1&recordsPerPage=5000&isTemplate=false&onlyRequired=false"
        html_content = self.load_url(url)

        soup = BeautifulSoup(html_content, "html.parser")
        table = soup.select_one("table.blockInfo__table")
        if not table:
            raise ValueError("Таблица с характеристиками не найдена")

        data_rows = []
        for row in table.select("tr.tableBlock__row"):
            cells = row.select("td")
            if len(cells) == 3:
                data_rows.append(
                    [
                        self._clean_text(cells[0]),
                        self._clean_text(cells[1]),
                        self._clean_text(cells[2]),
                    ]
                )
            elif len(cells) == 2:
                data_rows.append(
                    ["", self._clean_text(cells[0]), self._clean_text(cells[1])]
                )

        df = pd.DataFrame(
            data_rows,
            columns=[
                "Наименование характеристики",
                "Значение характеристики",
                "Единица измерения характеристики",
            ],
        )

        # Выбор пути для сохранения файлов через диалог
        root = Tk()
        root.withdraw()  # Скрываем основное окно
        output_dir = filedialog.askdirectory(title="Выберите папку для сохранения файлов")
        if not output_dir:
            output_dir = "."

        # Сохранение в файлы
        latex_file = os.path.join(output_dir, "tt.tex")
        excel_file = os.path.join(output_dir, f"{self.ktru}.xlsx")
        docx_file = os.path.join(output_dir, f"{self.ktru}.docx")

        df.to_latex(
            latex_file, index=False, column_format="|l|c|c|", header=True, multirow=True
        )
        df.to_excel(excel_file, sheet_name="Sheet1", index=False)

        os.system(f"pandoc.exe -s -f latex {latex_file} -o {docx_file}")
        os.remove(latex_file)


def processor() -> None:
    """Основная функция обработки КТРУ с пользовательским вводом"""
    print("Введите КТРУ или q для выхода")
    while True:
        ktru_input = input("введите КТРУ вида 26.20.15.000-00000024: ").strip()

        if ktru_input.lower() == "q":
            break

        if validate_ktru(ktru_input):
            processor_instance = ZakupkiProcessor(ktru_input)
            try:
                processor_instance.process_data()
                print(f"Данные для КТРУ {ktru_input} успешно обработаны")
                break
            except Exception as e:
                print(f"Ошибка при обработке КТРУ {ktru_input}: {e}")
                break
        else:
            print(
                "Неверный формат КТРУ. Ожидается формат XX.XX.XX.XXX-XXXXXXXX. Попробуйте снова."
            )


def main() -> None:
    """Точка входа в программу"""
    print("Hello from zakupki!")
    processor()


if __name__ == "__main__":
    main()
