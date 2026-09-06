import streamlit as st
import pandas as pd
from datetime import datetime, date, time, timezone, timedelta
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine, text

# ----------------- EGYPT TIMEZONE SETUP (UTC+3) -----------------
EGYPT_TZ = timezone(timedelta(hours=3))

def get_egypt_now():
    return datetime.now(EGYPT_TZ)

def get_egypt_now_str():
    return get_egypt_now().strftime("%Y-%m-%d %H:%M:%S")

def get_egypt_today_str():
    egypt_now = get_egypt_now()
    business_now = egypt_now - timedelta(hours=4)
    return business_now.strftime("%Y-%m-%d")

ARABIC_DAYS = {
    "Monday": "الإثنين", "Tuesday": "الثلاثاء", "Wednesday": "الأربعاء",
    "Thursday": "الخميس", "Friday": "الجمعة", "Saturday": "السبت", "Sunday": "الأحد"
}

def format_arabic_time(t_str):
    if not t_str:
        return ""
    return str(t_str).replace("AM", "ص").replace("PM", "م").replace("am", "ص").replace("pm", "م")

# ----------------- APP CONFIG & SAFE ARABIC STYLING -----------------
st.set_page_config(page_title="Photobooth Management System", page_icon="📸", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800;900&display=swap');
    
    /* تطبيق الخط العربي على النصوص دون كسر خط الأيقونات الخاص بـ Streamlit */
    p, h1, h2, h3, h4, h5, h6, label, .stMetric, .stDataFrame, .stSelectbox, .stTextInput, .stNumberInput {
        font-family: 'Cairo', sans-serif !important;
    }
    
    #MainMenu { visibility: hidden !important; }
    header { visibility: hidden !important; }
    footer { visibility: hidden !important; }
    [data-testid="stSidebar"] { display: none !important; }
    [data-testid="collapsedControl"] { display: none !important; }
    
    .stApp {
        direction: rtl;
        text-align: right;
    }

    /* حماية الأيقونات وأسهم الـ Expander من التحول لكلمات إنجليزية */
    [data-testid="stExpanderToggleIcon"], .material-icons, [class*="material-symbols"] {
        font-family: 'Material Icons', 'Material Symbols Outlined' !important;
        direction: ltr !important;
    }

    .alert-card-danger {
        background-color: rgba(255, 75, 75, 0.12);
        border: 1px solid #ff4b4b;
        border-radius: 12px;
        padding: 14px 18px;
        color: #ff6b6b;
        font-weight: 700;
        margin-bottom: 14px;
        text-align: right;
    }
    .alert-card-success {
        background-color: rgba(0, 204, 150, 0.12);
        border: 1px solid #00CC96;
        border-radius: 12px;
        padding: 14px 18px;
        color: #00CC96;
        font-weight: 700;
        margin-bottom: 14px;
        text-align: right;
    }
    .event-card {
        background-color: #1a1d24;
        border: 1px solid #2d323f;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 16px;
        direction: rtl;
        text-align: right;
    }
    .event-top {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid #2d323f;
        padding-bottom: 12px;
        margin-bottom: 12px;
    }
    .event-title {
        font-size: 19px;
        font-weight: 800;
        color: #ffffff;
    }
    .badge-heaven {
        background-color: #00CC96;
        color: white;
        padding: 4px 12px;
        border-radius: 6px;
        font-weight: 700;
        font-size: 13px;
    }
    .badge-9a {
        background-color: #636EFA;
        color: white;
        padding: 4px 12px;
        border-radius: 6px;
        font-weight: 700;
        font-size: 13px;
    }
    .event-meta {
        font-size: 14px;
        color: #a5abb8;
        margin-bottom: 12px;
        line-height: 1.6;
    }
    .event-finance-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
        gap: 10px;
        background-color: #12141a;
        padding: 12px;
        border-radius: 8px;
    }
    .finance-label {
        font-size: 12px;
        color: #848a99;
        margin-bottom: 3px;
    }
    .finance-val {
        font-size: 15px;
        font-weight: 700;
        color: #ffffff;
    }
    .finance-val-green {
        font-size: 15px;
        font-weight: 700;
        color: #00CC96;
    }
    .finance-val-red {
        font-size: 15px;
        font-weight: 700;
        color: #ff4b4b;
    }
    </style>
""", unsafe_allow_html=True)

# ----------------- DB SETUP & AUTO-MIGRATION -----------------
try:
    if "DATABASE_URL" in st.secrets:
        DB_URL = st.secrets["DATABASE_URL"]
        IS_POSTGRES = True
    else:
        DB_URL = "sqlite:///photobooth.db"
        IS_POSTGRES = False
except Exception:
    DB_URL = "sqlite:///photobooth.db"
    IS_POSTGRES = False

engine = create_engine(DB_URL, pool_pre_ping=True)

def init_db():
    pk_def = "id SERIAL PRIMARY KEY" if IS_POSTGRES else "id INTEGER PRIMARY KEY AUTOINCREMENT"
    with engine.begin() as conn:
        conn.execute(text(f"CREATE TABLE IF NOT EXISTS days ({pk_def}, date TEXT UNIQUE NOT NULL)"))
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS transactions (
                {pk_def}, day_id INTEGER NOT NULL, timestamp TEXT NOT NULL,
                prints_count INTEGER NOT NULL, amount_paid REAL NOT NULL,
                branch TEXT NOT NULL, is_collected INTEGER DEFAULT 1,
                FOREIGN KEY (day_id) REFERENCES days(id)
            )
        """))
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS inventory (
                {pk_def}, timestamp TEXT NOT NULL, action_type TEXT NOT NULL,
                quantity INTEGER NOT NULL, notes TEXT, branch TEXT NOT NULL
            )
        """))
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS audit_logs (
                {pk_def}, timestamp TEXT NOT NULL, branch TEXT NOT NULL,
                action_type TEXT NOT NULL, transaction_id INTEGER,
                entity_type TEXT DEFAULT 'transaction', entity_id INTEGER, details TEXT NOT NULL
            )
        """))
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS employee_leaves (
                {pk_def}, timestamp TEXT NOT NULL, branch TEXT NOT NULL,
                action_type TEXT NOT NULL, days_count INTEGER NOT NULL, notes TEXT
            )
        """))
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS expenses (
                {pk_def}, day_id INTEGER, timestamp TEXT NOT NULL, date TEXT NOT NULL,
                branch TEXT NOT NULL, amount REAL NOT NULL, description TEXT NOT NULL,
                created_by TEXT NOT NULL, category TEXT DEFAULT 'نثريات وتشغيل',
                FOREIGN KEY (day_id) REFERENCES days(id)
            )
        """))
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS events (
                {pk_def}, created_at TEXT NOT NULL, event_date TEXT NOT NULL,
                client_name TEXT NOT NULL, location TEXT NOT NULL, device TEXT NOT NULL,
                hours INTEGER NOT NULL, start_time TEXT NOT NULL, end_time TEXT NOT NULL,
                total_amount REAL NOT NULL, deposit_paid REAL NOT NULL,
                remaining_amount REAL NOT NULL, status TEXT NOT NULL, prints_used INTEGER DEFAULT 0,
                paper_cost REAL DEFAULT 0, transport_cost REAL DEFAULT 0, worker_cost REAL DEFAULT 0,
                total_expenses REAL DEFAULT 0, net_profit REAL DEFAULT 0, notes TEXT
            )
        """))
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS branch_settings (
                branch TEXT PRIMARY KEY,
                rent REAL DEFAULT 0.0,
                salary REAL DEFAULT 0.0,
                bills REAL DEFAULT 0.0,
                cost_per_print REAL DEFAULT 3.0,
                updated_at TEXT
            )
        """))
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS cash_drawings (
                {pk_def}, timestamp TEXT NOT NULL, date TEXT NOT NULL,
                amount REAL NOT NULL, receiver TEXT NOT NULL, notes TEXT
            )
        """))

    alters = [
        "ALTER TABLE transactions ADD COLUMN is_collected INTEGER DEFAULT 1",
        "ALTER TABLE expenses ADD COLUMN day_id INTEGER",
        "ALTER TABLE expenses ADD COLUMN category TEXT DEFAULT 'نثريات وتشغيل'",
        "ALTER TABLE audit_logs ADD COLUMN entity_type TEXT DEFAULT 'transaction'",
        "ALTER TABLE audit_logs ADD COLUMN entity_id INTEGER",
        "UPDATE audit_logs SET entity_id = transaction_id WHERE entity_id IS NULL AND transaction_id IS NOT NULL"
    ]
    for q in alters:
        try:
            with engine.begin() as conn:
                conn.execute(text(q))
        except Exception:
            pass

    try:
        with engine.begin() as conn:
            if IS_POSTGRES:
                conn.execute(text("INSERT INTO days (date) SELECT DISTINCT date FROM expenses WHERE date IS NOT NULL AND date != '' ON CONFLICT (date) DO NOTHING"))
                conn.execute(text("UPDATE expenses e SET day_id = d.id FROM days d WHERE e.date = d.date AND e.day_id IS NULL"))
            else:
                conn.execute(text("INSERT OR IGNORE INTO days (date) SELECT DISTINCT date FROM expenses WHERE date IS NOT NULL AND date != ''"))
                conn.execute(text("UPDATE expenses SET day_id = (SELECT id FROM days WHERE days.date = expenses.date) WHERE day_id IS NULL"))
    except Exception:
        pass

    with engine.begin() as conn:
        conn.execute(text("UPDATE expenses SET category = 'توزيعات أرباح' WHERE description LIKE '%توزيع ارباح%'"))

    # ضبط الأرصدة الافتتاحية بدقة مطابقة للواقع
    with engine.begin() as conn:
        check_init = conn.execute(text("SELECT COUNT(*) FROM inventory WHERE branch = 'Warehouse'")).fetchone()[0]
        if check_init == 0:
            conn.execute(text("""
                INSERT INTO inventory (timestamp, action_type, quantity, notes, branch)
                VALUES (:ts, 'restock', 7400, 'رصيد مخزن افتتاحي (74 باكتة)', 'Warehouse')
            """), {"ts": get_egypt_now_str()})
            conn.execute(text("""
                INSERT INTO inventory (timestamp, action_type, quantity, notes, branch)
                VALUES (:ts, 'restock_ink', 3, 'رصيد حبر افتتاحي (علبة ونصف = 3 مليات)', 'Warehouse_Ink')
            """), {"ts": get_egypt_now_str()})

        # كل المعاملات تعتبر محصلة كاش في جيبك (بما فيها إيفنتات فادي الـ 3100 ج)
        # المعلق فقط: مبيعات السبت 5-9 لفرعي 9A (340 ج) و Heaven (1330 ج) = 1670 ج.م
        conn.execute(text("UPDATE transactions SET is_collected = 1"))
        conn.execute(text("""
            UPDATE transactions 
            SET is_collected = 0 
            WHERE timestamp >= '2026-09-05 05:00:00' 
              AND branch IN ('9A', 'Heaven')
        """))

    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO branch_settings (branch, rent, salary, bills, cost_per_print, updated_at)
            VALUES ('9A', 3000, 4000, 650, 3.0, :ts)
            ON CONFLICT (branch) DO NOTHING
        """), {"ts": get_egypt_now_str()})
        conn.execute(text("""
            INSERT INTO branch_settings (branch, rent, salary, bills, cost_per_print, updated_at)
            VALUES ('Heaven', 2500, 2500, 0, 3.0, :ts)
            ON CONFLICT (branch) DO NOTHING
        """), {"ts": get_egypt_now_str()})

