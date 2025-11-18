"""
Улучшенный Email Extractor - Извлечение email-адресов с веб-страниц
"""

import argparse
import random
import sys
import time
from typing import Any, Dict, List, Literal, Optional

import requests
from bs4 import BeautifulSoup
from loguru import logger

from .database import EmailDatabase
from .utils import (ExtractionStats, extract_emails_from_text,
                    get_random_proxy, get_random_user_agent, is_good_proxy,
                    load_config, load_proxies, normalize_url, print_progress,
                    proxy_from_url, read_urls_from_file, save_emails_to_file,
                    setup_logging, validate_emails)


class EmailExtractor:
    """Основной класс для извлечения email-адресов"""

    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Инициализация извлекателя email-адресов
        
        Args:
            config_path: Путь к файлу конфигурации
        """
        self.config = load_config(config_path)
        self.db = EmailDatabase(self.config.get('database', {
                                }).get('path', 'data/database/emails.db'))
        self.stats = ExtractionStats()
        self.proxies = []

        # Загружаем прокси если включены
        if self.config.get('extraction', {}).get('use_proxies', False):
            proxy_file = load_proxies('data/input/proxies.txt')
            proxy_url = proxy_from_url(
                'https://raw.githubusercontent.com/proxifly/free-proxy-list/refs/heads/main/proxies/countries/RU/data.txt')
            proxy_file.extend(proxy_url)

            self.proxies = is_good_proxy(proxy_file)


    def get_webpage_content(self, url: str, max_retries: Optional[int] = None) -> Optional[str]:
        """
        Получает содержимое веб-страницы с повторными попытками
        
        Args:
            url: URL для загрузки
            max_retries: Максимальное количество попыток
            
        Returns:
            HTML содержимое страницы или None при ошибке
        """
        max_retries = max_retries if max_retries is not None else self.config.get('extraction', {}).get('max_retries', 3)

        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'priority': 'u=0, i',
            'sec-ch-ua': '"Chromium";v="130", "Google Chrome";v="130", "Not?A_Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': get_random_user_agent(),
        }

        # Добавляем случайные заголовки для большей уникальности
        if random.random() > 0.5:
            headers['Sec-Fetch-Dest'] = 'document'
            headers['Sec-Fetch-Mode'] = 'navigate'
            headers['Sec-Fetch-Site'] = 'cross-site'
            headers['Sec-Fetch-User'] = '?1'

        timeout = self.config.get('extraction', {}).get('timeout', 20)

        for attempt in range(max_retries):
            try:
                # Выбираем случайный прокси если доступны
                proxies = get_random_proxy(self.proxies) if self.proxies else None

                response = requests.get(
                    url,
                    headers=headers,
                    timeout=timeout,
                    proxies=proxies
                )
                response.raise_for_status()

                logger.debug("Успешно загружена страница: %s", url)
                return response.text

            except requests.exceptions.RequestException as e:
                logger.warning(
                    "Попытка %s/%s не удалась для %s: %s", attempt + 1, max_retries, url, e)

                if attempt < max_retries - 1:
                    # Экспоненциальная задержка между попытками
                    delay = 2 ** attempt
                    logger.debug(
                        "Ожидание %s секунд перед повторной попыткой...", delay
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        "Не удалось загрузить страницу %s после %s попыток", url, max_retries)

        return None

    def extract_emails_from_webpage(self, url: str) -> tuple[Literal[''], list[Any]] | list[str] | list[Any]:
        """
        Извлекает email-адреса с веб-страницы
        
        Args:
            url: URL веб-страницы
            
        Returns:
    TODO:        название компании
            Список найденных email-адресов
        """
        emails = []
        company = ''
        normalized_url = normalize_url(url)
        content = self.get_webpage_content(normalized_url)

        if not content:
            return company, emails

        try:
            # Используем BeautifulSoup для парсинга HTML
            soup = BeautifulSoup(content, 'html.parser')
            company = soup.find("a", {"class": "link fw-700 fs-24"}).text
            print(f'{company=}')

            # 1. Извлекаем email из ссылок mailto:
            mailto_links = soup.select('a[href^="mailto:"]')
            for link in mailto_links:
                href = link.get('href', '')
                if href.startswith('mailto:'):
                    email = href[7:]  # Убираем 'mailto:'
                    # Удаляем параметры после email (если есть)
                    email = email.split('?')[0]
                    if '@' in email:
                        emails.append(email)

            # 2. Ищем email в тексте ссылок
            for link in soup.find_all('a'):
                link_text = link.get_text().strip()
                if '@' in link_text and '.' in link_text:
                    found_emails = extract_emails_from_text(link_text)
                    emails.extend(found_emails)

            # 3. Ищем в элементах с атрибутом data-email или похожими
            for elem in soup.select('[data-email], [data-mail], [data-e-mail]'):
                for attr_name in ['data-email', 'data-mail', 'data-e-mail']:
                    if attr_name in elem.attrs:
                        emails.extend(extract_emails_from_text(elem[attr_name]))

            # 4. Ищем в элементах с классами, которые могут содержать email
            email_classes = ['email', 'mail', 'e-mail', 'contact-email', 'contact-mail']
            for class_name in email_classes:
                for elem in soup.select(f'.{class_name}'):
                    emails.extend(extract_emails_from_text(elem.get_text()))

            # 5. Ищем email в общем тексте страницы
            page_text = soup.get_text()
            emails.extend(extract_emails_from_text(page_text))

            # Валидируем и удаляем дубликаты
            valid_emails = validate_emails(emails)
            unique_emails = sorted(list(set(valid_emails)))

            logger.debug(
                "Найдено %s уникальных email-адресов на %s", len(unique_emails), url
            )
            return company, unique_emails

        except Exception as e:
            logger.error("Ошибка при извлечении email с %s: %s", url, e)
            return company, []

    def process_single_url(self, url: str, category: Optional[str] = None, company: Optional[str] = None) -> List[str]:
        """
        Обрабатывает один URL и возвращает найденные email-адреса

        Args:
            url: URL для обработки
            category: Категория URL
            company: Название компании

        Returns:
            Список найденных email-адресов
        """
        logger.debug("Обработка URL: %s", url)

        # Извлекаем email-адреса
        company, emails = self.extract_emails_from_webpage(url)

        # Добавляем компанию в базу данных
        company_id = self.db.add_company(url, category, company)

        if emails:
            # Сохраняем email-адреса в базу данных
            self.db.add_emails(emails, company_id, url)
            self.stats.update_extraction(category or "unknown", True, len(emails))
        else:
            self.stats.update_extraction(category or "unknown", False)

        return emails

    def process_category(self, category_name: str, urls_file: str, output_file: Optional[str] = None) -> List[str]:
        """
        Обрабатывает все URL из категории
        
        Args:
            category_name: Название категории
            urls_file: Файл с URL
            output_file: Файл для сохранения результатов
            
        Returns:
            Список всех найденных email-адресов
        """
        logger.debug("Обработка категории: %s", category_name)

        # Загружаем URL из файла
        urls = read_urls_from_file(urls_file)
        if not urls:
            logger.warning("Не найдено URL в файле: %s", urls_file)
            return []

        self.stats.add_category(category_name, len(urls))
        self.stats.total_urls += len(urls)

        all_emails = []

        for i, url in enumerate(urls, 1):
            print_progress(i, len(urls), f"Обработка {category_name}")

            try:
                emails = self.process_single_url(url, category_name)
                all_emails.extend(emails)

                # Задержка между запросами
                delay = self.config.get('extraction', {}).get('delay_between_requests', 30)
                if i < len(urls):  # Не ждем после последнего URL
                    time.sleep(delay)

            except Exception as e:
                logger.error("Ошибка при обработке URL %s: %s", url, e)
                self.stats.update_extraction(category_name, False)

        # Удаляем дубликаты
        unique_emails = sorted(list(set(all_emails)))

        # Сохраняем результаты в файл если указан
        if output_file:
            save_emails_to_file(unique_emails, output_file)

        # Сохраняем статистику
        duration = self.stats.get_duration()
        self.db.save_extraction_stats(
            category_name, len(urls),
            self.stats.categories[category_name]['successful'],
            len(unique_emails), duration
        )

        logger.debug(
            "Категория %s обработана. Найдено %s уникальных email-адресов",
            category_name,
            len(unique_emails),
        )
        return unique_emails

    def process_all_categories(self) -> Dict[str, List[str]]:
        """
        Обрабатывает все категории из конфигурации
        
        Returns:
            Словарь с результатами по категориям
        """
        results = {}
        categories = self.config.get('categories', [])

        for category in categories:
            category_name = category['name']
            urls_file = category['urls_file']
            output_file = category.get('output_file')

            logger.debug("Начинаем обработку категории: %s", category_name)
            emails = self.process_category(category_name, urls_file, output_file)
            results[category_name] = emails

        return results


def create_argument_parser() -> argparse.ArgumentParser:
    """Создает парсер аргументов командной строки"""
    parser = argparse.ArgumentParser(
        description='Извлечение email-адресов с веб-страниц',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python -m src.email_extractor example.com
  python -m src.email_extractor -f urls.txt -o results.txt
  python -m src.email_extractor --category monitor
  python -m src.email_extractor --all-categories
        """
    )

    parser.add_argument('url', nargs='?', help='URL веб-страницы для анализа')
    parser.add_argument('-o', '--output', help='Файл для сохранения результатов')
    parser.add_argument('-f', '--file', help='Файл со списком URL для анализа')
    parser.add_argument('-c', '--category', help='Обработать конкретную категорию')
    parser.add_argument('--all-categories', action='store_true',
                       help='Обработать все категории из конфигурации')
    parser.add_argument('--config', default='config/config.yaml',
                       help='Путь к файлу конфигурации')
    parser.add_argument('--stats', action='store_true',
                       help='Показать статистику извлечения')

    return parser


