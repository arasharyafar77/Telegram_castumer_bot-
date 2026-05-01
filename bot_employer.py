import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, BotCommand
from aiogram.filters import CommandStart, Command
from aiogram import Router, F

from config import BOT_TOKEN, ADMIN_ID
from keyboards import customer_menu, service_categories_menu, role_kb, SERVICE_DESCRIPTIONS
import database as db

from handlers import registration, orders, wallet, support, profile

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

start_router = Router()

def get_greeting_by_time():
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "☀️ صبح بخیر"
    elif 12 <= hour < 17:
        return "🌤 ظهر بخیر"
    elif 17 <= hour < 21:
        return "🌙 عصر بخیر"
    else:
        return "✨ شب بخیر"

@start_router.message(CommandStart())
async def cmd_start(message: Message):
    uid = message.from_user.id
    user_name = message.from_user.full_name
    greeting = get_greeting_by_time()

    # Check if user is admin
    if uid == ADMIN_ID:
        await message.answer(
            f"👑 {greeting} ادمین عزیز!\n\n"
            f"به پنل مدیریت خوش آمدید.",
            reply_markup=role_kb
        )
        return

    # Check if user is registered customer
    customer = db.get_customer(uid)
    if customer and customer["registered"] == 1:
        if customer.get("approved", 0) == 1:
            await message.answer(
                f"✨ {greeting} {customer['name']} جان! ✨\n\n"
                f"به ربات مارکت‌پلیس خوش آمدی.\n"
                f"از منوی زیر می‌توانی سفارش جدید ثبت کنی.",
                reply_markup=customer_menu
            )
        else:
            await message.answer(
                f"⏳ {greeting} {customer['name']} جان!\n\n"
                f"ثبت‌نام شما در انتظار تأیید ادمین است.\n"
                f"می‌توانی خدمات را ببینی ولی برای ثبت سفارش باید تأیید شوی.",
                reply_markup=service_categories_menu
            )
        return

    # New user - show services first
    await message.answer(
        f"🌟 {greeting} {user_name} عزیز! 🌟\n\n"
        f"به **مارکت‌پلیس حرفه‌ای** خوش آمدی.\n\n"
        f"⚡️ اینجا می‌تونی:\n"
        f"✅ سفارش‌های متنوع ثبت کنی\n"
        f"✅ از مجریان حرفه‌ای استفاده کنی\n"
        f"✅ با کیف پول امن پرداخت کنی\n\n"
        f"🔽 **خدمات ما:**",
        reply_markup=service_categories_menu
    )

# ─── Services Menu (visible to everyone) ─────────────────────
@start_router.message(F.text.in_(["🌐 ترجمه حرفه‌ای", "🎙 تبدیل ویس به متن", "🎨 طراحی لوگو", "📝 تولید محتوا", "🔧 سایر خدمات"]))
async def service_category_selected(message: Message):
    service_map = {
        "🌐 ترجمه حرفه‌ای": "ترجمه حرفه‌ای",
        "🎙 تبدیل ویس به متن": "تبدیل ویس به متن",
        "🎨 طراحی لوگو": "طراحی لوگو",
        "📝 تولید محتوا": "تولید محتوا",
        "🔧 سایر خدمات": "سایر خدمات"
    }
    
    service_name = service_map.get(message.text, message.text)
    
    # Show description for this service
    description = SERVICE_DESCRIPTIONS.get(service_name, SERVICE_DESCRIPTIONS["سایر خدمات"])
    
    await message.answer(
        description,
        reply_markup=inline(
            ("📝 ثبت سفارش", f"start_order:{service_name}"),
            ("🔙 بازگشت به خدمات", "back_to_services")
        )
    )

@start_router.callback_query(F.data == "back_to_services")
async def back_to_services(call: CallbackQuery):
    await call.message.answer(
        "✨ *خدمات ویژه مارکت‌پلیس* ✨\n\n"
        "لطفاً نوع خدمت مورد نظر خود را انتخاب کنید:",
        reply_markup=service_categories_menu
    )
    await call.answer()

@start_router.callback_query(F.data.startswith("start_order:"))
async def start_order_from_service(call: CallbackQuery, state: FSMContext):
    service_name = call.data.split(":")[1]
    uid = call.from_user.id
    
    # Check if user is registered
    customer = db.get_customer(uid)
    
    if not customer or customer["registered"] != 1:
        await call.message.answer(
            "❌ *لطفاً ابتدا ثبت‌نام کنید!*\n\n"
            "برای ثبت سفارش، ابتدا باید ثبت‌نام خود را کامل کنید.\n\n"
            "🔽 لطفاً روی دکمه «👤 مشتری» کلیک کنید.",
            reply_markup=role_kb
        )
        await call.answer()
        return
    
    if customer.get("approved", 0) != 1:
        await call.message.answer(
            "⏳ *در انتظار تأیید ادمین*\n\n"
            "ثبت‌نام شما در حال بررسی است.\n"
            "پس از تأیید، می‌توانید سفارش خود را ثبت کنید.\n\n"
            "برای پیگیری به بخش پشتیبانی مراجعه کنید.",
            reply_markup=service_categories_menu
        )
        await call.answer()
        return
    
    # User is approved, proceed to order
    await state.update_data(service=service_name)
    await state.set_state(NewOrder.description)
    
    await call.message.answer(
        f"📝 *ثبت سفارش - {service_name}*\n\n"
        f"لطفاً توضیحات کامل سفارش خود را وارد کنید:\n\n"
        f"✅ هرچه توضیحات کامل‌تر باشد، کیفیت کار بالاتر می‌رود.\n"
        f"✅ می‌توانید فایل یا عکس هم ارسال کنید.",
        reply_markup=cancel_kb
    )
    await call.answer()

@start_router.message(Command("menu"))
async def cmd_menu(message: Message):
    uid = message.from_user.id
    
    customer = db.get_customer(uid)
    if customer and customer["registered"] == 1 and customer.get("approved", 0) == 1:
        await message.answer(
            "📋 **منوی مشتری**\n\n"
            "🛍 چطور می‌تونم بهت کمک کنم؟",
            reply_markup=customer_menu
        )
        return
    
    await message.answer(
        "📋 **خدمات ما**\n\n"
        "برای ثبت سفارش، لطفاً ابتدا ثبت‌نام کنید.",
        reply_markup=service_categories_menu
    )

@start_router.message(F.text == "🔙 بازگشت")
async def go_back(message: Message):
    uid = message.from_user.id
    
    customer = db.get_customer(uid)
    if customer and customer["registered"] == 1 and customer.get("approved", 0) == 1:
        await message.answer(
            "🏠 **بازگشت به منوی اصلی**",
            reply_markup=customer_menu
        )
        return
    
    await message.answer(
        "🏠 **بازگشت به خدمات**",
        reply_markup=service_categories_menu
    )

@start_router.message(F.text == "🛍 خدمات")
async def show_services(message: Message):
    await message.answer(
        "✨ *خدمات ویژه مارکت‌پلیس* ✨\n\n"
        "لطفاً نوع خدمت مورد نظر خود را انتخاب کنید:",
        reply_markup=service_categories_menu
    )

async def set_commands():
    await bot.set_my_commands([
        BotCommand(command="start", description="شروع ربات"),
        BotCommand(command="menu", description="منوی اصلی"),
    ])

async def main():
    db.init_db()
    await set_commands()

    dp.include_router(start_router)
    dp.include_router(registration.router)
    dp.include_router(orders.router)
    dp.include_router(wallet.router)
    dp.include_router(support.router)
    dp.include_router(profile.router)

    logging.info("ربات مشتری شروع به کار کرد...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())