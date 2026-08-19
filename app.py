import streamlit as st
import pandas as pd
from datetime import datetime, date, timezone, timedelta
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine, text

# ----------------- EGYPT TIMEZONE SETUP (UTC+3) -----------------
EGYPT_TZ = timezone(timedelta(hours=3))

def get_egypt_now():
    return datetime.now(EGYPT_TZ)[span_1](start_span)[span_1](end_span)

def get_egypt_now_str():
    return get_egypt_now().strftime("%Y-%m-%d %H:%M:%S")[span_2](start_span)[span_2](end_span)

def get_egypt_today_str():
    # احتساب يوم العمل التشغيلي: يطرح 4 ساعات لضم ساعات الفجر (حتى 3:59 ص) لليوم السابق
    egypt_now = get_egypt_now()[span_3](start_span)[span_3](end_span)
    business_now = egypt_now - timedelta(hours=4)[span_4](start_span)[span_4](end_span)
    return business_now.strftime("%Y-%m-%d")[span_5](start_span)[span_5](end_span)

# ----------------- APP CONFIG -----------------
st.set_page_config(page_title="Photobooth Management System", page_icon="📸", layout="wide")[span_6](start_span)[span_6](end_span)

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)[span_7](start_span)[span_7](end_span)

# ----------------- DB SETUP -----------------
try:
    if "DATABASE_URL" in st.secrets:[span_8](start_span)[span_8](end_span)
        DB_URL = st.secrets["DATABASE_URL"][span_9](start_span)[span_9](end_span)
        IS_POSTGRES = True[span_10](start_span)[span_10](end_span)
    else:
        DB_URL = "sqlite:///photobooth.db[span_11](start_span)"[span_11](end_span)
        IS_POSTGRES = False[span_12](start_span)[span_12](end_span)
except Exception:
    DB_URL = "sqlite:///photobooth.db[span_13](start_span)"[span_13](end_span)
    IS_POSTGRES = False[span_14](start_span)[span_14](end_span)

engine = create_engine(DB_URL, pool_pre_ping=True)[span_15](start_span)[span_15](end_span)

