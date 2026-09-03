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

# ----------------- APP CONFIG -----------------
st.set_page_config(page_title="Photobooth Management System", page_icon="📸", layout="wide")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    [data-testid="stSidebar"] {display: none;}
    [data-testid="collapsedControl"] {display: none;}
    
    .event-card {
        background-color: #1a1d24;
        border: 1px solid #2d323f;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 16px;
        direction: rtl;
        text-align: right;
        font-family: inherit;
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
        font-size: 20px;
        font-weight: bold;
        color: #ffffff;
    }
    .badge-heaven {
        background-color: #00CC96;
        color: white;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: bold;
        font-size: 13px;
    }
    .badge-9a {
        background-color: #636EFA;
        color: white;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: bold;
        font-size: 13px;
    }
    .event-meta {
        font-size: 15px;
        color: #b0b4be;
        margin-bottom: 12px;
        line-height: 1.6;
    }
    .event-finance-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
        gap: 10px;
        background-color: #13151b;
        padding: 12px;
        border-radius: 8px;
        margin-bottom: 10px;
    }
    .finance-item {
        display: flex;
        flex-direction: column;
    }
    .finance-label {
        font-size: 13px;
        color: #8a8f9d;
        margin-bottom: 4px;
    }
    .finance-val {
        font-size: 16px;
        font-weight: bold;
        color: #ffffff;
    }
    .finance-val-green {
        font-size: 16px;
        font-weight: bold;
        color: #00CC96;
    }
    .finance-val-red {
        font-size: 16px;
        font-weight: bold;
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
    
    # 1. إنشاء الجداول الأساسية
    with engine.begin() as conn:
        conn.execute(text(f'''
            CREATE TABLE IF NOT EXISTS days (
                {pk_def},
                date TEXT UNIQUE NOT NULL
            )
        '''))
        conn.execute(text(f'''
            CREATE TABLE IF NOT EXISTS transactions (
                {pk_def},
                day_id INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                prints_count INTEGER NOT NULL,
                amount_paid REAL NOT NULL,
                branch TEXT NOT NULL,
                FOREIGN KEY (day_id) REFERENCES days(id)
            )
        '''))
        conn.execute(text(f'''
            CREATE TABLE IF NOT EXISTS inventory (
                {pk_def},
                timestamp TEXT NOT NULL,
                action_type TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                notes TEXT,
                branch TEXT NOT NULL
            )
        '''))
        conn.execute(text(f'''
            CREATE TABLE IF NOT EXISTS audit_logs (
                {pk_def},
                timestamp TEXT NOT NULL,
                branch TEXT NOT NULL,
                action_type TEXT NOT NULL,
                entity_type TEXT DEFAULT 'transaction',
                entity_id INTEGER,
                details TEXT NOT NULL
            )
        '''))
        conn.execute(text(f'''
            CREATE TABLE IF NOT EXISTS employee_leaves (
                {pk_def},
                timestamp TEXT NOT NULL,
                branch TEXT NOT NULL,
                action_type TEXT NOT NULL,
                days_count INTEGER NOT NULL,
                notes TEXT
            )
        '''))
        conn.execute(text(f'''
            CREATE TABLE IF NOT EXISTS expenses (
                {pk_def},
                day_id INTEGER,
                timestamp TEXT NOT NULL,
                date TEXT NOT NULL,
                branch TEXT NOT NULL,
                amount REAL NOT NULL,
                description TEXT NOT NULL,
                created_by TEXT NOT NULL,
                FOREIGN KEY (day_id) REFERENCES days(id)
            )
        '''))
        conn.execute(text(f'''
            CREATE TABLE IF NOT EXISTS events (
                {pk_def},
                created_at TEXT NOT NULL,
                event_date TEXT NOT NULL,
                client_name TEXT NOT NULL,
                location TEXT NOT NULL,
                device TEXT NOT NULL,
                hours INTEGER NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                total_amount REAL NOT NULL,
                deposit_paid REAL NOT NULL,
                remaining_amount REAL NOT NULL,
                status TEXT NOT NULL,
                prints_used INTEGER DEFAULT 0,
                paper_cost REAL DEFAULT 0,
                transport_cost REAL DEFAULT 0,
                worker_cost REAL DEFAULT 0,
                total_expenses REAL DEFAULT 0,
                net_profit REAL DEFAULT 0,
                notes TEXT
            )
        '''))

    # 2. ترقية الأعمدة القديمة (كل خطوة في Transaction منفصلة لضمان عدم حدوث Abort)
    alter_queries = [
        "ALTER TABLE expenses ADD COLUMN day_id INTEGER",
        "ALTER TABLE audit_logs ADD COLUMN entity_type TEXT DEFAULT 'transaction'",
        "ALTER TABLE audit_logs ADD COLUMN entity_id INTEGER",
        "UPDATE audit_logs SET entity_id = transaction_id WHERE entity_id IS NULL AND transaction_id IS NOT NULL"
    ]
    
    for q in alter_queries:
        try:
            with engine.begin() as conn:
                conn.execute(text(q))
        except Exception:
            pass  # لو العمود موجود بالفعل هيتجاهله ويكمل عادي جداً

    # 3. مزامنة التواريخ وربط المصاريف القديمة بـ days بأمان
    try:
        with engine.begin() as conn:
            # إضافة التواريخ الناقصة مع تفادي القيم الفارغة وتكرار الـ Unique
            if IS_POSTGRES:
                conn.execute(text('''
                    INSERT INTO days (date)
                    SELECT DISTINCT e.date 
                    FROM expenses e 
                    WHERE e.date IS NOT NULL AND e.date != ''
                    ON CONFLICT (date) DO NOTHING
                '''))
                conn.execute(text('''
                    UPDATE expenses e
                    SET day_id = d.id
                    FROM days d
                    WHERE e.date = d.date AND e.day_id IS NULL
                '''))
            else:
                conn.execute(text('''
                    INSERT OR IGNORE INTO days (date)
                    SELECT DISTINCT e.date 
                    FROM expenses e 
                    WHERE e.date IS NOT NULL AND e.date != ''
                '''))
                conn.execute(text('''
                    UPDATE expenses
                    SET day_id = (SELECT id FROM days WHERE days.date = expenses.date)
                    WHERE day_id IS NULL
                '''))
    except Exception as e:
        print(f"Warning during sync: {e}")

init_db()


# ----------------- GENERAL HELPERS -----------------
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

# ----------------- LEAVES HELPER FUNCTIONS -----------------
def check_and_add_monthly_allowance():
    current_month_str = get_egypt_now().strftime("%Y-%m")
    with engine.begin() as conn:
        for b in ["Heaven", "9A"]:
            row = conn.execute(
                text("SELECT id FROM employee_leaves WHERE branch = :branch AND action_type = 'monthly_allowance' AND notes LIKE :month_pattern"),
                {"branch": b, "month_pattern": f"%{current_month_str}%"}
            ).fetchone()
            if not row:
                conn.execute(text('''
                    INSERT INTO employee_leaves (timestamp, branch, action_type, days_count, notes)
                    VALUES (:ts, :branch, 'monthly_allowance', 4, :notes)
                '''), {
                    "ts": get_egypt_now_str(),
                    "branch": b,
                    "notes": f"رصيد إجازات شهر {current_month_str}"
                })

def get_leave_balance(branch: str):
    with engine.connect() as conn:
        res = conn.execute(
            text("SELECT COALESCE(SUM(days_count), 0) FROM employee_leaves WHERE branch = :branch"),
            {"branch": branch}
        ).fetchone()
        return res[0] if res else 0

def record_leave(branch: str, notes: str = "إجازة اعتيادية"):
    with engine.begin() as conn:
        conn.execute(text('''
            INSERT INTO employee_leaves (timestamp, branch, action_type, days_count, notes)
            VALUES (:ts, :branch, 'leave_taken', -1, :notes)
        '''), {
            "ts": get_egypt_now_str(),
            "branch": branch,
            "notes": notes
        })

# ----------------- DB HELPER FUNCTIONS -----------------
def get_current_stock(branch: str):
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT COALESCE(SUM(quantity), 0) as total FROM inventory WHERE branch = :branch"), 
            {"branch": branch}
        ).fetchone()
        return result[0] if result else 0