def main():
    """Основная функция программы"""
    parser = create_argument_parser()
    args = parser.parse_args()

    try:
        # Инициализация извлекателя
        extractor = EmailExtractor(args.config)

        # Показать статистику
        if args.stats:
            stats = extractor.db.get_extraction_stats()
            if stats:
                print("\nСтатистика извлечения:")
                for stat in stats:
                    print(f"Категория: {stat['category']}")
                    print(f"URL: {stat['total_urls']}, Успешно: {stat['successful_extractions']}")
                    print(f"Email: {stat['total_emails_found']}, Время: {stat['duration_seconds']:.1f}с")
                    print("-" * 40)
            else:
                print("Статистика не найдена")
            return

        # Обработка всех категорий
        if args.all_categories:
            results = extractor.process_all_categories()
            extractor.stats.print_summary()
            return

        # Обработка конкретной категории
        if args.category:
            categories = extractor.config.get('categories', [])
            category_config = next((c for c in categories if c['name'] == args.category), None)

            if not category_config:
                print(f"Категория '{args.category}' не найдена в конфигурации")
                return

            emails = extractor.process_category(
                args.category,
                category_config['urls_file'],
                args.output or category_config.get('output_file')
            )

            if not args.output:
                for email in emails:
                    print(email)

            extractor.stats.print_summary()
            return

        # Обработка файла с URL
        if args.file:
            urls = read_urls_from_file(args.file)
            if not urls:
                print("Файл с URL пуст или не может быть прочитан")
                return

            print(f"Загружено {len(urls)} URL из файла")
            all_emails = []

            for i, url in enumerate(urls, 1):
                print(f"Обработка URL {i}/{len(urls)}: {url}")
                emails = extractor.process_single_url(url)
                all_emails.extend(emails)

            unique_emails = sorted(list(set(all_emails)))

            if args.output:
                save_emails_to_file(unique_emails, args.output)
            else:
                for email in unique_emails:
                    print(email)

            print(f"\nОбработка завершена. Всего найдено {len(unique_emails)} уникальных email-адресов")
            return

        # Обработка одиночного URL
        if args.url:
            emails = extractor.process_single_url(args.url)

            if args.output:
                save_emails_to_file(emails, args.output)
            else:
                for email in emails:
                    print(email)

            print(f"\nНайдено {len(emails)} email-адресов")
            return

        # Интерактивный режим
        url = input("Введите URL веб-страницы для анализа: ")
        if url:
            emails = extractor.process_single_url(url)
            for email in emails:
                print(email)
            print(f"\nНайдено {len(emails)} email-адресов")

    except KeyboardInterrupt:
        print("\n\nПрограмма прервана пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"Произошла ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
