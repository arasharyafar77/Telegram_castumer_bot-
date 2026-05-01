from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from states import WalletStates
from keyboards import wallet_menu, customer_menu, cancel_kb, inline
import database as db

router = Router()

@router.message(F.text == "💰 کیف پول")
async def wallet_home(message: Message):
    uid = message.from_user.id
    balance = db.get_balance(uid)
    
    await message.answer(
        f"💰 *کیف پول شما*\n\n"
        f"💵 موجودی فعلی: {balance:,.0f} تومان\n\n"
        f"از منوی زیر می‌توانید اقدام به شارژ یا برداشت کنید:",
        reply_markup=wallet_menu
    )

@router.message(F.text == "💵 شارژ کیف پول")
async def deposit_start(message: Message, state: FSMContext):
    await state.set_state(WalletStates.waiting_for_amount)
    await message.answer(
        "💵 *شارژ کیف پول*\n\n"
        "لطفاً مبلغ مورد نظر برای شارژ را به تومان وارد کنید:\n"
        "(حداقل مبلغ: ۱۰,۰۰۰ تومان)",
        reply_markup=cancel_kb
    )

@router.message(WalletStates.waiting_for_amount)
async def deposit_amount(message: Message, state: FSMContext, bot: Bot):
    if message.text == "❌ انصراف":
        await state.clear()
        await message.answer("انصراف شد.", reply_markup=customer_menu)
        return
    
    try:
        amount = float(message.text.replace(",", "").replace(" ", ""))
        
        if amount < 10000:
            await message.answer("❌ حداقل مبلغ شارژ ۱۰,۰۰۰ تومان است. لطفاً دوباره وارد کنید:")
            return
        
        if amount > 50000000:
            await message.answer("❌ حداکثر مبلغ شارژ ۵۰,۰۰۰,۰۰۰ تومان است. لطفاً دوباره وارد کنید:")
            return
        
        # Create pending transaction
        tx_id = db.add_transaction(message.from_user.id, amount, "deposit", "pending")
        await state.clear()
        
        await message.answer(
            f"✅ *درخواست شارژ ثبت شد*\n\n"
            f"🔢 شماره تراکنش: {tx_id}\n"
            f"💵 مبلغ: {amount:,.0f} تومان\n\n"
            f"لطفاً مبلغ را به کارت زیر واریز کنید:\n"
            f"💳 `5894-6311-7132-1813`\n\n"
            f"بعد از واریز، لطفاً رسید را برای پشتیبانی ارسال کنید.\n"
            f"پس از تأیید ادمین، کیف پول شما شارژ می‌شود.",
            reply_markup=customer_menu
        )
        
        # Notify admin
        from config import ADMIN_ID
        await bot.send_message(
            ADMIN_ID,
            f"💰 *درخواست شارژ جدید*\n\n"
            f"👤 کاربر: {message.from_user.id}\n"
            f"💵 مبلغ: {amount:,.0f} تومان\n"
            f"🔢 تراکنش: #{tx_id}",
            reply_markup=inline(
                (f"✅ تأیید شارژ", f"approve_deposit:{tx_id}"),
                (f"❌ رد درخواست", f"reject_deposit:{tx_id}")
            )
        )
        
    except ValueError:
        await message.answer("❌ مبلغ نامعتبر است. لطفاً عدد وارد کنید:")

@router.message(F.text == "💸 برداشت")
async def withdraw_start(message: Message, state: FSMContext):
    balance = db.get_balance(message.from_user.id)
    
    if balance < 50000:
        await message.answer(
            f"❌ موجودی شما برای برداشت کافی نیست.\n\n"
            f"💰 موجودی فعلی: {balance:,.0f} تومان\n"
            f"حداقل مبلغ برداشت: ۵۰,۰۰۰ تومان",
            reply_markup=wallet_menu
        )
        return
    
    await state.set_state(WalletStates.waiting_for_withdraw_amount)
    await message.answer(
        f"💸 *برداشت از کیف پول*\n\n"
        f"💰 موجودی قابل برداشت: {balance:,.0f} تومان\n"
        f"حداقل مبلغ برداشت: ۵۰,۰۰۰ تومان\n\n"
        f"لطفاً مبلغ مورد نظر را وارد کنید:",
        reply_markup=cancel_kb
    )