def get_waste_count(branch: str = None):
    with engine.connect() as conn:
        if branch and branch != "الكل":
            result = conn.execute(
                text("SELECT ABS(COALESCE(SUM(quantity), 0)) as total FROM inventory WHERE action_type = 'waste' AND branch = :branch"),
                {"branch": branch}
            ).fetchone()
        else:
            result = conn.execute(
                text("SELECT ABS(COALESCE(SUM(quantity), 0)) as total FROM inventory WHERE action_type = 'waste'")
            ).fetchone()
        return result[0] if result else 0

def add_stock(branch: str, quantity: int, notes: str = ""):
    with engine.begin() as conn:
        conn.execute(text('''
            INSERT INTO inventory (timestamp, action_type, quantity, notes, branch)
            VALUES (:ts, 'restock', :qty, :notes, :branch)
        '''), {
            "ts": get_egypt_now_str(),
            "qty": quantity,
            "notes": notes,
            "branch": branch
        })

def record_waste(branch: str, quantity: int = 1, notes: str = "ورقة تالفة"):
    with engine.begin() as conn:
        conn.execute(text('''
            INSERT INTO inventory (timestamp, action_type, quantity, notes, branch)
            VALUES (:ts, 'waste', :qty, :notes, :branch)
        '''), {
            "ts": get_egypt_now_str(),
            "qty": -quantity,
            "notes": notes,
            "branch": branch
        })

def record_transaction(branch: str, prints_count: int, amount_paid: float):
    now_str = get_egypt_now_str()
    today_str = get_egypt_today_str()
    day_id = get_or_create_day_id(today_str)
    
    with engine.begin() as conn:
        conn.execute(text('''
            INSERT INTO transactions (day_id, timestamp, prints_count, amount_paid, branch)
            VALUES (:day_id, :ts, :prints, :amount, :branch)
        '''), {
            "day_id": day_id,
            "ts": now_str,
            "prints": prints_count,
            "amount": amount_paid,
            "branch": branch
        })
        
        conn.execute(text('''
            INSERT INTO inventory (timestamp, action_type, quantity, notes, branch)
            VALUES (:ts, 'consumption', :qty, 'Transaction consumption', :branch)
        '''), {
            "ts": now_str,
            "qty": -prints_count,
            "branch": branch
        })

def delete_transaction(tx_id: int, branch: str):
    now_str = get_egypt_now_str()
    with engine.begin() as conn:
        tx = conn.execute(text("SELECT * FROM transactions WHERE id = :id AND branch = :branch"), {"id": tx_id, "branch": branch}).mappings().fetchone()
        if tx:
            conn.execute(text('''
                INSERT INTO inventory (timestamp, action_type, quantity, notes, branch)
                VALUES (:ts, 'restock', :qty, :notes, :branch)
            '''), {
                "ts": now_str,
                "qty": tx["prints_count"],
                "notes": f"استرجاع ورق لحذف المعاملة #{tx_id}",
                "branch": branch
            })
            conn.execute(text('''
                INSERT INTO audit_logs (timestamp, branch, action_type, entity_type, entity_id, details)
                VALUES (:ts, :branch, 'حذف مبيعات', 'transaction', :tx_id, :details)
            '''), {
                "ts": now_str,
                "branch": branch,
                "tx_id": tx_id,
                "details": f"تم حذف العملية (الوقت: {tx['timestamp']} | الورق: {tx['prints_count']} | المبلغ: {tx['amount_paid']} ج.م)"
            })
            conn.execute(text("DELETE FROM transactions WHERE id = :id"), {"id": tx_id})
            return True
    return False

def update_transaction(tx_id: int, branch: str, new_prints: int, new_amount: float):
    now_str = get_egypt_now_str()
    with engine.begin() as conn:
        tx = conn.execute(text("SELECT * FROM transactions WHERE id = :id AND branch = :branch"), {"id": tx_id, "branch": branch}).mappings().fetchone()
        if tx:
            diff_prints = new_prints - tx["prints_count"]
            if diff_prints != 0:
                conn.execute(text('''
                    INSERT INTO inventory (timestamp, action_type, quantity, notes, branch)
                    VALUES (:ts, 'consumption', :qty, :notes, :branch)
                '''), {
                    "ts": now_str,
                    "qty": -diff_prints,
                    "notes": f"تسوية فرق ورق لتعديل المعاملة #{tx_id}",
                    "branch": branch
                })
            conn.execute(text('''
                INSERT INTO audit_logs (timestamp, branch, action_type, entity_type, entity_id, details)
                VALUES (:ts, :branch, 'تعديل مبيعات', 'transaction', :tx_id, :details)
            '''), {
                "ts": now_str,
                "branch": branch,
                "tx_id": tx_id,
                "details": f"تعديل من ({tx['prints_count']} ورق - {tx['amount_paid']} ج) إلى ({new_prints} ورق - {new_amount} ج)"
            })
            conn.execute(text('''
                UPDATE transactions 
                SET prints_count = :prints, amount_paid = :amount 
                WHERE id = :id
            '''), {
                "prints": new_prints,
                "amount": new_amount,
                "id": tx_id
            })
            return True
    return False

