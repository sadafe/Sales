import curses

from loguru import logger

import utils_data
import utils_email
import utils_ktru

# Инициализация экрана


def init_screen():
    global stdscr
    stdscr = curses.initscr()
    curses.noecho()
    curses.cbreak()
    stdscr.keypad(True)
    stdscr.nodelay(False)
    stdscr.leaveok(True)


def cleanup():
    global stdscr
    stdscr.keypad(False)
    curses.echo()
    curses.nocbreak()
    curses.endwin()


def display_menu(menu_items, selected_idx):
    """Отображает меню с заданными пунктами"""
    stdscr.clear()
    for idx, item in enumerate(menu_items):
        if idx == selected_idx:
            stdscr.addstr(f"> {item}\n")
        else:
            stdscr.addstr(f"  {idx + 1}. {item}\n")
    stdscr.refresh()


def select_from_menu(menu_items, callback_map: dict, selected_idx: int = 0):
    """
    Универсальная функция для выбора пункта меню.
    Параметры:
      - menu_items: список строк-пунктов меню
      - callback_map: словарь, ключ которого — номер выбранного пункта,
                     значение — соответствующая функция-обработчик
    """

    while True:
        display_menu(menu_items, selected_idx)
        key = stdscr.getch()
        if key in [113, 81, 1081, 1049]:
            exit_menu()

        if key == 259:
            selected_idx -= 1
            if selected_idx < 0:
                selected_idx = len(menu_items) - 1

        if key == 258:
            selected_idx += 1
            if selected_idx >= len(menu_items):
                selected_idx = 0

        if key == curses.KEY_ENTER or key in [10, 13, 459]:
            key = selected_idx + 49

        try:
            selected_item_idx = int(chr(key)) - 1

            if 0 <= selected_item_idx < len(menu_items):
                action = callback_map.get(selected_item_idx)

                if callable(action):
                    action()
                else:
                    return False  # Выходим из текущего меню
        except ValueError:
            continue  # игнорируем некорректные нажатия


def main_menu():
    menu_items = [
        "Выгрузка характеристик из КТРУ",
        "Поиск ОКПД2 по КТРУ",
        "Поиск производителей по ОКПД2 и(или) наименованию",
        "Поиск Email по производителю",
        "Помощь",
        "Выход",
    ]
    callback_map = {
        0: ktru_menu,
        1: okpd_ktru,
        2: okpd_menu,
        3: email_menu,
        4: help_menu,
        5: exit_menu,
    }
    select_from_menu(menu_items, callback_map, 0)


def help_menu():
    menu_items = ["О программе", "Горячие клавиши", "Назад"]
    callback_map = {
        0: about,
        1: hot_button,
        2: main_menu,  # Возвращаемся на верхний уровень
    }
    select_from_menu(menu_items, callback_map, 0)


def ktru_menu():
    curses.endwin()  # Завершаем curses перед запуском другой программы
    try:
        logger.debug("Запускаем модуль КТРУ ")
        utils_ktru.processor()
        logger.debug("Модуль КТРУ успешно завершен")
    except Exception as e:
        logger.error(f"Ошибка запуска программы КТРУ: {e}")
        print(f"Ошибка запуска программы: {e}")


def okpd_menu():
    curses.endwin()  # Завершаем curses перед запуском другой программы
    try:
        logger.debug("Запускаем модуль ОКПД ")
        utils_data.processor()
        logger.debug("Модуль ОКПД успешно завершен")
    except Exception as e:
        logger.error(f"Ошибка запуска программы ОКПД: {e}")
        print(f"Ошибка запуска программы: {e}")


def okpd_ktru():
    curses.endwin()  # Завершаем curses перед запуском другой программы
    try:
        logger.debug("Запускаем модуль поиска ОКПД2 ")
        utils_ktru.processor_okpd()
        logger.debug("Модуль поиска ОКПД успешно завершен")
    except Exception as e:
        logger.error(f"Ошибка запуска программы поиска ОКПД: {e}")
        print(f"Ошибка запуска программы: {e}")


def email_menu():
    curses.endwin()  # Завершаем curses перед запуском другой программы
    try:
        logger.debug("Запускаем модуль поиска emails ")
        utils_email.process()
        logger.debug("Модуль поиска emails успешно завершен")
    except Exception as e:
        logger.error(f"Ошибка запуска программы поиска emails: {e}")
        print(f"Ошибка запуска программы: {e}")


def about():
    stdscr.clear()
    stdscr.addstr(
        "Это приложение для обработки продаж и извлечения email.\n\nНажмите любую клавишу для возврата в меню."
    )
    stdscr.refresh()
    stdscr.getch()
    stdscr.clear()


def hot_button():
    stdscr.clear()
    stdscr.addstr("Горячие клавиши:\n")
    stdscr.addstr("- Стрелки вверх/вниз: навигация по меню\n")
    stdscr.addstr("- Enter: выбор пункта\n")
    stdscr.addstr("- Цифры 1-9: быстрый выбор пункта\n")
    stdscr.addstr(
        "- Q: выход из приложения\n\nНажмите любую клавишу для возврата в меню."
    )
    stdscr.refresh()
    stdscr.getch()


def exit_menu():
    cleanup()
    exit()


def main(stdscr):
    try:
        init_screen()
        main_menu()
    finally:
        cleanup()
