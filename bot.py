
import asyncio
import os

from aiogram import Bot, Dispatcher
from database import (
    init_db,
    save_application,
    get_applications,
    get_application_stats,
    update_application_status
)
from aiogram.filters import Command, CommandStart
from aiogram import F
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message,
    BotCommand,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from dotenv import load_dotenv

load_dotenv("D:/Programming/TelegramBots/bot1/.env")

TOKEN = os.getenv("BOT_TOKEN")

admin_id_text = os.getenv("ADMIN_ID")
print("ADMIN_ID найден:", admin_id_text is not None)
print("BOT_TOKEN найден:", TOKEN is not None)

if admin_id_text is None:
    raise ValueError("Не найден ADMIN_ID в файле .env")

ADMIN_ID = int(admin_id_text)

if not TOKEN:
    raise ValueError("Не найден токен бота в файле .env")

bot = Bot(token=TOKEN)
dp = Dispatcher()

class ApplicationForm(StatesGroup):
    waiting_for_name = State()
    waiting_for_problem = State()



from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# Клавиатура для клиентов
user_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Услуги"),
            KeyboardButton(text="Цены"),
        ],
        [
            KeyboardButton(text="Оставить заявку"),
            KeyboardButton(text="Помощь"),
        ],
    ],
    resize_keyboard=True,
)

# Клавиатура для администратора
admin_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Услуги"),
            KeyboardButton(text="Цены"),
        ],
        [
            KeyboardButton(text="Оставить заявку"),
            KeyboardButton(text="Помощь"),
        ],
        [
            KeyboardButton(text="📊 Статистика"),
            KeyboardButton(text="📋 Заявки"),
        ],
    ],
    resize_keyboard=True,
)



@dp.message(F.text == "Оставить заявку")
async def start_application(message: Message, state: FSMContext):
    await state.set_state(ApplicationForm.waiting_for_name)

    cancel_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True
    )

    await message.answer(
        "Здравствуйте! Как вас зовут?\n\n"
        "Если передумали оставлять заявку, нажмите «❌ Отмена».",
        reply_markup=cancel_keyboard
    )



@dp.message(F.text == "❌ Отмена")
async def cancel_application(message: Message, state: FSMContext):
    await state.clear()

    await message.answer(
        "Заполнение заявки отменено. Вы вернулись в главное меню.",
        reply_markup=admin_keyboard if message.from_user.id == ADMIN_ID else user_keyboard
    )



@dp.message(ApplicationForm.waiting_for_name)
async def get_name(message: Message, state: FSMContext):
    name = (message.text or "").strip()

    if not name:
        await message.answer(
            "Пожалуйста, напишите своё имя."
        )
        return

    if len(name) < 2:
        await message.answer(
            "Имя слишком короткое. Напишите имя ещё раз."
        )
        return

    if len(name) > 50:
        await message.answer(
            "Имя слишком длинное. Напишите имя покороче."
        )
        return

    await state.update_data(name=name)
    await state.set_state(ApplicationForm.waiting_for_problem)

    cancel_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True
    )

    await message.answer(
        f"Приятно познакомиться, {name}!\n"
        "Теперь опишите, какая услуга вам нужна.\n\n"
        "Если передумали, нажмите «❌ Отмена».",
        reply_markup=cancel_keyboard
    )




@dp.message(ApplicationForm.waiting_for_problem)
async def get_problem(message: Message, state: FSMContext):
    data = await state.get_data()

    name = data["name"]
    problem = (message.text or "").strip()

    if not problem:
        await message.answer(
            "Описание не может быть пустым. "
            "Напишите, какая услуга вам нужна."
        )
        return

    if len(problem) < 5:
        await message.answer(
            "Опишите задачу чуть подробнее — "
            "минимум 5 символов."
        )
        return

    if len(problem) > 1000:
        await message.answer(
            "Описание слишком длинное. "
            "Пожалуйста, сократите его до 1000 символов."
        )
        return

    save_application(
        name=name,
        problem=problem,
        user_id=message.from_user.id,
    )

    await state.clear()

    await message.answer(
        f"Спасибо, {name}! Ваша заявка принята.\n"
        f"Описание: {problem}",
        reply_markup=admin_keyboard if message.from_user.id == ADMIN_ID else user_keyboard
    )

    try:
        await message.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                "📩 Новая заявка!\n\n"
                f"👤 Имя: {name}\n"
                f"📝 Услуга: {problem}\n"
                f"🆔 Telegram ID клиента: {message.from_user.id}"
            )
        )
    except Exception as error:
        print(f"Не удалось отправить уведомление администратору: {error}")



@dp.message(Command("help"))
async def help_handler(message: Message):
    await message.answer(
        "Вот что я умею:\n"
        "/start — запустить бота\n"
        "/help — показать помощь"
    )




