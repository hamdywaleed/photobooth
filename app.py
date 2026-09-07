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

# ----------------- APP CONFIG & CLEAN ARABIC STYLING -----------------
st.set_page_config(page_title="Photobooth Management System", page_icon="📸", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800;900&display=swap');
    
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

    [data-testid="stExpanderToggleIcon"], .material-icons, [class*="material-symbols"] {
        font-family: 'Material Icons', 'Material Symbols Outlined' !important;
        direction: ltr !important;
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

# ----------------- DB SETUP (CACHED ENGINE) -----------------
@st.cache_resource
def get_db_engine():
    try:
        if "DATABASE_URL" in st.secrets:
            url = st.secrets["DATABASE_URL"]
        else:
            url = "sqlite:///photobooth.db"
    except Exception:
        url = "sqlite:///photobooth.db"
    return create_engine(url, pool_pre_ping=True)

engine = get_db_engine()
IS_POSTGRES = engine.url.drivername.startswith("postgres")

@st.cache_resource
def init_db():
    pk_def = "id SERIAL PRIMARY KEY" if IS_POSTGRES else "id INTEGER PRIMARY KEY AUTOINCREMENT"
    with engine.begin() as conn:
        conn.execute(text(f"CREATE TABLE IF NOT EXISTS days ({pk_def}, date TEXT UNIQUE NOT NULL)"))
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS transactions (
                {pk_def}, day_id INTEGER NOT NULL, timestamp TEXT NOT NULL,
                prints_count INTEGER NOT NULL, amount_paid REAL NOT NULL,
                branch TEXT NOT NULL, is_collected INTEGER DEFAULT 0, event_id INTEGER,
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
                created_by TEXT NOT NULL, category TEXT DEFAULT 'نثريات وتشغيل', event_id INTEGER,
                paid_from TEXT DEFAULT 'drawer',
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
                cost_per_print REAL DEFAULT 1.1,
                updated_at TEXT
            )
        """))
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS safe_transactions (
                {pk_def}, timestamp TEXT NOT NULL, date TEXT NOT NULL,
                type TEXT NOT NULL, amount REAL NOT NULL, source_destination TEXT NOT NULL, notes TEXT
            )
        """))
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS cash_drawings (
                {pk_def}, timestamp TEXT NOT NULL, date TEXT NOT NULL,
                amount REAL NOT NULL, receiver TEXT NOT NULL, notes TEXT
            )
        """))
        # الفهارس لضمان السرعة الفورية
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_tx_search ON transactions(branch, is_collected, day_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_exp_search ON expenses(branch, category, day_id)"))

        # إعدادات افتراضية للفروع فقط لو الجدول فارغ
        conn.execute(text("""
            INSERT INTO branch_settings (branch, rent, salary, bills, cost_per_print, updated_at)
            VALUES ('9A', 3000, 4000, 650, 1.1, :ts)
            ON CONFLICT (branch) DO NOTHING
        """), {"ts": get_egypt_now_str()})
        conn.execute(text("""
            INSERT INTO branch_settings (branch, rent, salary, bills, cost_per_print, updated_at)
            VALUES ('Heaven', 2500, 2500, 0, 1.1, :ts)
            ON CONFLICT (branch) DO NOTHING
        """), {"ts": get_egypt_now_str()})

    return True

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
        return {"rent": 0.0, "salary": 0.0, "bills": 0.0, "cost_per_print": 1.1}

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
                INSERT INTO expenses (day_id, timestamp, date, branch, amount, description, created_by, category, paid_from)
                VALUES (:d_id, :ts, :date, 'Warehouse', :amount, :desc, 'المدير', 'مشتريات مخزن وأصول', 'safe')
            """), {"d_id": d_id, "ts": now_str, "date": today_str, "amount": cost, "desc": f"فاتورة خامات: {packets} باكتة ورق + {ink_bottles} علبة حبر"})
            conn.execute(text("""
                INSERT INTO safe_transactions (timestamp, date, type, amount, source_destination, notes)
                VALUES (:ts, :date, 'expense', :amount, 'شراء خامات للمخزن', :notes)
            """), {"ts": now_str, "date": today_str, "amount": -cost, "notes": f"شراء {packets} باكتة ورق و {ink_bottles} علبة حبر"})

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

def manual_adjust_branch_stock(branch_name: str, sheets_count: int, action: str = "خصم", notes: str = ""):
    now_str = get_egypt_now_str()
    qty = -sheets_count if action == "خصم" else sheets_count
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO inventory (timestamp, action_type, quantity, notes, branch)
            VALUES (:ts, 'manual_adjust', :qty, :notes, :b)
        """), {"ts": now_str, "qty": qty, "notes": f"تسوية يدوية ({action} {sheets_count} ورقة) | {notes}", "b": branch_name})

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

# ----------------- TRANSACTIONS & SALES -----------------
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
            VALUES (:ts, 'consumption', :qty, 'استهلاك بيع', :b)
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

# ----------------- EXPENSES HELPERS -----------------
def record_expense(branch_name: str, amount: float, description: str, created_by: str, category: str = "نثريات وتشغيل", paid_from: str = "drawer"):
    now_str = get_egypt_now_str()
    today_str = get_egypt_today_str()
    day_id = get_or_create_day_id(today_str)
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO expenses (day_id, timestamp, date, branch, amount, description, created_by, category, paid_from)
            VALUES (:day_id, :ts, :date, :b, :amount, :desc, :user, :cat, :p_from)
        """), {"day_id": day_id, "ts": now_str, "date": today_str, "b": branch_name, "amount": amount, "desc": description, "user": created_by, "cat": category, "p_from": paid_from})
        
        # لو المصروف مدفوع من الخزينة مباشرة يخصم منها فوراً
        if paid_from == "safe":
            conn.execute(text("""
                INSERT INTO safe_transactions (timestamp, date, type, amount, source_destination, notes)
                VALUES (:ts, :date, 'expense', :amount, :dest, :notes)
            """), {"ts": now_str, "date": today_str, "amount": -amount, "dest": f"{branch_name} - {category}", "notes": description})

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
            """), {"ts": now_str, "b": exp["branch"], "exp_id": exp_id, "details": f"حذف مصروف #{exp_id} بقيمة {exp['amount']} ج.م ({exp['description']})"})
            
            # إذا كان مدفوعاً من الخزينة نعيد المبلغ إليها
            if exp.get("paid_from") == "safe":
                conn.execute(text("""
                    INSERT INTO safe_transactions (timestamp, date, type, amount, source_destination, notes)
                    VALUES (:ts, :date, 'refund', :amount, 'استرجاع مصروف محذوف', :notes)
                """), {"ts": now_str, "date": exp["date"], "amount": exp["amount"], "notes": f"استرجاع لحذف المصروف #{exp_id}"})

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
            diff = new_amount - float(exp["amount"])
            if exp.get("paid_from") == "safe" and diff != 0:
                conn.execute(text("""
                    INSERT INTO safe_transactions (timestamp, date, type, amount, source_destination, notes)
                    VALUES (:ts, :date, 'adjust', :amount, 'تعديل مصروف', :notes)
                """), {"ts": now_str, "date": exp["date"], "amount": -diff, "notes": f"تعديل المصروف #{exp_id}"})

            conn.execute(text("""
                INSERT INTO audit_logs (timestamp, branch, action_type, entity_type, entity_id, details)
                VALUES (:ts, :b, 'تعديل مصروف', 'expense', :exp_id, :details)
            """), {"ts": now_str, "b": exp["branch"], "exp_id": exp_id, "details": f"تعديل مصروف #{exp_id} من ({exp['amount']} ج) إلى ({new_amount} ج)"})
            conn.execute(text("UPDATE expenses SET amount = :amount, description = :desc WHERE id = :id"), {"amount": new_amount, "desc": new_desc, "id": exp_id})
            return True
    return False

# ----------------- SAFE & CUSTODY (خزينة وتصفية العهدة بدون افتراضات) -----------------
def record_safe_deposit(amount: float, notes: str = "إيداع كاش"):
    now_str = get_egypt_now_str()
    today_str = get_egypt_today_str()
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO safe_transactions (timestamp, date, type, amount, source_destination, notes)
            VALUES (:ts, :date, 'deposit', :amount, 'إيداع مباشر', :notes)
        """), {"ts": now_str, "date": today_str, "amount": amount, "notes": notes})

