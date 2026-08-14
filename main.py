import asyncio
import os
import sqlite3
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiohttp import web  # Web service uchun kerakli modul

# Tokenni Render Environment Variables bo'limidan olamiz
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("BOT_TOKEN server muhitida topilmadi! Render'da Environment Variable qo'shing.")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- 1. MA'LUMOTLAR BAZASI (SQLITE) NING TAYYORLANISHI ---
def init_db():
    conn = sqlite3.connect("bot_bazasi.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS malumotlar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            tur TEXT,
            nomi TEXT,
            kiymati TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# --- 2. MA'LUMOT SAQLASH UCHUN BOSQICH SHTATLAR (FSM) ---
class Form(StatesGroup):
    tur = State()
    nomi = State()
    kiymati = State()

# --- 3. BOSH MENYU TUGMALARI ---
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📥 Yangi ma'lumot saqlash")],
        [KeyboardButton(text="📂 Saqlangan ma'lumotlarim")],
        [KeyboardButton(text="🗑 Mening bazamni tozalash")]
    ],
    resize_keyboard=True
)

# --- 4. START BUYRUG'I ---
@dp.message(CommandStart())
async def start_handler(message: Message):
    await message.answer(
        f"Assalomu alaykum, {message.from_user.first_name}!\n\n"
        f"🔐 **Shaxsiy Ma'lumotlar Bazi Boti**ga xush kelibsiz.\n"
        f"Bu yerda siz Google, Instagram, Roblox parollaringiz yoki karta va telefon raqamlaringizni xavfsiz saqlashingiz mumkin.\n\n"
        f"⚠️ *Siz kiritgan ma'lumotlarni faqat o'zingiz ko'ra olasiz!*",
        reply_markup=main_keyboard,
        parse_mode="Markdown"
    )

# --- 5. MA'LUMOT SAQLASH KETMA-KETLIGI ---
@dp.message(F.text == "📥 Yangi ma'lumot saqlash")
async def add_info_start(message: Message, state: FSMContext):
    await state.set_state(Form.tur)
    await message.answer("📌 **Qaysi ilova yoki tarmoq ma'lumotini saqlamoqchisiz?**\n(Masalan: Roblox, Instagram, Google, Karta, Telefon)")

@dp.message(Form.tur)
async def process_tur(message: Message, state: FSMContext):
    await state.update_data(tur=message.text)
    await state.set_state(Form.nomi)
    await message.answer("🏷 **Bu ma'lumotga nom bering:**\n(Masalan: Asosiy akkauntim, Akamning kartasi, Ishchi login)")

@dp.message(Form.nomi)
async def process_nomi(message: Message, state: FSMContext):
    await state.update_data(nomi=message.text)
    await state.set_state(Form.kiymati)
    await message.answer("🔑 **Endi parol, raqam yoki kodingizni kiriting:**")

@dp.message(Form.kiymati)
async def process_kiymati(message: Message, state: FSMContext):
    user_data = await state.get_data()
    
    conn = sqlite3.connect("bot_bazasi.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO malumotlar (user_id, tur, nomi, kiymati) VALUES (?, ?, ?, ?)",
        (message.from_user.id, user_data['tur'], user_data['nomi'], message.text)
    )
    conn.commit()
    conn.close()

    await state.clear()
    await message.answer("✅ **Ma'lumotingiz bazaga xavfsiz saqlandi!**", reply_markup=main_keyboard)

# --- 6. SAQLANGAN MA'LUMOTLARNI KO'RISH ---
@dp.message(F.text == "📂 Saqlangan ma'lumotlarim")
async def show_data(message: Message):
    conn = sqlite3.connect("bot_bazasi.db")
    cursor = conn.cursor()
    cursor.execute("SELECT tur, nomi, kiymati FROM malumotlar WHERE user_id = ?", (message.from_user.id,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await message.answer("📭 Bazangizda hali hech qanday ma'lumot yo'q.")
        return

    text = "📂 **Sizning saqlangan ma'lumotlaringiz:**\n\n"
    for row in rows:
        text += f"🔹 **{row[0]}** ({row[1]}):\n`{row[2]}`\n\n"

    await message.answer(text, parse_mode="Markdown")

# --- 7. MA'LUMOTLARNI O'CHIRISH ---
@dp.message(F.text == "🗑 Mening bazamni tozalash")
async def clear_data(message: Message):
    conn = sqlite3.connect("bot_bazasi.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM malumotlar WHERE user_id = ?", (message.from_user.id,))
    conn.commit()
    conn.close()
    
    await message.answer("🗑 Sizga tegishli barcha saqlangan ma'lumotlar bazadan o'chirildi.")

# --- 8. RENDER UCHUN SOXTA WEB SERVER ---
async def handle_ping(request):
    return web.Response(text="Bot runs smoothly!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Render bergan PORT o'zgaruvchisini olamiz (standart 10000 bo'ladi)
    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"Web server started on port {port}")

# --- 9. BOT VA SERVERNI ISHGA TUSHIRISH ---
async def main():
    # Render sezishi uchun web serverni ishga tushiramiz
    await start_web_server()
    print("Bot muvaffaqiyatli ishga tushdi!")
    
    # Telegram bot polling rejimida ishlaydi
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
