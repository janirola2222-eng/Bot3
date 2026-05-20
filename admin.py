import logging
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import asyncio

# --- НАСТРОЙКИ ---
API_TOKEN = '8938811266:AAG9Is2ByWrivKIUY5Vvux2KfDOy-f9mNzQ'
GROQ_KEY = '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' # <--- Твой новый ключ
ADMIN_ID = 5934814012 # Твой Telegram ID

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

class AIGenerator(StatesGroup):
    waiting_for_query = State()

# --- БЕСПЛАТНЫЙ ЗАПРОС К GROQ API ---
async def ask_ai(system_prompt: str, user_text: str):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama3-70b-8192", # Самая мощная модель в бесплатном доступе
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text}
        ],
        "temperature": 0.7
    }
    
    timeout = aiohttp.ClientTimeout(total=20)
    
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data['choices'][0]['message']['content']
                else:
                    error_text = await resp.text()
                    return f"❌ Ошибка API Groq ({resp.status}): {error_text}"
    except asyncio.TimeoutError:
        return "❌ Ошибка: Нейросеть не ответила вовремя (таймаут)."
    except Exception as e:
        return f"❌ Системная ошибка сети: {e}"

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

# --- ЛОГИКА СТАРТА И АДМИНКИ ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("⚡ Терминал запущен на движке Groq. Выбирай вектор работы:", reply_markup=get_main_kb())

@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("🔐 Админ-панель Lnea Studio. Управление контентом:", reply_markup=get_admin_kb())
    else:
        await message.answer("❌ Доступ запрещен.")

@dp.message(F.text.in_(["📁 Управление портфолио", "⭐ Отзывы"]))
async def admin_mock_functions(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer(f"Раздел [{message.text}] в разработке. Здесь будет функционал добавления проектов и отзывов через Telegram команды.")

@dp.message(F.text == "🔙 В главное меню")
async def back_to_main(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Возврат в главное меню:", reply_markup=get_main_kb())

# --- ЛОГИКА ВЫБОРА КАТЕГОРИИ ---
@dp.message(F.text.in_(["🦾 Тело (Масса, Осанка, Ребра)", "🗣 Речь и Лицо", "👁 Зрение и Сон", "🧠 Учеба", "💼 Бизнес (Lnea Studio)"]))
async def ask_category(message: types.Message, state: FSMContext):
    await state.update_data(category=message.text)
    await message.answer(f"Раздел: **{message.text}**\nНапиши свой конкретный запрос:", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(AIGenerator.waiting_for_query)

# --- ГЕНЕРАЦИЯ ОТВЕТА ОТ ИИ ---
@dp.message(AIGenerator.waiting_for_query)
async def generate_response(message: types.Message, state: FSMContext):
    data = await state.get_data()
    category = data.get("category")
    
    await message.answer("⏳ Llama-3 генерирует ответ...")
    
    # Мощнейший промпт, закрывающий все твои требования
    system_prompt = (
        f"Ты — жесткий наставник. Клиент: 14 лет, вес 52 кг (цель 60+ кг к сентябрю), зрение -1.75. "
        f"Проблемы: парадоксальное дыхание (выпирают ребра / Rib Flare), плохая осанка, дикция (с детства нечетко выговаривает 'с' и 'ш'). "
        f"Он совладелец дизайн-студии Lnea Studio (дизайн + ИИ-услуги) и хочет заработать. "
        f"Текущая тема: {category}. "
        f"КРИТИЧЕСКИЕ ПРАВИЛА: "
        f"1. Тренировки должны быть ОЧЕНЬ разнообразными, без банальных повторений. "
        f"2. Рецепты должны быть сверхдетальными, с точными граммовками и обязательным описанием идеи для красивого ФОТО блюда. "
        f"3. Для речи давай четкую артикуляционную гимнастику. "
        f"4. Для бизнеса давай конкретные схемы поиска клиентов. "
        f"Пиши структурно, без воды, на русском языке."
    )
    
    answer = await ask_ai(system_prompt, message.text)
    await message.answer(answer, reply_markup=get_main_kb())
    await state.clear()

async def main():
    logging.basicConfig(level=logging.INFO)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
