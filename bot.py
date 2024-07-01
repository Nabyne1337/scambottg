import logging
import asyncio
import aiosqlite
from aiogram import Bot, Dispatcher, types, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup
from settings import API_TOKEN, file_path, products, PRODUCTS_PER_PAGE, profs
import time

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
router = Router()

# Словарь для хранения идентификаторов сообщений
user_messages = {}

async def init_db():
    async with aiosqlite.connect('mybd.db') as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id INTEGER NOT NULL UNIQUE,
                fullname TEXT,
                username TEXT,
                proffesion TEXT DEFAULT 'Нету',
                balance INTEGER DEFAULT 0,
                country TEXT,
                city TEXT,
                start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        await db.commit()

async def update_user(tg_id, username, fullname, country=None, city=None, proffesion='нету'):
    async with aiosqlite.connect('mybd.db') as db:
        async with db.execute('SELECT * FROM users WHERE tg_id = ?', (tg_id,)) as cursor:
            existing_user = await cursor.fetchone()
            if existing_user:
                await db.execute('''
                    UPDATE users
                    SET username = ?, fullname = ?, country = ?, city = ?, proffesion = ?
                    WHERE tg_id = ?
                ''', (username, fullname, country, city, proffesion, tg_id))
            else:
                await db.execute('''
                    INSERT INTO users (tg_id, username, fullname, country, city, balance, proffesion)
                    VALUES (?, ?, ?, ?, ?, 0, ?)
                ''', (tg_id, username, fullname, country, city, proffesion))
        await db.commit()

async def delete_previous_message(user_id):
    if user_id in user_messages:
        try:
            await bot.delete_message(chat_id=user_id, message_id=user_messages[user_id])
        except Exception as e:
            logging.exception(f"Не удалось удалить сообщение: {e}")

