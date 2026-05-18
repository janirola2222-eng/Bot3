import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command

# Вставьте сюда токен вашего бота
BOT_TOKEN = "8751547209:AAENcfFd0kbGWzrNlr2fgyRFl33O6JGOoCw"

# ID администратора (чтобы только вы могли добавлять работы)
ADMIN_ID = 5934814012 

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# 1. Определяем состояния (шаги заполнения карточки)
class PortfolioForm(StatesGroup):
    waiting_for_photo = State()
    waiting_for_title = State()
    waiting_for_desc = State()
    waiting_for_price = State()

# Клавиатура для пропуска ввода цены
skip_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Пропустить")]], 
    resize_keyboard=True
)

# 2. Команда запуска добавления работы (доступна только админу)
@dp.message(Command("add_portfolio"))
async def start_adding_portfolio(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("У вас нет прав для этого действия.")
    
    await message.answer("Отправьте фото для новой работы в портфолио (в сжатом виде):", reply_markup=ReplyKeyboardRemove())
    await state.set_state(PortfolioForm.waiting_for_photo)

# 3. Ловим фото
@dp.message(PortfolioForm.waiting_for_photo, F.photo)
async def process_photo(message: Message, state: FSMContext):
    # Берем фото лучшего качества (последнее в массиве)
    photo_id = message.photo[-1].file_id
    await state.update_data(photo_id=photo_id)
    
    await message.answer("Отлично. Теперь введите название работы (например: Ребрендинг FinTech):")
    await state.set_state(PortfolioForm.waiting_for_title)

# 4. Ловим название
@dp.message(PortfolioForm.waiting_for_title, F.text)
async def process_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    
    await message.answer("Введите краткое описание:")
    await state.set_state(PortfolioForm.waiting_for_desc)

# 5. Ловим описание
@dp.message(PortfolioForm.waiting_for_desc, F.text)
async def process_desc(message: Message, state: FSMContext):
    await state.update_data(desc=message.text)
    
    await message.answer("Введите цену (например: $1200) или нажмите 'Пропустить':", reply_markup=skip_kb)
    await state.set_state(PortfolioForm.waiting_for_price)

# 6. Ловим цену и сохраняем данные
@dp.message(PortfolioForm.waiting_for_price, F.text)
async def process_price(message: Message, state: FSMContext):
    user_data = await state.get_data()
    
    price = message.text if message.text != "Пропустить" else "По запросу"
    
    # Здесь данные подготовлены к отправке в базу (Supabase, Firebase или API вашего сайта)
    # Пример структуры, которая пойдет в базу:
    portfolio_item = {
        "photo_id": user_data['photo_id'], # В реальном проекте тут нужно получить ссылку на файл через bot.get_file
        "title": user_data['title'],
        "description": user_data['desc'],
        "price": price
    }
    
    # Имитация сохранения в базу данных
    # await send_to_supabase(portfolio_item)
    
    # Отправляем превью админу
    await message.answer_photo(
        photo=user_data['photo_id'],
        caption=f"✅ Работа успешно добавлена на сайт!\n\n"
                f"<b>{user_data['title']}</b>\n"
                f"{user_data['desc']}\n"
                f"Цена: {price}",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove()
    )
    
    # Завершаем машину состояний
    await state.clear()

async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())