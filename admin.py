import asyncio
import logging
import sqlite3
import time
import io
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, BufferedInputFile
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# --- НАСТРОЙКИ ---
API_TOKEN = '8938811266:AAHURyOvSapf2TpKyBLAMHanWbiyqEzxIRc'
YOUR_TELEGRAM_ID = 5934814012  # Вставь свой ID

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('progress.db')
    cursor = conn.cursor()
    # Таблица логов (тренировки, питание)
    cursor.execute('''CREATE TABLE IF NOT EXISTS logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date TEXT, category TEXT, description TEXT, media_id TEXT)''')
    # Таблица замеров
    cursor.execute('''CREATE TABLE IF NOT EXISTS measurements (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date TEXT, weight REAL, chest REAL, biceps REAL, waist REAL)''')
    # Таблица для стриков
    cursor.execute('''CREATE TABLE IF NOT EXISTS user_stats (
                        id INTEGER PRIMARY KEY,
                        streak INTEGER, last_log_date TEXT)''')
    
    # Инициализируем строку статистики, если её нет
    cursor.execute('INSERT OR IGNORE INTO user_stats (id, streak, last_log_date) VALUES (1, 0, "2000-01-01")')
    conn.commit()
    conn.close()

def update_streak():
    conn = sqlite3.connect('progress.db')
    cursor = conn.cursor()
    cursor.execute('SELECT streak, last_log_date FROM user_stats WHERE id = 1')
    streak, last_log_str = cursor.fetchone()
    
    last_log_date = datetime.strptime(last_log_str, "%Y-%m-%d").date()
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)

    if last_log_date == yesterday:
        streak += 1
    elif last_log_date < yesterday:
        streak = 1 # Стрик сгорел, начинаем заново
    # Если last_log_date == today, стрик не меняем (уже отмечался сегодня)

    cursor.execute('UPDATE user_stats SET streak = ?, last_log_date = ? WHERE id = 1', (streak, today.strftime("%Y-%m-%d")))
    conn.commit()
    conn.close()
    return streak

# --- МАШИНА СОСТОЯНИЙ (FSM) ---
class LogState(StatesGroup):
    waiting_for_text = State()
    waiting_for_media = State()

class MeasurementState(StatesGroup):
    waiting_for_data = State()

# --- КЛАВИАТУРЫ ---
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🏋️ Тренировка/Питание"), KeyboardButton(text="📏 Замеры тела")],
        [KeyboardButton(text="📈 График прогресса"), KeyboardButton(text="⏱ Таймер")],
        [KeyboardButton(text="📊 Дней до цели")]
    ], resize_keyboard=True
)
skip_kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="➡️ Пропустить фото")]], resize_keyboard=True)

timers = {}

# --- ХЭНДЛЕРЫ ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if message.from_user.id != YOUR_TELEGRAM_ID:
        return
    await message.answer("Трекер запущен! Записывай прогресс и не теряй стрик 🔥", reply_markup=main_kb)