@router.message(Command("start"))
async def send_welcome(message: Message):
    try:
        tg_id = message.from_user.id
        username = message.from_user.username
        fullname = message.from_user.full_name
        await update_user(tg_id, username, fullname)

        await delete_previous_message(tg_id)

        welcome_text = "Привет! Это RentexShop. Выберите один из вариантов ниже:"
        buttons = [
            [InlineKeyboardButton(text="Личный кабинет", callback_data="button1")],
            [InlineKeyboardButton(text="Информация", callback_data="button2")],
            [InlineKeyboardButton(text="Покупка", callback_data="button3")],
            [InlineKeyboardButton(text="Вакансии", callback_data="button5")]
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        sent_message = await message.answer_photo(photo=types.FSInputFile(path=file_path), caption=welcome_text, reply_markup=keyboard)

        # Сохраняем идентификатор сообщения
        user_messages[tg_id] = sent_message.message_id

    except Exception as e:
        logging.exception("Ошибка при отправке приветственного сообщения:")
        await message.answer(f"Произошла ошибка при отправке приветственного сообщения: {e}")

@router.callback_query()
async def process_callback(callback_query: CallbackQuery):
    try:
        await delete_previous_message(callback_query.from_user.id)
        tg_id = callback_query.from_user.id

        if callback_query.data == "button1":
            async with aiosqlite.connect('mybd.db') as db:
                async with db.execute("SELECT fullname, proffesion, balance FROM users WHERE tg_id = ?", (tg_id,)) as cursor:
                    user_data = await cursor.fetchone()
                    if user_data:
                        buttons = [
                            [InlineKeyboardButton(text="Пополнить баланс", callback_data="button4")],
                            [InlineKeyboardButton(text="Информация", callback_data="button2")],
                            [InlineKeyboardButton(text="Покупка", callback_data="button3")],
                            [InlineKeyboardButton(text="Назад", callback_data="back_to_menu")]
                        ]
                        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
                        fullname, proffesion, balance = user_data
                        sent_message = await callback_query.message.answer(f"Привет, {fullname}!\nВаш личный профиль:\nВакансия: {proffesion}\nВаш баланс: {balance} руб.", reply_markup=keyboard)
                        user_messages[tg_id] = sent_message.message_id
                    else:
                        sent_message = await callback_query.message.answer("Произошла ошибка: пользователь не найден в базе данных.")
                        user_messages[tg_id] = sent_message.message_id
        elif callback_query.data == "button2":
            buttons = [
                [InlineKeyboardButton(text="Личный кабинет", callback_data="button1")],
                [InlineKeyboardButton(text="Вакансии", callback_data="button5")],
                [InlineKeyboardButton(text="Покупка", callback_data="button3")],
                [InlineKeyboardButton(text="Назад", callback_data="back_to_menu")]
            ]
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
            sent_message = await callback_query.message.answer("Информация. ❤", reply_markup=keyboard)
            user_messages[tg_id] = sent_message.message_id
        elif callback_query.data == "button3":
            buttons = []
            for product_name, product_price in products.items():
                buttons.append([InlineKeyboardButton(text=f"{product_name} - {product_price} руб.", callback_data=f"product_{product_name}")])
            # Добавляем кнопку "назад"
            buttons.append([InlineKeyboardButton(text="Назад", callback_data="back_to_menu")])
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
            sent_message = await callback_query.message.answer("Выберите товар из списка:", reply_markup=keyboard)
            user_messages[tg_id] = sent_message.message_id
        elif callback_query.data == "button4":
            buttons = [[InlineKeyboardButton(text="Проверить оплату ✅", callback_data="buttonoplata2")],
            [InlineKeyboardButton(text="Назад", callback_data="back_to_menu")]]
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

            sent_message = await callback_query.message.answer(
                                f"Для пополнения баланса переведите нужную сумму на кошелёк: \n"f"TRe2UJZCYCZYxmkUx1VRvxwr3cvq6B7RfU",disable_notification=True,
                                reply_markup=keyboard
                            )
        elif callback_query.data == "button5":
            vacancies_text = "\n\n".join([f"{profs_name} - {profs_price} руб." for profs_name, profs_price in profs.items()])
            contact_text = "Для связи с менеджером по трудоустройству пишите сюда (@ВРЕМЕННОНЕТУ)"

            message_text = f"Вакансии:\n\n{vacancies_text}\n\n{contact_text}"
            
            buttons = [[InlineKeyboardButton(text="Назад", callback_data="back_to_menu")]]
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

            sent_message = await callback_query.message.answer(message_text, reply_markup=keyboard)
        elif callback_query.data == "back_to_menu":
            buttons = [
                [InlineKeyboardButton(text="Личный кабинет", callback_data="button1")],
                [InlineKeyboardButton(text="Информация", callback_data="button2")],
                [InlineKeyboardButton(text="Покупка", callback_data="button3")],
                [InlineKeyboardButton(text="Вакансии", callback_data="button5")]
            ]
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
            welcome_text = "Привет! Это RentexShop. Выберите один из вариантов ниже:"
            sent_message = await callback_query.message.answer_photo(photo=types.FSInputFile(path=file_path), caption=welcome_text, reply_markup=keyboard)
            user_messages[tg_id] = sent_message.message_id

        elif callback_query.data.startswith("product_"):
            product_name = callback_query.data.split("_")[1]
            product_price = products.get(product_name)
            if product_price:
                buttons = [
                    [InlineKeyboardButton(text="Личный кабинет", callback_data="button1")],
                    [InlineKeyboardButton(text="Информация", callback_data="button2")],
                    [InlineKeyboardButton(text="Покупка", callback_data="button3")],
                    [InlineKeyboardButton(text="Вакансии", callback_data="button5")],
                    [InlineKeyboardButton(text="Назад", callback_data="back_to_menu")]
                ]
                keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
                sent_message = await callback_query.message.answer(f"Вы выбрали {product_name}. Цена: {product_price} руб.", reply_markup=keyboard)
                user_messages[tg_id] = sent_message.message_id
            else:
                sent_message = await callback_query.message.answer("Товар не найден.")
                user_messages[tg_id] = sent_message.message_id

        await callback_query.answer()

    except Exception as e:
        logging.exception("Ошибка при обработке нажатия кнопки:")
        await callback_query.message.answer(f"Произошла ошибка при обработке нажатия кнопки: {e}")

async def main():
    await init_db()
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
