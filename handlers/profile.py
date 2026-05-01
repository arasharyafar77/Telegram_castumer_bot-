from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from states import EditProfile
from keyboards import customer_menu, service_categories_menu, edit_profile_menu, cancel_kb, confirm_kb, inline
import database as db

router = Router()

def get_user_menu(uid):
    """Get appropriate menu based on user status"""
    customer = db.get_customer(uid)
    if customer and customer.get("approved", 0) == 1:
        return customer_menu
    return service_categories_menu

@router.message(F.text == "👤 پروفایل من")
async def show_profile(message: Message):
    uid = message.from_user.id
    customer = db.get_customer(uid)
    
    if not customer or customer["registered"] != 1:
        await message.answer(
            "❌ شما ثبت‌نام نکرده‌اید.\n\n"
            "لطفاً ابتدا روی دکمه «👤 مشتری» کلیک کنید و ثبت‌نام را کامل کنید.",
            reply_markup=service_categories_menu
        )
        return
    
    approved_status = "✅ تأیید شده" if customer.get("approved", 0) == 1 else "⏳ در انتظار تأیید"
    orders_count = len(db.get_orders_by_customer(uid))
    balance = db.get_balance(uid)
    
    await message.answer(
        f"👤 *پروفایل شما*\n\n"
        f"─────────────────\n"
        f"📝 نام: {customer['name']}\n"
        f"📱 تلفن: {customer['phone']}\n"
        f"📌 وضعیت: {approved_status}\n"
        f"─────────────────\n"
        f"📦 تعداد سفارش‌ها: {orders_count}\n"
        f"💰 موجودی کیف پول: {balance:,.0f} تومان\n"
        f"─────────────────\n\n"
        f"از منوی زیر می‌توانید اطلاعات خود را ویرایش کنید:",
        reply_markup=edit_profile_menu
    )

@router.message(F.text == "✏️ ویرایش نام")
async def edit_name_start(message: Message, state: FSMContext):
    await state.set_state(EditProfile.waiting_for_new_name)
    await message.answer(
        "✏️ *ویرایش نام*\n\n"
        "لطفاً نام جدید خود را وارد کنید:",
        reply_markup=cancel_kb
    )

@router.message(EditProfile.waiting_for_new_name)
async def edit_name_process(message: Message, state: FSMContext):
    if message.text == "❌ انصراف":
        await state.clear()
        uid = message.from_user.id
        menu = get_user_menu(uid)
        await message.answer("انصراف شد.", reply_markup=menu)
        return
    
    new_name = message.text.strip()
    if len(new_name) < 3:
        await message.answer("❌ نام باید حداقل ۳ حرف باشد. لطفاً دوباره وارد کنید:")
        return
    
    uid = message.from_user.id
    db.update_customer(uid, "name", new_name)
    await state.clear()
    
    await message.answer(
        f"✅ نام شما با موفقیت به «{new_name}» تغییر یافت.",
        reply_markup=edit_profile_menu
    )

@router.message(F.text == "✏️ ویرایش شماره تماس")
async def edit_phone_start(message: Message, state: FSMContext):
    await state.set_state(EditProfile.waiting_for_new_phone)
    await message.answer(
        "✏️ *ویرایش شماره تماس*\n\n"
        "لطفاً شماره تماس جدید خود را وارد کنید:\n"
        "(مثال: ۰۹۱۲۳۴۵۶۷۸۹)",
        reply_markup=cancel_kb
    )

@router.message(EditProfile.waiting_for_new_phone)
async def edit_phone_process(message: Message, state: FSMContext):
    if message.text == "❌ انصراف":
        await state.clear()
        uid = message.from_user.id
        menu = get_user_menu(uid)
        await message.answer("انصراف شد.", reply_markup=menu)
        return
    
    phone = message.text.strip().replace("+", "").replace(" ", "")
    
    if not phone.isdigit() or len(phone) < 10:
        await message.answer("❌ شماره تماس نامعتبر است. لطفاً دوباره وارد کنید:")
        return
    
    uid = message.from_user.id
    db.update_customer(uid, "phone", phone)
    await state.clear()
    
    await message.answer(
        f"✅ شماره تماس شما با موفقیت به {phone} تغییر یافت.",
        reply_markup=edit_profile_menu
    )

@router.message(F.text == "🔙 بازگشت به پروفایل")
async def back_to_profile(message: Message):
    await show_profile(message)
