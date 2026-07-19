from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")],
        [InlineKeyboardButton(text="💸 Пополнить баланс", callback_data="topup")],
        [InlineKeyboardButton(text="⚙️ Настройки (Маршрутизация)", callback_data="settings")],
        [InlineKeyboardButton(text="❓ Поддержка", url="https://t.me/admin_tag")]
    ])

def topup_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Telegram Stars ⭐", callback_data="pay_stars")],
        [InlineKeyboardButton(text="CryptoBot (Крипта)", callback_data="pay_crypto")],
        [InlineKeyboardButton(text="Ввести промокод", callback_data="enter_promo")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
    ])

def settings_kb(split_tunneling: bool) -> InlineKeyboardMarkup:
    status = "ВКЛ (Только заблокированные)" if split_tunneling else "ВЫКЛ (Весь трафик)"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Маршрутизация РФ: {status}", callback_data="toggle_split")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
    ])
