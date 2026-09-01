import streamlit as st
import pandas as pd
from datetime import datetime, date, timezone, timedelta
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
    # احتساب يوم العمل التشغيلي: يطرح 4 ساعات لضم ساعات الفجر (حتى 3:59 ص) لليوم السابق
    egypt_now = get_egypt_now()
    business_now = egypt_now - timedelta(hours=4)
    return business_now.strftime("%Y-%m-%d")

# ----------------- APP CONFIG -----------------
st.set_page_config(page_title="Photobooth Management System", page_icon="📸", layout="wide")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# ----------------- DB SETUP -----------------
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
    with engine.begin() as conn:
        if IS_POSTGRES:
            days_id_def = "id SERIAL PRIMARY KEY"
            tx_id_def = "id SERIAL PRIMARY KEY"
            inv_id_def = "id SERIAL PRIMARY KEY"
            audit_id_def = "id SERIAL PRIMARY KEY"
            leaves_id_def = "id SERIAL PRIMARY KEY"
            exp_id_def = "id SERIAL PRIMARY KEY"
        else:
            days_id_def = "id INTEGER PRIMARY KEY AUTOINCREMENT"
            tx_id_def = "id INTEGER PRIMARY KEY AUTOINCREMENT"
            inv_id_def = "id INTEGER PRIMARY KEY AUTOINCREMENT"
            audit_id_def = "id INTEGER PRIMARY KEY AUTOINCREMENT"
            leaves_id_def = "id INTEGER PRIMARY KEY AUTOINCREMENT"
            exp_id_def = "id INTEGER PRIMARY KEY AUTOINCREMENT"
            
        conn.execute(text(f'''
            CREATE TABLE IF NOT EXISTS days (
                {days_id_def},
                date TEXT UNIQUE NOT NULL
            )
        '''))
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
        '''))
        conn.execute(text(f'''
            CREATE TABLE IF NOT EXISTS inventory (
                {inv_id_def},
                timestamp TEXT NOT NULL,
                action_type TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                notes TEXT,
                branch TEXT NOT NULL
            )
        '''))
        conn.execute(text(f'''
            CREATE TABLE IF NOT EXISTS audit_logs (
                {audit_id_def},
                timestamp TEXT NOT NULL,
                branch TEXT NOT NULL,
                action_type TEXT NOT NULL,
                transaction_id INTEGER,
                details TEXT NOT NULL
            )
        '''))
        conn.execute(text(f'''
            CREATE TABLE IF NOT EXISTS employee_leaves (
                {leaves_id_def},
                timestamp TEXT NOT NULL,
                branch TEXT NOT NULL,
                action_type TEXT NOT NULL,
                days_count INTEGER NOT NULL,
                notes TEXT
            )
        '''))
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

init_db()

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
    
    with engine.begin() as conn:
        row = conn.execute(text("SELECT id FROM days WHERE date = :date"), {"date": today_str}).fetchone()
        if not row:
            if IS_POSTGRES:
                res = conn.execute(text("INSERT INTO days (date) VALUES (:date) RETURNING id"), {"date": today_str}).fetchone()
                day_id = res[0]
            else:
                conn.execute(text("INSERT INTO days (date) VALUES (:date)"), {"date": today_str})
                res = conn.execute(text("SELECT last_insert_rowid()")).fetchone()
                day_id = res[0]
        else:
            day_id = row[0]
            
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
                INSERT INTO audit_logs (timestamp, branch, action_type, transaction_id, details)
                VALUES (:ts, :branch, 'حذف مبيعات', :tx_id, :details)
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
                INSERT INTO audit_logs (timestamp, branch, action_type, transaction_id, details)
                VALUES (:ts, :branch, 'تعديل مبيعات', :tx_id, :details)
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
    with engine.begin() as conn:
        conn.execute(text('''
            INSERT INTO expenses (timestamp, date, branch, amount, description, created_by)
            VALUES (:ts, :date, :branch, :amount, :desc, :user)
        '''), {
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
    current_stock = get_current_stock(branch)
    st.sidebar.metric(f"📦 رصيد الورق", f"{current_stock} ورقة")
    st.sidebar.caption(f"🕒 توقيت النظام: {get_egypt_now().strftime('%I:%M %p')}")
    st.sidebar.caption(f"📅 يوم العمل: {get_egypt_today_str()}")
    
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
    check_and_add_monthly_allowance()

    st.title("📊 لوحة تحكم الإدارة (Admin Analytics)")
    
    st.sidebar.subheader("🏢 فلتر الفرع")
    selected_branch = st.sidebar.selectbox("اختر الفرع للتحليل:", ["الكل", "Heaven", "9A"])
    
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
        
        st.sidebar.markdown("---")
        st.sidebar.subheader("📅 فلاتر التاريخ")
        date_range = st.sidebar.date_input(
            "اختر الفترة الزمنية للتحليل:",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )
        
        if len(date_range) == 2:
            start_dt, end_dt = date_range
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
                # تحميل الفرع بنصف المصاريف العامة
                total_exp_all = direct_exp + (general_exp / 2.0)
            else:
                total_exp_all = 0.0

        net_profit = total_rev_all - total_exp_all

        # مؤشرات المخزون والتالف
        if selected_branch == "الكل":
            stock_heaven = get_current_stock("Heaven")
            stock_9a = get_current_stock("9A")
            waste_heaven = get_waste_count("Heaven")
            waste_9a = get_waste_count("9A")
            stock_display = f"Heaven: {stock_heaven} | 9A: {stock_9a}"
            waste_display = f"Heaven: {waste_heaven} | 9A: {waste_9a}"
        else:
            stock_display = f"{get_current_stock(selected_branch)} ورقة"
            waste_display = f"{get_waste_count(selected_branch)} ورقة"

        # Top Financial KPIs
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("💰 إجمالي الإيرادات", f"{total_rev_all:,.0f} ج.م")
        kpi2.metric("💸 إجمالي المصروفات", f"{total_exp_all:,.0f} ج.م", delta=f"-{total_exp_all:,.0f}", delta_color="inverse")
        kpi3.metric("📈 صافي الربح", f"{net_profit:,.0f} ج.م", delta=f"{net_profit:,.0f}")

        kpi4, kpi5, kpi6 = st.columns(3)
        kpi4.metric("👥 إجمالي الزبائن", f"{total_cust_all:,}")
        kpi5.metric("🖨️ الورق المطبوع", f"{total_prints_all:,} ورقة")
        kpi6.metric("🗑️ إجمالي التالف", waste_display)

        st.metric("📦 المخزون المتبقي حالياً", stock_display)
        
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
        today_b_str = get_egypt_today_str()
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

        st.markdown("---")
        
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
            }
            
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
            
            st.subheader(f"📋 سلوك الزبائن اليومي ({selected_branch})")
            display_df = behavior_df[['date', 'day_name', 'first_time', 'last_time', 'peak_str', 'total_customers', 'total_revenue']]
            display_df.columns = ['تاريخ يوم العمل', 'اليوم', 'أول زبون', 'آخر زبون', 'ساعة الذروة', 'عدد الزبائن', 'الإيراد (ج.م)']
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            
            col_chart1, col_chart2 = st.columns(2)
            
            with col_chart1:
                st.subheader("📉 الإيرادات والزبائن خلال الفترة")
                fig = go.Figure()
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
                )
                st.plotly_chart(fig, use_container_width=True)
                
            with col_chart2:
                st.subheader("📅 الإقبال حسب أيام الأسبوع")
                weekday_stats = behavior_df.groupby('day_name').agg({'total_customers': 'sum'}).reset_index()
                day_order = ["السبت", "الأحد", "الإثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة"]
                weekday_stats['day_name'] = pd.Categorical(weekday_stats['day_name'], categories=day_order, ordered=True)
                weekday_stats = weekday_stats.sort_values('day_name')
                
                fig_week = px.bar(weekday_stats, x='day_name', y='total_customers', 
                                  labels={'day_name': 'اليوم', 'total_customers': 'عدد الزبائن'},
                                  color='total_customers', color_continuous_scale='Blues')
                st.plotly_chart(fig_week, use_container_width=True)
            
            st.subheader("🔥 ساعات الذروة الإجمالية في هذه الفترة")
            hourly = tx_subset.groupby('hour')['id'].count().reset_index().rename(columns={'id': 'الزيارات'})
            hourly['hour_str'] = hourly['hour'].apply(lambda x: f"{x}:00")
            fig_hour = px.bar(hourly, x='hour_str', y='الزيارات', color='الزيارات',
                              labels={'hour_str': 'الساعة'}, color_continuous_scale='Sunset')
            st.plotly_chart(fig_hour, use_container_width=True)
        else:
            st.warning("لا توجد بيانات مسجلة في الفترة المحددة.")
    else:
        st.info("لا توجد بيانات كافية لعرض الرسوم البيانية بعد.")

    # --- AUDIT LOGS SECTION FOR ADMIN ---
    st.markdown("---")
    st.subheader("🕵️ سجل المراقبة والتعديلات (Audit Logs)")
    st.caption("سجل مفصل يوضح كل عملية أو مصروف تم حذفها أو تعديلها من قبل الموظفين وتوقيتها الدقيق.")
    
    with engine.connect() as conn:
        audit_filter = ""
        audit_params = {}
        if selected_branch != "الكل":
            audit_filter = "WHERE branch = :branch"
            audit_params = {"branch": selected_branch}
            
        try:
            audit_df = pd.read_sql_query(
                text(f"SELECT timestamp, branch, action_type, details FROM audit_logs {audit_filter} ORDER BY timestamp DESC LIMIT 50"),
                conn,
                params=audit_params
            )
            if not audit_df.empty:
                audit_display = audit_df.rename(columns={
                    'timestamp': 'الوقت',
                    'branch': 'الفرع',
                    'action_type': 'نوع الإجراء',
                    'details': 'تفاصيل الإجراء'
                })
                st.dataframe(audit_display, use_container_width=True, hide_index=True)
            else:
                st.info("سجل المراقبة نظيف، لا توجد أي عمليات حذف أو تعديل حتى الآن.")
        except Exception:
            st.info("سجل المراقبة نظيف، لا توجد أي عمليات حذف أو تعديل حتى الآن.")

    # --- SECTION: LEAVES MANAGEMENT (AT BOTTOM) ---
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

    # --- BACKUP SECTION ---
    st.markdown("---")
    st.subheader("📥 النسخ الاحتياطي للبيانات (Backup)")
    st.caption("تقدر تحمل كل بيانات المبيعات والمصروفات كملفات إكسيل (CSV).")
    
    with engine.connect() as conn:
        all_backup_tx = pd.read_sql_query(text('''
            SELECT t.timestamp, d.date, t.prints_count, t.amount_paid, t.branch
            FROM transactions t
            JOIN days d ON t.day_id = d.id
            ORDER BY t.timestamp DESC
        '''), conn)
        
        all_backup_exp = pd.read_sql_query(text("SELECT * FROM expenses ORDER BY timestamp DESC"), conn)
        
    col_b1, col_b2, col_b3, col_b4 = st.columns(4)
    today_date_str = get_egypt_today_str()
    
    if not all_backup_tx.empty:
        all_backup_tx_display = all_backup_tx.rename(columns={
            'timestamp': 'الوقت',
            'date': 'تاريخ يوم العمل',
            'prints_count': 'عدد الورق',
            'amount_paid': 'المبلغ (ج.م)',
            'branch': 'الفرع'
        })
        csv_all = all_backup_tx_display.to_csv(index=False).encode('utf-8-sig')
        col_b1.download_button(
            label="📥 تحميل المبيعات (الكل)",
            data=csv_all,
            file_name=f"all_sales_{today_date_str}.csv",
            mime="text/csv",
            use_container_width=True
        )
        
        df_heaven = all_backup_tx_display[all_backup_tx_display["الفرع"] == "Heaven"]
        if not df_heaven.empty:
            csv_heaven = df_heaven.to_csv(index=False).encode('utf-8-sig')
            col_b2.download_button(
                label="📥 مبيعات Heaven",
                data=csv_heaven,
                file_name=f"heaven_sales_{today_date_str}.csv",
                mime="text/csv",
                use_container_width=True
            )
            
        df_9a = all_backup_tx_display[all_backup_tx_display["الفرع"] == "9A"]
        if not df_9a.empty:
            csv_9a = df_9a.to_csv(index=False).encode('utf-8-sig')
            col_b3.download_button(
                label="📥 مبيعات 9A",
                data=csv_9a,
                file_name=f"9a_sales_{today_date_str}.csv",
                mime="text/csv",
                use_container_width=True
            )
            
    if not all_backup_exp.empty:
        csv_exp = all_backup_exp.to_csv(index=False).encode('utf-8-sig')
        col_b4.download_button(
            label="📥 تحميل كل المصروفات",
            data=csv_exp,
            file_name=f"all_expenses_{today_date_str}.csv",
            mime="text/csv",
            use_container_width=True
                )
