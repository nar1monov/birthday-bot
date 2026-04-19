import asyncio
import sqlite3
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import aioschedule

# Loggingni sozlash (hatolarni ko'rish uchun)
logging.basicConfig(level=logging.INFO)

TOKEN = "8250842782:AAF6UEPX53jeepBbaho01qNTlRUrltHaTeo"
bot = Bot(token=TOKEN)
dp = Dispatcher()

def init_db():
    conn = sqlite3.connect('birthdays.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (user_id INTEGER, chat_id INTEGER, name TEXT, dob TEXT)''')
    conn.commit()
    conn.close()

def days_until_birthday(dob_str):
    today = datetime.now().date()
    try:
        dob = datetime.strptime(dob_str, "%d.%m").date().replace(year=today.year)
        if dob < today:
            dob = dob.replace(year=today.year + 1)
        return (dob - today).days
    except ValueError:
        return None

# --- HANDLERLAR ---

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer("Salom! Men tug'ilgan kunlarni eslatuvchi botman.\n\n"
                         "🔹 `/add 25.12` — Sanangizni saqlash\n"
                         "🔹 `/date` — Qolgan kunni tekshirish")

@dp.message(Command("add"))
async def add_birthday(message: types.Message):
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("Xato! Iltimos `/add kun.oy` shaklida yozing (Masalan: /add 15.08)")
        return

    date_str = parts[1]
    try:
        # Sanani tekshirish
        datetime.strptime(date_str, "%d.%m")
        
        conn = sqlite3.connect('birthdays.db')
        c = conn.cursor()
        c.execute("INSERT INTO users VALUES (?, ?, ?, ?)", 
                  (message.from_user.id, message.chat.id, message.from_user.full_name, date_str))
        conn.commit()
        conn.close()
        
        await message.reply(f"Saqlandi! {date_str} kuni sizni tabriklayman.")
    except ValueError:
        await message.reply("Xato format! Sanani DD.MM ko'rinishida kiriting (Masalan: 15.08)")

async def check_birthdays():
    conn = sqlite3.connect('birthdays.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users")
    users = c.fetchall()
    
    for user_id, chat_id, name, dob in users:
        days = days_until_birthday(dob)
        if days == 0:
            await bot.send_message(chat_id, f"🎉 BUGUN: {name} ning tug'ilgan kuni! Tabriklaymiz!")
        elif days is not None and days <= 3:
            await bot.send_message(chat_id, f"⏰ Eslatma: {name} ning tug'ilgan kuniga {days} kun qoldi!")
    conn.close()

@dp.message(Command("date"))
async def get_remaining_days(message: types.Message):
    conn = sqlite3.connect('birthdays.db')
    c = conn.cursor()
    
    # Foydalanuvchini ID si bo'yicha bazadan qidiramiz
    c.execute("SELECT dob FROM users WHERE user_id = ? AND chat_id = ? ORDER BY rowid DESC LIMIT 1", 
              (message.from_user.id, message.chat.id))
    result = c.fetchone()
    conn.close()

    if result:
        dob_str = result[0]
        days = days_until_birthday(dob_str)
        
        if days == 0:
            await message.reply(f"Sizning tug'ilgan kuningiz BUGUN! 🎂")
        else:
            await message.reply(f"Sizning tug'ilgan kuningizga **{days} kun** qoldi. ✨")
    else:
        await message.reply("Siz hali tug'ilgan kuningizni kiritmagansiz.\n"
                            "Masalan: `/add 15.08` deb yozing.")

async def scheduler():
    # Vaqtni "HH:MM" formatida ko'rsating
    aioschedule.every().day.at("09:00").do(check_birthdays)
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(1)

async def main():
    init_db()
    # Shcheduler'ni fonda ishga tushirish
    asyncio.create_task(scheduler())
    # Botni ishga tushirish
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to'xtatildi")