@dp.message(CommandStart())
async def start_handler(message: Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer(
            "Добро пожаловать, администратор! Выберите действие:",
            reply_markup=admin_keyboard,
        )
    else:
        await message.answer(
            "Добро пожаловать! Выберите нужный раздел:",
            reply_markup=user_keyboard,
        )



@dp.message(Command("applications"))
async def show_applications(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("У тебя нет доступа к этой команде.")
        return

    applications = get_applications()

    if not applications:
        await message.answer("Пока заявок нет.")
        return

    for application in applications:
        text = (
            f"Заявка №{application['id']}\n"
            f"Статус: {application['status']}\n"
            f"Имя: {application['name']}\n"
            f"Проблема: {application['problem']}\n"
            f"Telegram ID: {application['user_id']}\n"
            f"Дата: {application['created_at']}"
        )

        await message.answer(text)




@dp.message(Command("stats"))
async def stats_handler(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("У тебя нет доступа к этой команде.")
        return

    stats = get_application_stats()

    await message.answer(
        "📊 Статистика заявок\n\n"
        f"📩 Всего заявок: {stats['total']}\n"
        f"👥 Клиентов, отправивших заявки: "
        f"{stats['unique_users']}"
    )



@dp.message(F.text == "📊 Статистика")
async def stats_button(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    stats = get_application_stats()

    await message.answer(
        "📊 Статистика заявок\n\n"
        f"📩 Всего заявок: {stats['total']}\n"
        f"👥 Клиентов: {stats['unique_users']}"
    )


@dp.message(F.text == "📋 Заявки")
async def applications_button(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("У тебя нет доступа к этой функции.")
        return

    applications = get_applications()

    if not applications:
        await message.answer("Пока заявок нет.")
        return

    for application in applications:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🟡 В работе",
                        callback_data=f"status:{application['id']}:В работе",
                    ),
                    InlineKeyboardButton(
                        text="🟢 Выполнена",
                        callback_data=f"status:{application['id']}:Выполнена",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text="🔴 Отклонена",
                        callback_data=f"status:{application['id']}:Отклонена",
                    ),
                ],
            ]
        )

        text = (
            f"Заявка №{application['id']}\n"
            f"Статус: {application['status']}\n"
            f"Имя: {application['name']}\n"
            f"Проблема: {application['problem']}\n"
            f"Telegram ID: {application['user_id']}\n"
            f"Дата: {application['created_at']}"
        )

        await message.answer(text, reply_markup=keyboard)


@dp.callback_query(F.data.startswith("status:"))
async def change_application_status(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа.", show_alert=True)
        return

    try:
        _, application_id, status = callback.data.split(":", 2)
        application_id = int(application_id)

        update_application_status(application_id, status)

        applications = get_applications()
        application = next(
            (item for item in applications if item["id"] == application_id),
            None,
        )

        if application is None:
            await callback.answer("Заявка не найдена.", show_alert=True)
            return

        text = (
            f"Заявка №{application['id']}\n"
            f"Статус: {application['status']}\n"
            f"Имя: {application['name']}\n"
            f"Проблема: {application['problem']}\n"
            f"Telegram ID: {application['user_id']}\n"
            f"Дата: {application['created_at']}"
        )

        await callback.message.edit_text(
            text,
            reply_markup=callback.message.reply_markup,
        )
        await callback.answer("Статус обновлён!")

    except (ValueError, TypeError):
        await callback.answer("Не удалось изменить статус.", show_alert=True)



@dp.message(F.text == "Помощь")
async def help_button(message: Message):
    await message.answer(
        "ℹ️ Как пользоваться ботом\n\n"
        "1. Нажмите «Оставить заявку».\n"
        "2. Введите своё имя.\n"
        "3. Опишите, какая услуга вам нужна.\n"
        "4. Дождитесь подтверждения приёма заявки.\n\n"
        "Если передумали, нажмите «❌ Отмена».\n\n"
        "Кнопки «Услуги» и «Цены» помогут узнать подробности."
    )



@dp.message(F.text == "Услуги")
async def services_button(message: Message):
    await message.answer(
        "Наши услуги:\n"
        "💻 Ремонт компьютеров\n"
        "🛠 Настройка Windows\n"
        "⚙️ Установка программ"
    )


@dp.message(F.text == "Цены")
async def prices_button(message: Message):
    await message.answer(
        "Наши цены:\n"
        "💻 Ремонт компьютера — от 1000 ₽\n"
        "🛠 Настройка Windows — от 700 ₽\n"
        "⚙️ Установка программ — от 300 ₽"
    )



@dp.message()
async def echo_handler(message: Message):
    if not message.text:
        return

    text = message.text.lower().strip()

    if text == "привет":
        await message.answer("Привет! Рад тебя видеть!")

    elif text == "как дела":
        await message.answer("Отлично! Я работаю и учусь")

    elif text == "цена":
        await message.answer("Мои услуги пока бесплатны!")

    elif text == "кто ты":
        await message.answer("Я Telegram-бот, созданный на Python!")

    else:
        await message.answer(
            "Не совсем понял ваш запрос. "
            "Пожалуйста, выберите действие в меню."
        )




async def main():
    init_db()

    await bot.set_my_commands([
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="help", description="Показать помощь"),
        BotCommand(command="applications", description="Посмотреть заявки"),
        BotCommand(command="stats", description="Статистика заявок"),
    ])

    print("Бот запускается...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

