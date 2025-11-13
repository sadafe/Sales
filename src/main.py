import curses

import utils_ktru

MENU_BACK = "Назад"
MENU_MAIN = "Главная"
MENU_HELP = "Справка"
MENU_EXIT = "Выход"


class MenuItem:
    def __init__(self, text, action=None):
        self.text = text
        self.action = action


def display_menu(stdscr, menu_items, selected_idx):
    stdscr.clear()
    for idx, item in enumerate(menu_items):
        if idx == selected_idx:
            stdscr.addstr(f"> {item.text}\n")
        else:
            stdscr.addstr(f"  {idx + 1}. {item.text}\n")
    stdscr.refresh()


def handle_menu_choice(
    stdscr, choice_text, current_menu, selected_idx, top_level_menu, help_submenu
):
    """
    Обработка выбора пункта меню.

    Args:
        stdscr: Объект curses экрана
        choice_text (str): Текст выбранного пункта меню
        current_menu (list): Текущий список меню
        selected_idx (int): Текущий выбранный индекс
        top_level_menu (list): Ссылка на меню верхнего уровня
        help_submenu (list): Ссылка на подменю справки

    Returns:
        tuple: (new_current_menu, new_selected_idx)
    """
    if choice_text == "Запрос КТРУ":
        # Запуск программы src/utils_data.py
        curses.endwin()  # Завершаем curses перед запуском другой программы
        try:
            utils_ktru.processor()
        except Exception as e:
            print(f"Ошибка запуска программы: {e}")
        # После завершения программы возвращаемся в меню
        return top_level_menu, 0
    elif choice_text == "Справка":
        return help_submenu, 0
    elif choice_text == "О программе":
        stdscr.clear()
        stdscr.addstr(
            "Это приложение для обработки продаж и извлечения email.\n\nНажмите любую клавишу для возврата в меню."
        )
        stdscr.refresh()
        stdscr.getch()
        return help_submenu, 0
    elif choice_text == "Горячие клавиши":
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
        return help_submenu, 0

    menu_actions = {
        MENU_BACK: lambda: (top_level_menu, 0),
        # При необходимости добавьте сюда дополнительные действия.
        # MENU_MAIN: lambda: (top_level_menu, 0),
    }

    action = menu_actions.get(choice_text)
    if action:
        try:
            return action()
        except (AttributeError, TypeError) as e:
            # Log error or handle gracefully
            print(f"Error handling menu choice '{choice_text}': {e}")
            return current_menu, selected_idx
    else:
        # Handle unrecognized choices
        print(f"Unrecognized menu choice: {choice_text}")
        return current_menu, selected_idx


def main(stdscr):
    # Настройка экрана
    curses.curs_set(0)
    stdscr.nodelay(False)

    # Создание пунктов меню верхнего уровня
    top_level_menu = [
        MenuItem("Запрос КТРУ"),
        MenuItem("Справка"),
        MenuItem("Выход"),
    ]

    # Подменю справки
    help_submenu = [
        MenuItem("О программе"),
        MenuItem("Горячие клавиши"),
        MenuItem("Назад"),
    ]

    current_menu = top_level_menu
    selected_idx = 0
    while True:
        try:
            display_menu(stdscr, current_menu, selected_idx)

            key = stdscr.getch()  # Получаем нажатую клавишу

            if key == ord("q") or (
                current_menu == top_level_menu
                and current_menu[selected_idx].text == "Выход"
                and (key == curses.KEY_ENTER or key in [10, 13])
            ):
                break

            elif key == curses.KEY_UP:
                selected_idx -= 1
                if selected_idx < 0:
                    selected_idx = len(current_menu) - 1

            elif key == curses.KEY_DOWN:
                selected_idx += 1
                if selected_idx >= len(current_menu):
                    selected_idx = 0

            elif key == curses.KEY_ENTER or key in [10, 13]:
                choice_text = current_menu[selected_idx].text
                current_menu, selected_idx = handle_menu_choice(
                    stdscr,
                    choice_text,
                    current_menu,
                    selected_idx,
                    top_level_menu,
                    help_submenu,
                )

            elif str(chr(key)).isdigit():
                digit = int(chr(key)) - 1
                if 0 <= digit < len(current_menu):
                    selected_idx = digit
        except KeyboardInterrupt:
            break


curses.wrapper(main)
