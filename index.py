import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# 🔑 BotFather'dan olgan tokeningizni shu yerga qo'ying:
TOKEN = "8870358645:AAGcyBQjJD9kmpvrPlsVktEL4fq9UodArhk"  # Bu yerga o'z tokeningizni yozing

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- 1. MA'LUMOTLAR BAZASI (SQLITE) NING TAYYORLANI SHI ---
def init_db():
    conn = sqlite3.connect("bot_bazasi.db")
    cursor = conn.cursor()
    # Har bir foydalanuvchining ma'lumotlarini user_id orqali alohida saqlash jadvali
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

init_db()  # Bot ishga tushganda baza yaratiladi

# --- 2. MA'LUMOT SAQLASH UCHUN BOSQICH SHTATLAR (FSM) ---
class Form(StatesGroup):
    tur = State()       # Masalan: Roblox, Instagram, Google
    nomi = State()      # Masalan: Asosiy akkaunt, Ishchi login
    kiymati = State()   # Masalan: Parol12345, +998901234567

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
    
    # Bazaga yozish (Faqat shu foydalanuvchining ID si bilan)
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
    # Faqat xabar yuborgan foydalanuvchining user_id sidagi ma'lumotlarni saralab oladi
    cursor.execute("SELECT tur, nomi, kiymati FROM malumotlar WHERE user_id = ?", (message.from_user.id,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await message.answer("📭 Bazangizda hali hech qanday ma'lumot yo'q.")
        return

    text = "📂 **Sizning saqlangan ma'lumotlaringiz:**\n\n"
    for row in rows:
        # Parol yoki kod ustiga bir marta bossa nusxalanadigan (copy) qilib beradi:
        text += f"🔹 **{row[0]}** ({row[1]}):\n`{row[2]}`\n\n"

    await message.answer(text, parse_mode="Markdown")

# --- 7. MA'LUMOTLARNI O'CHIRISH ---
@dp.message(F.text == "🗑 Mening bazamni tozalash")
async def clear_data(message: Message):
    conn = sqlite3.connect("bot_bazasi.db")
    cursor = conn.cursor()
    # Faqat shu foydalanuvchining ma'lumotlarini bazadan o'chiradi
    cursor.execute("DELETE FROM malumotlar WHERE user_id = ?", (message.from_user.id,))
    conn.commit()
    conn.close()
    
    await message.answer("🗑 Sizga tegishli barcha saqlangan ma'lumotlar bazadan o'chirildi.")

# --- 8. BOTNI ISHGA TUSHIRISH ---
async def main():
    print("Bot muvaffaqiyatli ishga tushdi va bazaga ulandi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
