from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from states import RegCustomer
from keyboards import customer_menu, service_categories_menu, role_kb, cancel_kb, confirm_kb, inline
import database as db

router = Router()

@router.message(F.text == "👤 مشتری")
async def start_customer_reg(message: Message, state: FSMContext):
    uid = message.from_user.id
    customer = db.get_customer(uid)
    
    if customer and customer["registered"] == 1 and customer["approved"] == 1:
        await message.answer("✅ شما قبلاً ثبت‌نام کرده‌اید.", reply_markup=customer_menu)
        return
    elif customer and customer["registered"] == 1 and customer["approved"] == 0:
        await message.answer(
            "⏳ ثبت‌نام شما در انتظار تأیید ادمین است.\n"
            "پس از تأیید، می‌توانید سفارش ثبت کنید.\n"
            "برای پیگیری به بخش پشتیبانی مراجعه کنید.",
            reply_markup=service_categories_menu
        )
        return
    
    await state.set_state(RegCustomer.waiting_for_form)
    await message.answer(
        "📝 *فرم ثبت‌نام مشتری*\n\n"
        "لطفاً اطلاعات خود را به صورت یکجا ارسال کنید:\n\n"
        "─────────────────────\n"
        "نام و نام خانوادگی: محمد رضایی\n"
        "شماره تماس: ۰۹۱۲۳۴۵۶۷۸۹\n"
        "─────────────────────\n\n"
        "❗️ دقیقاً به همین ترتیب و با رعایت فرمت وارد کنید.",
        reply_markup=inline(
            ("📋 مشاهده نمونه", "sample_form"),
            ("❌ انصراف", "cancel_reg")
        )
    )

@router.callback_query(F.data == "sample_form")
async def sample_form(call: CallbackQuery):
    await call.message.answer(
        "📋 *نمونه فرم ثبت‌نامه:*\n\n"
        "نام و نام خانوادگی: سارا احمدی\n"
        "شماره تماس: ۰۹۱۲۳۴۵۶۷۸۹\n\n"
        "⚠️ همین فرمت را با اطلاعات خودتان ارسال کنید.",
        reply_markup=inline(("🔙 بازگشت به فرم", "back_to_form"))
    )
    await call.answer()

@router.callback_query(F.data == "back_to_form")
async def back_to_form(call: CallbackQuery, state: FSMContext):
    await state.set_state(RegCustomer.waiting_for_form)
    await call.message.answer(
        "لطفاً فرم ثبت‌نامه را ارسال کنید:",
        reply_markup=inline(("📋 مشاهده نمونه", "sample_form"))
    )
    await call.answer()

@router.message(RegCustomer.waiting_for_form)
async def process_registration_form(message: Message, state: FSMContext, bot: Bot):
    if message.text == "❌ انصراف":
        await state.clear()
        await message.answer("انصراف شد.", reply_markup=service_categories_menu)
        return
    
    text = message.text.strip()
    
    try:
        lines = text.split('\n')
        data = {}
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().replace("نام و نام خانوادگی", "name").replace("شماره تماس", "phone")
                data[key] = value.strip()
        
        name = data.get("name", "")
        phone = data.get("phone", "")
        
        if not name or not phone:
            raise ValueError("اطلاعات ناقص")
        
        phone_clean = phone.replace("+", "").replace(" ", "")
        if not phone_clean.isdigit() or len(phone_clean) < 10:
            await message.answer("❌ شماره تماس نامعتبر است.\nلطفاً دوباره ارسال کنید:")
            return
        
        await state.update_data(name=name, phone=phone_clean)
        await state.set_state(RegCustomer.confirmation)
        
        await message.answer(
            f"📋 *مشخصات وارد شده:*\n\n"
            f"👤 نام: {name}\n"
            f"📱 شماره تماس: {phone_clean}\n\n"
            f"آیا اطلاعات صحیح است؟",
            reply_markup=confirm_kb
        )
        
    except Exception:
        await message.answer(
            "❌ فرمت وارد شده صحیح نیست.\n\n"
            "لطفاً دقیقاً به این صورت وارد کنید:\n"
            "نام و نام خانوادگی: [نام شما]\n"
            "شماره تماس: [شماره تماس]"
        )

@router.message(RegCustomer.confirmation)
async def confirm_registration(message: Message, state: FSMContext, bot: Bot):
    if message.text == "❌ انصراف":
        await state.clear()
        await message.answer("انصراف شد.", reply_markup=service_categories_menu)
        return
    
    if message.text == "✅ تأیید":
        data = await state.get_data()
        
        db.add_customer(message.from_user.id, data["name"], data["phone"])
        await state.clear()
        
        from config import ADMIN_ID
        await bot.send_message(
            ADMIN_ID,
            f"🆕 *درخواست ثبت‌نام جدید*\n\n"
            f"👤 نام: {data['name']}\n"
            f"📱 شماره: {data['phone']}\n"
            f"🆔 آیدی: {message.from_user.id}\n"
            f"Username: @{message.from_user.username or 'ندارد'}",
            reply_markup=inline(
                (f"✅ تأیید", f"approve_customer:{message.from_user.id}"),
                (f"❌ رد", f"reject_customer:{message.from_user.id}")
            )
        )
        
        await message.answer(
            "✅ *فرم ثبت‌نامه شما ارسال شد!*\n\n"
            "⏳ در انتظار تأیید ادمین...\n"
            "به محض تأیید، می‌توانید سفارش خود را ثبت کنید.\n\n"
            "فعلاً می‌توانید خدمات را مشاهده کنید.",
            reply_markup=service_categories_menu
        )
    else:
        await message.answer("لطفاً روی دکمه تأیید یا انصراف کلیک کنید.")

@router.callback_query(F.data.startswith("approve_customer:"))
async def approve_customer(call: CallbackQuery, bot: Bot):
    from config import ADMIN_ID
    if call.from_user.id != ADMIN_ID:
        await call.answer("❌ دسترسی غیرمجاز", show_alert=True)
        return
    
    user_id = int(call.data.split(":")[1])
    db.approve_customer(user_id)
    
    await call.message.edit_text(f"✅ مشتری {user_id} تأیید شد.")
    await bot.send_message(
        user_id,
        "✅ *ثبت‌نامه شما تأیید شد!*\n\n"
        "اکنون می‌توانید سفارش خود را ثبت کنید.\n"
        "به خانواده مارکت‌پلیس خوش آمدید 🎉",
        reply_markup=customer_menu
    )
    await call.answer()

@router.callback_query(F.data.startswith("reject_customer:"))
async def reject_customer(call: CallbackQuery, bot: Bot):
    from config import ADMIN_ID
    if call.from_user.id != ADMIN_ID:
        await call.answer("❌ دسترسی غیرمجاز", show_alert=True)
        return
    
    user_id = int(call.data.split(":")[1])
    
    await call.message.edit_text(f"❌ مشتری {user_id} رد شد.")
    await bot.send_message(
        user_id,
        "❌ *متأسفانه ثبت‌نامه شما تأیید نشد.*\n\n"
        "برای اطلاعات بیشتر با پشتیبانی تماس بگیرید."
    )
    await call.answer()

@router.callback_query(F.data == "cancel_reg")
async def cancel_registration(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.answer("ثبت‌نامه لغو شد.", reply_markup=service_categories_menu)
    await call.answer()