init_db()

# ----------------- GENERAL & SETTINGS HELPERS -----------------
def get_or_create_day_id(date_str: str) -> int:
    with engine.begin() as conn:
        row = conn.execute(text("SELECT id FROM days WHERE date = :date"), {"date": date_str}).fetchone()
        if not row:
            if IS_POSTGRES:
                res = conn.execute(text("INSERT INTO days (date) VALUES (:date) RETURNING id"), {"date": date_str}).fetchone()
                return res[0]
            else:
                conn.execute(text("INSERT INTO days (date) VALUES (:date)"), {"date": date_str})
                res = conn.execute(text("SELECT last_insert_rowid()")).fetchone()
                return res[0]
        return row[0]

def get_branch_settings(branch_name: str):
    with engine.connect() as conn:
        row = conn.execute(text("SELECT * FROM branch_settings WHERE branch = :b"), {"b": branch_name}).mappings().fetchone()
        if row:
            return dict(row)
        return {"rent": 0.0, "salary": 0.0, "bills": 0.0, "cost_per_print": 3.0}

def update_branch_settings(branch_name: str, rent: float, salary: float, bills: float, cost_per_print: float):
    now_str = get_egypt_now_str()
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO branch_settings (branch, rent, salary, bills, cost_per_print, updated_at)
            VALUES (:b, :r, :s, :bills, :c, :ts)
            ON CONFLICT (branch) DO UPDATE 
            SET rent = :r, salary = :s, bills = :bills, cost_per_print = :c, updated_at = :ts
        """), {"b": branch_name, "r": rent, "s": salary, "bills": bills, "c": cost_per_print, "ts": now_str})

# ----------------- LEAVES HELPERS -----------------
def check_and_add_monthly_allowance():
    current_month_str = get_egypt_now().strftime("%Y-%m")
    with engine.begin() as conn:
        for b in ["Heaven", "9A"]:
            row = conn.execute(
                text("SELECT id FROM employee_leaves WHERE branch = :branch AND action_type = 'monthly_allowance' AND notes LIKE :month_pattern"),
                {"branch": b, "month_pattern": f"%{current_month_str}%"}
            ).fetchone()
            if not row:
                conn.execute(text("""
                    INSERT INTO employee_leaves (timestamp, branch, action_type, days_count, notes)
                    VALUES (:ts, :branch, 'monthly_allowance', 4, :notes)
                """), {"ts": get_egypt_now_str(), "branch": b, "notes": f"رصيد إجازات شهر {current_month_str}"})

def get_leave_balance(branch_name: str):
    with engine.connect() as conn:
        res = conn.execute(text("SELECT COALESCE(SUM(days_count), 0) FROM employee_leaves WHERE branch = :b"), {"b": branch_name}).fetchone()
        return res[0] if res else 0

def record_leave(branch_name: str, notes: str = "إجازة اعتيادية"):
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO employee_leaves (timestamp, branch, action_type, days_count, notes)
            VALUES (:ts, :b, 'leave_taken', -1, :notes)
        """), {"ts": get_egypt_now_str(), "b": branch_name, "notes": notes})

# ----------------- INVENTORY & INK HELPERS -----------------
def get_current_stock(target: str):
    with engine.connect() as conn:
        res = conn.execute(
            text("SELECT COALESCE(SUM(quantity), 0) FROM inventory WHERE branch = :b AND action_type NOT LIKE '%ink%'"),
            {"b": target}
        ).fetchone()
        return res[0] if res else 0

def get_waste_count(branch_name: str = None):
    with engine.connect() as conn:
        if branch_name and branch_name != "الكل":
            res = conn.execute(text("SELECT ABS(COALESCE(SUM(quantity), 0)) FROM inventory WHERE action_type = 'waste' AND branch = :b"), {"b": branch_name}).fetchone()
        else:
            res = conn.execute(text("SELECT ABS(COALESCE(SUM(quantity), 0)) FROM inventory WHERE action_type = 'waste'")).fetchone()
        return res[0] if res else 0

def get_free_count(branch_name: str = None):
    with engine.connect() as conn:
        if branch_name and branch_name != "الكل":
            res = conn.execute(text("SELECT ABS(COALESCE(SUM(quantity), 0)) FROM inventory WHERE action_type = 'free' AND branch = :b"), {"b": branch_name}).fetchone()
        else:
            res = conn.execute(text("SELECT ABS(COALESCE(SUM(quantity), 0)) FROM inventory WHERE action_type = 'free'")).fetchone()
        return res[0] if res else 0

def get_ink_refills(target: str):
    with engine.connect() as conn:
        if target == "Warehouse":
            res = conn.execute(text("SELECT COALESCE(SUM(quantity), 0) FROM inventory WHERE branch = 'Warehouse_Ink'")).fetchone()
        else:
            res = conn.execute(text("SELECT COALESCE(SUM(quantity), 0) FROM inventory WHERE branch = :b AND action_type = 'transfer_in_ink'"), {"b": target}).fetchone()
        return res[0] if res else 0

def add_warehouse_stock(packets: int, ink_bottles: float, cost: float, notes: str = ""):
    now_str = get_egypt_now_str()
    sheets = packets * 100
    refills = int(round(ink_bottles * 2))
    with engine.begin() as conn:
        if sheets > 0:
            conn.execute(text("""
                INSERT INTO inventory (timestamp, action_type, quantity, notes, branch)
                VALUES (:ts, 'restock', :qty, :notes, 'Warehouse')
            """), {"ts": now_str, "qty": sheets, "notes": f"شراء {packets} باكتة ورق | {notes}"})
        if refills > 0:
            conn.execute(text("""
                INSERT INTO inventory (timestamp, action_type, quantity, notes, branch)
                VALUES (:ts, 'restock_ink', :qty, :notes, 'Warehouse_Ink')
            """), {"ts": now_str, "qty": refills, "notes": f"شراء حبر: {ink_bottles} علبة ({refills} ملوة) | {notes}"})
        if cost > 0:
            today_str = get_egypt_today_str()
            d_id = get_or_create_day_id(today_str)
            conn.execute(text("""
                INSERT INTO expenses (day_id, timestamp, date, branch, amount, description, created_by, category)
                VALUES (:d_id, :ts, :date, 'Warehouse', :amount, :desc, 'المدير', 'مشتريات مخزن وأصول')
            """), {"d_id": d_id, "ts": now_str, "date": today_str, "amount": cost, "desc": f"فاتورة شراء خامات: {packets} باكتة ورق + {ink_bottles} علبة حبر"})

def transfer_stock_to_branch(to_branch: str, sheets_count: int, notes: str = ""):
    now_str = get_egypt_now_str()
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO inventory (timestamp, action_type, quantity, notes, branch)
            VALUES (:ts, 'transfer_out', :qty, :notes, 'Warehouse')
        """), {"ts": now_str, "qty": -sheets_count, "notes": f"تحويل إلى فرع {to_branch} | {notes}"})
        conn.execute(text("""
            INSERT INTO inventory (timestamp, action_type, quantity, notes, branch)
            VALUES (:ts, 'transfer_in', :qty, :notes, :branch)
        """), {"ts": now_str, "qty": sheets_count, "notes": f"مستلم من المخزن الرئيسي | {notes}", "branch": to_branch})

def transfer_ink_to_branch(to_branch: str, refills_count: int, notes: str = ""):
    now_str = get_egypt_now_str()
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO inventory (timestamp, action_type, quantity, notes, branch)
            VALUES (:ts, 'transfer_out_ink', :qty, :notes, 'Warehouse_Ink')
        """), {"ts": now_str, "qty": -refills_count, "notes": f"تزويد فرع {to_branch} بـ {refills_count} ملوة طابعة | {notes}"})
        conn.execute(text("""
            INSERT INTO inventory (timestamp, action_type, quantity, notes, branch)
            VALUES (:ts, 'transfer_in_ink', :qty, :notes, :branch)
        """), {"ts": now_str, "qty": refills_count, "notes": f"استلام {refills_count} ملوة حبر من المخزن | {notes}", "branch": to_branch})

def record_waste(branch_name: str, quantity: int = 1, notes: str = "ورقة تالفة"):
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO inventory (timestamp, action_type, quantity, notes, branch)
            VALUES (:ts, 'waste', :qty, :notes, :b)
        """), {"ts": get_egypt_now_str(), "qty": -quantity, "notes": notes, "b": branch_name})

def record_free_prints(branch_name: str, prints_count: int, notes: str = "طباعة مجانية / ضيافة"):
    now_str = get_egypt_now_str()
    today_str = get_egypt_today_str()
    day_id = get_or_create_day_id(today_str)
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO transactions (day_id, timestamp, prints_count, amount_paid, branch, is_collected)
            VALUES (:day_id, :ts, :prints, 0.0, :b, 1)
        """), {"day_id": day_id, "ts": now_str, "prints": prints_count, "b": branch_name})
        conn.execute(text("""
            INSERT INTO inventory (timestamp, action_type, quantity, notes, branch)
            VALUES (:ts, 'free', :qty, :notes, :b)
        """), {"ts": now_str, "qty": -prints_count, "notes": notes, "b": branch_name})

