from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_instructions_menu_keyboard() -> InlineKeyboardMarkup:
    """Return the instructions menu keyboard aligned with callback handlers."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📱 Android", callback_data="instr_android"),
                InlineKeyboardButton(text="📱 iOS", callback_data="instr_ios"),
            ],
            [
                InlineKeyboardButton(text="💻 Windows", callback_data="instr_windows"),
                InlineKeyboardButton(text="🍏 macOS", callback_data="instr_macos"),
            ],
            [
                InlineKeyboardButton(text="🐧 Linux", callback_data="instr_linux"),
                InlineKeyboardButton(text="🖥️ Desktop", callback_data="instr_desktop"),
            ],
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main"),
            ],
        ]
    )
    return keyboard
