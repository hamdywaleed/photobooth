import streamlit as st
import pandas as pd
import numpy as np
import random
from datetime import datetime, date, timezone, timedelta
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine, text

# ----------------- EGYPT TIMEZONE SETUP (UTC+3) -----------------
EGYPT_TZ = timezone(timedelta(hours=3))

def get_egypt_now():
    return datetime.now(EGYPT_TZ)[span_5](start_span)[span_5](end_span)

def get_egypt_now_str():
    return get_egypt_now().strftime("%Y-%m-%d %H:%M:%S")[span_6](start_span)[span_6](end_span)

def get_egypt_today_str():
    # احتساب يوم العمل التشغيلي: يطرح 4 ساعات لضم ساعات الفجر (حتى 3:59 ص) لليوم السابق
    egypt_now = get_egypt_now()[span_7](start_span)[span_7](end_span)
    business_now = egypt_now - timedelta(hours=4)[span_8](start_span)[span_8](end_span)
    return business_now.strftime("%Y-%m-%d")[span_9](start_span)[span_9](end_span)

# ----------------- APP CONFIG -----------------
st.set_page_config(page_title="Photobooth Management System", page_icon="📸", layout="wide")[span_10](start_span)[span_10](end_span)

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)[span_11](start_span)[span_11](end_span)

# ----------------- DB SETUP -----------------
try:
    if "DATABASE_URL" in st.secrets:[span_12](start_span)[span_12](end_span)
        DB_URL = st.secrets["DATABASE_URL"][span_13](start_span)[span_13](end_span)
        IS_POSTGRES = True[span_14](start_span)[span_14](end_span)
    else:
        DB_URL = "sqlite:///photobooth.db[span_15](start_span)"[span_15](end_span)
        IS_POSTGRES = False[span_16](start_span)[span_16](end_span)
except Exception:
    DB_URL = "sqlite:///photobooth.db[span_17](start_span)"[span_17](end_span)
    IS_POSTGRES = False[span_18](start_span)[span_18](end_span)

engine = create_engine(DB_URL, pool_pre_ping=True)[span_19](start_span)[span_19](end_span)

def init_db():
    with engine.begin() as conn:[span_20](start_span)[span_20](end_span)
        if IS_POSTGRES:[span_21](start_span)[span_21](end_span)
            days_id_def = "id SERIAL PRIMARY KEY[span_22](start_span)"[span_22](end_span)
            tx_id_def = "id SERIAL PRIMARY KEY[span_23](start_span)"[span_23](end_span)
            inv_id_def = "id SERIAL PRIMARY KEY[span_24](start_span)"[span_24](end_span)
            audit_id_def = "id SERIAL PRIMARY KEY[span_25](start_span)"[span_25](end_span)
            leaves_id_def = "id SERIAL PRIMARY KEY[span_26](start_span)"[span_26](end_span)
            exp_id_def = "id SERIAL PRIMARY KEY"
        else:
            days_id_def = "id INTEGER PRIMARY KEY AUTOINCREMENT[span_27](start_span)"[span_27](end_span)
            tx_id_def = "id INTEGER PRIMARY KEY AUTOINCREMENT[span_28](start_span)"[span_28](end_span)
            inv_id_def = "id INTEGER PRIMARY KEY AUTOINCREMENT[span_29](start_span)"[span_29](end_span)
            audit_id_def = "id INTEGER PRIMARY KEY AUTOINCREMENT[span_30](start_span)"[span_30](end_span)
            leaves_id_def = "id INTEGER PRIMARY KEY AUTOINCREMENT[span_31](start_span)"[span_31](end_span)
            exp_id_def = "id INTEGER PRIMARY KEY AUTOINCREMENT"
            
        conn.execute(text(f'''
            CREATE TABLE IF NOT EXISTS days (
                {days_id_def},
                date TEXT UNIQUE NOT NULL
            )
        '''))[span_32](start_span)[span_32](end_span)
        conn.execute(text(f'''
            CREATE TABLE IF NOT EXISTS transactions (
                {tx_id_def},
                day_id INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                prints_count INTEGER NOT NULL,
                amount_paid REAL NOT NULL,
                branch TEXT NOT NULL,
                FOREIGN KEY (day_id) REFERENCES days(id)
            )
        '''))[span_33](start_span)[span_33](end_span)
        conn.execute(text(f'''
            CREATE TABLE IF NOT EXISTS inventory (
                {inv_id_def},
                timestamp TEXT NOT NULL,
                action_type TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                notes TEXT,
                branch TEXT NOT NULL
            )
        '''))[span_34](start_span)[span_34](end_span)
        conn.execute(text(f'''
            CREATE TABLE IF NOT EXISTS audit_logs (
                {audit_id_def},
                timestamp TEXT NOT NULL,
                branch TEXT NOT NULL,
                action_type TEXT NOT NULL,
                transaction_id INTEGER,
                details TEXT NOT NULL
            )
        '''))[span_35](start_span)[span_35](end_span)
        conn.execute(text(f'''
            CREATE TABLE IF NOT EXISTS employee_leaves (
                {leaves_id_def},
                timestamp TEXT NOT NULL,
                branch TEXT NOT NULL,
                action_type TEXT NOT NULL,
                days_count INTEGER NOT NULL,
                notes TEXT
            )
        '''))[span_36](start_span)[span_36](end_span)
        conn.execute(text(f'''
            CREATE TABLE IF NOT EXISTS expenses (
                {exp_id_def},
                timestamp TEXT NOT NULL,
                date TEXT NOT NULL,
                branch TEXT NOT NULL,
                amount REAL NOT NULL,
                description TEXT NOT NULL,
                created_by TEXT NOT NULL
            )
        '''))

init_db()[span_37](start_span)[span_37](end_span)

# ----------------- LEAVES HELPER FUNCTIONS -----------------
def check_and_add_monthly_allowance():
    current_month_str = get_egypt_now().strftime("%Y-%m")[span_38](start_span)[span_38](end_span)
    with engine.begin() as conn:[span_39](start_span)[span_39](end_span)
        for b in ["Heaven", "9A"]:[span_40](start_span)[span_40](end_span)
            row = conn.execute(
                text("SELECT id FROM employee_leaves WHERE branch = :branch AND action_type = 'monthly_allowance' AND notes LIKE :month_pattern"),
                {"branch": b, "month_pattern": f"%{current_month_str}%"}
            ).fetchone()[span_41](start_span)[span_41](end_span)
            if not row:[span_42](start_span)[span_42](end_span)
                conn.execute(text('''
                    INSERT INTO employee_leaves (timestamp, branch, action_type, days_count, notes)
                    VALUES (:ts, :branch, 'monthly_allowance', 4, :notes)
                '''), {
                    "ts": get_egypt_now_str(),
                    "branch": b,
                    "notes": f"رصيد إجازات شهر {current_month_str}"
                })[span_43](start_span)[span_43](end_span)

def get_leave_balance(branch: str):
    with engine.connect() as conn:[span_44](start_span)[span_44](end_span)
        res = conn.execute(
            text("SELECT COALESCE(SUM(days_count), 0) FROM employee_leaves WHERE branch = :branch"),
            {"branch": branch}
        ).fetchone()[span_45](start_span)[span_45](end_span)
        return res[0] if res else 0[span_46](start_span)[span_46](end_span)