# ----------------- TRANSACTIONS HELPERS -----------------
def record_transaction(branch_name: str, prints_count: int, amount_paid: float):
    now_str = get_egypt_now_str()
    today_str = get_egypt_today_str()
    day_id = get_or_create_day_id(today_str)
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO transactions (day_id, timestamp, prints_count, amount_paid, branch, is_collected)
            VALUES (:day_id, :ts, :prints, :amount, :b, 0)
        """), {"day_id": day_id, "ts": now_str, "prints": prints_count, "amount": amount_paid, "b": branch_name})
        conn.execute(text("""
            INSERT INTO inventory (timestamp, action_type, quantity, notes, branch)
            VALUES (:ts, 'consumption', :qty, 'Transaction consumption', :b)
        """), {"ts": now_str, "qty": -prints_count, "b": branch_name})

def delete_transaction(tx_id: int, branch_name: str):
    now_str = get_egypt_now_str()
    with engine.begin() as conn:
        tx = conn.execute(text("SELECT * FROM transactions WHERE id = :id AND branch = :b"), {"id": tx_id, "b": branch_name}).mappings().fetchone()
        if tx:
            conn.execute(text("""
                INSERT INTO inventory (timestamp, action_type, quantity, notes, branch)
                VALUES (:ts, 'restock', :qty, :notes, :b)
            """), {"ts": now_str, "qty": tx["prints_count"], "notes": f"استرجاع ورق لحذف المعاملة #{tx_id}", "b": branch_name})
            conn.execute(text("""
                INSERT INTO audit_logs (timestamp, branch, action_type, entity_type, entity_id, details)
                VALUES (:ts, :b, 'حذف مبيعات', 'transaction', :tx_id, :details)
            """), {"ts": now_str, "b": branch_name, "tx_id": tx_id, "details": f"تم حذف العملية (الوقت: {tx['timestamp']} | الورق: {tx['prints_count']} | المبلغ: {tx['amount_paid']} ج.م)"})
            conn.execute(text("DELETE FROM transactions WHERE id = :id"), {"id": tx_id})
            return True
    return False

def update_transaction(tx_id: int, branch_name: str, new_prints: int, new_amount: float):
    now_str = get_egypt_now_str()
    with engine.begin() as conn:
        tx = conn.execute(text("SELECT * FROM transactions WHERE id = :id AND branch = :b"), {"id": tx_id, "b": branch_name}).mappings().fetchone()
        if tx:
            diff_prints = new_prints - tx["prints_count"]
            if diff_prints != 0:
                conn.execute(text("""
                    INSERT INTO inventory (timestamp, action_type, quantity, notes, branch)
                    VALUES (:ts, 'consumption', :qty, :notes, :b)
                """), {"ts": now_str, "qty": -diff_prints, "notes": f"تسوية فرق ورق لتعديل المعاملة #{tx_id}", "b": branch_name})
            conn.execute(text("""
                INSERT INTO audit_logs (timestamp, branch, action_type, entity_type, entity_id, details)
                VALUES (:ts, :b, 'تعديل مبيعات', 'transaction', :tx_id, :details)
            """), {"ts": now_str, "b": branch_name, "tx_id": tx_id, "details": f"تعديل من ({tx['prints_count']} ورق - {tx['amount_paid']} ج) إلى ({new_prints} ورق - {new_amount} ج)"})
            conn.execute(text("UPDATE transactions SET prints_count = :prints, amount_paid = :amount WHERE id = :id"), {"prints": new_prints, "amount": new_amount, "id": tx_id})
            return True
    return False

def mark_transactions_collected(branch_name: str = None):
    with engine.begin() as conn:
        if branch_name and branch_name != "الكل":
            conn.execute(text("UPDATE transactions SET is_collected = 1 WHERE branch = :b AND is_collected = 0"), {"b": branch_name})
        else:
            conn.execute(text("UPDATE transactions SET is_collected = 1 WHERE is_collected = 0"))

def record_cash_drawing(amount: float, receiver: str, notes: str):
    now_str = get_egypt_now_str()
    today_str = get_egypt_today_str()
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO cash_drawings (timestamp, date, amount, receiver, notes)
            VALUES (:ts, :date, :amount, :rec, :notes)
        """), {"ts": now_str, "date": today_str, "amount": amount, "rec": receiver, "notes": notes})

# ----------------- EXPENSES HELPERS -----------------
def record_expense(branch_name: str, amount: float, description: str, created_by: str, category: str = "نثريات وتشغيل"):
    now_str = get_egypt_now_str()
    today_str = get_egypt_today_str()
    day_id = get_or_create_day_id(today_str)
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO expenses (day_id, timestamp, date, branch, amount, description, created_by, category)
            VALUES (:day_id, :ts, :date, :b, :amount, :desc, :user, :cat)
        """), {"day_id": day_id, "ts": now_str, "date": today_str, "b": branch_name, "amount": amount, "desc": description, "user": created_by, "cat": category})

def delete_expense(exp_id: int, branch_name: str = None):
    now_str = get_egypt_now_str()
    with engine.begin() as conn:
        branch_clause = "AND branch = :b" if branch_name and branch_name != "All" and branch_name != "الكل" else ""
        params = {"id": exp_id}
        if branch_clause:
            params["b"] = branch_name
        exp = conn.execute(text(f"SELECT * FROM expenses WHERE id = :id {branch_clause}"), params).mappings().fetchone()
        if exp:
            conn.execute(text("""
                INSERT INTO audit_logs (timestamp, branch, action_type, entity_type, entity_id, details)
                VALUES (:ts, :b, 'حذف مصروف', 'expense', :exp_id, :details)
            """), {"ts": now_str, "b": exp["branch"], "exp_id": exp_id, "details": f"تم حذف مصروف #{exp_id} بقيمة {exp['amount']} ج.م ({exp['description']})"})
            conn.execute(text("DELETE FROM expenses WHERE id = :id"), {"id": exp_id})
            return True
    return False

def update_expense(exp_id: int, new_amount: float, new_desc: str, branch_name: str = None):
    now_str = get_egypt_now_str()
    with engine.begin() as conn:
        branch_clause = "AND branch = :b" if branch_name and branch_name != "All" and branch_name != "الكل" else ""
        params = {"id": exp_id}
        if branch_clause:
            params["b"] = branch_name
        exp = conn.execute(text(f"SELECT * FROM expenses WHERE id = :id {branch_clause}"), params).mappings().fetchone()
        if exp:
            conn.execute(text("""
                INSERT INTO audit_logs (timestamp, branch, action_type, entity_type, entity_id, details)
                VALUES (:ts, :b, 'تعديل مصروف', 'expense', :exp_id, :details)
            """), {"ts": now_str, "b": exp["branch"], "exp_id": exp_id, "details": f"تعديل مصروف #{exp_id} من ({exp['amount']} ج - {exp['description']}) إلى ({new_amount} ج - {new_desc})"})
            conn.execute(text("UPDATE expenses SET amount = :amount, description = :desc WHERE id = :id"), {"amount": new_amount, "desc": new_desc, "id": exp_id})
            return True
    return False

# ----------------- EVENTS HELPERS -----------------
def create_event(event_date: str, client_name: str, location: str, device: str, hours: int, start_time: str, end_time: str, total_amount: float, deposit_paid: float, notes: str):
    now_str = get_egypt_now_str()
    remaining = total_amount - deposit_paid
    status = "قيد الانتظار"
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO events (created_at, event_date, client_name, location, device, hours, start_time, end_time, total_amount, deposit_paid, remaining_amount, status, notes)
            VALUES (:created_at, :event_date, :client_name, :location, :device, :hours, :start_time, :end_time, :total_amount, :deposit_paid, :remaining_amount, :status, :notes)
        """), {
            "created_at": now_str, "event_date": event_date, "client_name": client_name,
            "location": location, "device": device, "hours": hours, "start_time": start_time,
            "end_time": end_time, "total_amount": total_amount, "deposit_paid": deposit_paid,
            "remaining_amount": remaining, "status": status, "notes": notes
        })
        if deposit_paid > 0:
            d_id = get_or_create_day_id(event_date)
            conn.execute(text("""
                INSERT INTO transactions (day_id, timestamp, prints_count, amount_paid, branch, is_collected)
                VALUES (:day_id, :ts, 0, :amount, 'Events', 0)
            """), {"day_id": d_id, "ts": now_str, "amount": deposit_paid})

def complete_event_settlement(event_id: int, prints_count: int, transport_cost: float, worker_cost: float):
    now_str = get_egypt_now_str()
    paper_cost = prints_count * 3.0
    total_exp = paper_cost + transport_cost + worker_cost
    with engine.begin() as conn:
        ev = conn.execute(text("SELECT * FROM events WHERE id = :id"), {"id": event_id}).mappings().fetchone()
        if ev:
            rem = ev["remaining_amount"]
            event_date = ev["event_date"]
            total_rev = ev["total_amount"]
            profit = total_rev - total_exp
            d_id = get_or_create_day_id(event_date)
            if rem > 0:
                conn.execute(text("""
                    INSERT INTO transactions (day_id, timestamp, prints_count, amount_paid, branch, is_collected)
                    VALUES (:day_id, :ts, :prints, :amount, 'Events', 1)
                """), {"day_id": d_id, "ts": now_str, "prints": prints_count, "amount": rem})
            if total_exp > 0:
                desc = f"مصروف إيفنت #{event_id} ({ev['client_name']}): ورق={paper_cost}ج، مواصلات={transport_cost}ج، موظف={worker_cost}ج"
                conn.execute(text("""
                    INSERT INTO expenses (day_id, timestamp, date, branch, amount, description, created_by, category)
                    VALUES (:day_id, :ts, :date, 'Events', :amount, :desc, 'تسوية إيفنت', 'تشغيل إيفنتات')
                """), {"day_id": d_id, "ts": now_str, "date": event_date, "amount": total_exp, "desc": desc})
            conn.execute(text("""
                UPDATE events
                SET deposit_paid = total_amount, remaining_amount = 0, status = 'تم التنفيذ والتسوية',
                    prints_used = :prints, paper_cost = :p_cost, transport_cost = :t_cost,
                    worker_cost = :w_cost, total_expenses = :tot_exp, net_profit = :profit
                WHERE id = :id
            """), {"prints": prints_count, "p_cost": paper_cost, "t_cost": transport_cost, "w_cost": worker_cost, "tot_exp": total_exp, "profit": profit, "id": event_id})

def delete_event(event_id: int):
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM events WHERE id = :id"), {"id": event_id})

# ----------------- AUTHENTICATION -----------------
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'role' not in st.session_state:
    st.session_state.role = None
if 'branch' not in st.session_state:
    st.session_state.branch = None

