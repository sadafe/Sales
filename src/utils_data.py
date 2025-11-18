"""загрузка и анализ файлов production.xlsx по адресу https://gisp.gov.ru/pp719v2/pub/prod/
 и каталог предпиятий export.xlsx по адресу https://gisp.gov.ru/company-catalog/

в базу данных"""

import datetime
import os
import sqlite3
import time
from pathlib import Path

import pandas as pd
from loguru import logger


class Ktru:
    def __init__(self, db_path: str = "data/database/ktru.db"):
        """
        Инициализация базы данных

        Args:
            db_path: Путь к файлу базы данных
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Инициализирован класс Ktru({db_path})")
        self.init_database()
        self.pd_to_sql()

    def init_database(self):
        """Создает таблицы базы данных если они не существуют"""
        logger.debug("Инициализация таблицы logs базы данных ")
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Таблица логов
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tables TEXT,
                        message TEXT,
                        Date_register DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()

                cursor.execute(
                    """CREATE TRIGGER IF NOT EXISTS log_insert
                        AFTER UPDATE ON logs
                        BEGIN
                            INSERT INTO logs (message)
                            VALUES ('Обнавлена база данных');
                        END;"""
                )

                conn.commit()

        except sqlite3.Error as e:
            logger.error(f"Ошибка при инициализации таблицы logs базы данных: {e}")
            raise

    def _load_pd(self, file: str, sheet_name: str, table_name: str, headers: int):
        """
        Загрузка данных в таблицу базы данных

        Args:
            file: Путь к файлу Excel c данными
            sheet_name: Имя страницы в файле Excel
            table_name: Имя таблицы в базе данных
            headers: Номер строки с которой начинаются данные
        """
        sql_query = """
        SELECT MAX(Date_register)
        FROM logs
        WHERE tables=?
        """
        time_file = datetime.datetime.fromtimestamp(
            int(self.get_data(file))
        )  # получаем дату файла
        with sqlite3.connect(self.db_path) as conn:
            date_bd_row = conn.execute(
                sql_query, (table_name,)
            ).fetchone()  # получаем дату из базы данных
            if date_bd_row and date_bd_row[0]:
                date_bd = datetime.datetime.strptime(
                    date_bd_row[0], "%Y-%m-%d %H:%M:%S"
                )
            else:
                date_bd = datetime.datetime(
                    2020, 1, 1
                )  # если дата не установлена, устанавливаем сами на 1 января 2020 г

            if time_file > date_bd:  # Если файл моложе, загружаем его в базу данных
                try:
                    logger.debug(f"Загрузка файла {file}")
                    print(f"Загрузка файла {file}")
                    wb = pd.read_excel(file, sheet_name=sheet_name, header=headers)
                    logger.debug(f"Запись данных из файла {file} в базу данных")
                    print(f"Запись данных из файла {file} в базу данных")
                    wb.to_sql(table_name, conn, index=True, if_exists="replace")
                    cursor = conn.cursor()
                    exect = f"CREATE INDEX IF NOT EXISTS idx_{table_name}_id ON {table_name}(ОГРН)"
                    cursor.execute(exect)
                    exect = f"INSERT INTO logs (tables, message) VALUES ('{table_name}', 'создана база данных')"
                    cursor.execute(exect)
                    conn.commit()
                except Exception as e:
                    logger.error(f"Ошибка в модуле _load_pd при загрузке {file}: {e}")
                    raise

            if datetime.datetime.now() > time_file + datetime.timedelta(days=10):
                logger.warning(f"Рекоментуется обновить файл {file}")
                print(f"Рекоментуется обновить файл {file}")
                time.sleep(5)

    def pd_to_sql(self):
        """Заполнение данными базу данных"""

        self._load_pd("export.xlsx", "Exp", "export", 0)
        self._load_pd("production.xlsx", "Продукция", "product", 2)

    def get_data(self, file):
        """
        Получаем дату создания файла в секундах

        Args:
            file: Имя файла
        Returns:
            Объект datatime когда файл был создан
        """
        return os.stat(file).st_birthtime

    def get_okpd(self, okpd):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT 
                        p."ОГРН",
                        p."ОКПД2",
                        COALESCE(e."Краткое наименование организации", 'нет данных') AS Результат
                    FROM product p
                    LEFT JOIN export e ON p."ОГРН" = e."ОГРН"
                    WHERE p."ОКПД2" like ?
                    GROUP BY p."ОГРН"
                    """,
                    (okpd,),
                )
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"Ошибка при получении ОКПД {okpd} из базы данных : {e}")
            return []


def processor() -> None:
    """Основная функция обработки КТРУ с пользовательским вводом"""
    print("Инициализация базы данных")
    processor_instance = Ktru()
    print("Введите номер ОКПД2 вида 26.20.15.000 (возможен ввод подстановочных знаков)")
    print("для укрупненного вывода ОКПД2 примет вид 26.20.15.% или q для выхода")
    while True:
        okpd = input("введите ОКПД2 : ").strip()
        logger.debug(f"введено для поиска из базы данных: {okpd}")

        if okpd.lower() == "q":
            break

        res = processor_instance.get_okpd(okpd)
        print('№\tНаименование\tОГРН')
        for n, r in enumerate(res, 1):
            print(f"{n}\t{r['Результат']}\t{r['ОГРН']}")


        
def main():
    ktru = Ktru()
    res = ktru.get_okpd("26.20.15.000")
    for n, r in enumerate(res, 1):
        print(f"{n} - {r=}")


if __name__ == "__main__":
    main()