def init_db():
    with engine.begin() as conn:[span_16](start_span)[span_16](end_span)
        if IS_POSTGRES:[span_17](start_span)[span_17](end_span)
            days_id_def = "id SERIAL PRIMARY KEY[span_18](start_span)"[span_18](end_span)
            tx_id_def = "id SERIAL PRIMARY KEY[span_19](start_span)"[span_19](end_span)
            inv_id_def = "id SERIAL PRIMARY KEY[span_20](start_span)"[span_20](end_span)
            audit_id_def = "id SERIAL PRIMARY KEY[span_21](start_span)"[span_21](end_span)
        else:
            days_id_def = "id INTEGER PRIMARY KEY AUTOINCREMENT[span_22](start_span)"[span_22](end_span)
            tx_id_def = "id INTEGER PRIMARY KEY AUTOINCREMENT[span_23](start_span)"[span_23](end_span)
            inv_id_def = "id INTEGER PRIMARY KEY AUTOINCREMENT[span_24](start_span)"[span_24](end_span)
            audit_id_def = "id INTEGER PRIMARY KEY AUTOINCREMENT[span_25](start_span)"[span_25](end_span)
            
        conn.execute(text(f'''
            CREATE TABLE IF NOT EXISTS days (
                {days_id_def},
                date TEXT UNIQUE NOT NULL
            )
        '''))[span_26](start_span)[span_26](end_span)
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
        '''))[span_27](start_span)[span_27](end_span)
        conn.execute(text(f'''
            CREATE TABLE IF NOT EXISTS inventory (
                {inv_id_def},
                timestamp TEXT NOT NULL,
                action_type TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                notes TEXT,
                branch TEXT NOT NULL
            )
        '''))[span_28](start_span)[span_28](end_span)
        conn.execute(text(f'''
            CREATE TABLE IF NOT EXISTS audit_logs (
                {audit_id_def},
                timestamp TEXT NOT NULL,
                branch TEXT NOT NULL,
                action_type TEXT NOT NULL,
                transaction_id INTEGER,
                details TEXT NOT NULL
            )
        '''))[span_29](start_span)[span_29](end_span)

init_db()[span_30](start_span)[span_30](end_span)

# ----------------- DB HELPER FUNCTIONS -----------------
def get_current_stock(branch: str):
    with engine.connect() as conn:[span_31](start_span)[span_31](end_span)
        result = conn.execute(
            text("SELECT COALESCE(SUM(quantity), 0) as total FROM inventory WHERE branch = :branch"), 
            {"branch": branch}
        ).fetchone()[span_32](start_span)[span_32](end_span)
        return result[0] if result else 0[span_33](start_span)[span_33](end_span)

def get_waste_count(branch: str = None):
    with engine.connect() as conn:[span_34](start_span)[span_34](end_span)
        if branch and branch != "الكل":[span_35](start_span)[span_35](end_span)
            result = conn.execute(
                text("SELECT ABS(COALESCE(SUM(quantity), 0)) as total FROM inventory WHERE action_type = 'waste' AND branch = :branch"),
                {"branch": branch}
            ).fetchone()[span_36](start_span)[span_36](end_span)
        else:
            result = conn.execute(
                text("SELECT ABS(COALESCE(SUM(quantity), 0)) as total FROM inventory WHERE action_type = 'waste'")
            ).fetchone()[span_37](start_span)[span_37](end_span)
        return result[0] if result else 0[span_38](start_span)[span_38](end_span)

def add_stock(branch: str, quantity: int, notes: str = ""):
    with engine.begin() as conn:[span_39](start_span)[span_39](end_span)
        conn.execute(text('''
            INSERT INTO inventory (timestamp, action_type, quantity, notes, branch)
            VALUES (:ts, 'restock', :qty, :notes, :branch)
        '''), {
            "ts": get_egypt_now_str(),
            "qty": quantity,
            "notes": notes,
            "branch": branch
        })[span_40](start_span)[span_40](end_span)

def record_waste(branch: str, quantity: int = 1, notes: str = "ورقة تالفة"):
    with engine.begin() as conn:[span_41](start_span)[span_41](end_span)
        conn.execute(text('''
            INSERT INTO inventory (timestamp, action_type, quantity, notes, branch)
            VALUES (:ts, 'waste', :qty, :notes, :branch)
        '''), {
            "ts": get_egypt_now_str(),
            "qty": -quantity,
            "notes": notes,
            "branch": branch
        })[span_42](start_span)[span_42](end_span)

def record_transaction(branch: str, prints_count: int, amount_paid: float):
    now_str = get_egypt_now_str()[span_43](start_span)[span_43](end_span)
    today_str = get_egypt_today_str()[span_44](start_span)[span_44](end_span)
    
    with engine.begin() as conn:[span_45](start_span)[span_45](end_span)
        row = conn.execute(text("SELECT id FROM days WHERE date = :date"), {"date": today_str}).fetchone()[span_46](start_span)[span_46](end_span)
        if not row:[span_47](start_span)[span_47](end_span)
            if IS_POSTGRES:[span_48](start_span)[span_48](end_span)
                res = conn.execute(text("INSERT INTO days (date) VALUES (:date) RETURNING id"), {"date": today_str}).fetchone()[span_49](start_span)[span_49](end_span)
                day_id = res[0][span_50](start_span)[span_50](end_span)
            else:
                conn.execute(text("INSERT INTO days (date) VALUES (:date)"), {"date": today_str})[span_51](start_span)[span_51](end_span)
                res = conn.execute(text("SELECT last_insert_rowid()")).fetchone()[span_52](start_span)[span_52](end_span)
                day_id = res[0][span_53](start_span)[span_53](end_span)
        else:
            day_id = row[0][span_54](start_span)[span_54](end_span)
            
        conn.execute(text('''
            INSERT INTO transactions (day_id, timestamp, prints_count, amount_paid, branch)
            VALUES (:day_id, :ts, :prints, :amount, :branch)
        '''), {
            "day_id": day_id,
            "ts": now_str,
            "prints": prints_count,
            "amount": amount_paid,
            "branch": branch
        })[span_55](start_span)[span_55](end_span)
        
        conn.execute(text('''
            INSERT INTO inventory (timestamp, action_type, quantity, notes, branch)
            VALUES (:ts, 'consumption', :qty, 'Transaction consumption', :branch)
        '''), {
            "ts": now_str,
            "qty": -prints_count,
            "branch": branch
        })[span_56](start_span)[span_56](end_span)

def delete_transaction(tx_id: int, branch: str):
    now_str = get_egypt_now_str()[span_57](start_span)[span_57](end_span)
    with engine.begin() as conn:[span_58](start_span)[span_58](end_span)
        tx = conn.execute(text("SELECT * FROM transactions WHERE id = :id AND branch = :branch"), {"id": tx_id, "branch": branch}).mappings().fetchone()[span_59](start_span)[span_59](end_span)
        if tx:[span_60](start_span)[span_60](end_span)
            conn.execute(text('''
                INSERT INTO inventory (timestamp, action_type, quantity, notes, branch)
                VALUES (:ts, 'restock', :qty, :notes, :branch)
            '''), {
                "ts": now_str,
                "qty": tx["prints_count"],
                "notes": f"استرجاع ورق لحذف المعاملة #{tx_id}",
                "branch": branch
            })[span_61](start_span)[span_61](end_span)
            conn.execute(text('''
                INSERT INTO audit_logs (timestamp, branch, action_type, transaction_id, details)
                VALUES (:ts, :branch, 'حذف', :tx_id, :details)
            '''), {
                "ts": now_str,
                "branch": branch,
                "tx_id": tx_id,
                "details": f"تم حذف العملية (الوقت: {tx['timestamp']} | الورق: {tx['prints_count']} | المبلغ: {tx['amount_paid']} ج.م)"
            })[span_62](start_span)[span_62](end_span)
            conn.execute(text("DELETE FROM transactions WHERE id = :id"), {"id": tx_id})[span_63](start_span)[span_63](end_span)
            return True[span_64](start_span)[span_64](end_span)
    return False[span_65](start_span)[span_65](end_span)

def update_transaction(tx_id: int, branch: str, new_prints: int, new_amount: float):
    now_str = get_egypt_now_str()[span_66](start_span)[span_66](end_span)
    with engine.begin() as conn:[span_67](start_span)[span_67](end_span)
        tx = conn.execute(text("SELECT * FROM transactions WHERE id = :id AND branch = :branch"), {"id": tx_id, "branch": branch}).mappings().fetchone()[span_68](start_span)[span_68](end_span)
        if tx:[span_69](start_span)[span_69](end_span)
            diff_prints = new_prints - tx["prints_count"][span_70](start_span)[span_70](end_span)
            if diff_prints != 0:[span_71](start_span)[span_71](end_span)
                conn.execute(text('''
                    INSERT INTO inventory (timestamp, action_type, quantity, notes, branch)
                    VALUES (:ts, 'consumption', :qty, :notes, :branch)
                '''), {
                    "ts": now_str,
                    "qty": -diff_prints,
                    "notes": f"تسوية فرق ورق لتعديل المعاملة #{tx_id}",
                    "branch": branch
                })[span_72](start_span)[span_72](end_span)
            conn.execute(text('''
                INSERT INTO audit_logs (timestamp, branch, action_type, transaction_id, details)
                VALUES (:ts, :branch, 'تعديل', :tx_id, :details)
            '''), {
                "ts": now_str,
                "branch": branch,
                "tx_id": tx_id,
                "details": f"تعديل من ({tx['prints_count']} ورق - {tx['amount_paid']} ج) إلى ({new_prints} ورق - {new_amount} ج)"
            })[span_73](start_span)[span_73](end_span)
            conn.execute(text('''
                UPDATE transactions 
                SET prints_count = :prints, amount_paid = :amount 
                WHERE id = :id
            '''), {
                "prints": new_prints,
                "amount": new_amount,
                "id": tx_id
            })[span_74](start_span)[span_74](end_span)
            return True[span_75](start_span)[span_75](end_span)
    return False[span_76](start_span)[span_76](end_span)

# ----------------- AUTHENTICATION -----------------
if 'logged_in' not in st.session_state:[span_77](start_span)[span_77](end_span)
    st.session_state.logged_in = False[span_78](start_span)[span_78](end_span)
if 'role' not in st.session_state:[span_79](start_span)[span_79](end_span)
    st.session_state.role = None[span_80](start_span)[span_80](end_span)
if 'branch' not in st.session_state:[span_81](start_span)[span_81](end_span)
    st.session_state.branch = None[span_82](start_span)[span_82](end_span)

def login():
    st.markdown("<h1 style='text-align: center;'>🔐 تسجيل الدخول للأنظمة</h1>", unsafe_allow_html=True)[span_83](start_span)[span_83](end_span)
    st.markdown("---")[span_84](start_span)[span_84](end_span)
    
    col1, col2, col3 = st.columns([1,2,1])[span_85](start_span)[span_85](end_span)
    with col2:[span_86](start_span)[span_86](end_span)
        with st.form("login_form"):[span_87](start_span)[span_87](end_span)
            password = st.text_input("أدخل كلمة المرور:", type="password")[span_88](start_span)[span_88](end_span)
            submit = st.form_submit_button("تسجيل الدخول", use_container_width=True)[span_89](start_span)[span_89](end_span)
            
            if submit:[span_90](start_span)[span_90](end_span)
                if password == "14161837":[span_91](start_span)[span_91](end_span)
                    st.session_state.logged_in = True[span_92](start_span)[span_92](end_span)
                    st.session_state.role = "employee[span_93](start_span)"[span_93](end_span)
                    st.session_state.branch = "Heaven[span_94](start_span)"[span_94](end_span)
                    st.rerun()[span_95](start_span)[span_95](end_span)
                elif password == "85879134":[span_96](start_span)[span_96](end_span)
                    st.session_state.logged_in = True[span_97](start_span)[span_97](end_span)
                    st.session_state.role = "employee[span_98](start_span)"[span_98](end_span)
                    st.session_state.branch = "9A[span_99](start_span)"[span_99](end_span)
                    st.rerun()[span_100](start_span)[span_100](end_span)
                elif password == "20072001":[span_101](start_span)[span_101](end_span)
                    st.session_state.logged_in = True[span_102](start_span)[span_102](end_span)
                    st.session_state.role = "admin[span_103](start_span)"[span_103](end_span)
                    st.session_state.branch = "All[span_104](start_span)"[span_104](end_span)
                    st.rerun()[span_105](start_span)[span_105](end_span)
                else:
                    st.error("كلمة المرور غير صحيحة!")[span_106](start_span)[span_106](end_span)

def logout():
    st.session_state.logged_in = False[span_107](start_span)[span_107](end_span)
    st.session_state.role = None[span_108](start_span)[span_108](end_span)
    st.session_state.branch = None[span_109](start_span)[span_109](end_span)

if not st.session_state.logged_in:[span_110](start_span)[span_110](end_span)
    login()[span_111](start_span)[span_111](end_span)
    st.stop()[span_112](start_span)[span_112](end_span)

# ----------------- SIDEBAR -----------------
st.sidebar.markdown(f"### 👋 مرحباً، {st.session_state.branch if st.session_state.role == 'employee' else 'المدير'}")[span_113](start_span)[span_113](end_span)
st.sidebar.button("🚪 تسجيل الخروج", on_click=logout, use_container_width=True)[span_114](start_span)[span_114](end_span)
st.sidebar.markdown("---")[span_115](start_span)[span_115](end_span)

role = st.session_state.role[span_116](start_span)[span_116](end_span)
branch = st.session_state.branch[span_117](start_span)[span_117](end_span)

# ================= 1. EMPLOYEE SCREEN =================
if role == "employee":[span_118](start_span)[span_118](end_span)
    current_stock = get_current_stock(branch)[span_119](start_span)[span_119](end_span)
    st.sidebar.metric(f"📦 رصيد الورق", f"{current_stock} ورقة")[span_120](start_span)[span_120](end_span)
    st.sidebar.caption(f"🕒 توقيت النظام: {get_egypt_now().strftime('%I:%M %p')}")[span_121](start_span)[span_121](end_span)
    st.sidebar.caption(f"📅 يوم العمل: {get_egypt_today_str()}")[span_122](start_span)[span_122](end_span)
    
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
    """, unsafe_allow_html=True)[span_123](start_span)[span_123](end_span)

    st.title(f"📸 فرع {branch} - المبيعات السريعة")[span_124](start_span)[span_124](end_span)
    st.caption("أزرار سريعة لتسجيل المبيعات وتتبع يوم العمل حتى 3:00 فجراً.")[span_125](start_span)[span_125](end_span)
    
    st.subheader("⚡ العمليات السريعة")[span_126](start_span)[span_126](end_span)
    
    # واجهة فرع Heaven المخصصة
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

    # واجهة فرع 9A المعتادة
    else:
        btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(4)[span_127](start_span)[span_127](end_span)
        with btn_col1:[span_128](start_span)[span_128](end_span)
            if st.button("🖼️ صورة فردي\n(50 ج - 1 ورقة)", use_container_width=True):[span_129](start_span)[span_129](end_span)
                if current_stock < 1:[span_130](start_span)[span_130](end_span)
                    st.error("⚠️ رصيد الورق غير كافٍ!")[span_131](start_span)[span_131](end_span)
                else:
                    record_transaction(branch, 1, 50.0)[span_132](start_span)[span_132](end_span)
                    st.success("✅ تم تسجيل البيع!")[span_133](start_span)[span_133](end_span)
                    st.rerun()[span_134](start_span)[span_134](end_span)
                    
        with btn_col2:[span_135](start_span)[span_135](end_span)
            if st.button("🎞️ كارت ثلاثي\n(90 ج - 2 ورقة)", use_container_width=True):[span_136](start_span)[span_136](end_span)
                if current_stock < 2:[span_137](start_span)[span_137](end_span)
                    st.error("⚠️ رصيد الورق غير كافٍ!")[span_138](start_span)[span_138](end_span)
                else:
                    record_transaction(branch, 2, 90.0)[span_139](start_span)[span_139](end_span)
                    st.success("✅ تم تسجيل البيع!")[span_140](start_span)[span_140](end_span)
                    st.rerun()[span_141](start_span)[span_141](end_span)
                    
        with btn_col3:[span_142](start_span)[span_142](end_span)
            if st.button("📸 كارت رباعي\n(120 ج - 3 ورقات)", use_container_width=True):[span_143](start_span)[span_143](end_span)
                if current_stock < 3:[span_144](start_span)[span_144](end_span)
                    st.error("⚠️ رصيد الورق غير كافٍ!")[span_145](start_span)[span_145](end_span)
                else:
                    record_transaction(branch, 3, 120.0)[span_146](start_span)[span_146](end_span)
                    st.success("✅ تم تسجيل البيع!")[span_147](start_span)[span_147](end_span)
                    st.rerun()[span_148](start_span)[span_148](end_span)

        with btn_col4:[span_149](start_span)[span_149](end_span)
            if st.button("🗑️ ورقة تالفة\n(خصم 1 ورقة)", use_container_width=True):[span_150](start_span)[span_150](end_span)
                if current_stock < 1:[span_151](start_span)[span_151](end_span)
                    st.error("⚠️ رصيد الورق فارغ بالفعل!")[span_152](start_span)[span_152](end_span)
                else:
                    record_waste(branch, 1, "تالف طباعة سريع")[span_153](start_span)[span_153](end_span)
                    st.warning("⚠️ تم خصم ورقة تالفة من المخزون!")[span_154](start_span)[span_154](end_span)
                    st.rerun()[span_155](start_span)[span_155](end_span)

    st.markdown("<br><hr><br>", unsafe_allow_html=True)[span_156](start_span)[span_156](end_span)
    col_manual, col_restock = st.columns(2)[span_157](start_span)[span_157](end_span)
    
    with col_manual:[span_158](start_span)[span_158](end_span)
        with st.expander("⚙️ إدخال يدوي", expanded=False):[span_159](start_span)[span_159](end_span)
            with st.form("manual_form", clear_on_submit=True):[span_160](start_span)[span_160](end_span)
                prints = st.number_input("عدد الورق المطبوع", min_value=1, max_value=50, value=None, step=1, placeholder="أدخل عدد الورق...")[span_161](start_span)[span_161](end_span)
                amount = st.number_input("المبلغ المدفوع", min_value=0.0, value=None, step=10.0, placeholder="أدخل المبلغ...")[span_162](start_span)[span_162](end_span)
                submit_btn = st.form_submit_button("✅ تسجيل يدوياً", use_container_width=True)[span_163](start_span)[span_163](end_span)
                
                if submit_btn:[span_164](start_span)[span_164](end_span)
                    if prints is None or amount is None:[span_165](start_span)[span_165](end_span)
                        st.error("⚠️ يرجى إدخال عدد الورق والمبلغ أولاً!")[span_166](start_span)[span_166](end_span)
                    elif current_stock < prints:[span_167](start_span)[span_167](end_span)
                        st.error("⚠️ رصيد الورق المتاح غير كافٍ!")[span_168](start_span)[span_168](end_span)
                    else:
                        record_transaction(branch, prints, amount)[span_169](start_span)[span_169](end_span)
                        st.success("تم التسجيل يدوياً!")[span_170](start_span)[span_170](end_span)
                        st.rerun()[span_171](start_span)[span_171](end_span)

    with col_restock:[span_172](start_span)[span_172](end_span)
        with st.expander("📦 إضافة ورق للمخزون", expanded=False):[span_173](start_span)[span_173](end_span)
            with st.form("restock_form", clear_on_submit=True):[span_174](start_span)[span_174](end_span)
                restock_qty = st.number_input("عدد الورق المضاف", min_value=1, max_value=5000, value=None, step=50, placeholder="أدخل الكمية...")[span_175](start_span)[span_175](end_span)
                notes = st.text_input("ملاحظات", "")[span_176](start_span)[span_176](end_span)
                restock_btn = st.form_submit_button("➕ تزويد المخزون", use_container_width=True)[span_177](start_span)[span_177](end_span)
                
                if restock_btn:[span_178](start_span)[span_178](end_span)
                    add_stock(branch, restock_qty, notes)[span_179](start_span)[span_179](end_span)
                    st.success("تم التزويد بنجاح!")[span_180](start_span)[span_180](end_span)
                    st.rerun()[span_181](start_span)[span_181](end_span)

    st.markdown("---")[span_182](start_span)[span_182](end_span)
    st.subheader("📋 عمليات يوم العمل الحالي (اليوم بالكامل)")[span_183](start_span)[span_183](end_span)
    
    with engine.connect() as conn:[span_184](start_span)[span_184](end_span)
        today_str = get_egypt_today_str()[span_185](start_span)[span_185](end_span)
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
        )[span_186](start_span)[span_186](end_span)
        
        if not today_tx.empty:[span_187](start_span)[span_187](end_span)
            display_user_tx = today_tx.rename(columns={
                'timestamp': 'الوقت',
                'prints_count': 'عدد الورق',
                'amount_paid': 'المبلغ (ج.م)'
            })
            st.dataframe(display_user_tx.drop(columns=['id']), use_container_width=True, hide_index=True)
            
            st.markdown("##### 🛠️ إدارة / تعديل / حذف عملية من اليوم")[span_188](start_span)[span_188](end_span)
            options = {f"عملية #{row['id']} - الساعة {row['timestamp'].split(' ')[1]} ({row['prints_count']} ورق | {row['amount_paid']} ج)": row['id'] for _, row in today_tx.iterrows()}
            selected_label = st.selectbox("اختر العملية للتحكم بها:", list(options.keys()))[span_189](start_span)[span_189](end_span)
            selected_id = options[selected_label][span_190](start_span)[span_190](end_span)
            selected_row = today_tx[today_tx['id'] == selected_id].iloc[0][span_191](start_span)[span_191](end_span)
            
            col_act1, col_act2 = st.columns(2)[span_192](start_span)[span_192](end_span)
            
            with col_act1:[span_193](start_span)[span_193](end_span)
                with st.expander("✏️ تعديل العملية المحددة", expanded=False):[span_194](start_span)[span_194](end_span)
                    with st.form("edit_form"):[span_195](start_span)[span_195](end_span)
                        new_p = st.number_input("تعديل عدد الورق:", min_value=1, max_value=50, value=int(selected_row['prints_count']), step=1)[span_196](start_span)[span_196](end_span)
                        new_a = st.number_input("تعديل المبلغ (ج.م):", min_value=0.0, value=float(selected_row['amount_paid']), step=10.0)[span_197](start_span)[span_197](end_span)
                        edit_btn = st.form_submit_button("حفظ التعديلات", use_container_width=True)[span_198](start_span)[span_198](end_span)
                        if edit_btn:[span_199](start_span)[span_199](end_span)
                            if update_transaction(selected_id, branch, new_p, new_a):[span_200](start_span)[span_200](end_span)
                                st.success("تم تعديل العملية وضبط المخزون وسجل المراقبة بنجاح!")[span_201](start_span)[span_201](end_span)
                                st.rerun()[span_202](start_span)[span_202](end_span)

            with col_act2:[span_203](start_span)[span_203](end_span)
                with st.expander("🗑️ حذف العملية المحددة", expanded=False):[span_204](start_span)[span_204](end_span)
                    st.warning(f"هل أنت متأكد من حذف العملية #{selected_id}؟ سيتم استرجاع الورق للمخزون وتسجيل الحذف.")[span_205](start_span)[span_205](end_span)
                    if st.button("تأكيد الحذف نهائياً", type="primary", use_container_width=True):[span_206](start_span)[span_206](end_span)
                        if delete_transaction(selected_id, branch):[span_207](start_span)[span_207](end_span)
                            st.success("تم مسح العملية واسترجاع الورق بنجاح!")[span_208](start_span)[span_208](end_span)
                            st.rerun()[span_209](start_span)[span_209](end_span)
        else:
            st.info("لا توجد عمليات مسجلة في يوم العمل الحالي حتى الآن.")[span_210](start_span)[span_210](end_span)

# ================= 2. ADMIN DASHBOARD =================
elif role == "admin":[span_211](start_span)[span_211](end_span)
    st.title("📊 لوحة تحكم الإدارة (Admin Analytics)")[span_212](start_span)[span_212](end_span)
    
    st.sidebar.subheader("🏢 فلتر الفرع")[span_213](start_span)[span_213](end_span)
    selected_branch = st.sidebar.selectbox("اختر الفرع للتحليل:", ["الكل", "Heaven", "9A"])[span_214](start_span)[span_214](end_span)
    
    branch_filter_tx = "[span_215](start_span)"[span_215](end_span)
    branch_params = {}[span_216](start_span)[span_216](end_span)
    if selected_branch != "الكل":[span_217](start_span)[span_217](end_span)
        branch_filter_tx = "WHERE t.branch = :branch[span_218](start_span)"[span_218](end_span)
        branch_params = {"branch": selected_branch}[span_219](start_span)[span_219](end_span)
        
    with engine.connect() as conn:[span_220](start_span)[span_220](end_span)
        query_all_tx = f'''
            SELECT t.*, d.date 
            FROM transactions t
            JOIN days d ON t.day_id = d.id
            {branch_filter_tx}
            ORDER BY t.timestamp ASC
        '''
        all_tx_df = pd.read_sql_query(text(query_all_tx), conn, params=branch_params)[span_221](start_span)[span_221](end_span)
        
        if not all_tx_df.empty:[span_222](start_span)[span_222](end_span)
            days_df = all_tx_df.groupby('date').agg(
                first_customer_time=('timestamp', 'min'),
                last_customer_time=('timestamp', 'max'),
                total_customers=('id', 'count'),
                total_prints=('prints_count', 'sum'),
                total_revenue=('amount_paid', 'sum')
            ).reset_index()[span_223](start_span)[span_223](end_span)
        else:
            days_df = pd.DataFrame()[span_224](start_span)[span_224](end_span)

    if not days_df.empty:[span_225](start_span)[span_225](end_span)
        min_date = pd.to_datetime(days_df['date']).dt.date.min()[span_226](start_span)[span_226](end_span)
        max_date = pd.to_datetime(days_df['date']).dt.date.max()[span_227](start_span)[span_227](end_span)
        
        st.sidebar.markdown("---")[span_228](start_span)[span_228](end_span)
        st.sidebar.subheader("📅 فلاتر التاريخ")[span_229](start_span)[span_229](end_span)
        date_range = st.sidebar.date_input(
            "اختر الفترة الزمنية للتحليل:",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )[span_230](start_span)[span_230](end_span)
        
        if len(date_range) == 2:[span_231](start_span)[span_231](end_span)
            start_dt, end_dt = date_range[span_232](start_span)[span_232](end_span)
            mask_days = (pd.to_datetime(days_df['date']).dt.date >= start_dt) & (pd.to_datetime(days_df['date']).dt.date <= end_dt)[span_233](start_span)[span_233](end_span)
            mask_tx = (pd.to_datetime(all_tx_df['date']).dt.date >= start_dt) & (pd.to_datetime(all_tx_df['date']).dt.date <= end_dt)[span_234](start_span)[span_234](end_span)
            
            filtered_days = days_df.loc[mask_days].copy()[span_235](start_span)[span_235](end_span)
            filtered_tx = all_tx_df.loc[mask_tx].copy()[span_236](start_span)[span_236](end_span)
        else:
            filtered_days = days_df.copy()[span_237](start_span)[span_237](end_span)
            filtered_tx = all_tx_df.copy()[span_238](start_span)[span_238](end_span)

        if selected_branch == "الكل":[span_239](start_span)[span_239](end_span)
            stock_heaven = get_current_stock("Heaven")[span_240](start_span)[span_240](end_span)
            stock_9a = get_current_stock("9A")[span_241](start_span)[span_241](end_span)
            waste_heaven = get_waste_count("Heaven")[span_242](start_span)[span_242](end_span)
            waste_9a = get_waste_count("9A")[span_243](start_span)[span_243](end_span)
            stock_display = f"Heaven: {stock_heaven} | 9A: {stock_9a}[span_244](start_span)"[span_244](end_span)
            waste_display = f"Heaven: {waste_heaven} | 9A: {waste_9a}[span_245](start_span)"[span_245](end_span)
        else:
            stock_display = f"{get_current_stock(selected_branch)} ورقة[span_246](start_span)"[span_246](end_span)
            waste_display = f"{get_waste_count(selected_branch)} ورقة[span_247](start_span)"[span_247](end_span)

        # Top KPIs
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)[span_248](start_span)[span_248](end_span)
        total_rev_all = filtered_days['total_revenue'].sum() if not filtered_days.empty else 0[span_249](start_span)[span_249](end_span)
        total_prints_all = filtered_days['total_prints'].sum() if not filtered_days.empty else 0[span_250](start_span)[span_250](end_span)
        total_cust_all = filtered_days['total_customers'].sum() if not filtered_days.empty else 0[span_251](start_span)[span_251](end_span)
        
        kpi1.metric("💰 إجمالي الإيرادات", f"{total_rev_all:,.0f} ج.م")[span_252](start_span)[span_252](end_span)
        kpi2.metric("👥 إجمالي الزبائن", f"{total_cust_all:,}")[span_253](start_span)[span_253](end_span)
        kpi3.metric("🖨️ الورق المطبوع", f"{total_prints_all:,} ورقة")[span_254](start_span)[span_254](end_span)
        kpi4.metric("🗑️ إجمالي التالف", waste_display)[span_255](start_span)[span_255](end_span)
        
        st.metric("📦 المخزون المتبقي حالياً", stock_display)[span_256](start_span)[span_256](end_span)
        
        st.markdown("---")[span_257](start_span)[span_257](end_span)
        
        if not filtered_days.empty:[span_258](start_span)[span_258](end_span)
            ARABIC_DAYS = {
                "Monday": "الإثنين", "Tuesday": "الثلاثاء", "Wednesday": "الأربعاء",
                "Thursday": "الخميس", "Friday": "الجمعة", "Saturday": "السبت", "Sunday": "الأحد"
            }[span_259](start_span)[span_259](end_span)
            
            filtered_tx['hour'] = pd.to_datetime(filtered_tx['timestamp']).dt.hour[span_260](start_span)[span_260](end_span)
            peak_hours = filtered_tx.groupby(['date', 'hour'])['id'].count().reset_index()[span_261](start_span)[span_261](end_span)
            peak_hours = peak_hours.sort_values(['date', 'id'], ascending=[True, False])[span_262](start_span)[span_262](end_span)
            peak_hours = peak_hours.drop_duplicates(subset=['date'])[span_263](start_span)[span_263](end_span)
            peak_hours = peak_hours.rename(columns={'hour': 'peak_hour'})[['date', 'peak_hour']][span_264](start_span)[span_264](end_span)
            
            behavior_df = filtered_days.merge(peak_hours, on='date', how='left')[span_265](start_span)[span_265](end_span)
            behavior_df['date_obj'] = pd.to_datetime(behavior_df['date'])[span_266](start_span)[span_266](end_span)
            behavior_df['day_name'] = behavior_df['date_obj'].dt.day_name().map(ARABIC_DAYS)[span_267](start_span)[span_267](end_span)
            
            def extract_time(ts):
                if pd.isna(ts): return "-[span_268](start_span)"[span_268](end_span)
                return pd.to_datetime(ts).strftime('%I:%M %p')[span_269](start_span)[span_269](end_span)
            
            behavior_df['first_time'] = behavior_df['first_customer_time'].apply(extract_time)[span_270](start_span)[span_270](end_span)
            behavior_df['last_time'] = behavior_df['last_customer_time'].apply(extract_time)[span_271](start_span)[span_271](end_span)
            behavior_df['peak_str'] = behavior_df['peak_hour'].apply(lambda x: f"{int(x)}:00" if pd.notna(x) else "-")[span_272](start_span)[span_272](end_span)
            
            st.subheader(f"📋 سلوك الزبائن اليومي ({selected_branch})")[span_273](start_span)[span_273](end_span)
            display_df = behavior_df[['date', 'day_name', 'first_time', 'last_time', 'peak_str', 'total_customers', 'total_revenue']][span_274](start_span)[span_274](end_span)
            display_df.columns = ['تاريخ يوم العمل', 'اليوم', 'أول زبون', 'آخر زبون', 'ساعة الذروة', 'عدد الزبائن', 'الإيراد (ج.م)'][span_275](start_span)[span_275](end_span)
            st.dataframe(display_df, use_container_width=True, hide_index=True)[span_276](start_span)[span_276](end_span)
            
            col_chart1, col_chart2 = st.columns(2)[span_277](start_span)[span_277](end_span)
            
            with col_chart1:[span_278](start_span)[span_278](end_span)
                st.subheader("📉 الإيرادات والزبائن خلال الفترة")[span_279](start_span)[span_279](end_span)
                fig = go.Figure()[span_280](start_span)[span_280](end_span)
                fig.add_trace(go.Scatter(
                    x=filtered_days['date'], y=filtered_days['total_revenue'],
                    mode='lines+markers', name='الإيراد',
                    line=dict(color='#00CC96', width=3)
                ))[span_281](start_span)[span_281](end_span)
                fig.add_trace(go.Bar(
                    x=filtered_days['date'], y=filtered_days['total_customers'],
                    name='عدد الزبائن', yaxis='y2',
                    marker_color='rgba(99, 110, 250, 0.5)'
                ))[span_282](start_span)[span_282](end_span)
                fig.update_layout(
                    yaxis=dict(title='الإيراد (ج.م)'),
                    yaxis2=dict(title='الزبائن', overlaying='y', side='right', showgrid=False),
                    hovermode="x unified",
                    legend=dict(orientation="h", y=1.1)
                )[span_283](start_span)[span_283](end_span)
                st.plotly_chart(fig, use_container_width=True)[span_284](start_span)[span_284](end_span)
                
            with col_chart2:[span_285](start_span)[span_285](end_span)
                st.subheader("📅 الإقبال حسب أيام الأسبوع")[span_286](start_span)[span_286](end_span)
                weekday_stats = behavior_df.groupby('day_name').agg({'total_customers': 'sum'}).reset_index()[span_287](start_span)[span_287](end_span)
                day_order = ["السبت", "الأحد", "الإثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة"][span_288](start_span)[span_288](end_span)
                weekday_stats['day_name'] = pd.Categorical(weekday_stats['day_name'], categories=day_order, ordered=True)[span_289](start_span)[span_289](end_span)
                weekday_stats = weekday_stats.sort_values('day_name')[span_290](start_span)[span_290](end_span)
                
                fig_week = px.bar(weekday_stats, x='day_name', y='total_customers', 
                                  labels={'day_name': 'اليوم', 'total_customers': 'عدد الزبائن'},
                                  color='total_customers', color_continuous_scale='Blues')[span_291](start_span)[span_291](end_span)
                st.plotly_chart(fig_week, use_container_width=True)[span_292](start_span)[span_292](end_span)
            
            st.subheader("🔥 ساعات الذروة الإجمالية في هذه الفترة")[span_293](start_span)[span_293](end_span)
            if not filtered_tx.empty:[span_294](start_span)[span_294](end_span)
                hourly = filtered_tx.groupby('hour')['id'].count().reset_index().rename(columns={'id': 'الزيارات'})[span_295](start_span)[span_295](end_span)
                hourly['hour_str'] = hourly['hour'].apply(lambda x: f"{x}:00")[span_296](start_span)[span_296](end_span)
                fig_hour = px.bar(hourly, x='hour_str', y='الزيارات', color='الزيارات',
                                  labels={'hour_str': 'الساعة'}, color_continuous_scale='Sunset')[span_297](start_span)[span_297](end_span)
                st.plotly_chart(fig_hour, use_container_width=True)[span_298](start_span)[span_298](end_span)
        else:
            st.warning("لا توجد بيانات مسجلة في الفترة المحددة.")[span_299](start_span)[span_299](end_span)
    else:
        st.info("لا توجد بيانات كافية لعرض الرسوم البيانية بعد.")[span_300](start_span)[span_300](end_span)

    # --- AUDIT LOGS SECTION FOR ADMIN ---
    st.markdown("---")[span_301](start_span)[span_301](end_span)
    st.subheader("🕵️ سجل المراقبة والتعديلات (Audit Logs)")[span_302](start_span)[span_302](end_span)
    st.caption("سجل مفصل يوضح كل عملية تم حذفها أو تعديلها من قبل الموظفين وتوقيتها الدقيق.")[span_303](start_span)[span_303](end_span)
    
    with engine.connect() as conn:[span_304](start_span)[span_304](end_span)
        audit_filter = "[span_305](start_span)"[span_305](end_span)
        audit_params = {}[span_306](start_span)[span_306](end_span)
        if selected_branch != "الكل":[span_307](start_span)[span_307](end_span)
            audit_filter = "WHERE branch = :branch[span_308](start_span)"[span_308](end_span)
            audit_params = {"branch": selected_branch}[span_309](start_span)[span_309](end_span)
            
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

    # --- BACKUP SECTION ---
    st.markdown("---")[span_310](start_span)[span_310](end_span)
    st.subheader("📥 النسخ الاحتياطي للبيانات (Backup)")[span_311](start_span)[span_311](end_span)
    st.caption("تقدر تحمل كل بيانات المبيعات بتاعتك في أي وقت كملف إكسيل (CSV) عشان تحتفظ بيها على جهازك.")[span_312](start_span)[span_312](end_span)
    
    with engine.connect() as conn:[span_313](start_span)[span_313](end_span)
        all_backup_tx = pd.read_sql_query(text('''
            SELECT t.timestamp, d.date, t.prints_count, t.amount_paid, t.branch
            FROM transactions t
            JOIN days d ON t.day_id = d.id
            ORDER BY t.timestamp DESC
        '''), conn)
        
    if not all_backup_tx.empty:[span_314](start_span)[span_314](end_span)
        all_backup_tx_display = all_backup_tx.rename(columns={
            'timestamp': 'الوقت',
            'date': 'تاريخ يوم العمل',
            'prints_count': 'عدد الورق',
            'amount_paid': 'المبلغ (ج.م)',
            'branch': 'الفرع'
        })
        col_b1, col_b2, col_b3 = st.columns(3)[span_315](start_span)[span_315](end_span)
        today_date_str = get_egypt_today_str()[span_316](start_span)[span_316](end_span)
        
        csv_all = all_backup_tx_display.to_csv(index=False).encode('utf-8-sig')
        col_b1.download_button(
            label="📥 تحميل المبيعات مجمعة (الكل)",
            data=csv_all,
            file_name=f"all_branches_backup_{today_date_str}.csv",
            mime="text/csv",
            use_container_width=True
        )[span_317](start_span)[span_317](end_span)
        
        df_heaven = all_backup_tx_display[all_backup_tx_display["الفرع"] == "Heaven"]
        if not df_heaven.empty:[span_318](start_span)[span_318](end_span)
            csv_heaven = df_heaven.to_csv(index=False).encode('utf-8-sig')[span_319](start_span)[span_319](end_span)
            col_b2.download_button(
                label="📥 مبيعات فرع Heaven",
                data=csv_heaven,
                file_name=f"heaven_backup_{today_date_str}.csv",
                mime="text/csv",
                use_container_width=True
            )[span_320](start_span)[span_320](end_span)
            
        df_9a = all_backup_tx_display[all_backup_tx_display["الفرع"] == "9A"]
        if not df_9a.empty:[span_321](start_span)[span_321](end_span)
            csv_9a = df_9a.to_csv(index=False).encode('utf-8-sig')[span_322](start_span)[span_322](end_span)
            col_b3.download_button(
                label="📥 مبيعات فرع 9A",
                data=csv_9a,
                file_name=f"9a_backup_{today_date_str}.csv",
                mime="text/csv",
                use_container_width=True
            )[span_323](start_span)[span_323](end_span)
