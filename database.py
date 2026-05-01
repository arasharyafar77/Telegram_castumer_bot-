import sqlite3
import json

DB_PATH = "database.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()
    
    # Customers table
    c.execute("""CREATE TABLE IF NOT EXISTS customers (
        user_id INTEGER PRIMARY KEY, 
        name TEXT, 
        phone TEXT,
        registered INTEGER DEFAULT 0,
        approved INTEGER DEFAULT 0)""")
    
    # Orders table
    c.execute("""CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        customer_id INTEGER, 
        seller_id INTEGER,
        service TEXT, 
        description TEXT, 
        status TEXT DEFAULT 'pending',
        chat_active INTEGER DEFAULT 0, 
        created_at TEXT DEFAULT (datetime('now')))""")
    
    # Reviews table
    c.execute("""CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        order_id INTEGER, 
        customer_id INTEGER,
        seller_id INTEGER, 
        rating INTEGER, 
        comment TEXT)""")
    
    # Wallets table
    c.execute("""CREATE TABLE IF NOT EXISTS wallets (
        user_id INTEGER PRIMARY KEY, 
        balance REAL DEFAULT 0)""")
    
    # Transactions table
    c.execute("""CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        user_id INTEGER, 
        amount REAL,
        type TEXT, 
        status TEXT DEFAULT 'pending', 
        date TEXT DEFAULT (datetime('now')))""")
    
    # Tickets table
    c.execute("""CREATE TABLE IF NOT EXISTS tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        user_id INTEGER, 
        message TEXT,
        reply TEXT, 
        status TEXT DEFAULT 'open', 
        created_at TEXT DEFAULT (datetime('now')))""")
    
    conn.commit()
    conn.close()

# ─── Customers ───────────────────────────────────────────────
def get_customer(user_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM customers WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return row

def add_customer(user_id, name, phone):
    conn = get_conn()
    conn.execute("INSERT OR REPLACE INTO customers (user_id, name, phone, registered, approved) VALUES (?,?,?,1,0)",
                 (user_id, name, phone))
    conn.execute("INSERT OR IGNORE INTO wallets (user_id, balance) VALUES (?,0)", (user_id,))
    conn.commit()
    conn.close()

def update_customer(user_id, field, value):
    conn = get_conn()
    conn.execute(f"UPDATE customers SET {field}=? WHERE user_id=?", (value, user_id))
    conn.commit()
    conn.close()

def approve_customer(user_id):
    conn = get_conn()
    conn.execute("UPDATE customers SET approved=1 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def get_pending_customers():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM customers WHERE registered=1 AND approved=0").fetchall()
    conn.close()
    return rows

def get_all_customers():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM customers WHERE approved=1").fetchall()
    conn.close()
    return rows

# ─── Orders ──────────────────────────────────────────────────
def create_order(customer_id, service, description):
    conn = get_conn()
    c = conn.execute("INSERT INTO orders (customer_id, service, description) VALUES (?,?,?)",
                     (customer_id, service, description))
    oid = c.lastrowid
    conn.commit()
    conn.close()
    return oid

def get_order(order_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
    conn.close()
    return row

def get_orders_by_customer(customer_id):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM orders WHERE customer_id=? ORDER BY id DESC", (customer_id,)).fetchall()
    conn.close()
    return rows

def update_order_status(order_id, status):
    conn = get_conn()
    conn.execute("UPDATE orders SET status=? WHERE id=?", (status, order_id))
    conn.commit()
    conn.close()

def get_active_chat_order(user_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM orders WHERE customer_id=? AND chat_active=1 ORDER BY id DESC LIMIT 1",
                       (user_id,)).fetchone()
    conn.close()
    return row

def deactivate_chat(order_id):
    conn = get_conn()
    conn.execute("UPDATE orders SET chat_active=0 WHERE id=?", (order_id,))
    conn.commit()
    conn.close()

# ─── Reviews ─────────────────────────────────────────────────
def add_review(order_id, customer_id, seller_id, rating, comment):
    conn = get_conn()
    conn.execute("INSERT INTO reviews (order_id, customer_id, seller_id, rating, comment) VALUES (?,?,?,?,?)",
                 (order_id, customer_id, seller_id, rating, comment))
    conn.execute("UPDATE orders SET status='rated', chat_active=0 WHERE id=?", (order_id,))
    conn.commit()
    conn.close()

# ─── Wallets ─────────────────────────────────────────────────
def get_balance(user_id):
    conn = get_conn()
    row = conn.execute("SELECT balance FROM wallets WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return row["balance"] if row else 0

def change_balance(user_id, amount):
    conn = get_conn()
    conn.execute("INSERT OR IGNORE INTO wallets (user_id, balance) VALUES (?,0)", (user_id,))
    conn.execute("UPDATE wallets SET balance = balance + ? WHERE user_id=?", (amount, user_id))
    conn.commit()
    conn.close()

def add_transaction(user_id, amount, tx_type, status="pending"):
    conn = get_conn()
    c = conn.execute("INSERT INTO transactions (user_id, amount, type, status) VALUES (?,?,?,?)",
                     (user_id, amount, tx_type, status))
    tid = c.lastrowid
    conn.commit()
    conn.close()
    return tid

def update_transaction(tx_id, status):
    conn = get_conn()
    conn.execute("UPDATE transactions SET status=? WHERE id=?", (status, tx_id))
    conn.commit()
    conn.close()

def get_transactions(user_id):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM transactions WHERE user_id=? ORDER BY id DESC", (user_id,)).fetchall()
    conn.close()
    return rows

def get_pending_transactions():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM transactions WHERE status='pending'").fetchall()
    conn.close()
    return rows

def get_transaction(tx_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM transactions WHERE id=?", (tx_id,)).fetchone()
    conn.close()
    return row

# ─── Tickets ─────────────────────────────────────────────────
def add_ticket(user_id, message):
    conn = get_conn()
    c = conn.execute("INSERT INTO tickets (user_id, message) VALUES (?,?)", (user_id, message))
    tid = c.lastrowid
    conn.commit()
    conn.close()
    return tid

def get_tickets_by_user(user_id):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM tickets WHERE user_id=? ORDER BY id DESC", (user_id,)).fetchall()
    conn.close()
    return rows

def get_ticket(ticket_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,)).fetchone()
    conn.close()
    return row

def reply_ticket(ticket_id, reply):
    conn = get_conn()
    conn.execute("UPDATE tickets SET reply=?, status='answered' WHERE id=?", (reply, ticket_id))
    conn.commit()
    conn.close()

def close_ticket(ticket_id):
    conn = get_conn()
    conn.execute("UPDATE tickets SET status='closed' WHERE id=?", (ticket_id,))
    conn.commit()
    conn.close()

def get_all_tickets():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM tickets ORDER BY id DESC").fetchall()
    conn.close()
    return rows