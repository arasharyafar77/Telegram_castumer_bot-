from aiogram.fsm.state import State, StatesGroup

# ─── Customer Registration ───────────────────────────────────
class RegCustomer(StatesGroup):
    waiting_for_form = State()
    confirmation = State()

# ─── New Order ───────────────────────────────────────────────
class NewOrder(StatesGroup):
    service = State()
    description = State()
    waiting_for_confirmation = State()

# ─── Rating Flow ─────────────────────────────────────────────
class RatingFlow(StatesGroup):
    rating = State()
    strengths = State()
    weaknesses = State()

# ─── Wallet ──────────────────────────────────────────────────
class WalletStates(StatesGroup):
    waiting_for_amount = State()
    waiting_for_withdraw_amount = State()
    waiting_for_card = State()

# ─── Edit Profile ────────────────────────────────────────────
class EditProfile(StatesGroup):
    waiting_for_new_name = State()
    waiting_for_new_phone = State()

# ─── Ticket ──────────────────────────────────────────────────
class TicketStates(StatesGroup):
    waiting_for_message = State()