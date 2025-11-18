"""
Модуль для работы с базой данных SQLite
TODO: Переделать модуль для работы без базы данных и в составе главного модуля
"""

import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class EmailDatabase:
    """Класс для работы с базой данных email-адресов"""

    def __init__(self, db_path: str = "data/database/emails.db"):
        """
        Инициализация базы данных

        Args:
            db_path: Путь к файлу базы данных
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
        self.init_database()

    def init_database(self) -> None:
        """Создает таблицы базы данных если они не существуют"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Таблица компаний
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS companies (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        url TEXT UNIQUE NOT NULL,
                        category TEXT,
                        company_name TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Таблица email-адресов
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS emails (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        email TEXT UNIQUE NOT NULL,
                        company_id INTEGER,
                        extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        is_valid BOOLEAN DEFAULT 1,
                        source_url TEXT,
                        FOREIGN KEY (company_id) REFERENCES companies (id)
                    )
                """)

                # Таблица статистики
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS extraction_stats (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        category TEXT,
                        total_urls INTEGER,
                        successful_extractions INTEGER,
                        total_emails_found INTEGER,
                        extraction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        duration_seconds REAL
                    )
                """)

                # Индексы для улучшения производительности
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_emails_company_id ON emails(company_id)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_emails_extracted_at ON emails(extracted_at)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_companies_category ON companies(category)"
                )

                conn.commit()
                self.logger.info("База данных инициализирована успешно")

        except sqlite3.Error as e:
            self.logger.error("Ошибка при инициализации базы данных: %s", e)
            raise

    def add_company(
        self,
        url: str,
        category: Optional[str] = None,
        company_name: Optional[str] = None,
    ) -> int | None:
        """
        Добавляет компанию в базу данных

        Args:
            url: URL компании
            category: Категория компании
            company_name: Название компании

        Returns:
            ID добавленной компании
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO companies (url, category, company_name, last_checked)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """,
                    (url, category, company_name),
                )
                conn.commit()
                return cursor.lastrowid
        except sqlite3.Error as e:
            self.logger.error("Ошибка при добавлении компании %s: %s", url, e)
            return -1

    def add_emails(
        self, emails: List[str], company_id: int, source_url: Optional[str] = None
    ) -> int:
        """
        Добавляет email-адреса в базу данных

        Args:
            emails: Список email-адресов
            company_id: ID компании
            source_url: URL источника

        Returns:
            Количество добавленных email-адресов
        """
        if not emails:
            return 0

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                added_count = 0

                for email in emails:
                    try:
                        cursor.execute(
                            """
                            INSERT OR IGNORE INTO emails (email, company_id, source_url)
                            VALUES (?, ?, ?)
                        """,
                            (email, company_id, source_url),
                        )
                        if cursor.rowcount > 0:
                            added_count += 1
                    except sqlite3.Error:
                        continue

                conn.commit()
                self.logger.info("Добавлено %s новых email-адресов", added_count)
                return added_count

        except sqlite3.Error as e:
            self.logger.error("Ошибка при добавлении email-адресов: %s", e)
            return 0

    def get_emails_by_category(self, category: str) -> List[Dict[str, Any]]:
        """
        Получает все email-адреса по категории

        Args:
            category: Категория для поиска

        Returns:
            Список словарей с информацией об email-адресах
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT e.email, e.extracted_at, c.url, c.company_name
                    FROM emails e
                    JOIN companies c ON e.company_id = c.id
                    WHERE c.category = ?
                    ORDER BY e.extracted_at DESC
                """,
                    (category,),
                )
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            self.logger.error(
                "Ошибка при получении email-адресов для категории %s: %s", category, e
            )
            return []

    def get_all_emails(self) -> List[Dict[str, Any]]:
        """
        Получает все email-адреса из базы данных

        Returns:
            Список словарей с информацией об email-адресах
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT e.email, e.extracted_at, c.url, c.company_name, c.category
                    FROM emails e
                    JOIN companies c ON e.company_id = c.id
                    ORDER BY e.extracted_at DESC
                """)
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            self.logger.error("Ошибка при получении всех email-адресов: %s", e)
            return []

    def save_extraction_stats(
        self,
        category: str,
        total_urls: int,
        successful_extractions: int,
        total_emails_found: int,
        duration_seconds: float,
    ) -> None:
        """
        Сохраняет статистику извлечения

        Args:
            category: Категория
            total_urls: Общее количество URL
            successful_extractions: Количество успешных извлечений
            total_emails_found: Общее количество найденных email-адресов
            duration_seconds: Время выполнения в секундах
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO extraction_stats 
                    (category, total_urls, successful_extractions, total_emails_found, duration_seconds)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (
                        category,
                        total_urls,
                        successful_extractions,
                        total_emails_found,
                        duration_seconds,
                    ),
                )
                conn.commit()
        except sqlite3.Error as e:
            self.logger.error("Ошибка при сохранении статистики: %s", e)

    def get_extraction_stats(
        self, category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Получает статистику извлечения

        Args:
            category: Категория для фильтрации (опционально)

        Returns:
            Список словарей со статистикой
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                if category:
                    cursor.execute(
                        """
                        SELECT * FROM extraction_stats 
                        WHERE category = ?
                        ORDER BY extraction_date DESC
                    """,
                        (category,),
                    )
                else:
                    cursor.execute("""
                        SELECT * FROM extraction_stats 
                        ORDER BY extraction_date DESC
                    """)

                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            self.logger.error("Ошибка при получении статистики: %s", e)
            return []

    def cleanup_old_data(self, days: int = 30) -> int:
        """
        Удаляет старые данные из базы данных

        Args:
            days: Количество дней для хранения данных

        Returns:
            Количество удаленных записей
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Удаляем старые записи статистики
                cursor.execute(
                    """
                    DELETE FROM extraction_stats 
                    WHERE extraction_date < datetime('now', '-{} days')
                """.format(days)
                )

                deleted_count = cursor.rowcount
                conn.commit()

                self.logger.info("Удалено %s старых записей", deleted_count)
                return deleted_count

        except sqlite3.Error as e:
            self.logger.error("Ошибка при очистке старых данных: %s", e)
            return 0

    def backup_database(self, backup_path: Optional[str] = None) -> bool:
        """
        Создает резервную копию базы данных

        Args:
            backup_path: Путь для резервной копии

        Returns:
            True если резервная копия создана успешно
        """
        try:
            if not backup_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = f"data/database/emails_backup_{timestamp}.db"

            backup_path_obj = Path(backup_path)
            backup_path_obj.parent.mkdir(parents=True, exist_ok=True)

            with sqlite3.connect(self.db_path) as source:
                with sqlite3.connect(str(backup_path_obj)) as backup:
                    source.backup(backup)

            self.logger.info("Резервная копия создана: %s", backup_path)
            return True

        except sqlite3.Error as e:
            self.logger.error("Ошибка при создании резервной копии: %s", e)
            return False
