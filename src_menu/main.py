import curses


class MenuItem:
    def __init__(self, text):
        self.text = text


def display_menu(stdscr, menu_items, selected_idx):
    stdscr.clear()
    for idx, item in enumerate(menu_items):
        if idx == selected_idx:
            stdscr.addstr(f"> {item.text}\n")
        else:
            stdscr.addstr(f"  {idx + 1}. {item.text}\n")
    stdscr.refresh()


def main(stdscr):
    # Настройка экрана
    curses.curs_set(0)
    stdscr.nodelay(False)

    # Создание пунктов меню верхнего уровня
    top_level_menu = [
        MenuItem("Главная"),
        MenuItem("Настройки"),
        MenuItem("Справка"),
        MenuItem("Выход"),
    ]

    # Подменю настроек
    settings_submenu = [
        MenuItem("Цветовая схема"),
        MenuItem("Размер шрифта"),
        MenuItem("Назад"),
    ]

    current_menu = top_level_menu
    selected_idx = 0
    while True:
        display_menu(stdscr, current_menu, selected_idx)


        key = stdscr.getch()  # Получаем нажатую клавишу

        if key == ord("q") or (
            current_menu == top_level_menu
            and current_menu[selected_idx].text == "Выход"
            and key == 10 # curses.KEY_ENTER
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
            # Обработка выбора элемента меню
            choice_text = current_menu[selected_idx].text
            if choice_text == "Назад":
                current_menu = top_level_menu
                selected_idx = 0
            elif choice_text == "Настройки":
                current_menu = settings_submenu
                selected_idx = 0

        elif str(chr(key)).isdigit():
            digit = int(chr(key)) - 1
            if 0 <= digit < len(current_menu):
                selected_idx = digit


curses.wrapper(main)


----------------------
# Добавьте эти константы в начало файла после импорта.
MENU_BACK = "Назад"
MENU_SETTINGS = "Настройки"
MENU_MAIN = "Главная"
MENU_HELP = "Справка"
MENU_EXIT = "Выход"

# При необходимости обновите класс MenuItem (необязательное улучшение).
class MenuItem:
    def __init__(self, text, action=None):
        self.text = text
        self.action = action

# Создайте функцию для обработки выбора меню.
def handle_menu_choice(choice_text, current_menu, selected_idx, top_level_menu, settings_submenu):
    """
    Обработка выбора пункта меню.
    
    Args:
        choice_text (str): Текст выбранного пункта меню
        current_menu (list): Текущий список меню
        selected_idx (int): Текущий выбранный индекс
        top_level_menu (list): Ссылка на меню верхнего уровня
        settings_submenu (list): Ссылка на подменю настроек
    
    Returns:
        tuple: (new_current_menu, new_selected_idx)
    """
    menu_actions = {
        MENU_BACK: lambda: (top_level_menu, 0),
        MENU_SETTINGS: lambda: (settings_submenu, 0),
        # При необходимости добавьте сюда дополнительные действия.
        # MENU_MAIN: lambda: (top_level_menu, 0),
        # MENU_HELP: lambda: (help_menu, 0),
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

# В основной функции замените блок if-elif на:
elif key == curses.KEY_ENTER or key in [10, 13]:
    choice_text = current_menu[selected_idx].text
    current_menu, selected_idx = handle_menu_choice(
        choice_text, current_menu, selected_idx, top_level_menu, settings_submenu
    )