def record_leave(branch: str, notes: str = "إجازة اعتيادية"):
    with engine.begin() as conn:[span_47](start_span)[span_47](end_span)
        conn.execute(text('''
            INSERT INTO employee_leaves (timestamp, branch, action_type, days_count, notes)
            VALUES (:ts, :branch, 'leave_taken', -1, :notes)
        '''), {
            "ts": get_egypt_now_str(),
            "branch": branch,
            "notes": notes
        })[span_48](start_span)[span_48](end_span)

# ----------------- DB HELPER FUNCTIONS -----------------
def get_current_stock(branch: str):
    with engine.connect() as conn:[span_49](start_span)[span_49](end_span)
        result = conn.execute(
            text("SELECT COALESCE(SUM(quantity), 0) as total FROM inventory WHERE branch = :branch"), 
            {"branch": branch}
        ).fetchone()[span_50](start_span)[span_50](end_span)
        return result[0] if result else 0[span_51](start_span)[span_51](end_span)

def get_waste_count(branch: str = None):
    with engine.connect() as conn:[span_52](start_span)[span_52](end_span)
        if branch and branch != "الكل":[span_53](start_span)[span_53](end_span)
            result = conn.execute(
                text("SELECT ABS(COALESCE(SUM(quantity), 0)) as total FROM inventory WHERE action_type = 'waste' AND branch = :branch"),
                {"branch": branch}
            ).fetchone()[span_54](start_span)[span_54](end_span)
        else:
            result = conn.execute(
                text("SELECT ABS(COALESCE(SUM(quantity), 0)) as total FROM inventory WHERE action_type = 'waste'")
            ).fetchone()[span_55](start_span)[span_55](end_span)
        return result[0] if result else 0[span_56](start_span)[span_56](end_span)

def add_stock(branch: str, quantity: int, notes: str = ""):
    with engine.begin() as conn:[span_57](start_span)[span_57](end_span)
        conn.execute(text('''
            INSERT INTO inventory (timestamp, action_type, quantity, notes, branch)
            VALUES (:ts, 'restock', :qty, :notes, :branch)
        '''), {
            "ts": get_egypt_now_str(),
            "qty": quantity,
            "notes": notes,
            "branch": branch
        })[span_58](start_span)[span_58](end_span)

def record_waste(branch: str, quantity: int = 1, notes: str = "ورقة تالفة"):
    with engine.begin() as conn:[span_59](start_span)[span_59](end_span)
        conn.execute(text('''
            INSERT INTO inventory (timestamp, action_type, quantity, notes, branch)
            VALUES (:ts, 'waste', :qty, :notes, :branch)
        '''), {
            "ts": get_egypt_now_str(),
            "qty": -quantity,
            "notes": notes,
            "branch": branch
        })[span_60](start_span)[span_60](end_span)

def record_transaction(branch: str, prints_count: int, amount_paid: float, custom_date: str = None, affect_inventory: bool = True):
    now_str = get_egypt_now_str()[span_61](start_span)[span_61](end_span)
    today_str = custom_date if custom_date else get_egypt_today_str()[span_62](start_span)[span_62](end_span)
    tx_timestamp = f"{today_str} 21:00:00" if custom_date else now_str
    
    with engine.begin() as conn:[span_63](start_span)[span_63](end_span)
        row = conn.execute(text("SELECT id FROM days WHERE date = :date"), {"date": today_str}).fetchone()[span_64](start_span)[span_64](end_span)
        if not row:[span_65](start_span)[span_65](end_span)
            if IS_POSTGRES:[span_66](start_span)[span_66](end_span)
                res = conn.execute(text("INSERT INTO days (date) VALUES (:date) RETURNING id"), {"date": today_str}).fetchone()[span_67](start_span)[span_67](end_span)
                day_id = res[0][span_68](start_span)[span_68](end_span)
            else:
                conn.execute(text("INSERT INTO days (date) VALUES (:date)"), {"date": today_str})[span_69](start_span)[span_69](end_span)
                res = conn.execute(text("SELECT last_insert_rowid()")).fetchone()[span_70](start_span)[span_70](end_span)
                day_id = res[0][span_71](start_span)[span_71](end_span)
        else:
            day_id = row[0][span_72](start_span)[span_72](end_span)
            
        conn.execute(text('''
            INSERT INTO transactions (day_id, timestamp, prints_count, amount_paid, branch)
            VALUES (:day_id, :ts, :prints, :amount, :branch)
        '''), {
            "day_id": day_id,
            "ts": tx_timestamp,
            "prints": prints_count,
            "amount": amount_paid,
            "branch": branch
        })[span_73](start_span)[span_73](end_span)
        
        if affect_inventory:
            conn.execute(text('''
                INSERT INTO inventory (timestamp, action_type, quantity, notes, branch)
                VALUES (:ts, 'consumption', :qty, :notes, :branch)
            '''), {
                "ts": tx_timestamp,
                "qty": -prints_count,
                "notes": f"استهلاك معاملة {today_str}",
                "branch": branch
            })

def delete_transaction(tx_id: int, branch: str):
    now_str = get_egypt_now_str()[span_74](start_span)[span_74](end_span)
    with engine.begin() as conn:[span_75](start_span)[span_75](end_span)
        tx = conn.execute(text("SELECT * FROM transactions WHERE id = :id AND branch = :branch"), {"id": tx_id, "branch": branch}).mappings().fetchone()[span_76](start_span)[span_76](end_span)
        if tx:[span_77](start_span)[span_77](end_span)
            conn.execute(text('''
                INSERT INTO inventory (timestamp, action_type, quantity, notes, branch)
                VALUES (:ts, 'restock', :qty, :notes, :branch)
            '''), {
                "ts": now_str,
                "qty": tx["prints_count"],
                "notes": f"استرجاع ورق لحذف المعاملة #{tx_id}",
                "branch": branch
            })[span_78](start_span)[span_78](end_span)
            conn.execute(text('''
                INSERT INTO audit_logs (timestamp, branch, action_type, transaction_id, details)
                VALUES (:ts, :branch, 'حذف مبيعات', :tx_id, :details)
            '''), {
                "ts": now_str,
                "branch": branch,
                "tx_id": tx_id,
                "details": f"تم حذف العملية (الوقت: {tx['timestamp']} | الورق: {tx['prints_count']} | المبلغ: {tx['amount_paid']} ج.م)"
            })[span_79](start_span)[span_79](end_span)
            conn.execute(text("DELETE FROM transactions WHERE id = :id"), {"id": tx_id})[span_80](start_span)[span_80](end_span)
            return True[span_81](start_span)[span_81](end_span)
    return False[span_82](start_span)[span_82](end_span)

