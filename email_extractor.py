import argparse
import random
import re
import sys

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent


def extract_emails_from_text(text):
    """Извлекает email-адреса из текста с помощью регулярных выражений."""
    # Регулярное выражение для поиска email-адресов
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    return re.findall(email_pattern, text)


def get_random_user_agent():
    """Возвращает случайный User-Agent."""
    try:
        ua = UserAgent()
        return ua.random
    except ValueError:
        # Если библиотека не установлена или произошла ошибка, используем предопределенный список
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


def get_webpage_content(url):
    """Получает содержимое веб-страницы по указанному URL."""

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
    # Добавляем случайные заголовки для большей уникальности запроса
    if random.random() > 0.5:
        headers['Sec-Fetch-Dest'] = 'document'
        headers['Sec-Fetch-Mode'] = 'navigate'
        headers['Sec-Fetch-Site'] = 'cross-site'
        headers['Sec-Fetch-User'] = '?1'

    # Выполняем запрос
    response = requests.get(
        url,
        headers=headers,
        timeout=20
    )

    return response.text


def normalize_url(url):
    """Нормализует URL, добавляя протокол, если он отсутствует."""
    if not url.startswith(('http://', 'https://')):
        return 'https://' + url
    return url


def extract_emails_from_webpage(url):
    """Извлекает email-адреса с веб-страницы."""
    normalized_url = normalize_url(url)
    content = get_webpage_content(normalized_url)
    if not content:
        return []

    emails = []

    # Используем BeautifulSoup для парсинга HTML
    soup = BeautifulSoup(content, 'html.parser')

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

    # 2. Ищем email в тексте ссылок, которые содержат @ и выглядят как email
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
    email_classes = ['email', 'mail', 'e-mail', 'contact-email']
    for class_name in email_classes:
        for elem in soup.select(f'.{class_name}'):
            emails.extend(extract_emails_from_text(elem.get_text()))

    # Удаляем дубликаты и сортируем
    return sorted(list(set(emails)))


def read_urls_from_file(file_path):
    """Читает URL из файла, по одному URL на строку."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            # Удаляем пробелы и пустые строки
            urls = [line.strip() for line in f if line.strip()]
        return urls
    except IOError as e:
        print(f"Ошибка при чтении файла с URL: {e}")
        return []


def process_single_url(url):
    """Обрабатывает один URL и возвращает найденные email-адреса."""
    print("Анализ страницы", end=" ")
    emails = extract_emails_from_webpage(url)

    if not emails:
        print("Email-адреса не найдены.")
        return []

    print(f"Найдено {len(emails)} email-адресов")

    return emails


def saves_outfile(output_file, emails):
    ''' запись данных в файл output_file '''
    try:
        with open(output_file, 'a', encoding='utf-8') as f:
            for email in emails:
                f.write(email + '\n')
            print(f"Результаты сохранены в файл: {output_file}")
    except IOError as e:
        print(f"Ошибка при сохранении в файл: {e}")


def parser_argument():
    ''' Получение аргументов командной строки '''
    parser = argparse.ArgumentParser(
        description='Извлечение email-адресов с веб-страницы')
    parser.add_argument('url', nargs='?', help='URL веб-страницы для анализа')
    parser.add_argument(
        '-o', '--output', help='Файл для сохранения результатов')
    parser.add_argument('-f', '--file', help='Файл со списком URL для анализа')
    parser.add_argument('-d', '--delay', type=int, default=30,
                        help='Задержка между запросами в секундах (по умолчанию 30)')
    return parser.parse_args()

def main():

    args = parser_argument()

    # Обработка URL из файла
    if args.file:
        urls = read_urls_from_file(args.file)
        if not urls:
            print("Файл с URL пуст или не может быть прочитан.")
            return

        print(f"Загружено {len(urls)} URL из файла.")
        all_emails = []
        for i, url in enumerate(urls, 1):
            print(f"Обработка URL {i}/{len(urls)}: {url}", end=" ")
            emails = process_single_url(url)
            all_emails.extend(emails)
        # Удаляем дубликаты
        unique_emails = sorted(list(set(all_emails)))

    # Обработка одиночного URL
    else:
        # Если URL не указан, запрашиваем его у пользователя
        url = args.url
        if not url:
            url = input("Введите URL веб-страницы для анализа: ")

        unique_emails = sorted(list(set(process_single_url(url))))
    print(
        f"\nОбработка завершена. Всего найдено {len(unique_emails)} уникальных email-адресов.")
    if args.output:
        saves_outfile(args.output, unique_emails)
    else:
        for email in unique_emails:
            print(email)


if __name__ == "__main__":
    main()