def record_safe_withdrawal(amount: float, receiver: str, notes: str = "سحب أرباح / مسحوبات"):
    now_str = get_egypt_now_str()
    today_str = get_egypt_today_str()
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO safe_transactions (timestamp, date, type, amount, source_destination, notes)
            VALUES (:ts, :date, 'withdrawal', :amount, :receiver, :notes)
        """), {"ts": now_str, "date": today_str, "amount": -amount, "receiver": receiver, "notes": notes})
        conn.execute(text("""
            INSERT INTO cash_drawings (timestamp, date, amount, receiver, notes)
            VALUES (:ts, :date, :amount, :rec, :notes)
        """), {"ts": now_str, "date": today_str, "amount": amount, "rec": receiver, "notes": notes})

def settle_drawer_custody(branch_name: str, amount_to_collect: float):
    now_str = get_egypt_now_str()
    today_str = get_egypt_today_str()
    with engine.begin() as conn:
        # تسوية نثريات الدرج الحالية
        unsettled_exp = conn.execute(text("""
            SELECT COALESCE(SUM(amount), 0) FROM expenses 
            WHERE branch = :b AND category = 'نثريات وتشغيل' AND paid_from = 'drawer'
        """), {"b": branch_name}).fetchone()[0]
        unsettled_exp = float(unsettled_exp)

        conn.execute(text("""
            UPDATE expenses SET category = 'نثريات مسواة' 
            WHERE branch = :b AND category = 'نثريات وتشغيل' AND paid_from = 'drawer'
        """), {"b": branch_name})

        # إجمالي ما يتم تسويته من المبيعات
        sales_needed = amount_to_collect + unsettled_exp

        uncoll = conn.execute(text("""
            SELECT id, amount_paid FROM transactions 
            WHERE branch = :b AND is_collected = 0 ORDER BY id ASC
        """), {"b": branch_name}).mappings().fetchall()

        rem = sales_needed
        for tx in uncoll:
            t_amt = float(tx["amount_paid"])
            if rem >= t_amt:
                conn.execute(text("UPDATE transactions SET is_collected = 1 WHERE id = :id"), {"id": tx["id"]})
                rem -= t_amt
            elif rem > 0:
                conn.execute(text("UPDATE transactions SET is_collected = 1 WHERE id = :id"), {"id": tx["id"]})
                rem = 0
                break

        # دخول المبلغ المستلم مباشرة إلى الخزينة
        if amount_to_collect > 0:
            conn.execute(text("""
                INSERT INTO safe_transactions (timestamp, date, type, amount, source_destination, notes)
                VALUES (:ts, :date, 'collection', :amount, :src, 'توريد عهدة درج')
            """), {"ts": now_str, "date": today_str, "amount": amount_to_collect, "src": f"فرع {branch_name}"})

def get_current_safe_balance():
    with engine.connect() as conn:
        res = conn.execute(text("SELECT COALESCE(SUM(amount), 0) FROM safe_transactions")).fetchone()
        return float(res[0]) if res else 0.0

# ----------------- EVENTS HELPERS WITH CASCADING -----------------
def create_event(event_date: str, client_name: str, location: str, device: str, hours: int, start_time: str, end_time: str, total_amount: float, deposit_paid: float, notes: str):
    now_str = get_egypt_now_str()
    remaining = total_amount - deposit_paid
    status = "قيد الانتظار"
    with engine.begin() as conn:
        if IS_POSTGRES:
            ev_id = conn.execute(text("""
                INSERT INTO events (created_at, event_date, client_name, location, device, hours, start_time, end_time, total_amount, deposit_paid, remaining_amount, status, notes)
                VALUES (:created_at, :event_date, :client_name, :location, :device, :hours, :start_time, :end_time, :total_amount, :deposit_paid, :remaining_amount, :status, :notes)
                RETURNING id
            """), {
                "created_at": now_str, "event_date": event_date, "client_name": client_name,
                "location": location, "device": device, "hours": hours, "start_time": start_time,
                "end_time": end_time, "total_amount": total_amount, "deposit_paid": deposit_paid,
                "remaining_amount": remaining, "status": status, "notes": notes
            }).fetchone()[0]
        else:
            conn.execute(text("""
                INSERT INTO events (created_at, event_date, client_name, location, device, hours, start_time, end_time, total_amount, deposit_paid, remaining_amount, status, notes)
                VALUES (:created_at, :event_date, :client_name, :location, :device, :hours, :start_time, :end_time, :total_amount, :deposit_paid, :remaining_amount, :status, :notes)
            """), {
                "created_at": now_str, "event_date": event_date, "client_name": client_name,
                "location": location, "device": device, "hours": hours, "start_time": start_time,
                "end_time": end_time, "total_amount": total_amount, "deposit_paid": deposit_paid,
                "remaining_amount": remaining, "status": status, "notes": notes
            })
            ev_id = conn.execute(text("SELECT last_insert_rowid()")).fetchone()[0]

        if deposit_paid > 0:
            d_id = get_or_create_day_id(event_date)
            # العربون يدخل مباشرة للخزينة
            conn.execute(text("""
                INSERT INTO transactions (day_id, timestamp, prints_count, amount_paid, branch, is_collected, event_id)
                VALUES (:day_id, :ts, 0, :amount, 'Events', 1, :ev_id)
            """), {"day_id": d_id, "ts": now_str, "amount": deposit_paid, "ev_id": ev_id})
            conn.execute(text("""
                INSERT INTO safe_transactions (timestamp, date, type, amount, source_destination, notes)
                VALUES (:ts, :date, 'event_deposit', :amount, 'حجز إيفنت', :notes)
            """), {"ts": now_str, "date": event_date, "amount": deposit_paid, "notes": f"عربون إيفنت #{ev_id} ({client_name})"})

def complete_event_settlement(event_id: int, from_branch: str, prints_count: int, transport_cost: float, worker_cost: float):
    now_str = get_egypt_now_str()
    cfg = get_branch_settings(from_branch if from_branch != "Warehouse" else "9A")
    cost_per_p = float(cfg.get("cost_per_print", 1.1))
    paper_cost = prints_count * cost_per_p
    total_exp = paper_cost + transport_cost + worker_cost
    with engine.begin() as conn:
        ev = conn.execute(text("SELECT * FROM events WHERE id = :id"), {"id": event_id}).mappings().fetchone()
        if ev:
            rem = float(ev["remaining_amount"])
            event_date = ev["event_date"]
            total_rev = float(ev["total_amount"])
            profit = total_rev - total_exp
            d_id = get_or_create_day_id(event_date)
            
            # باقي المبلغ المستلم يدخل الخزينة مباشرة
            if rem > 0:
                conn.execute(text("""
                    INSERT INTO transactions (day_id, timestamp, prints_count, amount_paid, branch, is_collected, event_id)
                    VALUES (:day_id, :ts, :prints, :amount, 'Events', 1, :ev_id)
                """), {"day_id": d_id, "ts": now_str, "prints": prints_count, "amount": rem, "ev_id": event_id})
                conn.execute(text("""
                    INSERT INTO safe_transactions (timestamp, date, type, amount, source_destination, notes)
                    VALUES (:ts, :date, 'event_settle', :amount, 'باقي إيفنت', :notes)
                """), {"ts": now_str, "date": event_date, "amount": rem, "notes": f"تسليم باقي إيفنت #{event_id} ({ev['client_name']})"})
            
            # خصم الورق المستهلك من عهدة الفرع
            if prints_count > 0 and from_branch:
                conn.execute(text("""
                    INSERT INTO inventory (timestamp, action_type, quantity, notes, branch)
                    VALUES (:ts, 'consumption', :qty, :notes, :branch)
                """), {"ts": now_str, "qty": -prints_count, "notes": f"استهلاك ورق إيفنت #{event_id}", "branch": from_branch})

            # تسجيل مصاريف الإيفنت وخصمها من الخزينة
            if total_exp > 0:
                desc = f"مصروف إيفنت #{event_id} ({ev['client_name']}): ورق={paper_cost:,.0f}ج، مواصلات={transport_cost:,.0f}ج، موظف={worker_cost:,.0f}ج"
                conn.execute(text("""
                    INSERT INTO expenses (day_id, timestamp, date, branch, amount, description, created_by, category, event_id, paid_from)
                    VALUES (:day_id, :ts, :date, 'Events', :amount, :desc, 'تسوية إيفنت', 'تشغيل إيفنتات', :ev_id, 'safe')
                """), {"day_id": d_id, "ts": now_str, "date": event_date, "amount": total_exp, "desc": desc, "ev_id": event_id})
                conn.execute(text("""
                    INSERT INTO safe_transactions (timestamp, date, type, amount, source_destination, notes)
                    VALUES (:ts, :date, 'event_expense', :amount, 'مصاريف إيفنت', :notes)
                """), {"ts": now_str, "date": event_date, "amount": -total_exp, "notes": desc})

            conn.execute(text("""
                UPDATE events
                SET deposit_paid = total_amount, remaining_amount = 0, status = 'تم التنفيذ والتسوية',
                    prints_used = :prints, paper_cost = :p_cost, transport_cost = :t_cost,
                    worker_cost = :w_cost, total_expenses = :tot_exp, net_profit = :profit
                WHERE id = :id
            """), {"prints": prints_count, "p_cost": paper_cost, "t_cost": transport_cost, "w_cost": worker_cost, "tot_exp": total_exp, "profit": profit, "id": event_id})

def delete_event(event_id: int):
    now_str = get_egypt_now_str()
    with engine.begin() as conn:
        ev = conn.execute(text("SELECT * FROM events WHERE id = :id"), {"id": event_id}).mappings().fetchone()
        if ev:
            # استرجاع الورق المستهلك
            if ev.get("prints_used", 0) > 0 and ev.get("device"):
                conn.execute(text("""
                    INSERT INTO inventory (timestamp, action_type, quantity, notes, branch)
                    VALUES (:ts, 'restock', :qty, :notes, :b)
                """), {"ts": now_str, "qty": ev["prints_used"], "notes": f"استرجاع ورق لحذف إيفنت #{event_id}", "b": ev["device"]})
            
            # تسوية معاملات الخزينة المرتبطة بالإيفنت
            conn.execute(text("DELETE FROM safe_transactions WHERE notes LIKE :pattern"), {"pattern": f"%إيفنت #{event_id}%"})
            conn.execute(text("DELETE FROM expenses WHERE event_id = :id"), {"id": event_id})
            conn.execute(text("DELETE FROM transactions WHERE event_id = :id"), {"id": event_id})
            conn.execute(text("DELETE FROM events WHERE id = :id"), {"id": event_id})
            return True
    return False

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
        btn_col1, btn_col2, btn_col3 = st.columns(3)
        with btn_col1:
            if st.button("🖼️ كارت فردي\n(30 ج - 1 ورقة)", use_container_width=True):
                if current_stock < 1:
                    st.error("⚠️ رصيد الورق غير كافٍ!")
                else:
                    record_transaction(branch, 1, 30.0)
                    st.rerun()
        with btn_col2:
            if st.button("🎞️ كارتين\n(50 ج - 2 ورقة)", use_container_width=True):
                if current_stock < 2:
                    st.error("⚠️ رصيد الورق غير كافٍ!")
                else:
                    record_transaction(branch, 2, 50.0)
                    st.rerun()
        with btn_col3:
            if st.button("📸 عرض 5 كروت\n(100 ج - 5 ورقات)", use_container_width=True):
                if current_stock < 5:
                    st.error("⚠️ رصيد الورق غير كافٍ!")
                else:
                    record_transaction(branch, 5, 100.0)
                    st.rerun()
    else:
        btn_col1, btn_col2, btn_col3 = st.columns(3)
        with btn_col1:
            if st.button("🖼️ صورة فردي\n(50 ج - 1 ورقة)", use_container_width=True):
                if current_stock < 1:
                    st.error("⚠️ رصيد الورق غير كافٍ!")
                else:
                    record_transaction(branch, 1, 50.0)
                    st.rerun()
        with btn_col2:
            if st.button("🎞️ كارت ثلاثي\n(90 ج - 2 ورقة)", use_container_width=True):
                if current_stock < 2:
                    st.error("⚠️ رصيد الورق غير كافٍ!")
                else:
                    record_transaction(branch, 2, 90.0)
                    st.rerun()
        with btn_col3:
            if st.button("📸 كارت رباعي\n(120 ج - 3 ورقات)", use_container_width=True):
                if current_stock < 3:
                    st.error("⚠️ رصيد الورق غير كافٍ!")
                else:
                    record_transaction(branch, 3, 120.0)
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
                        st.rerun()
    with act_c2:
        with st.expander("🎁 تسجيل طباعة مجانية (ضيافة / إهداء)", expanded=False):
            with st.form("free_input_form", clear_on_submit=True):
                f_qty = st.number_input("عدد الورق المجاني المطبوع:", min_value=1, max_value=50, value=1, step=1)
                f_notes = st.text_input("جهة الإهداء / السبب:", placeholder="مثال: صاحب المكان...")
                if st.form_submit_button("تأكيد صرف المجاني", use_container_width=True):
                    if current_stock < f_qty:
                        st.error("رصيد الورق المتاح لا يكفي!")
                    else:
                        record_free_prints(branch, int(f_qty), f_notes.strip() if f_notes.strip() else "طباعة مجانية / ضيافة")
                        st.rerun()

    st.markdown("<br><hr>", unsafe_allow_html=True)
    col_manual, col_exp = st.columns(2)
    with col_manual:
        with st.expander("⚙️ إدخال مبيعات يدوي", expanded=False):
            with st.form("manual_form", clear_on_submit=True):
                prints = st.number_input("عدد الورق المطبوع", min_value=1, max_value=50, value=None, step=1)
                amount = st.number_input("المبلغ المدفوع (ج.م)", min_value=0.0, value=None, step=10.0)
                if st.form_submit_button("✅ تسجيل يدوياً", use_container_width=True):
                    if prints and amount is not None:
                        if current_stock >= prints:
                            record_transaction(branch, prints, amount)
                            st.rerun()
                        else:
                            st.error("رصيد الورق لا يكفي!")
    with col_exp:
        with st.expander("💸 تسجيل مصروفات سريعة من الدرج", expanded=False):
            with st.form("employee_expense_form", clear_on_submit=True):
                exp_amount = st.number_input("مبلغ المصروف (ج.م):", min_value=1.0, value=None, step=5.0)
                exp_desc = st.text_input("وصف المصروف:", placeholder="شاي، صيانة، نثريات...")
                if st.form_submit_button("💸 تسجيل المصروف", use_container_width=True):
                    if exp_amount and exp_desc.strip():
                        record_expense(branch, float(exp_amount), exp_desc.strip(), f"موظف {branch}", "نثريات وتشغيل", "drawer")
                        st.rerun()

    st.markdown("---")
    st.subheader("📋 عمليات ومصروفات يوم العمل الحالي")
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
            
            options = {f"عملية #{row['id']} - ({row['prints_count']} ورق | {row['amount_paid']} ج)": row['id'] for _, row in today_tx.iterrows()}
            selected_label = st.selectbox("اختر العملية للتعديل أو الحذف:", list(options.keys()), key="sel_tx")
            selected_id = options[selected_label]
            selected_row = today_tx[today_tx['id'] == selected_id].iloc[0]
            
            col_act1, col_act2 = st.columns(2)
            with col_act1:
                with st.expander("✏️ تعديل العملية", expanded=False):
                    with st.form("edit_form"):
                        new_p = st.number_input("تعديل عدد الورق:", min_value=1, max_value=50, value=int(selected_row['prints_count']), step=1)
                        new_a = st.number_input("تعديل المبلغ:", min_value=0.0, value=float(selected_row['amount_paid']), step=10.0)
                        if st.form_submit_button("حفظ التعديل", use_container_width=True):
                            update_transaction(selected_id, branch, new_p, new_a)
                            st.rerun()
            with col_act2:
                with st.expander("🗑️ حذف العملية", expanded=False):
                    if st.button("تأكيد الحذف واسترجاع الورق", type="primary", use_container_width=True, key="del_tx_btn"):
                        delete_transaction(selected_id, branch)
                        st.rerun()

# ==============================================================
# 2. ADMIN DASHBOARD
# ==============================================================
elif role == "admin":
    check_and_add_monthly_allowance()

    bar_c1, bar_c2, bar_c3 = st.columns([3, 3, 1])
    with bar_c1:
        st.markdown("<h2 style='margin:0; font-weight:900;'>👑 إدارة المنظومة المالية</h2>", unsafe_allow_html=True)
    with bar_c2:
        sec_choice = st.radio("القسم:", ["📊 الفروع والتحليل المالي", "📦 المخزن والتوريدات", "🎪 حجوزات الإيفنتات", "⚙️ إعدادات الفروع"], horizontal=True)
    with bar_c3:
        st.button("🚪 خروج", on_click=logout, use_container_width=True)
    st.markdown("---")

    # ================= 2.A المخزن والتوريدات =================
    if sec_choice == "📦 المخزن والتوريدات":
        st.title("📦 إدارة المخزون العام وتوريدات الفروع")

        warehouse_sheets = get_current_stock("Warehouse")
        warehouse_packets = warehouse_sheets / 100.0
        stock_heaven = get_current_stock("Heaven")
        stock_9a = get_current_stock("9A")
        warehouse_refills = get_ink_refills("Warehouse")
        ink_heaven_refills = get_ink_refills("Heaven")
        ink_9a_refills = get_ink_refills("9A")

        inv_c1, inv_c2, inv_c3 = st.columns(3)
        inv_c1.metric("🏢 ورق المخزن العام", f"{warehouse_packets:,.1f} باكتة", f"{warehouse_sheets:,} ورقة")
        inv_c2.metric("🏪 ورق فرع 9A", f"{stock_9a:,} ورقة")
        inv_c3.metric("🏪 ورق فرع Heaven", f"{stock_heaven:,} ورقة")

        st.markdown("---")
        ink_c1, ink_c2, ink_c3 = st.columns(3)
        ink_c1.metric("🖋️ رصيد الحبر بالمخزن", f"{warehouse_refills} مليات طابعة")
        ink_c2.metric("🖋️ حبر فرع 9A المورد", f"{ink_9a_refills} ملوة")
        ink_c3.metric("🖋️ حبر فرع Heaven المورد", f"{ink_heaven_refills} ملوة")

        st.markdown("---")
        col_in1, col_in2 = st.columns(2)
        with col_in1:
            st.markdown("### 📥 استلام وتوريد شحنة جديدة للمخزن")
            with st.form("new_stock_form", clear_on_submit=True):
                p_qty = st.number_input("عدد باكتات الورق (1 باكتة = 100 ورقة):", min_value=0, value=0, step=10)
                ink_qty = st.number_input("عدد علب الحبر (العلبة = 2 ملوة طابعة):", min_value=0.0, value=0.0, step=0.5)
                bill_cost = st.number_input("إجمالي الفاتورة (ج.م) [يُخصم من الخزينة]:", min_value=0.0, value=0.0, step=100.0)
                stock_notes = st.text_input("ملاحظات الفاتورة:", placeholder="شراء ورق، أحبار...")
                if st.form_submit_button("📥 تأكيد دخول الشحنة", use_container_width=True):
                    if p_qty > 0 or ink_qty > 0:
                        add_warehouse_stock(int(p_qty), float(ink_qty), float(bill_cost), stock_notes)
                        st.rerun()

        with col_in2:
            st.markdown("### 🚚 تحويل ورق وحبر إلى الفروع")
            with st.expander("📄 تحويل ورق للفرع (بالورقة)", expanded=True):
                with st.form("transfer_stock_form", clear_on_submit=True):
                    target_b = st.selectbox("الفرع المحول إليه:", ["9A", "Heaven"], key="t_b_paper")
                    trans_sheets = st.number_input("عدد الورق المحول:", min_value=1, max_value=max(int(warehouse_sheets), 1), value=100, step=50)
                    trans_notes = st.text_input("ملاحظات التحويل:", placeholder="تسليم شيفت...")
                    if st.form_submit_button("🚚 تحويل الورق فوراً", use_container_width=True):
                        if warehouse_sheets >= trans_sheets:
                            transfer_stock_to_branch(target_b, int(trans_sheets), trans_notes)
                            st.rerun()

            with st.expander("🖋️ تزويد الفرع بحبر (بالملوة)"):
                with st.form("transfer_ink_form", clear_on_submit=True):
                    target_b_ink = st.selectbox("الفرع:", ["9A", "Heaven"], key="t_b_ink")
                    refills_to_send = st.number_input("عدد المليات:", min_value=1, max_value=max(warehouse_refills, 1), value=1, step=1)
                    ink_trans_notes = st.text_input("ملاحظات:", placeholder="ملء طابعة...")
                    if st.form_submit_button("تزويد الحبر فوراً", use_container_width=True):
                        if warehouse_refills >= refills_to_send:
                            transfer_ink_to_branch(target_b_ink, int(refills_to_send), ink_trans_notes)
                            st.rerun()

            with st.expander("✂️ تسوية / سحب رصيد ورق من فرع (بالورقة)"):
                with st.form("manual_adjust_stock_form", clear_on_submit=True):
                    adj_b = st.selectbox("الفرع:", ["9A", "Heaven"], key="adj_b")
                    adj_type = st.radio("نوع التعديل:", ["خصم", "إضافة"], horizontal=True)
                    adj_qty = st.number_input("عدد الورق:", min_value=1, max_value=2000, value=10, step=5)
                    adj_notes = st.text_input("سبب السحب / التعديل:", placeholder="تسوية جرد...")
                    if st.form_submit_button("تأكيد تعديل الرصيد", use_container_width=True):
                        manual_adjust_branch_stock(adj_b, int(adj_qty), adj_type, adj_notes)
                        st.rerun()

    # ================= 2.B قسم الإيفنتات =================
    elif sec_choice == "🎪 حجوزات الإيفنتات":
        st.title("🎪 إدارة حجوزات الإيفنتات الخارجية")
        with engine.connect() as conn:
            all_events_raw = pd.read_sql_query(text("SELECT * FROM events ORDER BY event_date ASC, start_time ASC"), conn)

        with st.expander("➕ تسجيل حجز إيفنت جديد", expanded=False):
            with st.form("new_event_form", clear_on_submit=True):
                ef1, ef2, ef3 = st.columns(3)
                with ef1:
                    ev_client = st.text_input("اسم العميل:")
                    ev_loc = st.text_input("مكان الإيفنت:")
                    ev_dev = st.selectbox("الجهاز المخصص:", ["Heaven", "9A"])
                with ef2:
                    ev_date = st.date_input("تاريخ الإيفنت:", value=date.today())
                    ev_hours = st.number_input("الساعات:", min_value=1, max_value=24, value=3, step=1)
                    ev_start = st.time_input("ساعة البداية:", value=time(19, 0))
                with ef3:
                    ev_total = st.number_input("قيمة الحجز (ج.م):", min_value=100.0, value=2000.0, step=500.0)
                    ev_deposit = st.number_input("العربون المدفوع (ج.م) [يدخل الخزينة فوراً]:", min_value=0.0, value=1000.0, step=500.0)
                    ev_notes = st.text_input("ملاحظات:")

                start_dt = datetime.combine(ev_date, ev_start)
                end_dt = start_dt + timedelta(hours=int(ev_hours))
                ev_start_str = format_arabic_time(start_dt.strftime("%I:%M %p"))
                ev_end_str = format_arabic_time(end_dt.strftime("%I:%M %p"))

                if st.form_submit_button("💾 حفظ الحجز", use_container_width=True):
                    if ev_client.strip() and ev_loc.strip():
                        create_event(str(ev_date), ev_client.strip(), ev_loc.strip(), ev_dev, int(ev_hours), ev_start_str, ev_end_str, float(ev_total), float(ev_deposit), ev_notes.strip())
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
                    if not is_settled:
                        with st.form(f"settle_form_{ev['id']}"):
                            c_b, c_p = st.columns(2)
                            with c_b:
                                default_idx = 0 if ev.get('device') == '9A' else 1
                                settle_branch = st.selectbox("🏢 خصم الورق من عهدة فرع:", ["9A", "Heaven", "Warehouse"], index=default_idx, key=f"b_{ev['id']}")
                            with c_p:
                                in_prints = c_p.number_input("الورق المستهلك:", min_value=0, max_value=2000, value=50, step=10, key=f"p_{ev['id']}")

                            c_t, c_w = st.columns(2)
                            with c_t:
                                in_trans = c_t.number_input("المواصلات (ج):", min_value=0.0, value=100.0, step=50.0, key=f"t_{ev['id']}")
                            with c_w:
                                in_worker = c_w.number_input("أجر الموظف (ج):", min_value=0.0, value=100.0, step=10.0, key=f"w_{ev['id']}")

                            if st.form_submit_button("✅ اعتماد التنفيذ والتسوية", use_container_width=True):
                                complete_event_settlement(ev['id'], settle_branch, int(in_prints), float(in_trans), float(in_worker))
                                st.rerun()

                    if st.button(f"🗑️ حذف الإيفنت ومسح متعلقاته #{ev['id']}", key=f"del_ev_{ev['id']}"):
                        delete_event(ev['id'])
                        st.rerun()

    # ================= 2.C إعدادات الفروع =================
    elif sec_choice == "⚙️ إعدادات الفروع":
        st.title("⚙️ إعدادات التكاليف الثابتة للفروع")
        set_col1, set_col2 = st.columns(2)
        for b_name, col in [("9A", set_col1), ("Heaven", set_col2)]:
            cfg = get_branch_settings(b_name)
            with col:
                st.markdown(f"### 🏢 إعدادات فرع {b_name}")
                with st.form(f"cfg_form_{b_name}"):
                    n_rent = st.number_input(f"الإيجار الشهري ({b_name}):", value=float(cfg.get('rent', 0.0)), step=100.0)
                    n_sal = st.number_input(f"إجمالي المرتبات والعمالة ({b_name}):", value=float(cfg.get('salary', 0.0)), step=100.0)
                    n_bills = st.number_input(f"فواتير وأقساط شهرية ({b_name}):", value=float(cfg.get('bills', 0.0)), step=50.0)
                    n_cost = st.number_input(f"تكلفة الورقة ({b_name}):", value=float(cfg.get('cost_per_print', 1.1)), step=0.1)
                    monthly_fixed = n_rent + n_sal + n_bills
                    st.info(f"إجمالي التكلفة الثابتة الشهرية: **{monthly_fixed:,.0f} ج.م** (~ {monthly_fixed/30:,.0f} ج / يومياً)")
                    if st.form_submit_button(f"💾 حفظ إعدادات {b_name}", use_container_width=True):
                        update_branch_settings(b_name, n_rent, n_sal, n_bills, n_cost)
                        st.rerun()

    # ================= 2.D الفروع والتحليل المالي =================
    else:
        with engine.connect() as conn:
            all_tx_raw = pd.read_sql_query(text("SELECT t.*, d.date FROM transactions t JOIN days d ON t.day_id = d.id ORDER BY t.timestamp ASC"), conn)
            all_exp_raw = pd.read_sql_query(text("SELECT e.*, d.date as operational_date FROM expenses e JOIN days d ON e.day_id = d.id ORDER BY e.timestamp ASC"), conn)
            all_drawings = pd.read_sql_query(text("SELECT * FROM cash_drawings ORDER BY timestamp DESC"), conn)

        all_dates = []
        if not all_tx_raw.empty:
            all_dates.extend(pd.to_datetime(all_tx_raw['date']).dt.date.tolist())
        if not all_exp_raw.empty:
            all_dates.extend(pd.to_datetime(all_exp_raw['operational_date']).dt.date.tolist())

        min_date = min(all_dates) if all_dates else date.today()
        max_date = max(all_dates) if all_dates else date.today()

        top_f1, top_f2 = st.columns([1, 1.5])
        with top_f1:
            selected_branch = st.selectbox("🏢 نطاق التحليل:", ["الكل", "Heaven", "9A", "Events"])
        with top_f2:
            date_range = st.date_input("📅 الفترة الزمنية:", value=(min_date, max_date), min_value=min_date, max_value=max_date)

        if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
            start_dt, end_dt = date_range
            mask_tx = (pd.to_datetime(all_tx_raw['date']).dt.date >= start_dt) & (pd.to_datetime(all_tx_raw['date']).dt.date <= end_dt) if not all_tx_raw.empty else pd.Series(dtype=bool)
            mask_exp = (pd.to_datetime(all_exp_raw['operational_date']).dt.date >= start_dt) & (pd.to_datetime(all_exp_raw['operational_date']).dt.date <= end_dt) if not all_exp_raw.empty else pd.Series(dtype=bool)
            filtered_tx = all_tx_raw.loc[mask_tx].copy() if not all_tx_raw.empty else pd.DataFrame()
            filtered_exp = all_exp_raw.loc[mask_exp].copy() if not all_exp_raw.empty else pd.DataFrame()
        else:
            filtered_tx = all_tx_raw.copy()
            filtered_exp = all_exp_raw.copy()

        tx_subset = filtered_tx if selected_branch == "الكل" else filtered_tx[filtered_tx['branch'] == selected_branch]
        exp_subset = filtered_exp if selected_branch == "الكل" else (filtered_exp[filtered_exp['branch'] == "Events"] if selected_branch == "Events" else filtered_exp[filtered_exp['branch'].isin([selected_branch, 'General'])])

        total_rev_all = tx_subset['amount_paid'].sum() if not tx_subset.empty else 0.0
        total_prints_all = tx_subset['prints_count'].sum() if not tx_subset.empty else 0
        
        opex_df = exp_subset[~exp_subset['category'].isin(['مشتريات مخزن وأصول', 'توزيعات أرباح'])] if not exp_subset.empty else pd.DataFrame()
        paid_opex_total = opex_df['amount'].sum() if not opex_df.empty else 0.0

        total_drawings = all_drawings['amount'].sum() if not all_drawings.empty else 0.0

        # حساب تكلفة الورق حسب الفرع
        if selected_branch in ["9A", "Heaven"]:
            unit_cost = float(get_branch_settings(selected_branch).get("cost_per_print", 1.1))
            cogs_total = total_prints_all * unit_cost
        else:
            cost_9a = float(get_branch_settings("9A").get("cost_per_print", 1.1))
            cost_h = float(get_branch_settings("Heaven").get("cost_per_print", 1.1))
            p_9a = tx_subset[tx_subset['branch'] == '9A']['prints_count'].sum() if not tx_subset.empty else 0
            p_h = tx_subset[tx_subset['branch'] == 'Heaven']['prints_count'].sum() if not tx_subset.empty else 0
            p_ev = tx_subset[tx_subset['branch'] == 'Events']['prints_count'].sum() if not tx_subset.empty else 0
            cogs_total = (p_9a * cost_9a) + (p_h * cost_h) + (p_ev * 1.1)

        # صافي الأرباح المحققة بعد خصم الورق والمصروفات
        net_profit = total_rev_all - cogs_total - paid_opex_total

        # العهدة الصافية الحالية في أدراج الفروع
        with engine.connect() as conn:
            uncoll_sales = conn.execute(text("SELECT COALESCE(SUM(amount_paid), 0) FROM transactions WHERE is_collected = 0")).fetchone()[0]
            unsettled_expenses = conn.execute(text("SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE category = 'نثريات وتشغيل' AND paid_from = 'drawer'")).fetchone()[0]
        net_uncollected_custody = max(float(uncoll_sales) - float(unsettled_expenses), 0.0)

        # الكاش الحقيقي بالخزينة
        safe_cash = get_current_safe_balance()

        waste_count = get_waste_count(selected_branch)
        free_count = get_free_count(selected_branch)

        # ----------------- المؤشرات العلوية -----------------
        st.markdown("#### 📈 الأرباح وقائمة الدخل الحقيقية (P&L)")
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("💰 إجمالي الإيرادات", f"{total_rev_all:,.0f} ج.م")
        kpi2.metric("🖨️ استهلاك الورق", f"{total_prints_all:,} ورقة", delta=f"{cogs_total:,.0f} ج تكلفة الخامات", delta_color="off")
        kpi3.metric("🏢 المصروفات المسجلة", f"{paid_opex_total:,.0f} ج.م", delta=f"-{paid_opex_total:,.0f}", delta_color="normal")
        kpi4.metric("📈 صافي الأرباح الكلية", f"{net_profit:,.0f} ج.م", delta=f"{net_profit:,.0f}", delta_color="normal")

        st.markdown("#### 💵 حركة السيولة والفلوس فين؟")
        kpi5, kpi6, kpi7, kpi8 = st.columns(4)
        kpi5.metric("🏦 الكاش بالخزينة (معاك الآن)", f"{safe_cash:,.0f} ج.م", delta="رصيد الخزينة الفعلي")
        kpi6.metric("⏳ عهدة معلقة بالأدراج (صافي)", f"{net_uncollected_custody:,.0f} ج.م", delta="مطلوب توريدها", delta_color="off")
        kpi7.metric("💼 إجمالي الأرباح المسحوبة", f"{total_drawings:,.0f} ج.م", delta="مسحوبات شركاء", delta_color="off")
        kpi8.metric("🗑️ تالف / 🎁 مجاني", f"{waste_count} تالف | {free_count} هدايا")
        st.markdown("---")

        # ----------------- تسليم وتوريد العهدة -----------------
        st.markdown("### 📥 تصفية وتوريد عهدة الفروع")
        b_list = ["9A", "Heaven"] if selected_branch == "الكل" else ([selected_branch] if selected_branch in ["9A", "Heaven"] else [])
        has_pending = False

        for b_name in b_list:
            with engine.connect() as conn:
                u_s = conn.execute(text("SELECT COALESCE(SUM(amount_paid), 0) FROM transactions WHERE branch = :b AND is_collected = 0"), {"b": b_name}).fetchone()[0]
                u_e = conn.execute(text("SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE branch = :b AND category = 'نثريات وتشغيل' AND paid_from = 'drawer'"), {"b": b_name}).fetchone()[0]
            u_s, u_e = float(u_s), float(u_e)
            net_d = max(u_s - u_e, 0.0)

            if u_s > 0 or u_e > 0:
                has_pending = True
                with st.expander(f"🏢 فرع {b_name} | الصافي المتاح بالدرج: {net_d:,.0f} ج.م (مبيعات: {u_s:,.0f} ج - نثريات: {u_e:,.0f} ج)", expanded=True):
                    col_p1, col_p2 = st.columns([3, 2])
                    with col_p1:
                        amt_to_take = st.number_input(f"المبلغ المستلم للتوريد إلى الخزينة (ج.م):", min_value=0.0, max_value=float(net_d), value=float(net_d), step=50.0, key=f"inp_{b_name}")
                        rem_in_drawer = net_d - amt_to_take
                        if rem_in_drawer > 0:
                            st.info(f"💡 سيتبقى في درج الفرع فكة مستمرة: **{rem_in_drawer:,.0f} ج.م**")
                    with col_p2:
                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.button(f"تأكيد استلام ({amt_to_take:,.0f} ج) للخزينة", key=f"btn_{b_name}", use_container_width=True):
                            if amt_to_take > 0:
                                settle_drawer_custody(b_name, amt_to_take)
                                st.rerun()

        if not has_pending:
            st.success("✅ العهدة مع الموظفين صفر حالياً، لا توجد أي مبالغ معلقة بالأدراج!")

        st.markdown("---")
        c_act1, c_act2, c_act3 = st.columns(3)
        with c_act1:
            with st.expander("📥 إيداع كاش بالخزينة (رأس مال / تمويل)"):
                with st.form("safe_deposit_form", clear_on_submit=True):
                    dep_amt = st.number_input("مبلغ الإيداع (ج.م):", min_value=100.0, step=500.0)
                    dep_notes = st.text_input("مصدر الإيداع / ملاحظات:", placeholder="رصيد افتتاحي، ضخ سيولة...")
                    if st.form_submit_button("تأكيد الإيداع للخزينة", use_container_width=True):
                        if dep_amt:
                            record_safe_deposit(float(dep_amt), dep_notes.strip())
                            st.rerun()

        with c_act2:
            with st.expander("💼 تسجيل سحب أرباح للشركاء (Drawings)"):
                with st.form("drawings_form", clear_on_submit=True):
                    d_amt = st.number_input("المبلغ المسحوب (ج.م):", min_value=100.0, step=500.0)
                    d_rec = st.text_input("اسم المستلم / الشريك:")
                    d_note = st.text_input("ملاحظات:")
                    if st.form_submit_button("سحب الأرباح من الخزينة", use_container_width=True):
                        if d_amt and d_rec.strip():
                            record_safe_withdrawal(float(d_amt), d_rec.strip(), d_note.strip())
                            st.rerun()

        with c_act3:
            with st.expander("💸 تسجيل مصروف يدفع كاش من الخزينة"):
                with st.form("admin_exp_form", clear_on_submit=True):
                    ad_branch = st.selectbox("جهة المصروف:", ["General", "Heaven", "9A", "Events"], format_func=lambda x: "عام (يوزع)" if x == "General" else ("🎪 إيفنت" if x == "Events" else f"فرع {x}"))
                    ad_cat = st.selectbox("بند المصروف:", ["إيجار", "مرتبات وعمالة", "فواتير وأقساط", "إعلانات وتسويق", "نثريات مسواة"])
                    ad_amount = st.number_input("المبلغ (ج.م):", min_value=1.0, value=None, step=50.0)
                    ad_desc = st.text_input("الوصف:", placeholder="إيجار، صيانة...")
                    if st.form_submit_button("صرف من الخزينة وتسجيل المصروف", use_container_width=True):
                        if ad_amount and ad_desc.strip():
                            record_expense(ad_branch, float(ad_amount), ad_desc.strip(), "المدير", ad_cat, "safe")
                            st.rerun()

        # ----------------- جداول اليوم الحالي (مبيعات ومصروفات اليوم) -----------------
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

        # ----------------- جدول سلوك العمليات والربح اليومي -----------------
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

            day_exp_map = exp_subset.groupby('operational_date')['amount'].sum().to_dict() if not exp_subset.empty else {}
            behavior_df['day_expenses'] = behavior_df['date'].map(day_exp_map).fillna(0.0)

            daily_fixed_cost = 255.0 if selected_branch == "9A" else (167.0 if selected_branch == "Heaven" else (0.0 if selected_branch == "Events" else 422.0))
            cfg_cost_val = float(get_branch_settings("9A").get("cost_per_print", 1.1))
            behavior_df['paper_cost'] = behavior_df['total_prints'] * cfg_cost_val
            behavior_df['daily_net_profit'] = behavior_df['total_revenue'] - behavior_df['paper_cost'] - behavior_df['day_expenses'] - daily_fixed_cost

            def extract_time(ts):
                if pd.isna(ts): return "-"
                return format_arabic_time(pd.to_datetime(ts).strftime('%I:%M %p'))

            behavior_df['first_time'] = behavior_df['first_customer_time'].apply(extract_time)
            behavior_df['last_time'] = behavior_df['last_customer_time'].apply(extract_time)
            behavior_df['peak_str'] = behavior_df['peak_hour'].apply(lambda x: f"{int(x)}:00" if pd.notna(x) else "-")

            st.subheader(f"📋 إيرادات وسلوك العمليات والربح اليومي ({selected_branch})")
            display_df = behavior_df[['date', 'day_name', 'first_time', 'last_time', 'peak_str', 'total_customers', 'total_prints', 'total_revenue', 'day_expenses', 'daily_net_profit']].copy()
            display_df.columns = ['تاريخ يوم العمل', 'اليوم', 'أول عملية', 'آخر عملية', 'ساعة الذروة', 'العمليات', 'الورق', 'الإيراد (ج.م)', 'نثريات (ج)', 'صافي ربح اليوم (ج)']
            st.dataframe(display_df, use_container_width=True, hide_index=True)

            # الرسوم البيانية الأربعة
            col_chart1, col_chart2 = st.columns(2)
            with col_chart1:
                st.markdown("##### 📉 الإيرادات والعمليات خلال الفترة")
                fig_trend = go.Figure()
                fig_trend.add_trace(go.Scatter(x=days_df['date'], y=days_df['total_revenue'], mode='lines+markers', name='الإيراد (ج.م)', line=dict(color='#00CC96', width=3)))
                fig_trend.add_trace(go.Bar(x=days_df['date'], y=days_df['total_customers'], name='عدد العمليات', yaxis='y2', marker_color='rgba(99, 110, 250, 0.45)'))
                fig_trend.update_layout(yaxis=dict(title='الإيراد (ج.م)'), yaxis2=dict(title='العمليات', overlaying='y', side='right', showgrid=False), hovermode="x unified", legend=dict(orientation="h", y=1.15), margin=dict(l=20, r=20, t=30, b=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_trend, use_container_width=True)

            with col_chart2:
                st.markdown("##### 📅 الإيرادات حسب أيام الأسبوع")
                weekday_stats = behavior_df.groupby('day_name').agg({'total_revenue': 'sum', 'total_customers': 'sum'}).reset_index()
                day_order = ["السبت", "الأحد", "الإثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة"]
                weekday_stats['day_name'] = pd.Categorical(weekday_stats['day_name'], categories=day_order, ordered=True)
                weekday_stats = weekday_stats.sort_values('day_name')
                fig_week = px.bar(weekday_stats, x='day_name', y='total_revenue', color='total_revenue', custom_data=['total_customers'], labels={'day_name': 'اليوم', 'total_revenue': 'الإيراد (ج.م)'}, color_continuous_scale='Greens')
                fig_week.update_traces(hovertemplate="<b>%{x}</b><br>الإيراد: %{y:,.0f} ج.م<br>عدد العمليات: %{customdata[0]:,}<extra></extra>")
                fig_week.update_layout(coloraxis_showscale=False, margin=dict(l=20, r=20, t=20, b=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_week, use_container_width=True)

            col_chart3, col_chart4 = st.columns(2)
            with col_chart3:
                st.markdown("##### 🔥 ساعات الذروة المالية وحركة الزبائن")
                hourly = tx_subset.groupby('hour').agg(total_revenue=('amount_paid', 'sum'), total_customers=('id', 'count')).reset_index()
                hourly['hour_str'] = hourly['hour'].apply(lambda x: f"{x:02d}:00")
                fig_hour = px.bar(hourly, x='hour_str', y='total_revenue', color='total_revenue', custom_data=['total_customers'], labels={'hour_str': 'الساعة', 'total_revenue': 'إجمالي الإيراد (ج.م)'}, color_continuous_scale='Sunset')
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
                        st.rerun()
        with col_l2:
            st.markdown(f"#### 🌴 فرع 9A: **{leave_9a} أيام متبقية**")
            with st.expander("تسجيل إجازة لموظف 9A (-1 يوم)", expanded=False):
                with st.form("leave_9a_form"):
                    note_9a = st.text_input("ملاحظات الإجازة:", value="إجازة اعتيادية")
                    if st.form_submit_button("🌴 تأكيد خصم يوم إجازة (9A)", use_container_width=True):
                        record_leave("9A", note_9a)
                        st.rerun()

        # ----------------- تصدير الملفات عند الطلب فقط (سريع وخفيف) -----------------
        st.markdown("---")
        with st.expander("📥 النسخ الاحتياطي وتصدير البيانات (إكسيل / CSV)", expanded=False):
            st.caption("يتم تجهيز الملفات فور ضغطك على الزر فقط:")
            col_b1, col_b2 = st.columns(2)
            today_date_str = get_egypt_today_str()
            
            with col_b1:
                if st.button("📄 تجهيز وتحميل شيت المبيعات بالكامل", use_container_width=True):
                    with engine.connect() as conn:
                        tx_exp = pd.read_sql_query(text("SELECT t.timestamp, d.date, t.prints_count, t.amount_paid, t.branch FROM transactions t JOIN days d ON t.day_id = d.id ORDER BY t.timestamp DESC"), conn)
                    csv_tx = tx_exp.to_csv(index=False).encode('utf-8-sig')
                    st.download_button("📥 اضغط لبدء تنزيل شيت المبيعات", data=csv_tx, file_name=f"sales_{today_date_str}.csv", mime="text/csv", use_container_width=True)
            
            with col_b2:
                if st.button("💸 تجهيز وتحميل شيت المصروفات بالكامل", use_container_width=True):
                    with engine.connect() as conn:
                        exp_exp = pd.read_sql_query(text("SELECT e.timestamp, d.date, e.branch, e.amount, e.description, e.created_by, e.category FROM expenses e JOIN days d ON e.day_id = d.id ORDER BY e.timestamp DESC"), conn)
                    csv_exp = exp_exp.to_csv(index=False).encode('utf-8-sig')
                    st.download_button("📥 اضغط لبدء تنزيل شيت المصروفات", data=csv_exp, file_name=f"expenses_{today_date_str}.csv", mime="text/csv", use_container_width=True)