def update_transaction(tx_id: int, branch: str, new_prints: int, new_amount: float):
    now_str = get_egypt_now_str()[span_83](start_span)[span_83](end_span)
    with engine.begin() as conn:[span_84](start_span)[span_84](end_span)
        tx = conn.execute(text("SELECT * FROM transactions WHERE id = :id AND branch = :branch"), {"id": tx_id, "branch": branch}).mappings().fetchone()[span_85](start_span)[span_85](end_span)
        if tx:[span_86](start_span)[span_86](end_span)
            diff_prints = new_prints - tx["prints_count"][span_87](start_span)[span_87](end_span)
            if diff_prints != 0:[span_88](start_span)[span_88](end_span)
                conn.execute(text('''
                    INSERT INTO inventory (timestamp, action_type, quantity, notes, branch)
                    VALUES (:ts, 'consumption', :qty, :notes, :branch)
                '''), {
                    "ts": now_str,
                    "qty": -diff_prints,
                    "notes": f"تسوية فرق ورق لتعديل المعاملة #{tx_id}",
                    "branch": branch
                })[span_89](start_span)[span_89](end_span)
            conn.execute(text('''
                INSERT INTO audit_logs (timestamp, branch, action_type, transaction_id, details)
                VALUES (:ts, :branch, 'تعديل مبيعات', :tx_id, :details)
            '''), {
                "ts": now_str,
                "branch": branch,
                "tx_id": tx_id,
                "details": f"تعديل من ({tx['prints_count']} ورق - {tx['amount_paid']} ج) إلى ({new_prints} ورق - {new_amount} ج)"
            })[span_90](start_span)[span_90](end_span)
            conn.execute(text('''
                UPDATE transactions 
                SET prints_count = :prints, amount_paid = :amount 
                WHERE id = :id
            '''), {
                "prints": new_prints,
                "amount": new_amount,
                "id": tx_id
            })[span_91](start_span)[span_91](end_span)
            return True[span_92](start_span)[span_92](end_span)
    return False[span_93](start_span)[span_93](end_span)