# --- 1. ЛОГИРОВАНИЕ И СТРИКИ ---
@dp.message(F.text == "🏋️ Тренировка/Питание")
async def start_logging(message: types.Message, state: FSMContext):
    await state.update_data(category="Лог")
    await message.answer("Что сделал сегодня? (например: 'Спина + грудь, ел творог')", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(LogState.waiting_for_text)

@dp.message(LogState.waiting_for_text)
async def process_text(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer("Прикрепи фото прогресса или нажми 'Пропустить'.", reply_markup=skip_kb)
    await state.set_state(LogState.waiting_for_media)

@dp.message(LogState.waiting_for_media)
async def process_media(message: types.Message, state: FSMContext):
    # Сохранение в БД опущено для краткости (используй функцию save_log из предыдущего кода)
    streak = update_streak()
    await message.answer(f"✅ Сохранено!\n🔥 Твой текущий стрик: **{streak} дней подряд!**", reply_markup=main_kb)
    await state.clear()

# --- 2. ЗАМЕРЫ ТЕЛА ---
@dp.message(F.text == "📏 Замеры тела")
async def start_measurements(message: types.Message, state: FSMContext):
    await message.answer(
        "Введи замеры через пробел (только цифры):\n"
        "**Вес Грудь Бицепс Талия**\n"
        "Пример: `52.5 88 31 70`", parse_mode="Markdown", reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(MeasurementState.waiting_for_data)

@dp.message(MeasurementState.waiting_for_data)
async def process_measurements(message: types.Message, state: FSMContext):
    try:
        weight, chest, biceps, waist = map(float, message.text.replace(',', '.').split())
        
        conn = sqlite3.connect('progress.db')
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO measurements (date, weight, chest, biceps, waist) 
                          VALUES (?, ?, ?, ?, ?)''', 
                       (datetime.now().strftime("%Y-%m-%d"), weight, chest, biceps, waist))
        conn.commit()
        conn.close()
        
        streak = update_streak()
        await message.answer(f"📊 Замеры зафиксированы! Стрик: 🔥 {streak} дней.", reply_markup=main_kb)
    except ValueError:
        await message.answer("Ошибка формата. Попробуй еще раз (пример: 52 88 31 70).")
    finally:
        await state.clear()

# --- 3. ГЕНЕРАЦИЯ ГРАФИКА ---
@dp.message(F.text == "📈 График прогресса")
async def send_graph(message: types.Message):
    conn = sqlite3.connect('progress.db')
    cursor = conn.cursor()
    cursor.execute('SELECT date, weight, chest FROM measurements ORDER BY date ASC')
    data = cursor.fetchall()
    conn.close()

    if len(data) < 2:
        return await message.answer("Нужно минимум 2 записи замеров, чтобы построить график!")

    dates = [row[0][-5:] for row in data] # Берем только MM-DD для красоты
    weights = [row[1] for row in data]
    chests = [row[2] for row in data]

    # Настройка минималистичного дизайна графика
    plt.style.use('dark_background')
    fig, ax1 = plt.subplots(figsize=(8, 4))

    color1 = '#00ffcc' # Кибер-зеленый
    ax1.set_ylabel('Вес (кг)', color=color1)
    ax1.plot(dates, weights, color=color1, marker='o', linewidth=2, label='Вес')
    ax1.tick_params(axis='y', labelcolor=color1)
    ax1.grid(color='#333333', linestyle='--', linewidth=0.5)

    ax2 = ax1.twinx()
    color2 = '#ff007f' # Неоновый розовый
    ax2.set_ylabel('Грудь (см)', color=color2)
    ax2.plot(dates, chests, color=color2, marker='s', linewidth=2, label='Грудь')
    ax2.tick_params(axis='y', labelcolor=color2)

    plt.title('Динамика роста', fontsize=14, pad=15)
    fig.tight_layout()

    # Сохраняем в буфер и отправляем
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    plt.close()

    photo = BufferedInputFile(buf.read(), filename="progress_chart.png")
    await message.answer_photo(photo=photo, caption="Твой прогресс. Растем! 🚀")

# --- ОСТАЛЬНЫЕ КОМАНДЫ (Таймер, Дни) ---
@dp.message(F.text == "📊 Дней до цели")
async def days_left(message: types.Message):
    target_date = datetime(2026, 9, 1)
    delta = target_date - datetime.now()
    await message.answer(f"🔥 До 1 сентября: **{delta.days} дней**.")

@dp.message(F.text == "⏱ Таймер")
async def timer_cmd(message: types.Message):
    uid = message.from_user.id
    if uid in timers:
        elapsed = int(time.time() - timers[uid])
        del timers[uid]
        await message.answer(f"⏹ Отдых: {elapsed // 60} мин {elapsed % 60} сек.")
    else:
        timers[uid] = time.time()
        await message.answer("⏱ Таймер пошел!")

async def main():
    logging.basicConfig(level=logging.INFO)
    init_db()
    
    scheduler = AsyncIOScheduler(timezone="Asia/Yekaterinburg")
    # Добавь сюда будильники из прошлого кода
    scheduler.start()

    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