@router.message(WalletStates.waiting_for_withdraw_amount)
async def withdraw_amount(message: Message, state: FSMContext, bot: Bot):
    if message.text == "❌ انصراف":
        await state.clear()
        await message.answer("انصراف شد.", reply_markup=customer_menu)
        return
    
    try:
        amount = float(message.text.replace(",", "").replace(" ", ""))
        balance = db.get_balance(message.from_user.id)
        
        if amount < 50000:
            await message.answer("❌ حداقل مبلغ برداشت ۵۰,۰۰۰ تومان است. لطفاً دوباره وارد کنید:")
            return
        
        if amount > balance:
            await message.answer(f"❌ موجودی کافی نیست.\n💰 موجودی شما: {balance:,.0f} تومان")
            return
        
        await state.update_data(withdraw_amount=amount)
        await state.set_state(WalletStates.waiting_for_card)
        await message.answer(
            "🏦 *اطلاعات کارت مقصد*\n\n"
            "لطفاً شماره کارت خود را وارد کنید:",
            reply_markup=cancel_kb
        )
        
    except ValueError:
        await message.answer("❌ مبلغ نامعتبر است. لطفاً عدد وارد کنید:")

@router.message(WalletStates.waiting_for_card)
async def withdraw_card(message: Message, state: FSMContext, bot: Bot):
    if message.text == "❌ انصراف":
        await state.clear()
        await message.answer("انصراف شد.", reply_markup=customer_menu)
        return
    
    card_number = message.text.strip().replace(" ", "")
    
    if not card_number.isdigit() or len(card_number) < 16:
        await message.answer("❌ شماره کارت نامعتبر است. لطفاً دوباره وارد کنید:")
        return
    
    data = await state.get_data()
    amount = data.get("withdraw_amount")
    
    # Create pending transaction
    tx_id = db.add_transaction(message.from_user.id, amount, "withdraw", "pending")
    await state.clear()
    
    await message.answer(
        f"✅ *درخواست برداشت ثبت شد*\n\n"
        f"🔢 شماره تراکنش: {tx_id}\n"
        f"💵 مبلغ: {amount:,.0f} تومان\n"
        f"💳 شماره کارت: {card_number}\n\n"
        f"درخواست شما در اسرع وقت بررسی و پرداخت می‌شود.",
        reply_markup=customer_menu
    )
    
    # Notify admin
    from config import ADMIN_ID
    await bot.send_message(
        ADMIN_ID,
        f"💸 *درخواست برداشت جدید*\n\n"
        f"👤 کاربر: {message.from_user.id}\n"
        f"💵 مبلغ: {amount:,.0f} تومان\n"
        f"💳 کارت مقصد: {card_number}\n"
        f"🔢 تراکنش: #{tx_id}",
        reply_markup=inline(
            (f"✅ تأیید برداشت", f"approve_withdraw:{tx_id}"),
            (f"❌ رد درخواست", f"reject_withdraw:{tx_id}")
        )
    )

@router.message(F.text == "📜 تاریخچه تراکنش‌ها")
async def transaction_history(message: Message):
    txs = db.get_transactions(message.from_user.id)
    
    if not txs:
        await message.answer("📭 تاریخچه تراکنشی ندارید.")
        return
    
    type_fa = {
        "deposit": "💰 شارژ",
        "withdraw": "💸 برداشت",
    }
    
    status_fa = {
        "pending": "⏳ در انتظار",
        "success": "✅ موفق",
        "failed": "❌ ناموفق"
    }
    
    text = "📜 *تاریخچه تراکنش‌ها:*\n\n"
    
    for tx in txs[:20]:
        text += (
            f"• {type_fa.get(tx['type'], tx['type'])}: "
            f"{tx['amount']:,.0f} تومان — "
            f"{status_fa.get(tx['status'], tx['status'])} — "
            f"{tx['date'][:10]}\n"
        )
    
    await message.answer(text)