# ----------------- EXPENSES HELPER FUNCTIONS -----------------
def record_expense(branch: str, amount: float, description: str, created_by: str, custom_date: str = None):
    now_str = get_egypt_now_str()
    today_str = custom_date if custom_date else get_egypt_today_str()
    tx_timestamp = f"{today_str} 21:00:00" if custom_date else now_str
    with engine.begin() as conn:
        conn.execute(text('''
            INSERT INTO expenses (timestamp, date, branch, amount, description, created_by)
            VALUES (:ts, :date, :branch, :amount, :desc, :user)
        '''), {
            "ts": tx_timestamp,
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
                INSERT INTO audit_logs (timestamp, branch, action_type, transaction_id, details)
                VALUES (:ts, :branch, 'حذف مصروف', :tx_id, :details)
            '''), {
                "ts": now_str,
                "branch": exp["branch"],
                "tx_id": exp_id,
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
                INSERT INTO audit_logs (timestamp, branch, action_type, transaction_id, details)
                VALUES (:ts, :branch, 'تعديل مصروف', :tx_id, :details)
            '''), {
                "ts": now_str,
                "branch": exp["branch"],
                "tx_id": exp_id,
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

# ----------------- REBALANCE 21:00 SPIKE FUNCTION -----------------
def rebalance_bulk_hours():
    with engine.begin() as conn:
        real_tx = pd.read_sql_query(
            text("SELECT timestamp FROM transactions WHERE timestamp NOT LIKE '%21:00:00%'"),
            conn
        )
        if not real_tx.empty:
            real_tx['hour'] = pd.to_datetime(real_tx['timestamp']).dt.hour
            hour_counts = real_tx['hour'].value_counts(normalize=True)
            hours = hour_counts.index.values
            probabilities = hour_counts.values
        else:
            hours = [17, 18, 19, 20, 21, 22, 23, 0, 1, 2, 3]
            probabilities = [0.04, 0.06, 0.08, 0.12, 0.15, 0.18, 0.17, 0.10, 0.06, 0.03, 0.01]

        bulk_tx = pd.read_sql_query(
            text("SELECT id, timestamp FROM transactions WHERE timestamp LIKE '%21:00:00%'"),
            conn
        )
        
        count = 0
        for _, row in bulk_tx.iterrows():
            tx_id = row['id']
            date_part = row['timestamp'].split(' ')[0]
            sampled_hour = int(np.random.choice(hours, p=probabilities))
            sampled_minute = random.randint(0, 59)
            sampled_second = random.randint(0, 59)
            new_ts = f"{date_part} {sampled_hour:02d}:{sampled_minute:02d}:{sampled_second:02d}"
            
            conn.execute(
                text("UPDATE transactions SET timestamp = :new_ts WHERE id = :id"),
                {"new_ts": new_ts, "id": tx_id}
            )
            count += 1
    return count

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

# ----------------- SIDEBAR -----------------
st.sidebar.markdown(f"### 👋 مرحباً، {st.session_state.branch if st.session_state.role == 'employee' else 'المدير'}")
st.sidebar.button("🚪 تسجيل الخروج", on_click=logout, use_container_width=True)
st.sidebar.markdown("---")

role = st.session_state.role
branch = st.session_state.branch

# ================= 1. EMPLOYEE SCREEN =================
if role == "employee":
    current_stock = get_current_stock(branch)[span_94](start_span)[span_94](end_span)
    st.sidebar.metric(f"📦 رصيد الورق", f"{current_stock} ورقة")[span_95](start_span)[span_95](end_span)
    st.sidebar.caption(f"🕒 توقيت النظام: {get_egypt_now().strftime('%I:%M %p')}")[span_96](start_span)[span_96](end_span)
    st.sidebar.caption(f"📅 يوم العمل: {get_egypt_today_str()}")[span_97](start_span)[span_97](end_span)
    
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
    """, unsafe_allow_html=True)[span_98](start_span)[span_98](end_span)

    st.title(f"📸 فرع {branch} - المبيعات السريعة")[span_99](start_span)[span_99](end_span)
    st.caption("أزرار سريعة لتسجيل المبيعات وتتبع يوم العمل حتى 3:00 فجراً.")[span_100](start_span)[span_100](end_span)
    
    st.subheader("⚡ العمليات السريعة")[span_101](start_span)[span_101](end_span)
    
    if branch == "Heaven":[span_102](start_span)[span_102](end_span)
        btn_col1, btn_col2, btn_col3 = st.columns(3)[span_103](start_span)[span_103](end_span)
        with btn_col1:[span_104](start_span)[span_104](end_span)
            if st.button("🖼️ كارت فردي\n(30 ج - 1 ورقة)", use_container_width=True):[span_105](start_span)[span_105](end_span)
                if current_stock < 1:[span_106](start_span)[span_106](end_span)
                    st.error("⚠️ رصيد الورق غير كافٍ!")[span_107](start_span)[span_107](end_span)
                else:
                    record_transaction(branch, 1, 30.0)[span_108](start_span)[span_108](end_span)
                    st.success("✅ تم تسجيل البيع!")[span_109](start_span)[span_109](end_span)
                    st.rerun()[span_110](start_span)[span_110](end_span)
                    
        with btn_col2:[span_111](start_span)[span_111](end_span)
            if st.button("🎞️ كارتين\n(50 ج - 2 ورقة)", use_container_width=True):[span_112](start_span)[span_112](end_span)
                if current_stock < 2:[span_113](start_span)[span_113](end_span)
                    st.error("⚠️ رصيد الورق غير كافٍ!")[span_114](start_span)[span_114](end_span)
                else:
                    record_transaction(branch, 2, 50.0)[span_115](start_span)[span_115](end_span)
                    st.success("✅ تم تسجيل البيع!")[span_116](start_span)[span_116](end_span)
                    st.rerun()[span_117](start_span)[span_117](end_span)

        with btn_col3:[span_118](start_span)[span_118](end_span)
            if st.button("🗑️ ورقة تالفة\n(خصم 1 ورقة)", use_container_width=True):[span_119](start_span)[span_119](end_span)
                if current_stock < 1:[span_120](start_span)[span_120](end_span)
                    st.error("⚠️ رصيد الورق فارغ بالفعل!")[span_121](start_span)[span_121](end_span)
                else:
                    record_waste(branch, 1, "تالف طباعة سريع")[span_122](start_span)[span_122](end_span)
                    st.warning("⚠️ تم خصم ورقة تالفة من المخزون!")[span_123](start_span)[span_123](end_span)
                    st.rerun()[span_124](start_span)[span_124](end_span)
    else:
        btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(4)[span_125](start_span)[span_125](end_span)
        with btn_col1:[span_126](start_span)[span_126](end_span)
            if st.button("🖼️ صورة فردي\n(50 ج - 1 ورقة)", use_container_width=True):[span_127](start_span)[span_127](end_span)
                if current_stock < 1:[span_128](start_span)[span_128](end_span)
                    st.error("⚠️ رصيد الورق غير كافٍ!")[span_129](start_span)[span_129](end_span)
                else:
                    record_transaction(branch, 1, 50.0)[span_130](start_span)[span_130](end_span)
                    st.success("✅ تم تسجيل البيع!")[span_131](start_span)[span_131](end_span)
                    st.rerun()[span_132](start_span)[span_132](end_span)
                    
        with btn_col2:[span_133](start_span)[span_133](end_span)
            if st.button("🎞️ كارت ثلاثي\n(90 ج - 2 ورقة)", use_container_width=True):[span_134](start_span)[span_134](end_span)
                if current_stock < 2:[span_135](start_span)[span_135](end_span)
                    st.error("⚠️ رصيد الورق غير كافٍ!")[span_136](start_span)[span_136](end_span)
                else:
                    record_transaction(branch, 2, 90.0)[span_137](start_span)[span_137](end_span)
                    st.success("✅ تم تسجيل البيع!")[span_138](start_span)[span_138](end_span)
                    st.rerun()[span_139](start_span)[span_139](end_span)
                    
        with btn_col3:[span_140](start_span)[span_140](end_span)
            if st.button("📸 كارت رباعي\n(120 ج - 3 ورقات)", use_container_width=True):[span_141](start_span)[span_141](end_span)
                if current_stock < 3:[span_142](start_span)[span_142](end_span)
                    st.error("⚠️ رصيد الورق غير كافٍ!")[span_143](start_span)[span_143](end_span)
                else:
                    record_transaction(branch, 3, 120.0)[span_144](start_span)[span_144](end_span)
                    st.success("✅ تم تسجيل البيع!")[span_145](start_span)[span_145](end_span)
                    st.rerun()[span_146](start_span)[span_146](end_span)

        with btn_col4:[span_147](start_span)[span_147](end_span)
            if st.button("🗑️ ورقة تالفة\n(خصم 1 ورقة)", use_container_width=True):[span_148](start_span)[span_148](end_span)
                if current_stock < 1:[span_149](start_span)[span_149](end_span)
                    st.error("⚠️ رصيد الورق فارغ بالفعل!")[span_150](start_span)[span_150](end_span)
                else:
                    record_waste(branch, 1, "تالف طباعة سريع")[span_151](start_span)[span_151](end_span)
                    st.warning("⚠️ تم خصم ورقة تالفة من المخزون!")[span_152](start_span)[span_152](end_span)
                    st.rerun()[span_153](start_span)[span_153](end_span)

    st.markdown("<br><hr><br>", unsafe_allow_html=True)[span_154](start_span)[span_154](end_span)
    col_manual, col_restock, col_exp = st.columns(3)
    
    with col_manual:
        with st.expander("⚙️ إدخال مبيعات يدوي", expanded=False):[span_155](start_span)[span_155](end_span)
            with st.form("manual_form", clear_on_submit=True):[span_156](start_span)[span_156](end_span)
                prints = st.number_input("عدد الورق المطبوع", min_value=1, max_value=50, value=None, step=1, placeholder="أدخل عدد الورق...")[span_157](start_span)[span_157](end_span)
                amount = st.number_input("المبلغ المدفوع", min_value=0.0, value=None, step=10.0, placeholder="أدخل المبلغ...")[span_158](start_span)[span_158](end_span)
                submit_btn = st.form_submit_button("✅ تسجيل يدوياً", use_container_width=True)[span_159](start_span)[span_159](end_span)
                
                if submit_btn:[span_160](start_span)[span_160](end_span)
                    if prints is None or amount is None:[span_161](start_span)[span_161](end_span)
                        st.error("⚠️ يرجى إدخال عدد الورق والمبلغ أولاً!")[span_162](start_span)[span_162](end_span)
                    elif current_stock < prints:[span_163](start_span)[span_163](end_span)
                        st.error("⚠️ رصيد الورق المتاح غير كافٍ!")[span_164](start_span)[span_164](end_span)
                    else:
                        record_transaction(branch, prints, amount)[span_165](start_span)[span_165](end_span)
                        st.success("تم التسجيل يدوياً!")[span_166](start_span)[span_166](end_span)
                        st.rerun()[span_167](start_span)[span_167](end_span)

    with col_restock:
        with st.expander("📦 إضافة ورق للمخزون", expanded=False):[span_168](start_span)[span_168](end_span)
            with st.form("restock_form", clear_on_submit=True):[span_169](start_span)[span_169](end_span)
                restock_qty = st.number_input("عدد الورق المضاف", min_value=1, max_value=5000, value=None, step=50, placeholder="أدخل الكمية...")[span_170](start_span)[span_170](end_span)
                notes = st.text_input("ملاحظات", "")[span_171](start_span)[span_171](end_span)
                restock_btn = st.form_submit_button("➕ تزويد المخزون", use_container_width=True)[span_172](start_span)[span_172](end_span)
                
                if restock_btn:[span_173](start_span)[span_173](end_span)
                    add_stock(branch, restock_qty, notes)[span_174](start_span)[span_174](end_span)
                    st.success("تم التزويد بنجاح!")[span_175](start_span)[span_175](end_span)
                    st.rerun()[span_176](start_span)[span_176](end_span)

    with col_exp:
        with st.expander("💸 تسجيل مصروفات الوردية", expanded=False):
            with st.form("employee_expense_form", clear_on_submit=True):
                exp_amount = st.number_input("مبلغ المصروف (ج.م)", min_value=1.0, value=None, step=5.0, placeholder="أدخل المبلغ...")
                exp_desc = st.text_input("وصف المصروف", placeholder="مثال: شاي، صيانة، نثريات...")
                submit_exp = st.form_submit_button("💸 تسجيل المصروف", use_container_width=True)
                if submit_exp:
                    if exp_amount is None or not exp_desc.strip():
                        st.error("⚠️ يرجى إدخال المبلغ ووصف المصروف!")
                    else:
                        record_expense(branch, float(exp_amount), exp_desc.strip(), f"موظف {branch}")
                        st.success("تم تسجيل المصروف بنجاح!")
                        st.rerun()

    st.markdown("---")[span_177](start_span)[span_177](end_span)
    st.subheader("📋 عمليات يوم العمل الحالي (اليوم بالكامل)")[span_178](start_span)[span_178](end_span)
    
    today_str = get_egypt_today_str()[span_179](start_span)[span_179](end_span)
    with engine.connect() as conn:[span_180](start_span)[span_180](end_span)
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
        )[span_181](start_span)[span_181](end_span)
        
        if not today_tx.empty:[span_182](start_span)[span_182](end_span)
            display_user_tx = today_tx.rename(columns={
                'timestamp': 'الوقت',
                'prints_count': 'عدد الورق',
                'amount_paid': 'المبلغ (ج.م)'
            })[span_183](start_span)[span_183](end_span)
            st.dataframe(display_user_tx.drop(columns=['id']), use_container_width=True, hide_index=True)[span_184](start_span)[span_184](end_span)
            
            st.markdown("##### 🛠️ إدارة / تعديل / حذف مبيعات اليوم")[span_185](start_span)[span_185](end_span)
            options = {f"عملية #{row['id']} - الساعة {row['timestamp'].split(' ')[1]} ({row['prints_count']} ورق | {row['amount_paid']} ج)": row['id'] for _, row in today_tx.iterrows()}[span_186](start_span)[span_186](end_span)
            selected_label = st.selectbox("اختر العملية للتحكم بها:", list(options.keys()), key="sel_tx")[span_187](start_span)[span_187](end_span)
            selected_id = options[selected_label][span_188](start_span)[span_188](end_span)
            selected_row = today_tx[today_tx['id'] == selected_id].iloc[0][span_189](start_span)[span_189](end_span)
            
            col_act1, col_act2 = st.columns(2)[span_190](start_span)[span_190](end_span)
            with col_act1:[span_191](start_span)[span_191](end_span)
                with st.expander("✏️ تعديل العملية المحددة", expanded=False):[span_192](start_span)[span_192](end_span)
                    with st.form("edit_form"):[span_193](start_span)[span_193](end_span)
                        new_p = st.number_input("تعديل عدد الورق:", min_value=1, max_value=50, value=int(selected_row['prints_count']), step=1)[span_194](start_span)[span_194](end_span)
                        new_a = st.number_input("تعديل المبلغ (ج.م):", min_value=0.0, value=float(selected_row['amount_paid']), step=10.0)[span_195](start_span)[span_195](end_span)
                        edit_btn = st.form_submit_button("حفظ التعديلات", use_container_width=True)[span_196](start_span)[span_196](end_span)
                        if edit_btn:[span_197](start_span)[span_197](end_span)
                            if update_transaction(selected_id, branch, new_p, new_a):[span_198](start_span)[span_198](end_span)
                                st.success("تم تعديل العملية وضبط المخزون وسجل المراقبة بنجاح!")[span_199](start_span)[span_199](end_span)
                                st.rerun()[span_200](start_span)[span_200](end_span)

            with col_act2:[span_201](start_span)[span_201](end_span)
                with st.expander("🗑️ حذف العملية المحددة", expanded=False):[span_202](start_span)[span_202](end_span)
                    st.warning(f"هل أنت متأكد من حذف العملية #{selected_id}؟ سيتم استرجاع الورق للمخزون وتسجيل الحذف.")[span_203](start_span)[span_203](end_span)
                    if st.button("تأكيد الحذف نهائياً", type="primary", use_container_width=True, key="del_tx_btn"):[span_204](start_span)[span_204](end_span)
                        if delete_transaction(selected_id, branch):[span_205](start_span)[span_205](end_span)
                            st.success("تم مسح العملية واسترجاع الورق بنجاح!")[span_206](start_span)[span_206](end_span)
                            st.rerun()[span_207](start_span)[span_207](end_span)
        else:
            st.info("لا توجد مبيعات مسجلة في يوم العمل الحالي حتى الآن.")[span_208](start_span)[span_208](end_span)

    st.markdown("---")
    st.subheader("💸 مصروفات يوم العمل الحالي")
    with engine.connect() as conn:
        today_exp_df = pd.read_sql_query(
            text("SELECT id, timestamp, amount, description FROM expenses WHERE date = :date AND branch = :branch ORDER BY timestamp DESC"),
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
    check_and_add_monthly_allowance()[span_209](start_span)[span_209](end_span)

    st.title("📊 لوحة تحكم الإدارة (Admin Analytics)")[span_210](start_span)[span_210](end_span)
    
    st.sidebar.subheader("🏢 فلتر الفرع")[span_211](start_span)[span_211](end_span)
    selected_branch = st.sidebar.selectbox("اختر الفرع للتحليل:", ["الكل", "Heaven", "9A"])[span_212](start_span)[span_212](end_span)
    
    with engine.connect() as conn:
        all_tx_raw = pd.read_sql_query(text('''
            SELECT t.*, d.date 
            FROM transactions t
            JOIN days d ON t.day_id = d.id
            ORDER BY t.timestamp ASC
        '''), conn)
        
        all_exp_raw = pd.read_sql_query(text("SELECT * FROM expenses ORDER BY timestamp ASC"), conn)

    if not all_tx_raw.empty:
        min_date = pd.to_datetime(all_tx_raw['date']).dt.date.min()
        max_date = pd.to_datetime(all_tx_raw['date']).dt.date.max()
        
        st.sidebar.markdown("---")[span_213](start_span)[span_213](end_span)
        st.sidebar.subheader("📅 فلاتر التاريخ")[span_214](start_span)[span_214](end_span)
        date_range = st.sidebar.date_input(
            "اختر الفترة الزمنية للتحليل:",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )[span_215](start_span)[span_215](end_span)
        
        if len(date_range) == 2:[span_216](start_span)[span_216](end_span)
            start_dt, end_dt = date_range[span_217](start_span)[span_217](end_span)
            mask_tx_date = (pd.to_datetime(all_tx_raw['date']).dt.date >= start_dt) & (pd.to_datetime(all_tx_raw['date']).dt.date <= end_dt)
            filtered_tx = all_tx_raw.loc[mask_tx_date].copy()
            
            if not all_exp_raw.empty:
                mask_exp_date = (pd.to_datetime(all_exp_raw['date']).dt.date >= start_dt) & (pd.to_datetime(all_exp_raw['date']).dt.date <= end_dt)
                filtered_exp = all_exp_raw.loc[mask_exp_date].copy()
            else:
                filtered_exp = pd.DataFrame()
        else:
            filtered_tx = all_tx_raw.copy()
            filtered_exp = all_exp_raw.copy()

        # حساب المصروفات وفق الفلتر
        if selected_branch == "الكل":
            tx_subset = filtered_tx
            total_rev_all = tx_subset['amount_paid'].sum() if not tx_subset.empty else 0
            total_prints_all = tx_subset['prints_count'].sum() if not tx_subset.empty else 0
            total_cust_all = len(tx_subset)
            total_exp_all = filtered_exp['amount'].sum() if not filtered_exp.empty else 0
        else:
            tx_subset = filtered_tx[filtered_tx['branch'] == selected_branch]
            total_rev_all = tx_subset['amount_paid'].sum() if not tx_subset.empty else 0
            total_prints_all = tx_subset['prints_count'].sum() if not tx_subset.empty else 0
            total_cust_all = len(tx_subset)
            
            if not filtered_exp.empty:
                direct_exp = filtered_exp[filtered_exp['branch'] == selected_branch]['amount'].sum()
                general_exp = filtered_exp[filtered_exp['branch'] == 'General']['amount'].sum()
                total_exp_all = direct_exp + (general_exp / 2.0)
            else:
                total_exp_all = 0.0

        net_profit = total_rev_all - total_exp_all

        # مؤشرات المخزون والتالف
        if selected_branch == "الكل":[span_218](start_span)[span_218](end_span)
            stock_heaven = get_current_stock("Heaven")[span_219](start_span)[span_219](end_span)
            stock_9a = get_current_stock("9A")[span_220](start_span)[span_220](end_span)
            waste_heaven = get_waste_count("Heaven")[span_221](start_span)[span_221](end_span)
            waste_9a = get_waste_count("9A")[span_222](start_span)[span_222](end_span)
            stock_display = f"Heaven: {stock_heaven} | 9A: {stock_9a}[span_223](start_span)"[span_223](end_span)
            waste_display = f"Heaven: {waste_heaven} | 9A: {waste_9a}[span_224](start_span)"[span_224](end_span)
        else:
            stock_display = f"{get_current_stock(selected_branch)} ورقة[span_225](start_span)"[span_225](end_span)
            waste_display = f"{get_waste_count(selected_branch)} ورقة[span_226](start_span)"[span_226](end_span)

        # Top Financial KPIs
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("💰 إجمالي الإيرادات", f"{total_rev_all:,.0f} ج.م")
        kpi2.metric("💸 إجمالي المصروفات", f"{total_exp_all:,.0f} ج.م", delta=f"-{total_exp_all:,.0f}", delta_color="inverse")
        kpi3.metric("📈 صافي الربح", f"{net_profit:,.0f} ج.م", delta=f"{net_profit:,.0f}")

        kpi4, kpi5, kpi6 = st.columns(3)
        kpi4.metric("👥 إجمالي الزبائن", f"{total_cust_all:,}")
        kpi5.metric("🖨️ الورق المطبوع", f"{total_prints_all:,} ورقة")
        kpi6.metric("🗑️ إجمالي التالف", waste_display)

        st.metric("📦 المخزون المتبقي حالياً", stock_display)[span_227](start_span)[span_227](end_span)
        
        st.markdown("---")[span_228](start_span)[span_228](end_span)

        # ----------------- REBALANCE 21:00 FIX BUTTON (سحر التوزيع) -----------------
        with st.expander("⚡ معالجة وإعادة توزيع ساعات البيانات القديمة (Spike Fix)", expanded=False):
            st.info("هذا الزر يقوم بفحص العمليات التي تم إدخالها عند الساعة 21:00:00 وتوزيع ساعاتها ودقائقها واقعياً وفق النسب الفعلية للزبائن في باقي الأيام دون المساس بالتاريخ أو المبالغ.")
            if st.button("🔄 ضبط وتوزيع ساعات العمليات القديمة عشوائياً وفق التوزيع الفعلي", type="primary", use_container_width=True):
                rebalanced_rows = rebalance_bulk_hours()
                st.success(f"✅ تم بنجاح معالجة وإعادة توزيع {rebalanced_rows} عملية بتوقيتات واقعية!")
                st.rerun()

        st.markdown("---")

        # ----------------- ADMIN EXPENSES ENTRY -----------------
        with st.expander("💸 تسجيل مصروفات جديدة بواسطة الأدمن", expanded=False):
            with st.form("admin_exp_form", clear_on_submit=True):
                c_a1, c_a2, c_a3 = st.columns(3)
                with c_a1:
                    ad_branch = st.selectbox("جهة المصروف:", ["General", "Heaven", "9A"], format_func=lambda x: "مصروف بيزنس عام (يوزع على الفرعين)" if x == "General" else f"فرع {x}")
                with c_a2:
                    ad_amount = st.number_input("المبلغ (ج.م):", min_value=1.0, value=None, step=50.0, placeholder="أدخل المبلغ...")
                with c_a3:
                    ad_desc = st.text_input("وصف المصروف:", placeholder="مثال: شراء ورق، صيانة، تسويق...")
                
                if st.form_submit_button("تسجيل المصروف للأدمن", use_container_width=True):
                    if ad_amount is None or not ad_desc.strip():
                        st.error("⚠️ يرجى إدخال المبلغ والوصف أولاً!")
                    else:
                        record_expense(ad_branch, float(ad_amount), ad_desc.strip(), "المدير")
                        st.success("تم تسجيل المصروف بنجاح!")
                        st.rerun()

        st.markdown("---")

        # ----------------- TODAY'S LIVE TRANSACTIONS FOR ADMIN -----------------
        today_b_str = get_egypt_today_str()[span_229](start_span)[span_229](end_span)
        st.subheader(f"⚡ عمليات ومصروفات يوم العمل الحالي ({selected_branch}) - {today_b_str}")
        
        col_tab1, col_tab2 = st.columns(2)
        with col_tab1:
            st.markdown("##### 🛒 مبيعات اليوم")
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
                    'branch': 'الفرع',
                    'prints_count': 'عدد الورق',
                    'amount_paid': 'المبلغ (ج.م)'
                })
                st.dataframe(display_admin_today, use_container_width=True, hide_index=True)
            else:
                st.info("لا توجد مبيعات مسجلة اليوم حتى الآن.")

        with col_tab2:
            st.markdown("##### 💸 مصروفات اليوم")
            with engine.connect() as conn:
                ad_exp_f = ""
                ad_exp_p = {"date": today_b_str}
                if selected_branch != "الكل":
                    ad_exp_f = "AND (branch = :branch OR branch = 'General')"
                    ad_exp_p["branch"] = selected_branch

                today_admin_exp = pd.read_sql_query(
                    text(f"SELECT timestamp, branch, amount, description, created_by FROM expenses WHERE date = :date {ad_exp_f} ORDER BY timestamp DESC"),
                    conn,
                    params=ad_exp_p
                )
            if not today_admin_exp.empty:
                disp_ad_exp = today_admin_exp.rename(columns={
                    'timestamp': 'الوقت',
                    'branch': 'الفرع',
                    'amount': 'المبلغ (ج.م)',
                    'description': 'الوصف',
                    'created_by': 'بواسطة'
                })
                st.dataframe(disp_ad_exp, use_container_width=True, hide_index=True)
            else:
                st.info("لا توجد مصروفات مسجلة اليوم حتى الآن.")

        st.markdown("---")[span_230](start_span)[span_230](end_span)
        
        # ----------------- CHARTS & BEHAVIOR -----------------
        if not tx_subset.empty:
            days_df = tx_subset.groupby('date').agg(
                first_customer_time=('timestamp', 'min'),
                last_customer_time=('timestamp', 'max'),
                total_customers=('id', 'count'),
                total_prints=('prints_count', 'sum'),
                total_revenue=('amount_paid', 'sum')
            ).reset_index()
            
            ARABIC_DAYS = {
                "Monday": "الإثنين", "Tuesday": "الثلاثاء", "Wednesday": "الأربعاء",
                "Thursday": "الخميس", "Friday": "الجمعة", "Saturday": "السبت", "Sunday": "الأحد"
            }[span_231](start_span)[span_231](end_span)
            
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
                return pd.to_datetime(ts).strftime('%I:%M %p')
            
            behavior_df['first_time'] = behavior_df['first_customer_time'].apply(extract_time)
            behavior_df['last_time'] = behavior_df['last_customer_time'].apply(extract_time)
            behavior_df['peak_str'] = behavior_df['peak_hour'].apply(lambda x: f"{int(x)}:00" if pd.notna(x) else "-")
            
            st.subheader(f"📋 سلوك الزبائن اليومي ({selected_branch})")[span_232](start_span)[span_232](end_span)
            display_df = behavior_df[['date', 'day_name', 'first_time', 'last_time', 'peak_str', 'total_customers', 'total_revenue']]
            display_df.columns = ['تاريخ يوم العمل', 'اليوم', 'أول زبون', 'آخر زبون', 'ساعة الذروة', 'عدد الزبائن', 'الإيراد (ج.م)'][span_233](start_span)[span_233](end_span)
            st.dataframe(display_df, use_container_width=True, hide_index=True)[span_234](start_span)[span_234](end_span)
            
            col_chart1, col_chart2 = st.columns(2)[span_235](start_span)[span_235](end_span)
            
            with col_chart1:[span_236](start_span)[span_236](end_span)
                st.subheader("📉 الإيرادات والزبائن خلال الفترة")[span_237](start_span)[span_237](end_span)
                fig = go.Figure()[span_238](start_span)[span_238](end_span)
                fig.add_trace(go.Scatter(
                    x=days_df['date'], y=days_df['total_revenue'],
                    mode='lines+markers', name='الإيراد',
                    line=dict(color='#00CC96', width=3)
                ))
                fig.add_trace(go.Bar(
                    x=days_df['date'], y=days_df['total_customers'],
                    name='عدد الزبائن', yaxis='y2',
                    marker_color='rgba(99, 110, 250, 0.5)'
                ))
                fig.update_layout(
                    yaxis=dict(title='الإيراد (ج.م)'),
                    yaxis2=dict(title='الزبائن', overlaying='y', side='right', showgrid=False),
                    hovermode="x unified",
                    legend=dict(orientation="h", y=1.1)
                )[span_239](start_span)[span_239](end_span)
                st.plotly_chart(fig, use_container_width=True)[span_240](start_span)[span_240](end_span)
                
            with col_chart2:[span_241](start_span)[span_241](end_span)
                st.subheader("📅 الإقبال حسب أيام الأسبوع")[span_242](start_span)[span_242](end_span)
                weekday_stats = behavior_df.groupby('day_name').agg({'total_customers': 'sum'}).reset_index()
                day_order = ["السبت", "الأحد", "الإثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة"][span_243](start_span)[span_243](end_span)
                weekday_stats['day_name'] = pd.Categorical(weekday_stats['day_name'], categories=day_order, ordered=True)[span_244](start_span)[span_244](end_span)
                weekday_stats = weekday_stats.sort_values('day_name')[span_245](start_span)[span_245](end_span)
                
                fig_week = px.bar(weekday_stats, x='day_name', y='total_customers', 
                                  labels={'day_name': 'اليوم', 'total_customers': 'عدد الزبائن'},
                                  color='total_customers', color_continuous_scale='Blues')[span_246](start_span)[span_246](end_span)
                st.plotly_chart(fig_week, use_container_width=True)[span_247](start_span)[span_247](end_span)
            
            st.subheader("🔥 ساعات الذروة الإجمالية في هذه الفترة")[span_248](start_span)[span_248](end_span)
            hourly = tx_subset.groupby('hour')['id'].count().reset_index().rename(columns={'id': 'الزيارات'})
            hourly['hour_str'] = hourly['hour'].apply(lambda x: f"{x}:00")
            fig_hour = px.bar(hourly, x='hour_str', y='الزيارات', color='الزيارات',
                              labels={'hour_str': 'الساعة'}, color_continuous_scale='Sunset')
            st.plotly_chart(fig_hour, use_container_width=True)
        else:
            st.warning("لا توجد بيانات مسجلة في الفترة المحددة.")[span_249](start_span)[span_249](end_span)
    else:
        st.info("لا توجد بيانات كافية لعرض الرسوم البيانية بعد.")[span_250](start_span)[span_250](end_span)

    # --- AUDIT LOGS SECTION FOR ADMIN ---
    st.markdown("---")[span_251](start_span)[span_251](end_span)
    st.subheader("🕵️ سجل المراقبة والتعديلات (Audit Logs)")[span_252](start_span)[span_252](end_span)
    st.caption("سجل مفصل يوضح كل عملية أو مصروف تم حذفها أو تعديلها من قبل الموظفين وتوقيتها الدقيق.")
    
    with engine.connect() as conn:[span_253](start_span)[span_253](end_span)
        audit_filter = "[span_254](start_span)"[span_254](end_span)
        audit_params = {}[span_255](start_span)[span_255](end_span)
        if selected_branch != "الكل":[span_256](start_span)[span_256](end_span)
            audit_filter = "WHERE branch = :branch[span_257](start_span)"[span_257](end_span)
            audit_params = {"branch": selected_branch}[span_258](start_span)[span_258](end_span)
            
        try:
            audit_df = pd.read_sql_query(
                text(f"SELECT timestamp, branch, action_type, details FROM audit_logs {audit_filter} ORDER BY timestamp DESC LIMIT 50"),
                conn,
                params=audit_params
            )[span_259](start_span)[span_259](end_span)
            if not audit_df.empty:[span_260](start_span)[span_260](end_span)
                audit_display = audit_df.rename(columns={
                    'timestamp': 'الوقت',
                    'branch': 'الفرع',
                    'action_type': 'نوع الإجراء',
                    'details': 'تفاصيل الإجراء'
                })[span_261](start_span)[span_261](end_span)
                st.dataframe(audit_display, use_container_width=True, hide_index=True)[span_262](start_span)[span_262](end_span)
            else:
                st.info("سجل المراقبة نظيف، لا توجد أي عمليات حذف أو تعديل حتى الآن.")[span_263](start_span)[span_263](end_span)
        except Exception:[span_264](start_span)[span_264](end_span)
            st.info("سجل المراقبة نظيف، لا توجد أي عمليات حذف أو تعديل حتى الآن.")[span_265](start_span)[span_265](end_span)

    # --- SECTION: LEAVES MANAGEMENT (AT BOTTOM) ---
    st.markdown("---")[span_266](start_span)[span_266](end_span)
    st.subheader("🏖️ رصيد وإجازات الموظفين")[span_267](start_span)[span_267](end_span)
    leave_heaven = get_leave_balance("Heaven")[span_268](start_span)[span_268](end_span)
    leave_9a = get_leave_balance("9A")[span_269](start_span)[span_269](end_span)
    
    col_l1, col_l2 = st.columns(2)[span_270](start_span)[span_270](end_span)
    with col_l1:[span_271](start_span)[span_271](end_span)
        st.markdown(f"#### 🌴 فرع Heaven: **{leave_heaven} أيام متبقية**")[span_272](start_span)[span_272](end_span)
        with st.expander("تسجيل إجازة لموظف Heaven (-1 يوم)", expanded=False):[span_273](start_span)[span_273](end_span)
            with st.form("leave_heaven_form"):[span_274](start_span)[span_274](end_span)
                note_h = st.text_input("ملاحظات الإجازة:", value="إجازة اعتيادية")[span_275](start_span)[span_275](end_span)
                if st.form_submit_button("🌴 تأكيد خصم يوم إجازة (Heaven)", use_container_width=True):[span_276](start_span)[span_276](end_span)
                    record_leave("Heaven", note_h)[span_277](start_span)[span_277](end_span)
                    st.success("تم خصم يوم إجازة بنجاح!")[span_278](start_span)[span_278](end_span)
                    st.rerun()[span_279](start_span)[span_279](end_span)

    with col_l2:[span_280](start_span)[span_280](end_span)
        st.markdown(f"#### 🌴 فرع 9A: **{leave_9a} أيام متبقية**")[span_281](start_span)[span_281](end_span)
        with st.expander("تسجيل إجازة لموظف 9A (-1 يوم)", expanded=False):[span_282](start_span)[span_282](end_span)
            with st.form("leave_9a_form"):[span_283](start_span)[span_283](end_span)
                note_9a = st.text_input("ملاحظات الإجازة:", value="إجازة اعتيادية")[span_284](start_span)[span_284](end_span)
                if st.form_submit_button("🌴 تأكيد خصم يوم إجازة (9A)", use_container_width=True):[span_285](start_span)[span_285](end_span)
                    record_leave("9A", note_9a)[span_286](start_span)[span_286](end_span)
                    st.success("تم خصم يوم إجازة بنجاح!")[span_287](start_span)[span_287](end_span)
                    st.rerun()[span_288](start_span)[span_288](end_span)

    with st.expander("📋 عرض سجل حركات الإجازات بالكامل", expanded=False):[span_289](start_span)[span_289](end_span)
        with engine.connect() as conn:[span_290](start_span)[span_290](end_span)
            leaves_df = pd.read_sql_query(
                text("SELECT timestamp, branch, action_type, days_count, notes FROM employee_leaves ORDER BY timestamp DESC LIMIT 50"),
                conn
            )[span_291](start_span)[span_291](end_span)
            if not leaves_df.empty:[span_292](start_span)[span_292](end_span)
                display_leaves = leaves_df.rename(columns={
                    'timestamp': 'الوقت',
                    'branch': 'الفرع',
                    'action_type': 'نوع الحركة',
                    'days_count': 'الأيام',
                    'notes': 'الملاحظات'
                })[span_293](start_span)[span_293](end_span)
                st.dataframe(display_leaves, use_container_width=True, hide_index=True)[span_294](start_span)[span_294](end_span)
            else:
                st.info("لا توجد حركات إجازات مسجلة بعد.")[span_295](start_span)[span_295](end_span)

    # --- BACKUP SECTION ---
    st.markdown("---")[span_296](start_span)[span_296](end_span)
    st.subheader("📥 النسخ الاحتياطي للبيانات (Backup)")[span_297](start_span)[span_297](end_span)
    st.caption("تقدر تحمل كل بيانات المبيعات والمصروفات كملفات إكسيل (CSV).")[span_298](start_span)[span_298](end_span)
    
    with engine.connect() as conn:[span_299](start_span)[span_299](end_span)
        all_backup_tx = pd.read_sql_query(text('''
            SELECT t.timestamp, d.date, t.prints_count, t.amount_paid, t.branch
            FROM transactions t
            JOIN days d ON t.day_id = d.id
            ORDER BY t.timestamp DESC
        '''), conn)[span_300](start_span)[span_300](end_span)
        
        all_backup_exp = pd.read_sql_query(text("SELECT * FROM expenses ORDER BY timestamp DESC"), conn)
        
    col_b1, col_b2, col_b3, col_b4 = st.columns(4)[span_301](start_span)[span_301](end_span)
    today_date_str = get_egypt_today_str()[span_302](start_span)[span_302](end_span)
    
    if not all_backup_tx.empty:[span_303](start_span)[span_303](end_span)
        all_backup_tx_display = all_backup_tx.rename(columns={
            'timestamp': 'الوقت',
            'date': 'تاريخ يوم العمل',
            'prints_count': 'عدد الورق',
            'amount_paid': 'المبلغ (ج.م)',
            'branch': 'الفرع'
        })[span_304](start_span)[span_304](end_span)
        csv_all = all_backup_tx_display.to_csv(index=False).encode('utf-8-sig')[span_305](start_span)[span_305](end_span)
        col_b1.download_button(
            label="📥 تحميل المبيعات (الكل)",
            data=csv_all,
            file_name=f"all_sales_{today_date_str}.csv",
            mime="text/csv",
            use_container_width=True
        )[span_306](start_span)[span_306](end_span)
        
        df_heaven = all_backup_tx_display[all_backup_tx_display["الفرع"] == "Heaven"][span_307](start_span)[span_307](end_span)
        if not df_heaven.empty:[span_308](start_span)[span_308](end_span)
            csv_heaven = df_heaven.to_csv(index=False).encode('utf-8-sig')[span_309](start_span)[span_309](end_span)
            col_b2.download_button(
                label="📥 مبيعات Heaven",
                data=csv_heaven,
                file_name=f"heaven_sales_{today_date_str}.csv",
                mime="text/csv",
                use_container_width=True
            )[span_310](start_span)[span_310](end_span)
            
        df_9a = all_backup_tx_display[all_backup_tx_display["الفرع"] == "9A"][span_311](start_span)[span_311](end_span)
        if not df_9a.empty:[span_312](start_span)[span_312](end_span)
            csv_9a = df_9a.to_csv(index=False).encode('utf-8-sig')[span_313](start_span)[span_313](end_span)
            col_b3.download_button(
                label="📥 مبيعات 9A",
                data=csv_9a,
                file_name=f"9a_sales_{today_date_str}.csv",
                mime="text/csv",
                use_container_width=True
            )[span_314](start_span)[span_314](end_span)
            
    if not all_backup_exp.empty:
        csv_exp = all_backup_exp.to_csv(index=False).encode('utf-8-sig')
        col_b4.download_button(
            label="📥 تحميل كل المصروفات",
            data=csv_exp,
            file_name=f"all_expenses_{today_date_str}.csv",
            mime="text/csv",
            use_container_width=True
        )

