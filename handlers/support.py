from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from states import TicketStates
from keyboards import support_menu, customer_menu, service_categories_menu, cancel_kb, inline
import database as db

router = Router()

def get_user_menu(uid):
    """Get appropriate menu based on user status"""
    customer = db.get_customer(uid)
    if customer and customer.get("approved", 0) == 1:
        return customer_menu
    return service_categories_menu

@router.message(F.text == "🎫 پشتیبانی")
async def support_home(message: Message):
    uid = message.from_user.id
    menu = get_user_menu(uid)
    
    await message.answer(
        "🎫 *بخش پشتیبانی*\n\n"
        "از این بخش می‌توانید:\n"
        "✅ سوالات خود را بپرسید\n"
        "✅ گزارش مشکلات را ارسال کنید\n"
        "✅ پیگیری درخواست‌های قبلی\n\n"
        "لطفاً یکی از گزینه‌ها را انتخاب کنید:",
        reply_markup=support_menu
    )

@router.message(F.text == "📩 ارسال تیکت جدید")
async def new_ticket_start(message: Message, state: FSMContext):
    await state.set_state(TicketStates.waiting_for_message)
    await message.answer(
        "📩 *تیکت جدید*\n\n"
        "لطفاً مشکل یا سوال خود را به طور کامل توضیح دهید:\n\n"
        "📌 نکات مهم:\n"
        "- شماره سفارش (اگر مربوط به سفارش خاصی است) را ذکر کنید\n"
        "- تصاویر یا مدارک مربوطه را می‌توانید ارسال کنید\n\n"
        "پشتیبانی در اسرع وقت پاسخ خواهد داد.",
        reply_markup=cancel_kb
    )

@router.message(TicketStates.waiting_for_message)
async def new_ticket_message(message: Message, state: FSMContext, bot: Bot):
    if message.text == "❌ انصراف":
        await state.clear()
        uid = message.from_user.id
        menu = get_user_menu(uid)
        await message.answer("انصراف شد.", reply_markup=menu)
        return
    
    # Get message text or caption if it's a photo
    ticket_text = message.text.strip() if message.text else ""
    if message.caption:
        ticket_text = message.caption.strip()
    
    if not ticket_text:
        await message.answer("❌ لطفاً متن تیکت خود را وارد کنید:")
        return
    
    # Create ticket
    ticket_id = db.add_ticket(message.from_user.id, ticket_text)
    await state.clear()
    
    uid = message.from_user.id
    menu = get_user_menu(uid)
    
    await message.answer(
        f"✅ *تیکت شما با موفقیت ثبت شد!*\n\n"
        f"🔢 شماره تیکت: `{ticket_id}`\n"
        f"📝 پیام شما: {ticket_text[:100]}...\n\n"
        f"پشتیبانی به زودی پاسخ شما را خواهد داد.\n"
        f"می‌توانید پاسخ را از بخش «تیکت‌های من» مشاهده کنید.",
        reply_markup=menu
    )
    
    # Notify admin
    from config import ADMIN_ID
    await bot.send_message(
        ADMIN_ID,
        f"🎫 *تیکت جدید*\n\n"
        f"🔢 شماره: #{ticket_id}\n"
        f"👤 کاربر: {message.from_user.id}\n"
        f"📝 پیام: {ticket_text[:500]}\n\n"
        f"@{message.from_user.username or 'بدون یوزرنیم'}",
        reply_markup=inline(
            (f"💬 پاسخ به تیکت #{ticket_id}", f"admin_reply_ticket:{ticket_id}"),
            (f"🔒 بستن تیکت", f"admin_close_ticket:{ticket_id}")
        )
    )

@router.message(F.text == "📋 تیکت‌های من")
async def my_tickets(message: Message):
    uid = message.from_user.id
    tickets = db.get_tickets_by_user(uid)
    
    if not tickets:
        await message.answer("📭 تیکتی ندارید.\n\nبرای ارسال تیکت جدید، از گزینه «ارسال تیکت جدید» استفاده کنید.")
        return
    
    status_fa = {
        "open": "⏳ باز",
        "answered": "✅ پاسخ داده شده",
        "closed": "🔒 بسته"
    }
    
    for ticket in tickets[:10]:
        status_text = status_fa.get(ticket["status"], ticket["status"])
        
        text = (
            f"🎫 *تیکت #{ticket['id']}*\n"
            f"📌 وضعیت: {status_text}\n"
            f"📅 تاریخ: {ticket['created_at'][:10]}\n"
            f"─────────────\n"
            f"📝 *پیام شما:*\n{ticket['message'][:300]}"
        )
        
        if ticket["reply"]:
            text += f"\n\n💬 *پاسخ پشتیبانی:*\n{ticket['reply'][:300]}"
        
        await message.answer(text)

