import logging
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import asyncio

# --- НАСТРОЙКИ ---
API_TOKEN = '8938811266:AAG9Is2ByWrivKIUY5Vvux2KfDOy-f9mNzQ'
DEEPSEEK_KEY = 'sk-543df0a77aae48f5a3af208231050170' # <--- Вставь свой ключ сюда
ADMIN_ID = 5934814012

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

class AIGenerator(StatesGroup):
    waiting_for_query = State()

# --- ПРЯМОЙ ЗАПРОС К DEEPSEEK API ---
async def ask_deepseek(system_prompt: str, user_text: str):
    url = "https://api.deepseek.com/chat/completions"
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-chat", # Модель общего назначения (V3)
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text}
        ],
        "temperature": 0.7
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data['choices'][0]['message']['content']
                else:
                    error_text = await resp.text()
                    return f"Ошибка API DeepSeek ({resp.status}): {error_text}"
        except Exception as e:
            return f"Ошибка соединения: {e}"

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
        await message.answer("Отказано в доступе. Вы не администратор.")

@dp.message(F.text == "🔙 В главное меню")
async def back_to_main(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Главное меню:", reply_markup=get_main_kb())

# --- ЛОВЦЫ КНОПОК МЕНЮ ---
@dp.message(F.text.in_(["🦾 Тело (Масса, Осанка, Ребра)", "🗣 Речь и Лицо", "👁 Зрение и Сон", "🧠 Учеба", "💼 Бизнес (Lnea Studio)"]))
async def ask_category(message: types.Message, state: FSMContext):
    await state.update_data(category=message.text)
    await message.answer(f"Раздел: **{message.text}**.\nНапиши конкретный запрос для ИИ:", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(AIGenerator.waiting_for_query)

# --- ГЕНЕРАЦИЯ ОТВЕТА ОТ DEEPSEEK ---
@dp.message(AIGenerator.waiting_for_query)
async def generate_response(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    category = user_data.get("category")
    
    await message.answer("⏳ Анализирую...")
    
    # Жесткий системный промпт, заточенный под все твои цели и требования
    system_prompt = (
        "Ты — бескомпромиссный наставник. Клиент: 14 лет, вес 52 кг (цель 60+ кг к сентябрю), зрение -1.75. "
        "Проблемы: парадоксальное дыхание (выпирают ребра / Rib Flare), плохая осанка, дикция (нечетко выговаривает 'с' и 'ш'). "
        "Развивает дизайн-студию Lnea Studio с партнером (дизайн + ИИ-ассистенты). "
        f"Текущая тема: {category}. "
        "Твои правила: "
        "1. Для тела и питания: давай ОЧЕНЬ разнообразные программы тренировок и сверхдетальные рецепты с идеями для фото. "
        "2. Для речи: четкая артикуляционная гимнастика и скороговорки. "
        "3. Для бизнеса: конкретные шаги для Lnea Studio, скрипты продаж и упаковка портфолио. "
        "Отвечай структурно, жестко и по делу."
    )
    
    answer = await ask_deepseek(system_prompt, message.text)
    await message.answer(answer, reply_markup=get_main_kb())
    await state.clear()

async def main():
    logging.basicConfig(level=logging.INFO)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