# Admin approve handlers
@router.callback_query(F.data.startswith("approve_deposit:"))
async def approve_deposit(call: CallbackQuery, bot: Bot):
    from config import ADMIN_ID
    if call.from_user.id != ADMIN_ID:
        await call.answer("❌ دسترسی غیرمجاز", show_alert=True)
        return
    
    tx_id = int(call.data.split(":")[1])
    tx = db.get_transaction(tx_id)
    
    if not tx or tx["status"] != "pending":
        await call.answer("❌ تراکنش یافت نشد یا قبلاً بررسی شده.", show_alert=True)
        return
    
    db.update_transaction(tx_id, "success")
    db.change_balance(tx["user_id"], tx["amount"])
    
    await call.message.edit_text(f"✅ تراکنش #{tx_id} تأیید و شارژ شد.")
    
    await bot.send_message(
        tx["user_id"],
        f"✅ *کیف پول شما شارژ شد!*\n\n"
        f"💰 مبلغ: {tx['amount']:,.0f} تومان\n"
        f"🔢 شماره تراکنش: {tx_id}"
    )
    await call.answer()

@router.callback_query(F.data.startswith("reject_deposit:"))
async def reject_deposit(call: CallbackQuery, bot: Bot):
    from config import ADMIN_ID
    if call.from_user.id != ADMIN_ID:
        await call.answer("❌ دسترسی غیرمجاز", show_alert=True)
        return
    
    tx_id = int(call.data.split(":")[1])
    tx = db.get_transaction(tx_id)
    
    if not tx:
        await call.answer("❌ تراکنش یافت نشد.", show_alert=True)
        return
    
    db.update_transaction(tx_id, "failed")
    await call.message.edit_text(f"❌ تراکنش #{tx_id} رد شد.")
    
    await bot.send_message(
        tx["user_id"],
        f"❌ *درخواست شارژ شما رد شد*\n\n"
        f"🔢 شماره تراکنش: {tx_id}\n"
        f"برای اطلاعات بیشتر با پشتیبانی تماس بگیرید."
    )
    await call.answer()

@router.callback_query(F.data.startswith("approve_withdraw:"))
async def approve_withdraw(call: CallbackQuery, bot: Bot):
    from config import ADMIN_ID
    if call.from_user.id != ADMIN_ID:
        await call.answer("❌ دسترسی غیرمجاز", show_alert=True)
        return
    
    tx_id = int(call.data.split(":")[1])
    tx = db.get_transaction(tx_id)
    
    if not tx or tx["status"] != "pending":
        await call.answer("❌ تراکنش یافت نشد یا قبلاً بررسی شده.", show_alert=True)
        return
    
    db.update_transaction(tx_id, "success")
    db.change_balance(tx["user_id"], -tx["amount"])
    
    await call.message.edit_text(f"✅ تراکنش #{tx_id} تأیید شد.")
    
    await bot.send_message(
        tx["user_id"],
        f"✅ *درخواست برداشت شما تأیید شد*\n\n"
        f"💰 مبلغ: {tx['amount']:,.0f} تومان\n"
        f"🔢 شماره تراکنش: {tx_id}\n\n"
        f"وجه به حساب شما واریز خواهد شد."
    )
    await call.answer()

@router.callback_query(F.data.startswith("reject_withdraw:"))
async def reject_withdraw(call: CallbackQuery, bot: Bot):
    from config import ADMIN_ID
    if call.from_user.id != ADMIN_ID:
        await call.answer("❌ دسترسی غیرمجاز", show_alert=True)
        return
    
    tx_id = int(call.data.split(":")[1])
    tx = db.get_transaction(tx_id)
    
    if not tx:
        await call.answer("❌ تراکنش یافت نشد.", show_alert=True)
        return
    
    db.update_transaction(tx_id, "failed")
    await call.message.edit_text(f"❌ تراکنش #{tx_id} رد شد.")
    
    await bot.send_message(
        tx["user_id"],
        f"❌ *درخواست برداشت شما رد شد*\n\n"
        f"🔢 شماره تراکنش: {tx_id}\n"
        f"برای اطلاعات بیشتر با پشتیبانی تماس بگیرید."
    )
    await call.answer()
