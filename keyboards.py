from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def kb(*buttons, one_time=False):
    rows = []
    for row in buttons:
        if isinstance(row, (list, tuple)):
            rows.append([KeyboardButton(text=b) for b in row])
        else:
            rows.append([KeyboardButton(text=row)])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, one_time_keyboard=one_time)

def inline(*rows):
    keyboard = []
    for row in rows:
        if isinstance(row, (list, tuple)):
            keyboard.append([InlineKeyboardButton(text=b[0], callback_data=b[1]) for b in row])
        else:
            keyboard.append([InlineKeyboardButton(text=row[0], callback_data=row[1])])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# ─── Role selection ───────────────────────────────────────────
role_kb = kb(["👤 مشتری"])

# ─── Service Categories Menu ─────────────────────────────────
service_categories_menu = kb(
    ["🌐 ترجمه حرفه‌ای", "🎙 تبدیل ویس به متن"],
    ["🎨 طراحی لوگو", "📝 تولید محتوا"],
    ["🔧 سایر خدمات"]
)

# ─── Customer Menu (after approval) ──────────────────────────
customer_menu = kb(
    ["🛍 خدمات", "📋 سفارش‌های من"],
    ["💰 کیف پول", "🎫 پشتیبانی"],
    ["👤 پروفایل من", "📜 قوانین و راهنما"],
    ["🔙 بازگشت"]
)

# ─── Wallet Menu ─────────────────────────────────────────────
wallet_menu = kb(
    ["💵 شارژ کیف پول", "💸 برداشت"],
    ["📜 تاریخچه تراکنش‌ها", "🔙 بازگشت"]
)

# ─── Support Menu ────────────────────────────────────────────
support_menu = kb(
    ["📩 ارسال تیکت جدید", "📋 تیکت‌های من"],
    ["🔙 بازگشت"]
)

# ─── Edit Profile Menu ───────────────────────────────────────
edit_profile_menu = kb(
    ["✏️ ویرایش نام", "✏️ ویرایش شماره تماس"],
    ["🔙 بازگشت به پروفایل"]
)

# ─── Back and Cancel Buttons ─────────────────────────────────
back_kb = kb("🔙 بازگشت")
cancel_kb = kb("❌ انصراف")
confirm_kb = kb(["✅ تأیید", "❌ انصراف"])

# ─── Service Descriptions ────────────────────────────────────
SERVICE_DESCRIPTIONS = {
    "ترجمه حرفه‌ای": "🌐 *خدمات ترجمه حرفه‌ای*\n\n"
                     "✅ ترجمه متون تخصصی و عمومی\n"
                     "✅ ترجمه کتاب، مقاله، اسناد رسمی\n"
                     "✅ ترجمه انگلیسی به فارسی و بالعکس\n"
                     "✅ تحویل تضمینی در کوتاه‌ترین زمان\n"
                     "✅ ویرایش و بازبینی رایگان\n\n"
                     "📝 لطفاً توضیحات کامل متن مورد نظر برای ترجمه را ارسال کنید:",
    
    "تبدیل ویس به متن": "🎙 *خدمات تبدیل ویس به متن*\n\n"
                         "✅ تبدیل فایل‌های صوتی به متن دقیق\n"
                         "✅ پشتیبانی از فرمت‌های MP3، WAV، M4A\n"
                         "✅ تشخیص خودکار گوینده‌های مختلف\n"
                         "✅ دقت بالای ۹۸٪ در تشخیص گفتار\n"
                         "✅ تحویل در ۲۴ ساعت\n\n"
                         "📝 لطفاً فایل صوتی خود را ارسال کنید:",
    
    "طراحی لوگو": "🎨 *خدمات طراحی لوگو*\n\n"
                   "✅ طراحی لوگو حرفه‌ای و اختصاصی\n"
                   "✅ ارائه ۳ طرح اولیه\n"
                   "✅ فایل‌های نهایی با کیفیت بالا\n"
                   "✅ اصلاحات نامحدود\n\n"
                   "📝 لطفاً توضیحات کاملی از لوگوی مورد نظر خود بدهید:",
    
    "تولید محتوا": "📝 *خدمات تولید محتوا*\n\n"
                    "✅ تولید محتوای متنی حرفه‌ای\n"
                    "✅ مناسب برای وبسایت و شبکه‌های اجتماعی\n"
                    "✅ سئو شده و جذاب\n"
                    "✅ تحویل به موقع\n\n"
                    "📝 لطفاً موضوع، حجم و نوع محتوای مورد نظر را مشخص کنید:",
    
    "سایر خدمات": "🔧 *سایر خدمات*\n\n"
                   "اگر خدمتی مد نظر دارید که در لیست نیست، لطفاً توضیح دهید:\n\n"
                   "📝 توضیحات کامل درخواست خود را ارسال کنید:"
}

# ─── Order Actions (Inline) ─────────────────────────────────
def order_actions_customer(order_id):
    return inline(
        ("💬 چت با مجری", f"open_chat:{order_id}"),
        ("🔄 درخواست تغییر مجری", f"change_seller:{order_id}")
    )

def get_order_status_text(status):
    status_map = {
        "pending": "⏳ در انتظار مجری",
        "accepted": "✅ پذیرفته شده",
        "in_progress": "🔄 در حال انجام",
        "completed": "✅ تکمیل شده",
        "rated": "⭐ امتیاز داده شده"
    }
    return status_map.get(status, status)