# ----------------- EXPENSES HELPER FUNCTIONS -----------------
def record_expense(branch: str, amount: float, description: str, created_by: str):
    now_str = get_egypt_now_str()
    today_str = get_egypt_today_str()
    day_id = get_or_create_day_id(today_str)
    with engine.begin() as conn:
        conn.execute(text('''
            INSERT INTO expenses (day_id, timestamp, date, branch, amount, description, created_by)
            VALUES (:day_id, :ts, :date, :branch, :amount, :desc, :user)
        '''), {
            "day_id": day_id,
            "ts": now_str,
            "date": today_str,
            "branch": branch,
            "amount": amount,
            "desc": description,
            "user": created_by
        })

def delete_expense(exp_id: int, branch: str = None):
    now_str = get_egypt_now_str()
    with engine.begin() as conn:
        branch_clause = "AND branch = :branch" if branch and branch != "All" else ""
        params = {"id": exp_id}
        if branch and branch != "All":
            params["branch"] = branch
            
        exp = conn.execute(text(f"SELECT * FROM expenses WHERE id = :id {branch_clause}"), params).mappings().fetchone()
        if exp:
            conn.execute(text('''
                INSERT INTO audit_logs (timestamp, branch, action_type, entity_type, entity_id, details)
                VALUES (:ts, :branch, 'حذف مصروف', 'expense', :exp_id, :details)
            '''), {
                "ts": now_str,
                "branch": exp["branch"],
                "exp_id": exp_id,
                "details": f"تم حذف مصروف #{exp_id} بقيمة {exp['amount']} ج.م (الوصف: {exp['description']})"
            })
            conn.execute(text("DELETE FROM expenses WHERE id = :id"), {"id": exp_id})
            return True
    return False

def update_expense(exp_id: int, new_amount: float, new_desc: str, branch: str = None):
    now_str = get_egypt_now_str()
    with engine.begin() as conn:
        branch_clause = "AND branch = :branch" if branch and branch != "All" else ""
        params = {"id": exp_id}
        if branch and branch != "All":
            params["branch"] = branch
            
        exp = conn.execute(text(f"SELECT * FROM expenses WHERE id = :id {branch_clause}"), params).mappings().fetchone()
        if exp:
            conn.execute(text('''
                INSERT INTO audit_logs (timestamp, branch, action_type, entity_type, entity_id, details)
                VALUES (:ts, :branch, 'تعديل مصروف', 'expense', :exp_id, :details)
            '''), {
                "ts": now_str,
                "branch": exp["branch"],
                "exp_id": exp_id,
                "details": f"تعديل مصروف #{exp_id} من ({exp['amount']} ج - {exp['description']}) إلى ({new_amount} ج - {new_desc})"
            })
            conn.execute(text('''
                UPDATE expenses 
                SET amount = :amount, description = :desc 
                WHERE id = :id
            '''), {
                "amount": new_amount,
                "desc": new_desc,
                "id": exp_id
            })
            return True
    return False

# ----------------- EVENTS HELPER FUNCTIONS -----------------
def create_event(event_date: str, client_name: str, location: str, device: str, hours: int, start_time: str, end_time: str, total_amount: float, deposit_paid: float, notes: str):
    now_str = get_egypt_now_str()
    remaining = total_amount - deposit_paid
    status = "قيد الانتظار"
    with engine.begin() as conn:
        conn.execute(text('''
            INSERT INTO events (created_at, event_date, client_name, location, device, hours, start_time, end_time, total_amount, deposit_paid, remaining_amount, status, notes)
            VALUES (:created_at, :event_date, :client_name, :location, :device, :hours, :start_time, :end_time, :total_amount, :deposit_paid, :remaining_amount, :status, :notes)
        '''), {
            "created_at": now_str,
            "event_date": event_date,
            "client_name": client_name,
            "location": location,
            "device": device,
            "hours": hours,
            "start_time": start_time,
            "end_time": end_time,
            "total_amount": total_amount,
            "deposit_paid": deposit_paid,
            "remaining_amount": remaining,
            "status": status,
            "notes": notes
        })
        if deposit_paid > 0:
            d_id = get_or_create_day_id(event_date)
            conn.execute(text('''
                INSERT INTO transactions (day_id, timestamp, prints_count, amount_paid, branch)
                VALUES (:day_id, :ts, 0, :amount, 'Events')
            '''), {
                "day_id": d_id,
                "ts": now_str,
                "amount": deposit_paid
            })

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
                
            conn.execute(text('''
                INSERT INTO transactions (day_id, timestamp, prints_count, amount_paid, branch)
                VALUES (:day_id, :ts, :prints, :amount, 'Events')
            '''), {
                "day_id": d_id,
                "ts": now_str,
                "prints": prints_count,
                "amount": rem if rem > 0 else 0
            })

            if total_exp > 0:
                desc = f"مصروفات إيفنت #{event_id} ({ev['client_name']}): ورق={paper_cost}ج، مواصلات={transport_cost}ج، موظف={worker_cost}ج"
                conn.execute(text('''
                    INSERT INTO expenses (day_id, timestamp, date, branch, amount, description, created_by)
                    VALUES (:day_id, :ts, :date, 'Events', :amount, :desc, 'تسوية إيفنت')
                '''), {
                    "day_id": d_id,
                    "ts": now_str,
                    "date": event_date,
                    "amount": total_exp,
                    "desc": desc
                })

            conn.execute(text('''
                UPDATE events
                SET deposit_paid = total_amount,
                    remaining_amount = 0,
                    status = 'تم التنفيذ والتسوية',
                    prints_used = :prints,
                    paper_cost = :p_cost,
                    transport_cost = :t_cost,
                    worker_cost = :w_cost,
                    total_expenses = :tot_exp,
                    net_profit = :profit
                WHERE id = :id
            '''), {
                "prints": prints_count,
                "p_cost": paper_cost,
                "t_cost": transport_cost,
                "w_cost": worker_cost,
                "tot_exp": total_exp,
                "profit": profit,
                "id": event_id
            })

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
    st.markdown("<h1 style='text-align: center;'>🔐 تسجيل الدخول للأنظمة</h1>", unsafe_allow_html=True)
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1,2,1])
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

