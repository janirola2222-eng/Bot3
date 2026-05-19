import logging
from google import genai
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import asyncio

# --- НАСТРОЙКИ И КЛЮЧИ ---
API_TOKEN = '8938811266:AAG9Is2ByWrivKIUY5Vvux2KfDOy-f9mNzQ'
GEMINI_KEY = 'AIzaSyDcLFdfaXSdFjjkQhTC5vN5y1W9yJ4hmxk'
ADMIN_ID = 5934814012  # Твой Telegram ID для админки

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Инициализируем нового клиента Google по свежему стандарту
gemini_client = genai.Client(api_key=GEMINI_KEY)

class AIGenerator(StatesGroup):
    waiting_for_query = State()

# --- АСИНХРОННЫЙ ЗАПРОС К ИИ (НОВЫЙ SDK) ---
async def ask_gemini(prompt_text):
    try:
        response = await gemini_client.aio.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt_text,
        )
        return response.text
    except Exception as e:
        return f"Ошибка ИИ: {e}. Проверь сборку на хостинге."

# --- КЛАВИАТУРЫ ---
def get_main_kb():
    kb = [
        [types.KeyboardButton(text="🦾 Тело (Масса, Осанка, Ребра)")],
        [types.KeyboardButton(text="🗣 Речь и Дикция"), types.KeyboardButton(text="👁 Зрение и Сон")],
        [types.KeyboardButton(text="🧠 Учеба и Фокус"), types.KeyboardButton(text="💼 Бизнес (Lnea Studio)")]
    ]
    return types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_admin_kb():
    kb = [
        [types.KeyboardButton(text="📁 Управление портфолио"), types.KeyboardButton(text="⭐ Отзывы")],
        [types.KeyboardButton(text="🔙 В главное меню")]
    ]
    return types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# --- БЛОК СТАРТА И АДМИНКИ ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🧠 Терминал личной трансформации запущен.\n\n"
        "Каждое нажатие кнопки — это шаг к твоей новой версии. Выбирай вектор работы:", 
        reply_markup=get_main_kb()
    )

@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("🔐 Доступ в панель управления Lnea Studio открыт. Выбери действие:", reply_markup=get_admin_kb())
    else:
        await message.answer("Ошибка доступа. Вы не являетесь администратором.")

@dp.message(F.text == "🔙 В главное меню")
async def back_to_main(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Главное меню:", reply_markup=get_main_kb())

# --- ОБРАБОТКА ВЫБОРА КАТЕГОРИИ ---
@dp.message(F.text.in_([
    "🦾 Тело (Масса, Осанка, Ребра)", 
    "🗣 Речь и Дикция", 
    "👁 Зрение и Сон", 
    "🧠 Учеба и Фокус", 
    "💼 Бизнес (Lnea Studio)"
]))
async def ask_category(message: types.Message, state: FSMContext):
    await state.update_data(category=message.text)
    
    # Даем подсказки в зависимости от выбранной кнопки
    hints = {
        "🦾 Тело (Масса, Осанка, Ребра)": "Напиши запрос. Например: 'Дай сессию переобучения на дыхание животом' или 'Распиши высококалорийный ужин для набора массы'.",
        "🗣 Речь и Дикция": "Напиши запрос. Например: 'Дай артикуляционную гимнастику для четких звуков С и Ш' или 'Сделай подборку сложных скороговорок'.",
        "👁 Зрение и Сон": "Напиши запрос. Например: 'Дай 3-минутную разминку для глаз от усталости' или 'Рассчитай режим сна, если вставать в 7 утра'.",
        "🧠 Учеба и Фокус": "Напиши запрос. Например: 'Как быстро запомнить сложный материал' или 'Техника концентрации на 45 минут'.",
        "💼 Бизнес (Lnea Studio)": "Напиши запрос. Например: 'Как упаковать ИИ-ассистента для B2B продаж' или 'Схема поиска первых крупных клиентов на дизайн'."
    }
    
    await message.answer(
        f"🎯 Направление: **{message.text}**\n\n{hints[message.text]}", 
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(AIGenerator.waiting_for_query)

# --- ОБРАБОТКА ЗАПРОСА И ОТВЕТ ИИ ---
@dp.message(AIGenerator.waiting_for_query)
async def generate_response(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    category = user_data.get("category")
    
    await message.answer("⏳ Системы ИИ анализируют протоколы трансформации...")
    
    # Мощный скрытый промпт, заставляющий ИИ работать строго на твои цели
    system_prompt = (
        f"Ты — жесткий, прямой и бескомпромиссный наставник по селф-импрувменту. Говоришь как старший брат, структурно и без воды. "
        f"Твой подопечный: парень 14 лет, вес 52 кг (жесткая цель — набрать качественные 60 кг к 1 сентября). "
        f"У него парадоксальное дыхание (при вдохе живот втягивается, из-за чего выпирают нижние ребра / Rib Flare), плохая осанка. "
        f"Есть проблемы с дикцией (с детства нечетко выговаривает звуки 'с' и 'ш'). Зрение -1.75 (нужна профилактика спазма аккомодации). "
        f"Он развивает собственную дизайн-студию Lnea Studio и хочет выйти на серьезный доход. "
        f"Категория вопроса: {category}. Конкретный запрос парня: {message.text}. "
        f"Давай только практические инструкции. Если это тренировки или еда — пиши ОЧЕНЬ разнообразные программы и детальные рецепты. "
        f"Если это речь — давай конкретные логопедические упражнения и комплексы."
    )
    
    response_text = await ask_gemini(system_prompt)
    await message.answer(response_text, reply_markup=get_main_kb())
    await state.clear()

# --- ЗАПУСК БОТА ---
async def main():
    logging.basicConfig(level=logging.INFO)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
