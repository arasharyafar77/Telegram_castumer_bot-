from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from states import NewOrder, RatingFlow
from keyboards import customer_menu, service_categories_menu, cancel_kb, order_actions_customer, get_order_status_text, inline
import database as db

router = Router()

@router.message(NewOrder.description)
async def process_order_description(message: Message, state: FSMContext):
    if message.text == "❌ انصراف":
        await state.clear()
        await message.answer("انصراف شد.", reply_markup=customer_menu)
        return
    
    description = message.text.strip()
    if message.caption:
        description = message.caption.strip()
    
    await state.update_data(description=description)
    await state.set_state(NewOrder.waiting_for_confirmation)
    
    data = await state.get_data()
    
    await message.answer(
        f"📋 *خلاصه سفارش:*\n\n"
        f"📦 خدمت: {data['service']}\n"
        f"📝 توضیحات: {description[:300]}{'...' if len(description) > 300 else ''}\n\n"
        f"✅ سفارش شما ثبت شود؟",
        reply_markup=inline(
            ("✅ ثبت سفارش", "confirm_order"),
            ("✏️ ویرایش", "edit_description"),
            ("❌ انصراف", "cancel_order")
        )
    )

@router.callback_query(F.data == "edit_description")
async def edit_description(call: CallbackQuery, state: FSMContext):
    await state.set_state(NewOrder.description)
    await call.message.answer("توضیحات جدید را وارد کنید:", reply_markup=cancel_kb)
    await call.answer()

@router.callback_query(F.data == "cancel_order")
async def cancel_order(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.answer("سفارش لغو شد.", reply_markup=customer_menu)
    await call.answer()

@router.callback_query(F.data == "confirm_order")
async def confirm_order(call: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    order_id = db.create_order(call.from_user.id, data["service"], data["description"])
    await state.clear()
    
    await call.message.edit_text(
        f"✅ *سفارش شما با موفقیت ثبت شد!*\n\n"
        f"🔢 شماره سفارش: `#{order_id}`\n"
        f"📦 خدمت: {data['service']}\n"
        f"📌 وضعیت: در انتظار مجری\n\n"
        f"به زودی مجری برای انجام کار شما انتخاب می‌شود.\n"
        f"می‌توانید وضعیت را از بخش «سفارش‌های من» پیگیری کنید.",
        reply_markup=customer_menu
    )
    
    # Notify admin
    from config import ADMIN_ID
    await bot.send_message(
        ADMIN_ID,
        f"🆕 *سفارش جدید*\n\n"
        f"🔢 شماره: #{order_id}\n"
        f"👤 مشتری: {call.from_user.id}\n"
        f"📦 خدمت: {data['service']}\n"
        f"📝 توضیحات: {data['description'][:300]}"
    )
    
    await call.answer()

@router.message(F.text == "📋 سفارش‌های من")
async def my_orders(message: Message):
    uid = message.from_user.id
    orders = db.get_orders_by_customer(uid)
    
    if not orders:
        await message.answer("📭 سفارشی ندارید.")
        return
    
    for order in orders[:10]:
        status_text = get_order_status_text(order["status"])
        text = (
            f"🔢 *سفارش #{order['id']}*\n"
            f"📦 خدمت: {order['service']}\n"
            f"📝 توضیحات: {order['description'][:150]}...\n"
            f"📌 وضعیت: {status_text}\n"
            f"📅 تاریخ: {order['created_at'][:10]}"
        )
        
        kb = None
        if order["status"] in ["accepted", "in_progress"]:
            kb = order_actions_customer(order["id"])
        
        await message.answer(text, reply_markup=kb)

@router.message(F.text == "/start_rating")
async def start_rating(message: Message, state: FSMContext):
    # This would be called after order completion
    pass

@router.callback_query(F.data.startswith("open_chat:"))
async def open_chat(call: CallbackQuery):
    order_id = int(call.data.split(":")[1])
    order = db.get_order(order_id)
    
    if not order or order["customer_id"] != call.from_user.id:
        await call.answer("❌ دسترسی ندارید.", show_alert=True)
        return
    
    if order["chat_active"] != 1:
        await call.answer("❌ چت برای این سفارش فعال نیست.", show_alert=True)
        return
    
    await call.message.answer(
        f"💬 *چت سفارش #{order_id}*\n\n"
        f"می‌توانید پیام خود را ارسال کنید.\n"
        f"پیام‌های شما به مجری ارسال می‌شود.\n\n"
        f"برای بستن چت، دستور /endchat را ارسال کنید."
    )
    await call.answer()

@router.callback_query(F.data.startswith("change_seller:"))
async def change_seller_request(call: CallbackQuery, bot: Bot):
    order_id = int(call.data.split(":")[1])
    order = db.get_order(order_id)
    
    if not order or order["customer_id"] != call.from_user.id:
        await call.answer("❌ دسترسی ندارید.", show_alert=True)
        return
    
    from config import ADMIN_ID
    await bot.send_message(
        ADMIN_ID,
        f"🔄 *درخواست تغییر مجری*\n\n"
        f"سفارش: #{order_id}\n"
        f"مشتری: {call.from_user.id}",
        reply_markup=inline(
            (f"✅ تأیید تغییر", f"admin_change_seller:{order_id}"),
            (f"❌ رد درخواست", f"admin_reject_change:{order_id}")
        )
    )
    
    await call.message.answer("📨 درخواست تغییر مجری برای ادمین ارسال شد.")
    await call.answer()

@router.message(F.text == "/endchat")
async def end_chat(message: Message):
    uid = message.from_user.id
    order = db.get_active_chat_order(uid)
    
    if order:
        db.deactivate_chat(order["id"])
        await message.answer("💬 چت بسته شد.", reply_markup=customer_menu)
    else:
        await message.answer("💬 چت فعالی وجود ندارد.")
