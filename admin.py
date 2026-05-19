import logging
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import asyncio

# --- НАСТРОЙКИ ---
API_TOKEN = '8938811266:AAG9Is2ByWrivKIUY5Vvux2KfDOy-f9mNzQ'
GEMINI_KEY = 'AIzaSyDcLFdfaXSdFjjkQhTC5vN5y1W9yJ4hmxk'
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_KEY}"
ADMIN_ID = 5934814012 # Твой Telegram ID для доступа к админке

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

class AIGenerator(StatesGroup):
    waiting_for_query = State()
    context_type = State()

# --- ПРЯМОЙ ЗАПРОС К GEMINI ---
async def ask_gemini(prompt_text):
    payload = {"contents": [{"parts": [{"text": prompt_text}]}]}
    async with aiohttp.ClientSession() as session:
        async with session.post(GEMINI_URL, json=payload) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data['candidates'][0]['content']['parts'][0]['text']
            else:
                return f"Ошибка API: {resp.status}. Сервер Google ругается."

# --- КЛАВИАТУРЫ ---
def get_main_kb():
    kb = [
        [types.KeyboardButton(text="🦾 Тело (Масса, Осанка, Ребра)")],
        [types.KeyboardButton(text="🗣 Речь и Лицо"), types.KeyboardButton(text="👁 Зрение и Сон")],
        [types.KeyboardButton(text="🧠 Учеба"), types.KeyboardButton(text="💼 Бизнес (Lnea Studio)")]
    ]
    return types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_admin_kb():
    kb = [
        [types.KeyboardButton(text="📁 Управление портфолио"), types.KeyboardButton(text="⭐ Отзывы")],
        [types.KeyboardButton(text="🔙 В главное меню")]
    ]
    return types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# --- СТАРТ И АДМИНКА ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Терминал трансформации запущен. Выбирай вектор работы:", reply_markup=get_main_kb())

@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("🔐 Доступ в Админ-панель открыт. Выбери действие:", reply_markup=get_admin_kb())
    else:
        await message.answer("Отказано в доступе.")

@dp.message(F.text == "🔙 В главное меню")
async def back_to_main(message: types.Message):
    await message.answer("Главное меню:", reply_markup=get_main_kb())

# --- ЛОВЦЫ КНОПОК ---
@dp.message(F.text.in_(["🦾 Тело (Масса, Осанка, Ребра)", "🗣 Речь и Лицо", "👁 Зрение и Сон", "🧠 Учеба", "💼 Бизнес (Lnea Studio)"]))
async def ask_category(message: types.Message, state: FSMContext):
    await state.update_data(category=message.text)
    await message.answer(f"Выбран раздел: **{message.text}**.\nНапиши свой конкретный запрос (например: 'дай упражнения', 'распиши рецепт', 'как продать дизайн').", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(AIGenerator.waiting_for_query)

# --- ГЕНЕРАЦИЯ ОТВЕТА ---
@dp.message(AIGenerator.waiting_for_query)
async def generate_response(message: types.Message, state: FSMContext):
    data = await state.get_data()
    category = data.get("category")
    
    await message.answer("⏳ Нейросеть генерирует протокол...")
    
    # Жесткий системный промпт, закрывающий все твои требования
    system_prompt = (
        f"Ты бескомпромиссный наставник. Твой клиент: 14 лет, вес 52 кг (цель 60+), зрение -1.75, "
        f"проблемы с дикцией (с, ш), парадоксальное дыхание (выпирают ребра). Он совладелец студии дизайна Lnea Studio. "
        f"Раздел запроса: {category}. Запрос клиента: {message.text}. "
        f"Если это тело/питание — давай ОЧЕНЬ разнообразные тренировки и детальные рецепты с идеями для фото-оформления. "
        f"Если бизнес — давай конкретные схемы поиска клиентов. "
        f"Отвечай структурно, без воды, как старший брат."
    )
    
    response = await ask_gemini(system_prompt)
    await message.answer(response, reply_markup=get_main_kb())
    await state.clear()

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
