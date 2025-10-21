# 🚀 Руководство по использованию Email Extractor

## 📋 Быстрый старт

### 1. Установка зависимостей

```bash
# Установка через uv (рекомендуется)
uv pip install -r requirements.txt

# Или через pip
pip install -r requirements.txt
```

### 2. Первый запуск

```bash
# Простой запуск одной страницы
uv run python run.py example.com

# Или через модуль
uv run python -m src.email_extractor example.com
```

## 🎯 Основные команды

### Обработка одной страницы

```bash
# Базовое извлечение
uv run python run.py https://example.com

# С сохранением в файл
uv run python run.py https://example.com -o results.txt
```

### Обработка файла с URL

```bash
# Обработка CSV файла
uv run python run.py -f data/input/urls/monitor.csv

# С сохранением результатов
uv run python run.py -f data/input/urls/monitor.csv -o monitor_emails.txt
```

### Обработка по категориям

```bash
# Обработка конкретной категории
uv run python run.py --category monitor

# Обработка всех категорий
uv run python run.py --all-categories
```

### Просмотр статистики

```bash
# Показать статистику извлечения
uv run python run.py --stats
```

## 📊 Работа с базой данных

### Просмотр всех email-адресов

```python
from src.database import EmailDatabase

db = EmailDatabase()
emails = db.get_all_emails()

for email_info in emails:
    print(f"Email: {email_info['email']}")
    print(f"Компания: {email_info['company_name']}")
    print(f"URL: {email_info['url']}")
    print(f"Дата: {email_info['extracted_at']}")
    print("-" * 40)
```

### Статистика по категориям

```python
from src.database import EmailDatabase

db = EmailDatabase()
stats = db.get_extraction_stats()

for stat in stats:
    print(f"Категория: {stat['category']}")
    print(f"URL обработано: {stat['total_urls']}")
    print(f"Успешных извлечений: {stat['successful_extractions']}")
    print(f"Email найдено: {stat['total_emails_found']}")
    print(f"Время выполнения: {stat['duration_seconds']:.1f} секунд")
    print("-" * 50)
```

## ⚙️ Настройка конфигурации

### Основные параметры (config/config.yaml)

```yaml
extraction:
  delay_between_requests: 30  # Задержка между запросами (сек)
  max_retries: 3              # Количество повторных попыток
  timeout: 20                 # Таймаут запроса (сек)
  use_proxies: false          # Использовать прокси

database:
  path: "data/database/emails.db"
  backup_enabled: true

logging:
  level: "INFO"               # DEBUG, INFO, WARNING, ERROR
  file: "data/output/logs/email_extractor.log"
```

### Категории товаров (config/categories.yaml)

```yaml
categories:
  monitor:
    name: "Мониторы и дисплеи"
    keywords: ["монитор", "дисплей", "экран"]
    urls_file: "monitor.csv"
```

## 📁 Структура файлов

```
Sales/
├── src/                          # Исходный код
│   ├── email_extractor.py        # Основной модуль
│   ├── database.py               # Работа с БД
│   └── utils.py                  # Утилиты
├── data/                         # Данные
│   ├── input/urls/               # CSV файлы с URL
│   ├── output/emails/            # Результаты извлечения
│   ├── output/logs/              # Файлы логов
│   └── database/                 # База данных SQLite
├── config/                       # Конфигурация
├── tests/                        # Тесты
├── requirements.txt              # Зависимости
└── run.py                       # Скрипт запуска
```

## 🔧 Расширенные возможности

### Использование прокси

1. Создайте файл `data/input/proxies.txt`:
```
http://proxy1:port
http://proxy2:port
```

2. Включите прокси в конфигурации:
```yaml
extraction:
  use_proxies: true
```

### Настройка логирования

```python
from src.utils import setup_logging

# Настройка детального логирования
logger = setup_logging("DEBUG", "custom.log")
```

### Очистка старых данных

```python
from src.database import EmailDatabase

db = EmailDatabase()
# Удалить данные старше 30 дней
deleted_count = db.cleanup_old_data(30)
print(f"Удалено {deleted_count} записей")
```

### Создание резервной копии

```python
from src.database import EmailDatabase

db = EmailDatabase()
success = db.backup_database("backup_emails.db")
if success:
    print("Резервная копия создана успешно")
```

## 🧪 Тестирование

### Запуск тестов

```bash
# Все тесты
pytest tests/

# Конкретный тест
pytest tests/test_extractor.py::TestEmailValidation::test_valid_emails

# С покрытием кода
pytest --cov=src tests/
```

### Тестирование валидации email

```python
from src.utils import is_valid_email, validate_emails

# Проверка одного email
print(is_valid_email("test@example.com"))  # True
print(is_valid_email("invalid-email"))     # False

# Фильтрация списка
emails = ["valid@example.com", "invalid-email", "another@test.org"]
valid_emails = validate_emails(emails)
print(valid_emails)  # ['valid@example.com', 'another@test.org']
```

## 📈 Мониторинг и отладка

### Просмотр логов

```bash
# Просмотр последних записей
tail -f data/output/logs/email_extractor.log

# Поиск ошибок
grep "ERROR" data/output/logs/email_extractor.log
```

### Отладка проблем

1. **Проверьте логи** в `data/output/logs/`
2. **Убедитесь в доступности интернета**
3. **Проверьте корректность URL** в CSV файлах
4. **Запустите тесты** для диагностики

### Оптимизация производительности

1. **Увеличьте задержку** между запросами (30-60 сек)
2. **Используйте SSD** для базы данных
3. **Настройте регулярную очистку** старых данных
4. **Создавайте резервные копии** базы данных

## 🚨 Решение проблем

### Частые ошибки

1. **"Модуль не найден"**
   ```bash
   # Убедитесь, что находитесь в корневой директории проекта
   cd C:\Users\Admin\Documents\PYTHON\Sales
   python run.py
   ```

2. **"База данных заблокирована"**
   ```bash
   # Закройте все программы, использующие базу данных
   # Перезапустите программу
   ```

3. **"Ошибка подключения"**
   ```bash
   # Проверьте интернет-соединение
   # Увеличьте timeout в конфигурации
   ```

### Получение помощи

1. Проверьте логи в `data/output/logs/`
2. Запустите тесты: `pytest tests/`
3. Проверьте конфигурацию в `config/config.yaml`
4. Убедитесь в корректности URL в CSV файлах

## 📞 Поддержка

При возникновении проблем:

1. **Проверьте логи** в `data/output/logs/email_extractor.log`
2. **Запустите тесты** для диагностики
3. **Проверьте конфигурацию** в `config/config.yaml`
4. **Убедитесь в доступности** интернет-соединения

---

**Версия**: 1.0.0  
**Автор**: Admin  
**Дата**: 2024
