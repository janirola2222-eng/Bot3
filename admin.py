import asyncio
import logging
import google.generativeai as genai
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# --- НАСТРОЙКИ ---
TG_TOKEN = '8938811266:AAHURyOvSapf2TpKyBLAMHanWbiyqEzxIRc'
GEMINI_API_KEY = 'AIzaSyDcLFdfaXSdFjjkQhTC5vN5y1W9yJ4hmxk' # AIzaSy...
YOUR_TELEGRAM_ID = 5934814012

# Инициализация Telegram
bot = Bot(token=TG_TOKEN)
dp = Dispatcher()

# Инициализация Gemini ИИ
genai.configure(api_key=GEMINI_API_KEY)
# Используем актуальную модель
model = genai.GenerativeModel('gemini-1.5-flash')

# --- МАШИНА СОСТОЯНИЙ ---
class AIGenerator(StatesGroup):
    waiting_for_workout_req = State()
    waiting_for_food_req = State()

# --- КЛАВИАТУРА ---
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🧠 ИИ: Сгенерировать тренировку")],
        [KeyboardButton(text="🍳 ИИ: Рецепт для массы")],
        [KeyboardButton(text="🌙 Эстетика и Режим (База)")]
    ], resize_keyboard=True
)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if message.from_user.id != YOUR_TELEGRAM_ID:
        return
    await message.answer("Система управления трансформацией подключена к Gemini. Выбирай задачу:", reply_markup=main_kb)

# --- 1. ГЕНЕРАЦИЯ БЕСКОНЕЧНЫХ ТРЕНИРОВОК ---
@dp.message(F.text == "🧠 ИИ: Сгенерировать тренировку")
async def ask_workout(message: types.Message, state: FSMContext):
    await message.answer(
        "На какую группу мышц сегодня делаем упор? Что из инвентаря есть под рукой? (например: 'Спина и плечи, есть гантели и турник')",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(AIGenerator.waiting_for_workout_req)

@dp.message(AIGenerator.waiting_for_workout_req)
async def generate_workout(message: types.Message, state: FSMContext):
    await message.answer("⏳ Нейросеть составляет программу...")
    
    prompt = (
        f"Ты профессиональный тренер по самбо и фитнесу. Составь тренировку для подростка 14 лет (вес 52 кг), "
        f"цель - набор мышечной массы. Условия от пользователя: {message.text}. "
        f"Распиши упражнения, подходы и количество повторений. Добавь совет по технике."
    )
    
    try:
        response = model.generate_content(prompt)
        await message.answer(response.text, reply_markup=main_kb)
    except Exception as e:
        await message.answer(f"Ошибка API: {e}", reply_markup=main_kb)
    finally:
        await state.clear()

# --- 2. ГЕНЕРАЦИЯ БЕСКОНЕЧНЫХ РЕЦЕПТОВ ---
@dp.message(F.text == "🍳 ИИ: Рецепт для массы")
async def ask_food(message: types.Message, state: FSMContext):
    await message.answer(
        "Какие продукты у тебя сейчас есть? (например: 'Курица, рис, яйца, немного сыра')",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(AIGenerator.waiting_for_food_req)

@dp.message(AIGenerator.waiting_for_food_req)
async def generate_food(message: types.Message, state: FSMContext):
    await message.answer("⏳ Нейросеть придумывает рецепт...")
    
    prompt = (
        f"Ты спортивный нутрициолог. У пользователя есть эти продукты: {message.text}. "
        f"Цель парня: набор чистой мышечной массы (высококалорийное белковое питание). "
        f"Придумай из этих продуктов вкусный рецепт, распиши шаги готовки и примерное КБЖУ (акцент на белок и сложные углеводы)."
    )
    
    try:
        response = model.generate_content(prompt)
        await message.answer(response.text, reply_markup=main_kb)
    except Exception as e:
        await message.answer(f"Ошибка API: {e}", reply_markup=main_kb)
    finally:
        await state.clear()

# --- 3. СТАТИЧНАЯ БАЗА (Режим и Эстетика) ---
@dp.message(F.text == "🌙 Эстетика и Режим (База)")
async def static_info(message: types.Message):
    # Сюда можно зашить жесткие правила, которые не меняются
    text = (
        "**ОСНОВА ТРАНСФОРМАЦИИ:**\n\n"
        "1️⃣ **Сон:** Отбой в 22:30. Мышцы растут только во сне.\n"
        "2️⃣ **Осанка:** Каждое утро 3 подхода вакуума по 20 секунд, чтобы скрыть ребра.\n"
        "3️⃣ **Вода:** 2 литра чистой воды в день.\n"
        "4️⃣ **Дисциплина:** Тренировки не пропускаем, питание держим в профиците."
    )
    await message.answer(text, parse_mode="Markdown")

async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