# ================= 1. EMPLOYEE SCREEN =================
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
            border: 2px solid #e0e0e0;
            transition: all 0.2s ease;
            white-space: pre-wrap !important;
        }
        div[data-testid="stButton"] > button:hover {
            border-color: #ff4b4b;
            color: #ff4b4b;
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(255, 75, 75, 0.15);
        }
        div[data-testid="stForm"] button {
            height: 80px !important;
            font-size: 18px !important;
        }
        div[data-testid="stNumberInput"] label {
            font-size: 18px !important;
            font-weight: bold !important;
        }
        </style>
    """, unsafe_allow_html=True)

    st.title(f"📸 فرع {branch} - المبيعات السريعة")
    st.caption("أزرار سريعة لتسجيل المبيعات وتتبع يوم العمل حتى 3:00 فجراً.")
    
    st.subheader("⚡ العمليات السريعة")
    
    if branch == "Heaven":
        btn_col1, btn_col2, btn_col3 = st.columns(3)
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

        with btn_col3:
            if st.button("🗑️ ورقة تالفة\n(خصم 1 ورقة)", use_container_width=True):
                if current_stock < 1:
                    st.error("⚠️ رصيد الورق فارغ بالفعل!")
                else:
                    record_waste(branch, 1, "تالف طباعة سريع")
                    st.warning("⚠️ تم خصم ورقة تالفة من المخزون!")
                    st.rerun()
    else:
        btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(4)
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

        with btn_col4:
            if st.button("🗑️ ورقة تالفة\n(خصم 1 ورقة)", use_container_width=True):
                if current_stock < 1:
                    st.error("⚠️ رصيد الورق فارغ بالفعل!")
                else:
                    record_waste(branch, 1, "تالف طباعة سريع")
                    st.warning("⚠️ تم خصم ورقة تالفة من المخزون!")
                    st.rerun()

    st.markdown("<br><hr><br>", unsafe_allow_html=True)
    col_manual, col_restock, col_exp = st.columns(3)
    
    with col_manual:
        with st.expander("⚙️ إدخال مبيعات يدوي", expanded=False):
            with st.form("manual_form", clear_on_submit=True):
                prints = st.number_input("عدد الورق المطبوع", min_value=1, max_value=50, value=None, step=1, placeholder="أدخل عدد الورق...")
                amount = st.number_input("المبلغ المدفوع", min_value=0.0, value=None, step=10.0, placeholder="أدخل المبلغ...")
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

    with col_restock:
        with st.expander("📦 إضافة ورق للمخزون", expanded=False):
            with st.form("restock_form", clear_on_submit=True):
                restock_qty = st.number_input("عدد الورق المضاف", min_value=1, max_value=5000, value=None, step=50, placeholder="أدخل الكمية...")
                notes = st.text_input("ملاحظات", "")
                restock_btn = st.form_submit_button("➕ تزويد المخزون", use_container_width=True)
                
                if restock_btn:
                    add_stock(branch, restock_qty, notes)
                    st.success("تم التزويد بنجاح!")
                    st.rerun()

    with col_exp:
        with st.expander("💸 تسجيل مصروفات", expanded=False):
            with st.form("employee_expense_form", clear_on_submit=True):
                exp_target = st.selectbox("جهة المصروف:", [branch, "Events"], format_func=lambda x: f"فرع {x}" if x != "Events" else "🎪 إيفنت خارجي (Events)")
                exp_amount = st.number_input("مبلغ المصروف (ج.م)", min_value=1.0, value=None, step=5.0, placeholder="أدخل المبلغ...")
                exp_desc = st.text_input("وصف المصروف", placeholder="مثال: شاي، بنزين، نقل إيفنت...")
                submit_exp = st.form_submit_button("💸 تسجيل المصروف", use_container_width=True)
                if submit_exp:
                    if exp_amount is None or not exp_desc.strip():
                        st.error("⚠️ يرجى إدخال المبلغ ووصف المصروف!")
                    else:
                        record_expense(exp_target, float(exp_amount), exp_desc.strip(), f"موظف {branch}")
                        st.success("تم تسجيل المصروف بنجاح!")
                        st.rerun()

    st.markdown("---")
    st.subheader("📋 عمليات يوم العمل الحالي (اليوم بالكامل)")
    
    today_str = get_egypt_today_str()
    with engine.connect() as conn:
        today_tx = pd.read_sql_query(
            text('''
            SELECT t.id, t.timestamp, t.prints_count, t.amount_paid
            FROM transactions t
            JOIN days d ON t.day_id = d.id
            WHERE d.date = :date AND t.branch = :branch
            ORDER BY t.timestamp DESC
            '''), 
            conn, 
            params={"date": today_str, "branch": branch}
        )
        
        if not today_tx.empty:
            display_user_tx = today_tx.rename(columns={
                'timestamp': 'الوقت',
                'prints_count': 'عدد الورق',
                'amount_paid': 'المبلغ (ج.م)'
            })
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
                        edit_btn = st.form_submit_button("حفظ التعديلات", use_container_width=True)
                        if edit_btn:
                            if update_transaction(selected_id, branch, new_p, new_a):
                                st.success("تم تعديل العملية وضبط المخزون وسجل المراقبة بنجاح!")
                                st.rerun()

            with col_act2:
                with st.expander("🗑️ حذف العملية المحددة", expanded=False):
                    st.warning(f"هل أنت متأكد من حذف العملية #{selected_id}؟ سيتم استرجاع الورق للمخزون وتسجيل الحذف.")
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
            text('''
            SELECT e.id, e.timestamp, e.amount, e.description 
            FROM expenses e
            JOIN days d ON e.day_id = d.id
            WHERE d.date = :date AND e.branch = :branch 
            ORDER BY e.timestamp DESC
            '''),
            conn,
            params={"date": today_str, "branch": branch}
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

# ================= 2. ADMIN DASHBOARD =================
elif role == "admin":
    check_and_add_monthly_allowance()

    with engine.connect() as conn:
        all_tx_raw = pd.read_sql_query(text('''
            SELECT t.*, d.date 
            FROM transactions t
            JOIN days d ON t.day_id = d.id
            ORDER BY t.timestamp ASC
        '''), conn)
        
        all_exp_raw = pd.read_sql_query(text('''
            SELECT e.*, d.date as operational_date 
            FROM expenses e
            JOIN days d ON e.day_id = d.id
            ORDER BY e.timestamp ASC
        '''), conn)
        
        all_events_raw = pd.read_sql_query(text("SELECT * FROM events ORDER BY event_date ASC, start_time ASC"), conn)

    for col_name in ['total_amount', 'total_expenses', 'net_profit', 'remaining_amount', 'deposit_paid']:
        if col_name not in all_events_raw.columns:
            all_events_raw[col_name] = 0.0

    all_dates = []
    if not all_tx_raw.empty:
        all_dates.extend(pd.to_datetime(all_tx_raw['date']).dt.date.tolist())
    if not all_exp_raw.empty:
        all_dates.extend(pd.to_datetime(all_exp_raw['operational_date']).dt.date.tolist())

    if all_dates:
        min_date = min(all_dates)
        max_date = max(all_dates)
    else:
        min_date = date.today()
        max_date = date.today()

    bar_c1, bar_c2, bar_c3, bar_c4, bar_c5 = st.columns([3, 2, 2, 2, 1])
    with bar_c1:
        st.markdown("## 👑 إدارة المنظومة")
    with bar_c2:
        sec_choice = st.radio("القسم:", ["📊 الفروع والمبيعات", "🎪 حجوزات الإيفنتات"], horizontal=True)
    with bar_c3:
        selected_branch = st.selectbox("🏢 نطاق التحليل:", ["الكل", "Heaven", "9A", "Events"])
    with bar_c4:
        date_range = st.date_input("📅 الفترة:", value=(min_date, max_date), min_value=min_date, max_value=max_date)
    with bar_c5:
        st.markdown("<br>", unsafe_allow_html=True)
        st.button("🚪 خروج", on_click=logout, use_container_width=True)
    st.markdown("---")

    # ================= 2.A قسم حجوزات الإيفنتات =================
    if sec_choice == "🎪 حجوزات الإيفنتات":
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
                    ev_client = st.text_input("اسم العميل / المناسبة:", placeholder="")
                    ev_loc = st.text_input("مكان الإيفنت / القاعة:", placeholder="")
                    ev_dev = st.selectbox("الجهاز المخصص:", ["Heaven", "9A"])
                with ef2:
                    ev_date = st.date_input("تاريخ الإيفنت:", value=date.today())
                    ev_hours = st.number_input("عدد الساعات:", min_value=1, max_value=24, value=3, step=1)
                    ev_start = st.time_input("ساعة البداية:", value=time(19, 0))
                with ef3:
                    ev_total = st.number_input("إجمالي قيمة الحجز (ج.م):", min_value=100.0, value=2000.0, step=500.0)
                    ev_deposit = st.number_input("العربون المدفوع (ج.م):", min_value=0.0, value=1000.0, step=500.0)
                    ev_notes = st.text_input("ملاحظات إضافية:", placeholder="خلفية خاصة، برواز مخصص...")
                
                start_dt = datetime.combine(ev_date, ev_start)
                end_dt = start_dt + timedelta(hours=int(ev_hours))
                ev_start_str = format_arabic_time(start_dt.strftime("%I:%M %p"))
                ev_end_str = format_arabic_time(end_dt.strftime("%I:%M %p"))
                
                st.caption(f"🕒 التوقيت: من {ev_start_str} إلى {ev_end_str} | ⏳ المتبقي: {ev_total - ev_deposit:,.0f} ج.م")
                
                if st.form_submit_button("💾 تأكيد وحفظ الحجز", use_container_width=True):
                    if not ev_client.strip() or not ev_loc.strip():
                        st.error("⚠️ يرجى إدخال اسم العميل ومكان الإيفنت!")
                    elif ev_deposit > ev_total:
                        st.error("⚠️ العربون أكبر من إجمالي المبلغ!")
                    else:
                        create_event(
                            str(ev_date), ev_client.strip(), ev_loc.strip(), ev_dev, 
                            int(ev_hours), ev_start_str, ev_end_str, float(ev_total), 
                            float(ev_deposit), ev_notes.strip()
                        )
                        st.success("✅ تم تسجيل الحجز بنجاح!")
                        st.rerun()

        st.subheader("📌 بطاقات الإيفنتات والموقف المالي")
        if not all_events_raw.empty:
            for _, ev in all_events_raw.iterrows():
                badge_class = "badge-heaven" if ev['device'] == "Heaven" else "badge-9a"
                is_settled = ev['status'] == 'تم التنفيذ والتسوية'
                start_t_ar = format_arabic_time(ev['start_time'])
                end_t_ar = format_arabic_time(ev['end_time'])
                
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
                        📅 <b>تاريخ الإيفنت:</b> {ev['event_date']} &nbsp;&nbsp;|&nbsp;&nbsp; 
                        ⏰ <b>التوقيت:</b> من {start_t_ar} إلى {end_t_ar} ({ev['hours']} ساعات)
                    </div>
                    <div class="event-finance-grid">
                        <div class="finance-item">
                            <div class="finance-label">قيمة الحجز</div>
                            <div class="finance-val">{ev.get('total_amount', 0):,.0f} ج.م</div>
                        </div>
                        <div class="finance-item">
                            <div class="finance-label">المدفوع</div>
                            <div class="finance-val">{ev.get('deposit_paid', 0):,.0f} ج.م</div>
                        </div>
                        <div class="finance-item">
                            <div class="finance-label">المتبقي</div>
                            <div class="{rem_class}">{rem_text}</div>
                        </div>
                        <div class="finance-item">
                            <div class="finance-label">إجمالي المصروفات</div>
                            <div class="finance-val">{ev.get('total_expenses', 0):,.0f} ج.م</div>
                        </div>
                        <div class="finance-item">
                            <div class="finance-label">صافي الربح</div>
                            <div class="finance-val-green">{ev.get('net_profit', 0):,.0f} ج.م</div>
                        </div>
                        <div class="finance-item">
                            <div class="finance-label">حالة الحجز</div>
                            <div class="finance-val" style="font-size:14px;">{ev.get('status', '-')}</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                if ev.get("notes"):
                    st.caption(f"📝 ملاحظات: {ev['notes']}")

                with st.expander(f"🔍 تفاصيل المصروفات والتسوية لإيفنت #{ev['id']} ({ev['client_name']})", expanded=False):
                    if is_settled:
                        sc1, sc2, sc3, sc4 = st.columns(4)
                        sc1.info(f"🖨️ الورق: {ev.get('prints_used', 0)} ورقة ({ev.get('paper_cost', 0):,.0f} ج)")
                        sc2.info(f"🚗 مواصلات: {ev.get('transport_cost', 0):,.0f} ج")
                        sc3.info(f"👨‍💼 أجر الموظف: {ev.get('worker_cost', 0):,.0f} ج")
                        sc4.success(f"📈 صافي الربح: {ev.get('net_profit', 0):,.0f} ج.م")
                    else:
                        st.markdown("##### 📝 إتمام وتسوية مصاريف الإيفنت بعد التنفيذ")
                        st.caption("أدخل بيانات المصروفات الفعلية لحساب تكلفة الورق (الورقة بـ 3 ج) والمواصلات والموظف وتوريد الباقي:")
                        with st.form(f"settle_form_{ev['id']}"):
                            c_p, c_t, c_w = st.columns(3)
                            with c_p:
                                in_prints = st.number_input("عدد الورق المستهلك في الإيفنت:", min_value=0, max_value=2000, value=50, step=10, key=f"p_{ev['id']}")
                                st.caption(f"تكلفة الورق المحسوبة (×3 ج): **{in_prints * 3:,.0f} ج.م**")
                            with c_t:
                                in_trans = st.number_input("مصاريف المواصلات / النقل (ج.م):", min_value=0.0, value=100.0, step=50.0, key=f"t_{ev['id']}")
                            with c_w:
                                in_worker = st.number_input("فلوس الموظف المسؤول (ج.م):", min_value=0.0, value=100.0, step=10.0, key=f"w_{ev['id']}")
                            
                            sub_settle = st.form_submit_button("✅ اعتماد تنفيذ الإيفنت وحساب صافي الربح وتوريد المبلغ", use_container_width=True)
                            if sub_settle:
                                complete_event_settlement(ev['id'], int(in_prints), float(in_trans), float(in_worker))
                                st.success("تم تسوية الإيفنت وحساب صافي الربح بنجاح!")
                                st.rerun()

                    if st.button(f"🗑️ حذف الإيفنت #{ev['id']}", key=f"del_ev_btn_{ev['id']}"):
                        delete_event(ev['id'])
                        st.warning("تم حذف الإيفنت.")
                        st.rerun()

            st.markdown("---")
            st.subheader("📥 تصدير سجل الإيفنتات بالكامل")
            events_export = all_events_raw.rename(columns={
                'id': 'رقم الحجز',
                'event_date': 'تاريخ الإيفنت',
                'client_name': 'العميل',
                'location': 'المكان',
                'device': 'الجهاز',
                'hours': 'الساعات',
                'start_time': 'البداية',
                'end_time': 'النهاية',
                'total_amount': 'إجمالي التعاقد (ج.م)',
                'deposit_paid': 'المبلغ المدفوع (ج.م)',
                'remaining_amount': 'المتبقي (ج.م)',
                'prints_used': 'الورق المستهلك',
                'paper_cost': 'تكلفة الورق (ج.م)',
                'transport_cost': 'المواصلات (ج.م)',
                'worker_cost': 'أجر الموظف (ج.م)',
                'total_expenses': 'إجمالي المصروفات (ج.م)',
                'net_profit': 'صافي الربح (ج.م)',
                'status': 'الحالة',
                'notes': 'ملاحظات'
            })
            csv_ev = events_export.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                "📥 تحميل شيت إكسيل الإيفنتات والمصاريف والأرباح (CSV)",
                data=csv_ev,
                file_name=f"events_report_{get_egypt_today_str()}.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.info("لا توجد حجوزات إيفنتات مسجلة حتى الآن.")

    # ================= 2.B قسم مبيعات وتشغيل الفروع =================
    else:
        if len(date_range) == 2:
            start_dt, end_dt = date_range
            mask_tx_date = (pd.to_datetime(all_tx_raw['date']).dt.date >= start_dt) & (pd.to_datetime(all_tx_raw['date']).dt.date <= end_dt) if not all_tx_raw.empty else pd.Series(dtype=bool)
            filtered_tx = all_tx_raw.loc[mask_tx_date].copy() if not all_tx_raw.empty else pd.DataFrame()
            
            mask_exp_date = (pd.to_datetime(all_exp_raw['operational_date']).dt.date >= start_dt) & (pd.to_datetime(all_exp_raw['operational_date']).dt.date <= end_dt) if not all_exp_raw.empty else pd.Series(dtype=bool)
            filtered_exp = all_exp_raw.loc[mask_exp_date].copy() if not all_exp_raw.empty else pd.DataFrame()
        else:
            filtered_tx = all_tx_raw.copy()
            filtered_exp = all_exp_raw.copy()

        if selected_branch == "الكل":
            tx_subset = filtered_tx
            exp_subset = filtered_exp
            total_rev_all = tx_subset['amount_paid'].sum() if not tx_subset.empty else 0
            total_prints_all = tx_subset['prints_count'].sum() if not tx_subset.empty else 0
            total_cust_all = len(tx_subset)
            total_exp_all = exp_subset['amount'].sum() if not exp_subset.empty else 0
        elif selected_branch == "Events":
            tx_subset = filtered_tx[filtered_tx['branch'] == "Events"] if not filtered_tx.empty else pd.DataFrame()
            exp_subset = filtered_exp[filtered_exp['branch'] == "Events"] if not filtered_exp.empty else pd.DataFrame()
            total_rev_all = tx_subset['amount_paid'].sum() if not tx_subset.empty else 0
            total_prints_all = tx_subset['prints_count'].sum() if not tx_subset.empty else 0
            total_cust_all = len(tx_subset)
            total_exp_all = exp_subset['amount'].sum() if not exp_subset.empty else 0
        else:
            tx_subset = filtered_tx[filtered_tx['branch'] == selected_branch] if not filtered_tx.empty else pd.DataFrame()
            total_rev_all = tx_subset['amount_paid'].sum() if not tx_subset.empty else 0
            total_prints_all = tx_subset['prints_count'].sum() if not tx_subset.empty else 0
            total_cust_all = len(tx_subset)
            
            if not filtered_exp.empty:
                direct_exp_df = filtered_exp[filtered_exp['branch'] == selected_branch]
                general_exp_df = filtered_exp[filtered_exp['branch'] == 'General']
                exp_subset = filtered_exp[(filtered_exp['branch'] == selected_branch) | (filtered_exp['branch'] == 'General')].copy()
                total_exp_all = direct_exp_df['amount'].sum() + (general_exp_df['amount'].sum() / 2.0)
            else:
                exp_subset = pd.DataFrame()
                total_exp_all = 0.0

        net_profit = total_rev_all - total_exp_all

        if selected_branch in ["الكل", "Events"]:
            stock_heaven = get_current_stock("Heaven")
            stock_9a = get_current_stock("9A")
            waste_heaven = get_waste_count("Heaven")
            waste_9a = get_waste_count("9A")
            stock_display = f"Heaven: {stock_heaven} | 9A: {stock_9a}"
            waste_display = f"Heaven: {waste_heaven} | 9A: {waste_9a}"
        else:
            stock_display = f"{get_current_stock(selected_branch)} ورقة"
            waste_display = f"{get_waste_count(selected_branch)} ورقة"

        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("💰 إجمالي الإيرادات", f"{total_rev_all:,.0f} ج.م")
        kpi2.metric("💸 إجمالي المصروفات", f"{total_exp_all:,.0f} ج.م", delta=f"-{total_exp_all:,.0f}", delta_color="normal")
        kpi3.metric("📈 صافي الربح", f"{net_profit:,.0f} ج.م", delta=f"{net_profit:,.0f}", delta_color="normal")

        kpi4, kpi5, kpi6 = st.columns(3)
        kpi4.metric("👥 إجمالي العمليات / الزبائن", f"{total_cust_all:,}")
        kpi5.metric("🖨️ الورق المطبوع", f"{total_prints_all:,} ورقة")
        kpi6.metric("🗑️ إجمالي التالف", waste_display)

        st.metric("📦 المخزون المتبقي حالياً", stock_display)
        st.markdown("---")

        with st.expander("💸 تسجيل مصروفات جديدة بواسطة الأدمن", expanded=False):
            with st.form("admin_exp_form", clear_on_submit=True):
                c_a1, c_a2, c_a3 = st.columns(3)
                with c_a1:
                    ad_branch = st.selectbox(
                        "جهة المصروف:", 
                        ["General", "Heaven", "9A", "Events"], 
                        format_func=lambda x: "مصروف بيزنس عام (يوزع على الفرعين)" if x == "General" else ("🎪 إيفنت خارجي (Events)" if x == "Events" else f"فرع {x}")
                    )
                with c_a2:
                    ad_amount = st.number_input("المبلغ (ج.م):", min_value=1.0, value=None, step=50.0, placeholder="أدخل المبلغ...")
                with c_a3:
                    ad_desc = st.text_input("وصف المصروف:", placeholder="مثال: شراء ورق، بنزين إيفنت، صيانة...")
                
                if st.form_submit_button("تسجيل المصروف للأدمن", use_container_width=True):
                    if ad_amount is None or not ad_desc.strip():
                        st.error("⚠️ يرجى إدخال المبلغ والوصف أولاً!")
                    else:
                        record_expense(ad_branch, float(ad_amount), ad_desc.strip(), "المدير")
                        st.success("تم تسجيل المصروف بنجاح!")
                        st.rerun()

        st.markdown("---")

        today_b_str = get_egypt_today_str()
        st.subheader(f"⚡ مبيعات ومصروفات يوم العمل الحالي ({selected_branch}) - {today_b_str}")
        
        st.markdown("##### 🛒 مبيعات اليوم الحالي")
        with engine.connect() as conn:
            admin_today_branch_filter = ""
            admin_today_params = {"date": today_b_str}
            if selected_branch != "الكل":
                admin_today_branch_filter = "AND t.branch = :branch"
                admin_today_params["branch"] = selected_branch

            today_admin_tx = pd.read_sql_query(
                text(f'''
                SELECT t.timestamp, t.branch, t.prints_count, t.amount_paid
                FROM transactions t
                JOIN days d ON t.day_id = d.id
                WHERE d.date = :date {admin_today_branch_filter}
                ORDER BY t.timestamp DESC
                '''),
                conn,
                params=admin_today_params
            )

        if not today_admin_tx.empty:
            display_admin_today = today_admin_tx.rename(columns={
                'timestamp': 'الوقت',
                'branch': 'الجهة / الفرع',
                'prints_count': 'عدد الورق',
                'amount_paid': 'المبلغ (ج.م)'
            })
            st.dataframe(display_admin_today, use_container_width=True, hide_index=True)
        else:
            st.info("لا توجد مبيعات مسجلة اليوم حتى الآن.")

        st.markdown("##### 💸 مصروفات اليوم الحالي")
        with engine.connect() as conn:
            ad_exp_f = ""
            ad_exp_p = {"date": today_b_str}
            if selected_branch != "الكل":
                ad_exp_f = "AND (e.branch = :branch OR e.branch = 'General')"
                ad_exp_p["branch"] = selected_branch

            today_admin_exp = pd.read_sql_query(
                text(f'''
                SELECT e.timestamp, e.branch, e.amount, e.description, e.created_by 
                FROM expenses e
                JOIN days d ON e.day_id = d.id
                WHERE d.date = :date {ad_exp_f} 
                ORDER BY e.timestamp DESC
                '''),
                conn,
                params=ad_exp_p
            )
        if not today_admin_exp.empty:
            disp_ad_exp = today_admin_exp.rename(columns={
                'timestamp': 'الوقت',
                'branch': 'الجهة / الفرع',
                'amount': 'المبلغ (ج.م)',
                'description': 'الوصف',
                'created_by': 'بواسطة'
            })
            st.dataframe(disp_ad_exp, use_container_width=True, hide_index=True)
        else:
            st.info("لا توجد مصروفات مسجلة اليوم حتى الآن.")

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
            peak_hours = peak_hours.sort_values(['date', 'id'], ascending=[True, False])
            peak_hours = peak_hours.drop_duplicates(subset=['date'])
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
        else:
            st.info("لا توجد مصروفات مسجلة خلال الفترة المحددة.")

        st.markdown("---")

        if not tx_subset.empty:
            col_chart1, col_chart2 = st.columns(2)
            with col_chart1:
                st.subheader("📉 الإيرادات والعمليات خلال الفترة")
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=days_df['date'], y=days_df['total_revenue'],
                    mode='lines+markers', name='الإيراد',
                    line=dict(color='#00CC96', width=3)
                ))
                fig.add_trace(go.Bar(
                    x=days_df['date'], y=days_df['total_customers'],
                    name='عدد العمليات', yaxis='y2',
                    marker_color='rgba(99, 110, 250, 0.5)'
                ))
                fig.update_layout(
                    yaxis=dict(title='الإيراد (ج.م)'),
                    yaxis2=dict(title='العمليات', overlaying='y', side='right', showgrid=False),
                    hovermode="x unified",
                    legend=dict(orientation="h", y=1.1)
                )
                st.plotly_chart(fig, use_container_width=True)
                
            with col_chart2:
                st.subheader("📅 الإيرادات حسب أيام الأسبوع")
                weekday_stats = behavior_df.groupby('day_name').agg({
                    'total_revenue': 'sum',
                    'total_customers': 'sum'
                }).reset_index()
                day_order = ["السبت", "الأحد", "الإثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة"]
                weekday_stats['day_name'] = pd.Categorical(weekday_stats['day_name'], categories=day_order, ordered=True)
                weekday_stats = weekday_stats.sort_values('day_name')
                
                fig_week = px.bar(
                    weekday_stats, 
                    x='day_name', 
                    y='total_revenue',
                    custom_data=['total_customers'],
                    labels={'day_name': 'اليوم', 'total_revenue': 'الإيراد (ج.م)'},
                    color='total_revenue', 
                    color_continuous_scale='Greens'
                )
                fig_week.update_traces(
                    hovertemplate="<b>%{x}</b><br>الإيراد: %{y:,.0f} ج.م<br>عدد العمليات: %{customdata[0]:,}<extra></extra>"
                )
                st.plotly_chart(fig_week, use_container_width=True)
            
            st.subheader("🔥 ساعات الذروة المالية (الإيراد والعمليات)")
            hourly = tx_subset.groupby('hour').agg(
                total_revenue=('amount_paid', 'sum'),
                total_customers=('id', 'count')
            ).reset_index()
            hourly['hour_str'] = hourly['hour'].apply(lambda x: f"{x}:00")
            
            fig_hour = px.bar(
                hourly, 
                x='hour_str', 
                y='total_revenue', 
                color='total_revenue',
                custom_data=['total_customers'],
                labels={'hour_str': 'الساعة', 'total_revenue': 'إجمالي الإيراد (ج.م)'}, 
                color_continuous_scale='Sunset'
            )
            fig_hour.update_traces(
                hovertemplate="<b>الساعة: %{x}</b><br>إجمالي الإيراد: %{y:,.0f} ج.م<br>عدد العمليات: %{customdata[0]:,}<extra></extra>"
            )
            st.plotly_chart(fig_hour, use_container_width=True)

        st.markdown("---")
        st.subheader("🕵️ سجل المراقبة والتعديلات (Audit Logs)")
        with engine.connect() as conn:
            audit_filter = ""
            audit_params = {}
            if selected_branch != "الكل":
                audit_filter = "WHERE branch = :branch"
                audit_params = {"branch": selected_branch}
                
            try:
                audit_df = pd.read_sql_query(
                    text(f"SELECT timestamp, branch, action_type, entity_type, entity_id, details FROM audit_logs {audit_filter} ORDER BY timestamp DESC LIMIT 50"),
                    conn,
                    params=audit_params
                )
                if not audit_df.empty:
                    audit_display = audit_df.rename(columns={
                        'timestamp': 'الوقت',
                        'branch': 'الفرع',
                        'action_type': 'نوع الإجراء',
                        'entity_type': 'نوع الكيان',
                        'entity_id': 'رقم المعاملة/المصروف',
                        'details': 'تفاصيل الإجراء'
                    })
                    st.dataframe(audit_display, use_container_width=True, hide_index=True)
                else:
                    st.info("سجل المراقبة نظيف، لا توجد أي عمليات حذف أو تعديل حتى الآن.")
            except Exception:
                st.info("سجل المراقبة نظيف، لا توجد أي عمليات حذف أو تعديل حتى الآن.")

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
                leaves_df = pd.read_sql_query(
                    text("SELECT timestamp, branch, action_type, days_count, notes FROM employee_leaves ORDER BY timestamp DESC LIMIT 50"),
                    conn
                )
                if not leaves_df.empty:
                    display_leaves = leaves_df.rename(columns={
                        'timestamp': 'الوقت',
                        'branch': 'الفرع',
                        'action_type': 'نوع الحركة',
                        'days_count': 'الأيام',
                        'notes': 'الملاحظات'
                    })
                    st.dataframe(display_leaves, use_container_width=True, hide_index=True)
                else:
                    st.info("لا توجد حركات إجازات مسجلة بعد.")

        st.markdown("---")
        st.subheader("📥 النسخ الاحتياطي وتصدير البيانات (Backup & Exports)")
        
        with engine.connect() as conn:
            all_backup_tx = pd.read_sql_query(text('''
                SELECT t.timestamp, d.date, t.prints_count, t.amount_paid, t.branch
                FROM transactions t
                JOIN days d ON t.day_id = d.id
                ORDER BY t.timestamp DESC
            '''), conn)
            
            all_backup_exp = pd.read_sql_query(text('''
                SELECT e.timestamp, d.date, e.branch, e.amount, e.description, e.created_by
                FROM expenses e
                JOIN days d ON e.day_id = d.id
                ORDER BY e.timestamp DESC
            '''), conn)
            
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
                'date': 'التاريخ',
                'day_name': 'اليوم',
                'branch': 'الجهة / الفرع',
                'total_customers': 'عدد العمليات',
                'total_prints': 'إجمالي الورق',
                'total_revenue': 'إجمالي الإيراد (ج.م)'
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
                'timestamp': 'الوقت',
                'date': 'تاريخ يوم العمل',
                'prints_count': 'عدد الورق',
                'amount_paid': 'المبلغ (ج.م)',
                'branch': 'الجهة / الفرع'
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
                'timestamp': 'الوقت',
                'date': 'تاريخ يوم العمل',
                'branch': 'الجهة / الفرع',
                'amount': 'المبلغ (ج.م)',
                'description': 'الوصف',
                'created_by': 'بواسطة'
            })
            csv_exp = all_backup_exp_display.to_csv(index=False).encode('utf-8-sig')
            col_b4.download_button("📥 تحميل كل المصروفات", data=csv_exp, file_name=f"all_expenses_{today_date_str}.csv", mime="text/csv", use_container_width=True)