# Admin handlers
@router.callback_query(F.data.startswith("admin_reply_ticket:"))
async def admin_reply_ticket_start(call: CallbackQuery, state: FSMContext):
    from config import ADMIN_ID
    if call.from_user.id != ADMIN_ID:
        await call.answer("❌ دسترسی غیرمجاز", show_alert=True)
        return
    
    ticket_id = int(call.data.split(":")[1])
    await state.update_data(reply_ticket_id=ticket_id)
    await state.set_state(TicketStates.waiting_for_reply)
    
    await call.message.answer(
        f"💬 *پاسخ به تیکت #{ticket_id}*\n\n"
        f"لطفاً پاسخ خود را وارد کنید:",
        reply_markup=cancel_kb
    )
    await call.answer()

@router.message(TicketStates.waiting_for_reply)
async def admin_send_reply(message: Message, state: FSMContext, bot: Bot):
    from config import ADMIN_ID
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ دسترسی غیرمجاز")
        return
    
    if message.text == "❌ انصراف":
        await state.clear()
        await message.answer("انصراف شد.")
        return
    
    data = await state.get_data()
    ticket_id = data.get("reply_ticket_id")
    
    if not ticket_id:
        await state.clear()
        await message.answer("❌ خطا: تیکت یافت نشد.")
        return
    
    ticket = db.get_ticket(ticket_id)
    if not ticket:
        await state.clear()
        await message.answer("❌ تیکت یافت نشد.")
        return
    
    # Save reply
    db.reply_ticket(ticket_id, message.text.strip())
    await state.clear()
    
    await message.answer(f"✅ پاسخ شما به تیکت #{ticket_id} ارسال شد.")
    
    # Notify user
    await bot.send_message(
        ticket["user_id"],
        f"💬 *پاسخ جدید به تیکت شما*\n\n"
        f"🎫 تیکت #{ticket_id}\n"
        f"─────────────────\n"
        f"📝 *پاسخ پشتیبانی:*\n{message.text.strip()}\n\n"
        f"برای مشاهده تیکت‌های خود، به بخش «تیکت‌های من» مراجعه کنید.",
        reply_markup=inline((f"📋 مشاهده تیکت", f"view_ticket:{ticket_id}"))
    )

@router.callback_query(F.data.startswith("admin_close_ticket:"))
async def admin_close_ticket(call: CallbackQuery, bot: Bot):
    from config import ADMIN_ID
    if call.from_user.id != ADMIN_ID:
        await call.answer("❌ دسترسی غیرمجاز", show_alert=True)
        return
    
    ticket_id = int(call.data.split(":")[1])
    ticket = db.get_ticket(ticket_id)
    
    if not ticket:
        await call.answer("❌ تیکت یافت نشد.", show_alert=True)
        return
    
    db.close_ticket(ticket_id)
    await call.message.edit_text(f"🔒 تیکت #{ticket_id} بسته شد.")
    
    await bot.send_message(
        ticket["user_id"],
        f"🔒 *تیکت شما بسته شد*\n\n"
        f"🎫 تیکت #{ticket_id}\n"
        f"وضعیت: بسته شده\n\n"
        f"اگر مشکل جدیدی دارید، می‌توانید تیکت جدید ارسال کنید."
    )
    await call.answer()

@router.callback_query(F.data.startswith("view_ticket:"))
async def view_ticket(call: CallbackQuery):
    ticket_id = int(call.data.split(":")[1])
    ticket = db.get_ticket(ticket_id)
    
    if not ticket or ticket["user_id"] != call.from_user.id:
        await call.answer("❌ دسترسی غیرمجاز", show_alert=True)
        return
    
    status_fa = {
        "open": "⏳ باز",
        "answered": "✅ پاسخ داده شده",
        "closed": "🔒 بسته"
    }
    
    text = (
        f"🎫 *تیکت #{ticket['id']}*\n"
        f"📌 وضعیت: {status_fa.get(ticket['status'], ticket['status'])}\n"
        f"📅 تاریخ: {ticket['created_at'][:10]}\n"
        f"─────────────\n"
        f"📝 *پیام شما:*\n{ticket['message']}"
    )
    
    if ticket["reply"]:
        text += f"\n\n💬 *پاسخ:*\n{ticket['reply']}"
    
    await call.message.answer(text)
    await call.answer()