def login():
    st.markdown("<h2 style='text-align: center; font-weight: 800;'>🔐 تسجيل الدخول للأنظمة</h2>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.8, 1])
    with col2:
        with st.form("login_form"):
            password = st.text_input("أدخل كلمة المرور:", type="password")
            submit = st.form_submit_button("تسجيل الدخول", use_container_width=True)
            if submit:
                if password == "14161837":
                    st.session_state.logged_in = True
                    st.session_state.role = "employee"
                    st.session_state.branch = "Heaven"
                    st.rerun()
                elif password == "85879134":
                    st.session_state.logged_in = True
                    st.session_state.role = "employee"
                    st.session_state.branch = "9A"
                    st.rerun()
                elif password == "20072001":
                    st.session_state.logged_in = True
                    st.session_state.role = "admin"
                    st.session_state.branch = "All"
                    st.rerun()
                else:
                    st.error("كلمة المرور غير صحيحة!")

def logout():
    st.session_state.logged_in = False
    st.session_state.role = None
    st.session_state.branch = None

if not st.session_state.logged_in:
    login()
    st.stop()

role = st.session_state.role
branch = st.session_state.branch

# ==============================================================
# 1. EMPLOYEE SCREEN
# ==============================================================
if role == "employee":
    current_stock = get_current_stock(branch)

    top_c1, top_c2, top_c3, top_c4 = st.columns([3, 2, 2, 1])
    with top_c1:
        st.markdown(f"#### 👋 فرع: **{branch}** | 📦 الرصيد: **{current_stock} ورقة**")
    with top_c2:
        st.caption(f"📅 يوم العمل: **{get_egypt_today_str()}**")
    with top_c3:
        st.caption(f"🕒 التوقيت: **{get_egypt_now().strftime('%I:%M %p')}**")
    with top_c4:
        st.button("🚪 خروج", on_click=logout, use_container_width=True)
    st.markdown("---")

    st.markdown("""
        <style>
        div[data-testid="stButton"] > button {
            height: 120px !important;
            font-size: 20px !important;
            font-weight: 800 !important;
            border-radius: 12px;
            border: 2px solid #2d323f;
            transition: all 0.2s ease;
            white-space: pre-wrap !important;
        }
        div[data-testid="stButton"] > button:hover {
            border-color: #00CC96;
            color: #00CC96;
            transform: translateY(-2px);
        }
        </style>
    """, unsafe_allow_html=True)

    st.title(f"📸 فرع {branch} - المبيعات السريعة")

    st.subheader("⚡ العمليات السريعة")
    if branch == "Heaven":
        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            if st.button("🖼️ كارت فردي\n(30 ج - 1 ورقة)", use_container_width=True):
                if current_stock < 1:
                    st.error("⚠️ رصيد الورق غير كافٍ!")
                else:
                    record_transaction(branch, 1, 30.0)
                    st.success("✅ تم تسجيل البيع!")
                    st.rerun()
        with btn_col2:
            if st.button("🎞️ كارتين\n(50 ج - 2 ورقة)", use_container_width=True):
                if current_stock < 2:
                    st.error("⚠️ رصيد الورق غير كافٍ!")
                else:
                    record_transaction(branch, 2, 50.0)
                    st.success("✅ تم تسجيل البيع!")
                    st.rerun()
    else:
        btn_col1, btn_col2, btn_col3 = st.columns(3)
        with btn_col1:
            if st.button("🖼️ صورة فردي\n(50 ج - 1 ورقة)", use_container_width=True):
                if current_stock < 1:
                    st.error("⚠️ رصيد الورق غير كافٍ!")
                else:
                    record_transaction(branch, 1, 50.0)
                    st.success("✅ تم تسجيل البيع!")
                    st.rerun()
        with btn_col2:
            if st.button("🎞️ كارت ثلاثي\n(90 ج - 2 ورقة)", use_container_width=True):
                if current_stock < 2:
                    st.error("⚠️ رصيد الورق غير كافٍ!")
                else:
                    record_transaction(branch, 2, 90.0)
                    st.success("✅ تم تسجيل البيع!")
                    st.rerun()
        with btn_col3:
            if st.button("📸 كارت رباعي\n(120 ج - 3 ورقات)", use_container_width=True):
                if current_stock < 3:
                    st.error("⚠️ رصيد الورق غير كافٍ!")
                else:
                    record_transaction(branch, 3, 120.0)
                    st.success("✅ تم تسجيل البيع!")
                    st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("🛠️ تسجيل الهالك والطباعة المجانية")
    act_c1, act_c2 = st.columns(2)
    with act_c1:
        with st.expander("🗑️ تسجيل ورق تالف (طباعة باظت)", expanded=False):
            with st.form("waste_input_form", clear_on_submit=True):
                w_qty = st.number_input("عدد الورق التالف:", min_value=1, max_value=50, value=1, step=1)
                w_notes = st.text_input("سبب التلف (اختياري):", value="تالف طباعة")
                if st.form_submit_button("تأكيد خصم التالف", use_container_width=True):
                    if current_stock < w_qty:
                        st.error("رصيد الورق المتاح لا يكفي!")
                    else:
                        record_waste(branch, int(w_qty), w_notes.strip())
                        st.warning(f"تم خصم {w_qty} ورقة تالفة من المخزون.")
                        st.rerun()
    with act_c2:
        with st.expander("🎁 تسجيل طباعة مجانية (ضيافة / إهداء)", expanded=False):
            with st.form("free_input_form", clear_on_submit=True):
                f_qty = st.number_input("عدد الورق المجاني المطبوع:", min_value=1, max_value=50, value=1, step=1)
                f_notes = st.text_input("جهة الإهداء / السبب:", placeholder="مثال: صاحب المكان، تسويق...")
                if st.form_submit_button("تأكيد صرف المجاني", use_container_width=True):
                    if current_stock < f_qty:
                        st.error("رصيد الورق المتاح لا يكفي!")
                    else:
                        record_free_prints(branch, int(f_qty), f_notes.strip() if f_notes.strip() else "طباعة مجانية / ضيافة")
                        st.success(f"تم تسجيل {f_qty} ورقة مجانية وخصمها من الرصيد.")
                        st.rerun()

    st.markdown("<br><hr>", unsafe_allow_html=True)
    col_manual, col_exp = st.columns(2)
    with col_manual:
        with st.expander("⚙️ إدخال مبيعات يدوي", expanded=False):
            with st.form("manual_form", clear_on_submit=True):
                prints = st.number_input("عدد الورق المطبوع", min_value=1, max_value=50, value=None, step=1, placeholder="أدخل عدد الورق...")
                amount = st.number_input("المبلغ المدفوع (ج.م)", min_value=0.0, value=None, step=10.0, placeholder="أدخل المبلغ...")
                submit_btn = st.form_submit_button("✅ تسجيل يدوياً", use_container_width=True)
                if submit_btn:
                    if prints is None or amount is None:
                        st.error("⚠️ يرجى إدخال عدد الورق والمبلغ أولاً!")
                    elif current_stock < prints:
                        st.error("⚠️ رصيد الورق المتاح غير كافٍ!")
                    else:
                        record_transaction(branch, prints, amount)
                        st.success("تم التسجيل يدوياً!")
                        st.rerun()

    with col_exp:
        with st.expander("💸 تسجيل مصروفات سريعة", expanded=False):
            with st.form("employee_expense_form", clear_on_submit=True):
                exp_target = st.selectbox("جهة المصروف:", [branch, "Events"], format_func=lambda x: f"فرع {x}" if x != "Events" else "🎪 إيفنت خارجي (Events)")
                exp_amount = st.number_input("مبلغ المصروف (ج.م)", min_value=1.0, value=None, step=5.0, placeholder="أدخل المبلغ...")
                exp_desc = st.text_input("وصف المصروف", placeholder="مثال: شاي، صيانة، نثريات...")
                submit_exp = st.form_submit_button("💸 تسجيل المصروف", use_container_width=True)
                if submit_exp:
                    if exp_amount is None or not exp_desc.strip():
                        st.error("⚠️ يرجى إدخال المبلغ ووصف المصروف!")
                    else:
                        record_expense(exp_target, float(exp_amount), exp_desc.strip(), f"موظف {branch}", "نثريات وتشغيل")
                        st.success("تم تسجيل المصروف بنجاح!")
                        st.rerun()

    st.markdown("---")
    st.subheader("📋 عمليات يوم العمل الحالي (اليوم بالكامل)")
    today_str = get_egypt_today_str()
    with engine.connect() as conn:
        today_tx = pd.read_sql_query(
            text("""
                SELECT t.id, t.timestamp, t.prints_count, t.amount_paid
                FROM transactions t
                JOIN days d ON t.day_id = d.id
                WHERE d.date = :date AND t.branch = :branch
                ORDER BY t.timestamp DESC
            """), conn, params={"date": today_str, "branch": branch}
        )
        if not today_tx.empty:
            display_user_tx = today_tx.rename(columns={'timestamp': 'الوقت', 'prints_count': 'عدد الورق', 'amount_paid': 'المبلغ (ج.م)'})
            st.dataframe(display_user_tx.drop(columns=['id']), use_container_width=True, hide_index=True)
            
            st.markdown("##### 🛠️ إدارة / تعديل / حذف مبيعات اليوم")
            options = {f"عملية #{row['id']} - الساعة {row['timestamp'].split(' ')[1]} ({row['prints_count']} ورق | {row['amount_paid']} ج)": row['id'] for _, row in today_tx.iterrows()}
            selected_label = st.selectbox("اختر العملية للتحكم بها:", list(options.keys()), key="sel_tx")
            selected_id = options[selected_label]
            selected_row = today_tx[today_tx['id'] == selected_id].iloc[0]
            
            col_act1, col_act2 = st.columns(2)
            with col_act1:
                with st.expander("✏️ تعديل العملية المحددة", expanded=False):
                    with st.form("edit_form"):
                        new_p = st.number_input("تعديل عدد الورق:", min_value=1, max_value=50, value=int(selected_row['prints_count']), step=1)
                        new_a = st.number_input("تعديل المبلغ (ج.م):", min_value=0.0, value=float(selected_row['amount_paid']), step=10.0)
                        if st.form_submit_button("حفظ التعديلات", use_container_width=True):
                            if update_transaction(selected_id, branch, new_p, new_a):
                                st.success("تم تعديل العملية بنجاح!")
                                st.rerun()
            with col_act2:
                with st.expander("🗑️ حذف العملية المحددة", expanded=False):
                    st.warning(f"هل أنت متأكد من حذف العملية #{selected_id}؟ سيتم استرجاع الورق للمخزون.")
                    if st.button("تأكيد الحذف نهائياً", type="primary", use_container_width=True, key="del_tx_btn"):
                        if delete_transaction(selected_id, branch):
                            st.success("تم مسح العملية واسترجاع الورق بنجاح!")
                            st.rerun()
        else:
            st.info("لا توجد مبيعات مسجلة في يوم العمل الحالي حتى الآن.")

    st.markdown("---")
    st.subheader("💸 مصروفات يوم العمل الحالي")
    with engine.connect() as conn:
        today_exp_df = pd.read_sql_query(
            text("""
                SELECT e.id, e.timestamp, e.amount, e.description 
                FROM expenses e
                JOIN days d ON e.day_id = d.id
                WHERE d.date = :date AND e.branch = :branch 
                ORDER BY e.timestamp DESC
            """), conn, params={"date": today_str, "branch": branch}
        )
        if not today_exp_df.empty:
            disp_exp = today_exp_df.rename(columns={'timestamp': 'الوقت', 'amount': 'المبلغ (ج.م)', 'description': 'الوصف'})
            st.dataframe(disp_exp.drop(columns=['id']), use_container_width=True, hide_index=True)
            
            st.markdown("##### 🛠️ إدارة / تعديل / حذف مصروف من اليوم")
            exp_opts = {f"مصروف #{r['id']} - الساعة {r['timestamp'].split(' ')[1]} ({r['amount']} ج | {r['description']})": r['id'] for _, r in today_exp_df.iterrows()}
            sel_exp_label = st.selectbox("اختر المصروف للتحكم به:", list(exp_opts.keys()), key="sel_exp")
            sel_exp_id = exp_opts[sel_exp_label]
            sel_exp_row = today_exp_df[today_exp_df['id'] == sel_exp_id].iloc[0]
            
            col_e1, col_e2 = st.columns(2)
            with col_e1:
                with st.expander("✏️ تعديل المصروف المحدد", expanded=False):
                    with st.form("edit_exp_form"):
                        new_ea = st.number_input("تعديل المبلغ:", min_value=1.0, value=float(sel_exp_row['amount']), step=5.0)
                        new_ed = st.text_input("تعديل الوصف:", value=str(sel_exp_row['description']))
                        if st.form_submit_button("حفظ تعديل المصروف", use_container_width=True):
                            if update_expense(sel_exp_id, new_ea, new_ed, branch):
                                st.success("تم تعديل المصروف بنجاح!")
                                st.rerun()
            with col_e2:
                with st.expander("🗑️ حذف المصروف المحدد", expanded=False):
                    st.warning(f"هل أنت متأكد من حذف المصروف #{sel_exp_id}؟")
                    if st.button("تأكيد حذف المصروف نهائياً", type="primary", use_container_width=True, key="del_exp_btn"):
                        if delete_expense(sel_exp_id, branch):
                            st.success("تم حذف المصروف بنجاح!")
                            st.rerun()
        else:
            st.info("لا توجد مصروفات مسجلة في هذا الفرع لليوم الحالي.")

# ==============================================================
# 2. ADMIN DASHBOARD
# ==============================================================
elif role == "admin":
    check_and_add_monthly_allowance()

    with engine.connect() as conn:
        all_tx_raw = pd.read_sql_query(text("SELECT t.*, d.date FROM transactions t JOIN days d ON t.day_id = d.id ORDER BY t.timestamp ASC"), conn)
        all_exp_raw = pd.read_sql_query(text("SELECT e.*, d.date as operational_date FROM expenses e JOIN days d ON e.day_id = d.id ORDER BY e.timestamp ASC"), conn)
        all_events_raw = pd.read_sql_query(text("SELECT * FROM events ORDER BY event_date ASC, start_time ASC"), conn)
        all_drawings = pd.read_sql_query(text("SELECT * FROM cash_drawings ORDER BY timestamp DESC"), conn)

    for col_name in ['total_amount', 'total_expenses', 'net_profit', 'remaining_amount', 'deposit_paid']:
        if col_name not in all_events_raw.columns:
            all_events_raw[col_name] = 0.0

    all_dates = []
    if not all_tx_raw.empty:
        all_dates.extend(pd.to_datetime(all_tx_raw['date']).dt.date.tolist())
    if not all_exp_raw.empty:
        all_dates.extend(pd.to_datetime(all_exp_raw['operational_date']).dt.date.tolist())

    min_date = min(all_dates) if all_dates else date.today()
    max_date = max(all_dates) if all_dates else date.today()

    bar_c1, bar_c2, bar_c3, bar_c4, bar_c5 = st.columns([2.8, 2.7, 2, 2.2, 1])
    with bar_c1:
        st.markdown("<h2 style='margin:0; font-weight:900;'>👑 إدارة المنظومة المالية</h2>", unsafe_allow_html=True)
    with bar_c2:
        sec_choice = st.radio("القسم:", ["📊 الفروع والتحليل المالي", "📦 المخزن والتوريدات", "🎪 حجوزات الإيفنتات", "⚙️ إعدادات الفروع"], horizontal=True)
    with bar_c3:
        selected_branch = st.selectbox("🏢 نطاق التحليل:", ["الكل", "Heaven", "9A", "Events"])
    with bar_c4:
        date_range = st.date_input("📅 الفترة:", value=(min_date, max_date), min_value=min_date, max_value=max_date)
    with bar_c5:
        st.markdown("<br>", unsafe_allow_html=True)
        st.button("🚪 خروج", on_click=logout, use_container_width=True)
    st.markdown("---")

    # ================= 2.A المخزن العام والتوريدات والحبر =================
    if sec_choice == "📦 المخزن والتوريدات":
        st.title("📦 إدارة المخزون العام وتوريدات الفروع")

        warehouse_sheets = get_current_stock("Warehouse")
        warehouse_packets = warehouse_sheets / 100.0
        stock_heaven = get_current_stock("Heaven")
        stock_9a = get_current_stock("9A")
        warehouse_refills = get_ink_refills("Warehouse")
        ink_heaven_refills = get_ink_refills("Heaven")
        ink_9a_refills = get_ink_refills("9A")

        if warehouse_packets <= 20:
            st.markdown(f"""
                <div class="alert-card-danger">
                    🚨 <b>تنبيه عاجل لإعادة الطلب:</b> رصيد المخزن العام وصل إلى <b>{warehouse_packets:.0f} باكتة</b> ({warehouse_sheets:,} ورقة) وهو أقل من أو يساوي الحد الأدنى (20 باكتة)! يرجى طلب شحنة جديدة.
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
                <div class="alert-card-success">
                    ✅ <b>حالة المخزن العام ممتازة:</b> متوفر حالياً <b>{warehouse_packets:.0f} باكتة</b> ({warehouse_sheets:,} ورقة).
                </div>
            """, unsafe_allow_html=True)

        if stock_heaven < 200:
            st.warning(f"⚠️ **تنبيه فرع Heaven:** رصيد الورق منخفض ({stock_heaven} ورقة)! الحد الأدنى 200 ورقة.")
        if stock_9a < 200:
            st.warning(f"⚠️ **تنبيه فرع 9A:** رصيد الورق منخفض ({stock_9a} ورقة)! الحد الأدنى 200 ورقة.")

        inv_c1, inv_c2, inv_c3 = st.columns(3)
        inv_c1.metric("🏢 ورق المخزن العام", f"{warehouse_packets:,.1f} باكتة", f"{warehouse_sheets:,} ورقة")
        inv_c2.metric("🏪 ورق فرع 9A", f"{stock_9a:,} ورقة", delta=f"{stock_9a - 200}" if stock_9a < 200 else "آمن", delta_color="normal")
        inv_c3.metric("🏪 ورق فرع Heaven", f"{stock_heaven:,} ورقة", delta=f"{stock_heaven - 200}" if stock_heaven < 200 else "آمن", delta_color="normal")

        st.markdown("---")
        ink_c1, ink_c2, ink_c3 = st.columns(3)
        ink_c1.metric("🖋️ رصيد الحبر بالمخزن", f"{warehouse_refills} مليات طابعة", f"({warehouse_refills/2:.1f} علبة حبر)")
        ink_c2.metric("🖋️ حبر فرع 9A المورد", f"{ink_9a_refills} ملوة")
        ink_c3.metric("🖋️ حبر فرع Heaven المورد", f"{ink_heaven_refills} ملوة")

        st.markdown("---")
        col_in1, col_in2 = st.columns(2)
        with col_in1:
            st.markdown("### 📥 استلام وتوريد شحنة جديدة للمخزن")
            with st.form("new_stock_form", clear_on_submit=True):
                p_qty = st.number_input("عدد باكتات الورق المستلمة (1 باكتة = 100 ورقة):", min_value=0, value=0, step=10)
                ink_qty = st.number_input("عدد علب الحبر المستلمة (العلبة = 2 ملوة طابعة):", min_value=0.0, value=0.0, step=0.5)
                bill_cost = st.number_input("إجمالي فاتورة الشراء (ج.م) [لحساب الأصول]:", min_value=0.0, value=0.0, step=100.0)
                stock_notes = st.text_input("ملاحظات الفاتورة / المورد:", placeholder="شراء ورق، أحبار...")
                if st.form_submit_button("📥 تأكيد دخول الشحنة للمخزن", use_container_width=True):
                    if p_qty > 0 or ink_qty > 0:
                        add_warehouse_stock(int(p_qty), float(ink_qty), float(bill_cost), stock_notes)
                        st.success("✅ تم إضافة الشحنة للمخزن بنجاح وتحديث الرصيد!")
                        st.rerun()
                    else:
                        st.error("يرجى إدخال كمية الورق أو الحبر!")

        with col_in2:
            st.markdown("### 🚚 تحويل ورق وحبر إلى الفروع")
            with st.expander("📄 تحويل ورق للفرع", expanded=True):
                with st.form("transfer_stock_form", clear_on_submit=True):
                    target_b = st.selectbox("اختر الفرع المحول إليه:", ["9A", "Heaven"], key="t_b_paper")
                    trans_sheets = st.number_input("عدد الورق المحول (ورقة):", min_value=50, max_value=max(int(warehouse_sheets), 50), value=200, step=50)
                    trans_notes = st.text_input("ملاحظات التحويل:", placeholder="تسليم شيفت المساء...")
                    if st.form_submit_button("🚚 تحويل الورق فوراً للفرع", use_container_width=True):
                        if warehouse_sheets >= trans_sheets:
                            transfer_stock_to_branch(target_b, int(trans_sheets), trans_notes)
                            st.success(f"✅ تم تحويل {trans_sheets} ورقة إلى فرع {target_b} بنجاح!")
                            st.rerun()
                        else:
                            st.error("⚠️ رصيد المخزن الرئيسي غير كافٍ لهذا التحويل!")

            with st.expander("🖋️ تزويد الفرع بحبر (بالملوة)"):
                with st.form("transfer_ink_form", clear_on_submit=True):
                    target_b_ink = st.selectbox("اختر الفرع لتزويده بالحبر:", ["9A", "Heaven"], key="t_b_ink")
                    refills_to_send = st.number_input("عدد المليات المحولة (1 ملوة = نص علبة حبر تكفي ملء الطابعة):", min_value=1, max_value=max(warehouse_refills, 1), value=1, step=1)
                    ink_trans_notes = st.text_input("ملاحظات تزويد الحبر:", placeholder="ملء طابعة الفرع...")
                    if st.form_submit_button("تزويد الفرع بالحبر فوراً", use_container_width=True):
                        if warehouse_refills >= refills_to_send:
                            transfer_ink_to_branch(target_b_ink, int(refills_to_send), ink_trans_notes)
                            st.success(f"تم تزويد فرع {target_b_ink} بـ {refills_to_send} ملوة حبر بنجاح!")
                            st.rerun()
                        else:
                            st.error("رصيد الحبر بالمخزن العام لا يكفي!")

    # ================= 2.B قسم الإيفنتات الخارجية =================
    elif sec_choice == "🎪 حجوزات الإيفنتات":
        st.title("🎪 إدارة حجوزات الإيفنتات الخارجية")
        total_ev_count = len(all_events_raw)
        total_ev_rev = all_events_raw['total_amount'].sum() if not all_events_raw.empty else 0
        total_ev_exp = all_events_raw['total_expenses'].sum() if not all_events_raw.empty else 0
        total_ev_profit = all_events_raw['net_profit'].sum() if not all_events_raw.empty else 0
        total_ev_rem = all_events_raw['remaining_amount'].sum() if not all_events_raw.empty else 0

        ev_k1, ev_k2, ev_k3, ev_k4, ev_k5 = st.columns(5)
        ev_k1.metric("🎪 إجمالي الإيفنتات", f"{total_ev_count}")
        ev_k2.metric("💰 إجمالي التعاقدات", f"{total_ev_rev:,.0f} ج.م")
        ev_k3.metric("💸 إجمالي المصروفات", f"{total_ev_exp:,.0f} ج.م", delta=f"-{total_ev_exp:,.0f}", delta_color="normal")
        ev_k4.metric("📈 صافي الأرباح", f"{total_ev_profit:,.0f} ج.م", delta=f"{total_ev_profit:,.0f}", delta_color="normal")
        ev_k5.metric("⏳ المتبقي تحصيله", f"{total_ev_rem:,.0f} ج.م", delta=f"-{total_ev_rem:,.0f}" if total_ev_rem > 0 else "0", delta_color="normal")
        st.markdown("---")

        with st.expander("➕ تسجيل حجز إيفنت جديد", expanded=False):
            with st.form("new_event_form", clear_on_submit=True):
                ef1, ef2, ef3 = st.columns(3)
                with ef1:
                    ev_client = st.text_input("اسم العميل / المناسبة:")
                    ev_loc = st.text_input("مكان الإيفنت / القاعة:")
                    ev_dev = st.selectbox("الجهاز المخصص:", ["Heaven", "9A"])
                with ef2:
                    ev_date = st.date_input("تاريخ الإيفنت:", value=date.today())
                    ev_hours = st.number_input("عدد الساعات:", min_value=1, max_value=24, value=3, step=1)
                    ev_start = st.time_input("ساعة البداية:", value=time(19, 0))
                with ef3:
                    ev_total = st.number_input("إجمالي قيمة الحجز (ج.م):", min_value=100.0, value=2000.0, step=500.0)
                    ev_deposit = st.number_input("العربون المدفوع (ج.م):", min_value=0.0, value=1000.0, step=500.0)
                    ev_notes = st.text_input("ملاحظات إضافية:")

                start_dt = datetime.combine(ev_date, ev_start)
                end_dt = start_dt + timedelta(hours=int(ev_hours))
                ev_start_str = format_arabic_time(start_dt.strftime("%I:%M %p"))
                ev_end_str = format_arabic_time(end_dt.strftime("%I:%M %p"))

                if st.form_submit_button("💾 تأكيد وحفظ الحجز", use_container_width=True):
                    if ev_client.strip() and ev_loc.strip():
                        create_event(str(ev_date), ev_client.strip(), ev_loc.strip(), ev_dev, int(ev_hours), ev_start_str, ev_end_str, float(ev_total), float(ev_deposit), ev_notes.strip())
                        st.success("✅ تم تسجيل الحجز بنجاح!")
                        st.rerun()

        st.subheader("📌 بطاقات الإيفنتات والموقف المالي")
        if not all_events_raw.empty:
            for _, ev in all_events_raw.iterrows():
                badge_class = "badge-heaven" if ev['device'] == "Heaven" else "badge-9a"
                is_settled = ev['status'] == 'تم التنفيذ والتسوية'
                rem_val = float(ev.get('remaining_amount', 0))
                rem_text = f"{rem_val:,.0f} ج.م" if rem_val > 0 else "تم السداد بالكامل"
                rem_class = "finance-val-red" if rem_val > 0 else "finance-val-green"

                st.markdown(f"""
                <div class="event-card">
                    <div class="event-top">
                        <div class="event-title">🎉 {ev['client_name']} &nbsp;•&nbsp; 📍 {ev['location']}</div>
                        <div class="{badge_class}">جهاز: {ev['device']}</div>
                    </div>
                    <div class="event-meta">
                        📅 <b>تاريخ الإيفنت:</b> {ev['event_date']} &nbsp;&nbsp;|&nbsp;&nbsp; ⏰ <b>التوقيت:</b> من {ev['start_time']} إلى {ev['end_time']} ({ev['hours']} ساعات)
                    </div>
                    <div class="event-finance-grid">
                        <div><div class="finance-label">قيمة الحجز</div><div class="finance-val">{ev.get('total_amount', 0):,.0f} ج</div></div>
                        <div><div class="finance-label">المدفوع</div><div class="finance-val">{ev.get('deposit_paid', 0):,.0f} ج</div></div>
                        <div><div class="finance-label">المتبقي</div><div class="{rem_class}">{rem_text}</div></div>
                        <div><div class="finance-label">المصروفات</div><div class="finance-val">{ev.get('total_expenses', 0):,.0f} ج</div></div>
                        <div><div class="finance-label">صافي الربح</div><div class="finance-val-green">{ev.get('net_profit', 0):,.0f} ج</div></div>
                        <div><div class="finance-label">الحالة</div><div class="finance-val" style="font-size:13px;">{ev.get('status', '-')}</div></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                with st.expander(f"🔍 تفاصيل وتسوية إيفنت #{ev['id']} ({ev['client_name']})"):
                    if is_settled:
                        sc1, sc2, sc3, sc4 = st.columns(4)
                        sc1.info(f"🖨️ الورق: {ev.get('prints_used', 0)} ({ev.get('paper_cost', 0):,.0f} ج)")
                        sc2.info(f"🚗 مواصلات: {ev.get('transport_cost', 0):,.0f} ج")
                        sc3.info(f"👨‍💼 أجر موظف: {ev.get('worker_cost', 0):,.0f} ج")
                        sc4.success(f"📈 صافي ربح: {ev.get('net_profit', 0):,.0f} ج")
                    else:
                        with st.form(f"settle_form_{ev['id']}"):
                            c_p, c_t, c_w = st.columns(3)
                            in_prints = c_p.number_input("الورق المستهلك:", min_value=0, max_value=2000, value=50, step=10, key=f"p_{ev['id']}")
                            in_trans = c_t.number_input("المواصلات (ج):", min_value=0.0, value=100.0, step=50.0, key=f"t_{ev['id']}")
                            in_worker = c_w.number_input("أجر الموظف (ج):", min_value=0.0, value=100.0, step=10.0, key=f"w_{ev['id']}")
                            if st.form_submit_button("✅ اعتماد التنفيذ والتسوية", use_container_width=True):
                                complete_event_settlement(ev['id'], int(in_prints), float(in_trans), float(in_worker))
                                st.success("تمت تسوية الإيفنت بنجاح!")
                                st.rerun()

                    if st.button(f"🗑️ حذف الإيفنت #{ev['id']}", key=f"del_ev_{ev['id']}"):
                        delete_event(ev['id'])
                        st.warning("تم حذف الإيفنت.")
                        st.rerun()

            st.markdown("---")
            st.subheader("📥 تصدير سجل الإيفنتات بالكامل")
            events_export = all_events_raw.rename(columns={
                'id': 'رقم الحجز', 'event_date': 'تاريخ الإيفنت', 'client_name': 'العميل',
                'location': 'المكان', 'device': 'الجهاز', 'hours': 'الساعات',
                'start_time': 'البداية', 'end_time': 'النهاية', 'total_amount': 'إجمالي التعاقد (ج.م)',
                'deposit_paid': 'المبلغ المدفوع (ج.م)', 'remaining_amount': 'المتبقي (ج.م)',
                'prints_used': 'الورق المستهلك', 'paper_cost': 'تكلفة الورق (ج.م)',
                'transport_cost': 'المواصلات (ج.م)', 'worker_cost': 'أجر الموظف (ج.م)',
                'total_expenses': 'إجمالي المصروفات (ج.م)', 'net_profit': 'صافي الربح (ج.م)',
                'status': 'الحالة', 'notes': 'ملاحظات'
            })
            csv_ev = events_export.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 تحميل شيت إكسيل الإيفنتات والمصاريف والأرباح (CSV)", data=csv_ev, file_name=f"events_report_{get_egypt_today_str()}.csv", mime="text/csv", use_container_width=True)

    # ================= 2.C إعدادات الفروع والمرونة =================
    elif sec_choice == "⚙️ إعدادات الفروع":
        st.title("⚙️ إعدادات التكاليف الثابتة للفروع")
        st.caption("يمكنك تعديل إيجار أو مرتبات أو تكاليف أي فرع في أي وقت، وسيتم تحديث الحسابات فوراً دون لمس الكود.")
        set_col1, set_col2 = st.columns(2)
        for b_name, col in [("9A", set_col1), ("Heaven", set_col2)]:
            cfg = get_branch_settings(b_name)
            with col:
                st.markdown(f"### 🏢 إعدادات فرع {b_name}")
                with st.form(f"cfg_form_{b_name}"):
                    n_rent = st.number_input(f"الإيجار الشهري ({b_name}):", value=float(cfg.get('rent', 0.0)), step=100.0)
                    n_sal = st.number_input(f"إجمالي المرتبات والعمالة ({b_name}):", value=float(cfg.get('salary', 0.0)), step=100.0)
                    n_bills = st.number_input(f"فواتير وأقساط شهرية ({b_name}):", value=float(cfg.get('bills', 0.0)), step=50.0)
                    n_cost = st.number_input(f"تكلفة الورقة والحبر ({b_name}):", value=float(cfg.get('cost_per_print', 3.0)), step=0.5)
                    monthly_fixed = n_rent + n_sal + n_bills
                    st.info(f"إجمالي التكلفة الثابتة الشهرية: **{monthly_fixed:,.0f} ج.م** (~ {monthly_fixed/30:,.0f} ج / يومياً)")
                    if st.form_submit_button(f"💾 حفظ إعدادات {b_name}", use_container_width=True):
                        update_branch_settings(b_name, n_rent, n_sal, n_bills, n_cost)
                        st.success(f"تم تحديث بيانات فرع {b_name} بنجاح!")
                        st.rerun()

    # ================= 2.D الفروع والتحليل المالي =================
    else:
        if len(date_range) == 2:
            start_dt, end_dt = date_range
            mask_tx = (pd.to_datetime(all_tx_raw['date']).dt.date >= start_dt) & (pd.to_datetime(all_tx_raw['date']).dt.date <= end_dt) if not all_tx_raw.empty else pd.Series(dtype=bool)
            mask_exp = (pd.to_datetime(all_exp_raw['operational_date']).dt.date >= start_dt) & (pd.to_datetime(all_exp_raw['operational_date']).dt.date <= end_dt) if not all_exp_raw.empty else pd.Series(dtype=bool)
            filtered_tx = all_tx_raw.loc[mask_tx].copy() if not all_tx_raw.empty else pd.DataFrame()
            filtered_exp = all_exp_raw.loc[mask_exp].copy() if not all_exp_raw.empty else pd.DataFrame()
        else:
            filtered_tx = all_tx_raw.copy()
            filtered_exp = all_exp_raw.copy()

        if selected_branch == "الكل":
            tx_subset = filtered_tx
            exp_subset = filtered_exp
        elif selected_branch == "Events":
            tx_subset = filtered_tx[filtered_tx['branch'] == "Events"] if not filtered_tx.empty else pd.DataFrame()
            exp_subset = filtered_exp[filtered_exp['branch'] == "Events"] if not filtered_exp.empty else pd.DataFrame()
        else:
            tx_subset = filtered_tx[filtered_tx['branch'] == selected_branch] if not filtered_tx.empty else pd.DataFrame()
            exp_subset = filtered_exp[filtered_exp['branch'].isin([selected_branch, 'General'])] if not filtered_exp.empty else pd.DataFrame()

        total_rev_all = tx_subset['amount_paid'].sum() if not tx_subset.empty else 0.0
        total_prints_all = tx_subset['prints_count'].sum() if not tx_subset.empty else 0
        total_cust_all = len(tx_subset)
        
        # المصروفات التشغيلية الحقيقية (بدون أرباح الشركاء المسحوبة ولا مشتريات الأصول)
        opex_df = exp_subset[~exp_subset['category'].isin(['مشتريات مخزن وأصول', 'توزيعات أرباح'])] if not exp_subset.empty else pd.DataFrame()
        total_exp_all = opex_df['amount'].sum() if not opex_df.empty else 0.0

        drawings_df = exp_subset[exp_subset['category'] == 'توزيعات أرباح'] if not exp_subset.empty else pd.DataFrame()
        drawings_exp_sum = drawings_df['amount'].sum() if not drawings_df.empty else 0.0
        total_drawings = all_drawings['amount'].sum() + drawings_exp_sum

        # صافي الربح = الإيرادات - المصروفات التشغيلية
        net_profit = total_rev_all - total_exp_all

        # السيولة الدقيقة المحسوبة (التي تطابق الواقع 100%)
        uncollected_cash = tx_subset[tx_subset['is_collected'] == 0]['amount_paid'].sum() if not tx_subset.empty else 0.0
        collected_cash = total_rev_all - uncollected_cash
        safe_cash = max(collected_cash - total_exp_all - total_drawings, 0.0)

        waste_count = get_waste_count(selected_branch)
        free_count = get_free_count(selected_branch)

        # ----------------- المؤشرات المالية العلوية -----------------
        st.markdown("#### 📈 الأرباح وقائمة الدخل الحقيقية (P&L)")
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("💰 إجمالي الإيرادات", f"{total_rev_all:,.0f} ج.م")
        kpi2.metric("🖨️ الورق المستهلك", f"{total_prints_all:,} ورقة", delta=f"{total_prints_all*3:,.0f} ج خامات", delta_color="off")
        kpi3.metric("🏢 المصاريف التشغيلية", f"{total_exp_all:,.0f} ج.م", delta=f"-{total_exp_all:,.0f}", delta_color="normal")
        kpi4.metric("📈 صافي الأرباح المحققة", f"{net_profit:,.0f} ج.م", delta=f"{net_profit:,.0f}", delta_color="normal")

        st.markdown("#### 💵 حركة السيولة والفلوس فين؟")
        kpi5, kpi6, kpi7, kpi8 = st.columns(4)
        kpi5.metric("🏦 الكاش المتبقي بالخزينة (معاك)", f"{safe_cash:,.0f} ج.م", delta="في يدك الآن")
        kpi6.metric("⏳ فلوس معلقة برة (ذمم)", f"{uncollected_cash:,.0f} ج.م", delta="عهدة السبت مع الموظفين", delta_color="off")
        kpi7.metric("💼 إجمالي الأرباح المسحوبة", f"{total_drawings:,.0f} ج.م", delta="مسحوبات الشركاء", delta_color="off")
        kpi8.metric("🗑️ تالف / 🎁 مجاني", f"{waste_count} تالف | {free_count} هدايا")
        st.markdown("---")

        col_act_c1, col_act_c2 = st.columns(2)
        with col_act_c1:
            with st.expander("📥 تسليم وتوريد الكاش المعلق إلى الخزينة"):
                st.write(f"المبلغ المعلق غير المورد حالياً: **{uncollected_cash:,.0f} ج.م**")
                if st.button("✅ تأكيد استلام وتوريد كل الكاش المعلق للخزينة", use_container_width=True):
                    mark_transactions_collected(selected_branch)
                    st.success("تم تأكيد الاستلام وتوريد الفلوس للخزينة!")
                    st.rerun()
        with col_act_c2:
            with st.expander("💼 تسجيل سحب أرباح للشركاء (Drawings)"):
                with st.form("drawings_form", clear_on_submit=True):
                    d_amt = st.number_input("المبلغ المسحوب (ج.م):", min_value=100.0, step=500.0)
                    d_rec = st.text_input("اسم المستلم / الشريك:")
                    d_note = st.text_input("ملاحظات:")
                    if st.form_submit_button("سحب الأرباح", use_container_width=True):
                        if d_amt and d_rec.strip():
                            record_cash_drawing(float(d_amt), d_rec.strip(), d_note.strip())
                            st.success("تم تسجيل مسحوبات الأرباح بنجاح!")
                            st.rerun()

        st.markdown("---")
        with st.expander("💸 تسجيل مصروفات جديدة بواسطة الأدمن", expanded=False):
            with st.form("admin_exp_form", clear_on_submit=True):
                c_a1, c_a2, c_a3, c_a4 = st.columns(4)
                with c_a1:
                    ad_branch = st.selectbox("جهة المصروف:", ["General", "Heaven", "9A", "Events"], format_func=lambda x: "عام (يوزع)" if x == "General" else ("🎪 إيفنت (Events)" if x == "Events" else f"فرع {x}"))
                with c_a2:
                    ad_cat = st.selectbox("بند المصروف:", ["نثريات وتشغيل", "إيجار", "مرتبات وعمالة", "فواتير وأقساط", "إعلانات وتسويق"])
                with c_a3:
                    ad_amount = st.number_input("المبلغ (ج.م):", min_value=1.0, value=None, step=50.0)
                with c_a4:
                    ad_desc = st.text_input("وصف المصروف:", placeholder="شاي، صيانة، إيجار...")
                if st.form_submit_button("تسجيل المصروف للأدمن", use_container_width=True):
                    if ad_amount and ad_desc.strip():
                        record_expense(ad_branch, float(ad_amount), ad_desc.strip(), "المدير", ad_cat)
                        st.success("تم تسجيل المصروف بنجاح!")
                        st.rerun()

        # ----------------- جداول اليوم الحالي -----------------
        st.markdown("---")
        today_b_str = get_egypt_today_str()
        st.subheader(f"⚡ مبيعات ومصروفات يوم العمل الحالي ({selected_branch}) - {today_b_str}")
        
        c_tod1, c_tod2 = st.columns(2)
        with c_tod1:
            st.markdown("##### 🛒 مبيعات اليوم الحالي")
            with engine.connect() as conn:
                f_b = "AND t.branch = :branch" if selected_branch != "الكل" else ""
                p_b = {"date": today_b_str, "branch": selected_branch} if selected_branch != "الكل" else {"date": today_b_str}
                today_admin_tx = pd.read_sql_query(text(f"""
                    SELECT t.timestamp, t.branch, t.prints_count, t.amount_paid
                    FROM transactions t JOIN days d ON t.day_id = d.id
                    WHERE d.date = :date {f_b} ORDER BY t.timestamp DESC
                """), conn, params=p_b)
            if not today_admin_tx.empty:
                st.dataframe(today_admin_tx.rename(columns={'timestamp': 'الوقت', 'branch': 'الفرع', 'prints_count': 'الورق', 'amount_paid': 'المبلغ (ج.م)'}), use_container_width=True, hide_index=True)
            else:
                st.info("لا توجد مبيعات مسجلة اليوم.")

        with c_tod2:
            st.markdown("##### 💸 مصروفات اليوم الحالي")
            with engine.connect() as conn:
                f_e = "AND (e.branch = :branch OR e.branch = 'General')" if selected_branch != "الكل" else ""
                p_e = {"date": today_b_str, "branch": selected_branch} if selected_branch != "الكل" else {"date": today_b_str}
                today_admin_exp = pd.read_sql_query(text(f"""
                    SELECT e.timestamp, e.branch, e.amount, e.description, e.created_by 
                    FROM expenses e JOIN days d ON e.day_id = d.id
                    WHERE d.date = :date {f_e} ORDER BY e.timestamp DESC
                """), conn, params=p_e)
            if not today_admin_exp.empty:
                st.dataframe(today_admin_exp.rename(columns={'timestamp': 'الوقت', 'branch': 'الفرع', 'amount': 'المبلغ (ج.م)', 'description': 'الوصف', 'created_by': 'بواسطة'}), use_container_width=True, hide_index=True)
            else:
                st.info("لا توجد مصروفات مسجلة اليوم.")

        # ----------------- جدول سلوك العمليات اليومي -----------------
        st.markdown("---")
        if not tx_subset.empty:
            days_df = tx_subset.groupby('date').agg(
                first_customer_time=('timestamp', 'min'),
                last_customer_time=('timestamp', 'max'),
                total_customers=('id', 'count'),
                total_prints=('prints_count', 'sum'),
                total_revenue=('amount_paid', 'sum')
            ).reset_index()

            tx_subset['hour'] = pd.to_datetime(tx_subset['timestamp']).dt.hour
            peak_hours = tx_subset.groupby(['date', 'hour'])['id'].count().reset_index()
            peak_hours = peak_hours.sort_values(['date', 'id'], ascending=[True, False]).drop_duplicates(subset=['date'])
            peak_hours = peak_hours.rename(columns={'hour': 'peak_hour'})[['date', 'peak_hour']]

            behavior_df = days_df.merge(peak_hours, on='date', how='left')
            behavior_df['date_obj'] = pd.to_datetime(behavior_df['date'])
            behavior_df['day_name'] = behavior_df['date_obj'].dt.day_name().map(ARABIC_DAYS)

            def extract_time(ts):
                if pd.isna(ts): return "-"
                return format_arabic_time(pd.to_datetime(ts).strftime('%I:%M %p'))

            behavior_df['first_time'] = behavior_df['first_customer_time'].apply(extract_time)
            behavior_df['last_time'] = behavior_df['last_customer_time'].apply(extract_time)
            behavior_df['peak_str'] = behavior_df['peak_hour'].apply(lambda x: f"{int(x)}:00" if pd.notna(x) else "-")

            st.subheader(f"📋 إيرادات وسلوك العمليات اليومي ({selected_branch})")
            display_df = behavior_df[['date', 'day_name', 'first_time', 'last_time', 'peak_str', 'total_customers', 'total_prints', 'total_revenue']].copy()
            display_df.columns = ['تاريخ يوم العمل', 'اليوم', 'أول عملية', 'آخر عملية', 'ساعة الذروة', 'العمليات', 'الورق المطبوع', 'الإيراد (ج.م)']
            st.dataframe(display_df, use_container_width=True, hide_index=True)

        st.subheader(f"💸 سجل ومصاريف الأيام خلال الفترة ({selected_branch})")
        if not exp_subset.empty:
            exp_display_df = exp_subset[['operational_date', 'timestamp', 'branch', 'amount', 'description', 'created_by']].copy()
            exp_display_df['date_obj'] = pd.to_datetime(exp_display_df['operational_date'])
            exp_display_df['day_name'] = exp_display_df['date_obj'].dt.day_name().map(ARABIC_DAYS)
            exp_display_df = exp_display_df.sort_values(by='timestamp', ascending=False)
            final_exp_table = exp_display_df[['operational_date', 'day_name', 'timestamp', 'branch', 'amount', 'description', 'created_by']].copy()
            final_exp_table.columns = ['التاريخ', 'اليوم', 'الوقت', 'الجهة / الفرع', 'المبلغ (ج.م)', 'الوصف', 'المسؤول']
            st.dataframe(final_exp_table, use_container_width=True, hide_index=True)

        # ----------------- الرسوم البيانية -----------------
        st.markdown("---")
        st.subheader("📈 التحليلات والرسوم البيانية")

        if not tx_subset.empty:
            col_chart1, col_chart2 = st.columns(2)
            with col_chart1:
                st.markdown("##### 📉 الإيرادات والعمليات خلال الفترة")
                fig_trend = go.Figure()
                fig_trend.add_trace(go.Scatter(
                    x=days_df['date'], y=days_df['total_revenue'],
                    mode='lines+markers', name='الإيراد (ج.م)', line=dict(color='#00CC96', width=3)
                ))
                fig_trend.add_trace(go.Bar(
                    x=days_df['date'], y=days_df['total_customers'],
                    name='عدد العمليات', yaxis='y2', marker_color='rgba(99, 110, 250, 0.45)'
                ))
                fig_trend.update_layout(
                    yaxis=dict(title='الإيراد (ج.م)'),
                    yaxis2=dict(title='العمليات', overlaying='y', side='right', showgrid=False),
                    hovermode="x unified", legend=dict(orientation="h", y=1.15),
                    margin=dict(l=20, r=20, t=30, b=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
                )
                st.plotly_chart(fig_trend, use_container_width=True)

            with col_chart2:
                st.markdown("##### 📅 الإيرادات حسب أيام الأسبوع")
                weekday_stats = behavior_df.groupby('day_name').agg({'total_revenue': 'sum', 'total_customers': 'sum'}).reset_index()
                day_order = ["السبت", "الأحد", "الإثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة"]
                weekday_stats['day_name'] = pd.Categorical(weekday_stats['day_name'], categories=day_order, ordered=True)
                weekday_stats = weekday_stats.sort_values('day_name')

                fig_week = px.bar(
                    weekday_stats, x='day_name', y='total_revenue',
                    color='total_revenue', custom_data=['total_customers'],
                    labels={'day_name': 'اليوم', 'total_revenue': 'الإيراد (ج.م)'},
                    color_continuous_scale='Greens'
                )
                fig_week.update_traces(hovertemplate="<b>%{x}</b><br>الإيراد: %{y:,.0f} ج.م<br>عدد العمليات: %{customdata[0]:,}<extra></extra>")
                fig_week.update_layout(coloraxis_showscale=False, margin=dict(l=20, r=20, t=20, b=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_week, use_container_width=True)

            col_chart3, col_chart4 = st.columns(2)
            with col_chart3:
                st.markdown("##### 🔥 ساعات الذروة المالية وحركة الزبائن")
                hourly = tx_subset.groupby('hour').agg(total_revenue=('amount_paid', 'sum'), total_customers=('id', 'count')).reset_index()
                hourly['hour_str'] = hourly['hour'].apply(lambda x: f"{x:02d}:00")

                fig_hour = px.bar(
                    hourly, x='hour_str', y='total_revenue',
                    color='total_revenue', custom_data=['total_customers'],
                    labels={'hour_str': 'الساعة', 'total_revenue': 'إجمالي الإيراد (ج.م)'},
                    color_continuous_scale='Sunset'
                )
                fig_hour.update_traces(hovertemplate="<b>الساعة: %{x}</b><br>الإيراد: %{y:,.0f} ج.م<br>عدد العمليات: %{customdata[0]:,}<extra></extra>")
                fig_hour.update_layout(coloraxis_showscale=False, margin=dict(l=20, r=20, t=20, b=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_hour, use_container_width=True)

            with col_chart4:
                st.markdown("##### 🍩 توزيع المصاريف التشغيلية")
                if not opex_df.empty:
                    exp_cat_summary = opex_df.groupby('category')['amount'].sum().reset_index()
                    fig_pie = px.pie(exp_cat_summary, values='amount', names='category', hole=0.45, color_discrete_sequence=px.colors.qualitative.Pastel)
                    fig_pie.update_layout(margin=dict(l=20, r=20, t=20, b=20), paper_bgcolor='rgba(0,0,0,0)', showlegend=True)
                    st.plotly_chart(fig_pie, use_container_width=True)
                else:
                    st.info("لا توجد مصاريف تشغيلية لتوزيعها.")

        # ----------------- سجل المراقبة والإجازات -----------------
        st.markdown("---")
        st.subheader("🕵️ سجل المراقبة والتعديلات (Audit Logs)")
        with engine.connect() as conn:
            audit_filter = "WHERE branch = :b" if selected_branch != "الكل" else ""
            audit_params = {"b": selected_branch} if selected_branch != "الكل" else {}
            try:
                audit_df = pd.read_sql_query(text(f"SELECT timestamp, branch, action_type, entity_type, entity_id, details FROM audit_logs {audit_filter} ORDER BY timestamp DESC LIMIT 50"), conn, params=audit_params)
                if not audit_df.empty:
                    st.dataframe(audit_df.rename(columns={
                        'timestamp': 'الوقت', 'branch': 'الفرع', 'action_type': 'نوع الإجراء',
                        'entity_type': 'الكيان', 'entity_id': 'رقم المعاملة', 'details': 'التفاصيل'
                    }), use_container_width=True, hide_index=True)
                else:
                    st.info("سجل المراقبة نظيف، لا توجد أي تعديلات أو حذوفات.")
            except Exception:
                st.info("سجل المراقبة نظيف.")

        st.markdown("---")
        st.subheader("🏖️ رصيد وإجازات الموظفين")
        leave_heaven = get_leave_balance("Heaven")
        leave_9a = get_leave_balance("9A")
        col_l1, col_l2 = st.columns(2)
        with col_l1:
            st.markdown(f"#### 🌴 فرع Heaven: **{leave_heaven} أيام متبقية**")
            with st.expander("تسجيل إجازة لموظف Heaven (-1 يوم)", expanded=False):
                with st.form("leave_heaven_form"):
                    note_h = st.text_input("ملاحظات الإجازة:", value="إجازة اعتيادية")
                    if st.form_submit_button("🌴 تأكيد خصم يوم إجازة (Heaven)", use_container_width=True):
                        record_leave("Heaven", note_h)
                        st.success("تم خصم يوم إجازة بنجاح!")
                        st.rerun()
        with col_l2:
            st.markdown(f"#### 🌴 فرع 9A: **{leave_9a} أيام متبقية**")
            with st.expander("تسجيل إجازة لموظف 9A (-1 يوم)", expanded=False):
                with st.form("leave_9a_form"):
                    note_9a = st.text_input("ملاحظات الإجازة:", value="إجازة اعتيادية")
                    if st.form_submit_button("🌴 تأكيد خصم يوم إجازة (9A)", use_container_width=True):
                        record_leave("9A", note_9a)
                        st.success("تم خصم يوم إجازة بنجاح!")
                        st.rerun()

        with st.expander("📋 عرض سجل حركات الإجازات بالكامل", expanded=False):
            with engine.connect() as conn:
                leaves_df = pd.read_sql_query(text("SELECT timestamp, branch, action_type, days_count, notes FROM employee_leaves ORDER BY timestamp DESC LIMIT 50"), conn)
                if not leaves_df.empty:
                    st.dataframe(leaves_df.rename(columns={'timestamp': 'الوقت', 'branch': 'الفرع', 'action_type': 'نوع الحركة', 'days_count': 'الأيام', 'notes': 'الملاحظات'}), use_container_width=True, hide_index=True)
                else:
                    st.info("لا توجد حركات إجازات مسجلة بعد.")

        # ----------------- تصدير الملفات بالكامل -----------------
        st.markdown("---")
        st.subheader("📥 النسخ الاحتياطي وتصدير البيانات (Backup & Exports)")
        with engine.connect() as conn:
            all_backup_tx = pd.read_sql_query(text("""
                SELECT t.timestamp, d.date, t.prints_count, t.amount_paid, t.branch
                FROM transactions t JOIN days d ON t.day_id = d.id ORDER BY t.timestamp DESC
            """), conn)
            all_backup_exp = pd.read_sql_query(text("""
                SELECT e.timestamp, d.date, e.branch, e.amount, e.description, e.created_by, e.category
                FROM expenses e JOIN days d ON e.day_id = d.id ORDER BY e.timestamp DESC
            """), conn)

        today_date_str = get_egypt_today_str()

        st.markdown("##### 📅 تحميل ملخص المبيعات اليومية (مجمعة باليوم)")
        if not all_backup_tx.empty:
            daily_summary_all = all_backup_tx.groupby(['date', 'branch']).agg(
                total_customers=('timestamp', 'count'),
                total_prints=('prints_count', 'sum'),
                total_revenue=('amount_paid', 'sum')
            ).reset_index()
            daily_summary_all['date_obj'] = pd.to_datetime(daily_summary_all['date'])
            daily_summary_all['day_name'] = daily_summary_all['date_obj'].dt.day_name().map(ARABIC_DAYS)
            daily_summary_all = daily_summary_all.sort_values(by='date', ascending=False)
            daily_summary_export = daily_summary_all[['date', 'day_name', 'branch', 'total_customers', 'total_prints', 'total_revenue']].rename(columns={
                'date': 'التاريخ', 'day_name': 'اليوم', 'branch': 'الجهة / الفرع',
                'total_customers': 'عدد العمليات', 'total_prints': 'إجمالي الورق', 'total_revenue': 'إجمالي الإيراد (ج.م)'
            })

            col_d1, col_d2, col_d3, col_d4 = st.columns(4)
            csv_daily_all = daily_summary_export.to_csv(index=False).encode('utf-8-sig')
            col_d1.download_button("📥 ملخص الأيام (الكل)", data=csv_daily_all, file_name=f"daily_summary_all_{today_date_str}.csv", mime="text/csv", use_container_width=True)

            df_d_heaven = daily_summary_export[daily_summary_export["الجهة / الفرع"] == "Heaven"]
            if not df_d_heaven.empty:
                csv_d_heaven = df_d_heaven.to_csv(index=False).encode('utf-8-sig')
                col_d2.download_button("📥 ملخص أيام Heaven", data=csv_d_heaven, file_name=f"daily_summary_heaven_{today_date_str}.csv", mime="text/csv", use_container_width=True)

            df_d_9a = daily_summary_export[daily_summary_export["الجهة / الفرع"] == "9A"]
            if not df_d_9a.empty:
                csv_d_9a = df_d_9a.to_csv(index=False).encode('utf-8-sig')
                col_d3.download_button("📥 ملخص أيام 9A", data=csv_d_9a, file_name=f"daily_summary_9a_{today_date_str}.csv", mime="text/csv", use_container_width=True)

            df_d_ev = daily_summary_export[daily_summary_export["الجهة / الفرع"] == "Events"]
            if not df_d_ev.empty:
                csv_d_ev = df_d_ev.to_csv(index=False).encode('utf-8-sig')
                col_d4.download_button("📥 ملخص أيام Events", data=csv_d_ev, file_name=f"daily_summary_events_{today_date_str}.csv", mime="text/csv", use_container_width=True)

        st.markdown("##### 📄 تحميل تفاصيل العمليات الفردية والمصروفات")
        col_b1, col_b2, col_b3, col_b4 = st.columns(4)
        if not all_backup_tx.empty:
            all_backup_tx_display = all_backup_tx.rename(columns={
                'timestamp': 'الوقت', 'date': 'تاريخ يوم العمل', 'prints_count': 'عدد الورق',
                'amount_paid': 'المبلغ (ج.م)', 'branch': 'الجهة / الفرع'
            })
            csv_all = all_backup_tx_display.to_csv(index=False).encode('utf-8-sig')
            col_b1.download_button("📥 تفاصيل العمليات (الكل)", data=csv_all, file_name=f"all_sales_details_{today_date_str}.csv", mime="text/csv", use_container_width=True)

            df_heaven = all_backup_tx_display[all_backup_tx_display["الجهة / الفرع"] == "Heaven"]
            if not df_heaven.empty:
                csv_heaven = df_heaven.to_csv(index=False).encode('utf-8-sig')
                col_b2.download_button("📥 تفاصيل Heaven", data=csv_heaven, file_name=f"heaven_sales_details_{today_date_str}.csv", mime="text/csv", use_container_width=True)

            df_9a = all_backup_tx_display[all_backup_tx_display["الجهة / الفرع"] == "9A"]
            if not df_9a.empty:
                csv_9a = df_9a.to_csv(index=False).encode('utf-8-sig')
                col_b3.download_button("📥 تفاصيل 9A", data=csv_9a, file_name=f"9a_sales_details_{today_date_str}.csv", mime="text/csv", use_container_width=True)

        if not all_backup_exp.empty:
            all_backup_exp_display = all_backup_exp.rename(columns={
                'timestamp': 'الوقت', 'date': 'تاريخ يوم العمل', 'branch': 'الجهة / الفرع',
                'amount': 'المبلغ (ج.م)', 'description': 'الوصف', 'created_by': 'بواسطة', 'category': 'التصنيف'
            })
            csv_exp = all_backup_exp_display.to_csv(index=False).encode('utf-8-sig')
            col_b4.download_button("📥 تحميل كل المصروفات", data=csv_exp, file_name=f"all_expenses_{today_date_str}.csv", mime="text/csv", use_container_width=True)
