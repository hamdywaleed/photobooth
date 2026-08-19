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
# Streamlit secrets lookup for Cloud deployment, fallback to SQLite locally
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
        else:
            days_id_def = "id INTEGER PRIMARY KEY AUTOINCREMENT"
            tx_id_def = "id INTEGER PRIMARY KEY AUTOINCREMENT"
            inv_id_def = "id INTEGER PRIMARY KEY AUTOINCREMENT"
            
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

init_db()

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
    col_manual, col_restock = st.columns(2)
    
    with col_manual:
        with st.expander("⚙️ إدخال يدوي", expanded=False):
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

    st.markdown("---")
    st.subheader("📋 آخر 5 عمليات مسجلة في يوم العمل الحالي")
    with engine.connect() as conn:
        today_str = get_egypt_today_str()
        today_tx = pd.read_sql_query(
            text('''
            SELECT t.timestamp as "الوقت", t.prints_count as "عدد الورق", t.amount_paid as "المبلغ (ج.م)"
            FROM transactions t
            JOIN days d ON t.day_id = d.id
            WHERE d.date = :date AND t.branch = :branch
            ORDER BY t.timestamp DESC LIMIT 5
            '''), 
            conn, 
            params={"date": today_str, "branch": branch}
        )
        if not today_tx.empty:
            st.dataframe(today_tx, use_container_width=True, hide_index=True)
        else:
            st.info("لا توجد عمليات مسجلة في يوم العمل الحالي حتى الآن.")

# ================= 2. ADMIN DASHBOARD =================
elif role == "admin":
    st.title("📊 لوحة تحكم الإدارة (Admin Analytics)")
    
    st.sidebar.subheader("🏢 فلتر الفرع")
    selected_branch = st.sidebar.selectbox("اختر الفرع للتحليل:", ["الكل", "Heaven", "9A"])
    
    branch_filter_tx = ""
    branch_params = {}
    if selected_branch != "الكل":
        branch_filter_tx = "WHERE t.branch = :branch"
        branch_params = {"branch": selected_branch}
        
    with engine.connect() as conn:
        query_all_tx = f'''
            SELECT t.*, d.date 
            FROM transactions t
            JOIN days d ON t.day_id = d.id
            {branch_filter_tx}
            ORDER BY t.timestamp ASC
        '''
        all_tx_df = pd.read_sql_query(text(query_all_tx), conn, params=branch_params)
        
        if not all_tx_df.empty:
            days_df = all_tx_df.groupby('date').agg(
                first_customer_time=('timestamp', 'min'),
                last_customer_time=('timestamp', 'max'),
                total_customers=('id', 'count'),
                total_prints=('prints_count', 'sum'),
                total_revenue=('amount_paid', 'sum')
            ).reset_index()
        else:
            days_df = pd.DataFrame()

    if not days_df.empty:
        # Date Filter
        min_date = pd.to_datetime(days_df['date']).dt.date.min()
        max_date = pd.to_datetime(days_df['date']).dt.date.max()
        
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
            mask_days = (pd.to_datetime(days_df['date']).dt.date >= start_dt) & (pd.to_datetime(days_df['date']).dt.date <= end_dt)
            mask_tx = (pd.to_datetime(all_tx_df['date']).dt.date >= start_dt) & (pd.to_datetime(all_tx_df['date']).dt.date <= end_dt)
            
            filtered_days = days_df.loc[mask_days].copy()
            filtered_tx = all_tx_df.loc[mask_tx].copy()
        else:
            filtered_days = days_df.copy()
            filtered_tx = all_tx_df.copy()

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

        # Top KPIs (4 columns now with Waste)
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        total_rev_all = filtered_days['total_revenue'].sum() if not filtered_days.empty else 0
        total_prints_all = filtered_days['total_prints'].sum() if not filtered_days.empty else 0
        total_cust_all = filtered_days['total_customers'].sum() if not filtered_days.empty else 0
        
        kpi1.metric("💰 إجمالي الإيرادات", f"{total_rev_all:,.0f} ج.م")
        kpi2.metric("👥 إجمالي الزبائن", f"{total_cust_all:,}")
        kpi3.metric("🖨️ الورق المطبوع", f"{total_prints_all:,} ورقة")
        kpi4.metric("🗑️ إجمالي التالف", waste_display)
        
        st.metric("📦 المخزون المتبقي حالياً", stock_display)
        
        st.markdown("---")
        
        if not filtered_days.empty:
            ARABIC_DAYS = {
                "Monday": "الإثنين", "Tuesday": "الثلاثاء", "Wednesday": "الأربعاء",
                "Thursday": "الخميس", "Friday": "الجمعة", "Saturday": "السبت", "Sunday": "الأحد"
            }
            
            filtered_tx['hour'] = pd.to_datetime(filtered_tx['timestamp']).dt.hour
            peak_hours = filtered_tx.groupby(['date', 'hour'])['id'].count().reset_index()
            peak_hours = peak_hours.sort_values(['date', 'id'], ascending=[True, False])
            peak_hours = peak_hours.drop_duplicates(subset=['date'])
            peak_hours = peak_hours.rename(columns={'hour': 'peak_hour'})[['date', 'peak_hour']]
            
            behavior_df = filtered_days.merge(peak_hours, on='date', how='left')
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
                    x=filtered_days['date'], y=filtered_days['total_revenue'],
                    mode='lines+markers', name='الإيراد',
                    line=dict(color='#00CC96', width=3)
                ))
                fig.add_trace(go.Bar(
                    x=filtered_days['date'], y=filtered_days['total_customers'],
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
            if not filtered_tx.empty:
                hourly = filtered_tx.groupby('hour')['id'].count().reset_index().rename(columns={'id': 'الزيارات'})
                hourly['hour_str'] = hourly['hour'].apply(lambda x: f"{x}:00")
                fig_hour = px.bar(hourly, x='hour_str', y='الزيارات', color='الزيارات',
                                  labels={'hour_str': 'الساعة'}, color_continuous_scale='Sunset')
                st.plotly_chart(fig_hour, use_container_width=True)
        else:
            st.warning("لا توجد بيانات مسجلة في الفترة المحددة.")
    else:
        st.info("لا توجد بيانات كافية لعرض الرسوم البيانية بعد.")

    # --- BACKUP SECTION ---
    st.markdown("---")
    st.subheader("📥 النسخ الاحتياطي للبيانات (Backup)")
    st.caption("تقدر تحمل كل بيانات المبيعات بتاعتك في أي وقت كملف إكسيل (CSV) عشان تحتفظ بيها على جهازك.")
    
    with engine.connect() as conn:
        all_backup_tx = pd.read_sql_query(text('''
            SELECT t.timestamp as "الوقت", d.date as "تاريخ يوم العمل", t.prints_count as "عدد الورق", 
                   t.amount_paid as "المبلغ (ج.م)", t.branch as "الفرع"
            FROM transactions t
            JOIN days d ON t.day_id = d.id
            ORDER BY t.timestamp DESC
        '''), conn)
        
    if not all_backup_tx.empty:
        col_b1, col_b2, col_b3 = st.columns(3)
        today_date_str = get_egypt_today_str()
        
        csv_all = all_backup_tx.to_csv(index=False).encode('utf-8-sig')
        col_b1.download_button(
            label="📥 تحميل المبيعات مجمعة (الكل)",
            data=csv_all,
            file_name=f"all_branches_backup_{today_date_str}.csv",
            mime="text/csv",
            use_container_width=True
        )
        
        df_heaven = all_backup_tx[all_backup_tx["الفرع"] == "Heaven"]
        if not df_heaven.empty:
            csv_heaven = df_heaven.to_csv(index=False).encode('utf-8-sig')
            col_b2.download_button(
                label="📥 مبيعات فرع Heaven",
                data=csv_heaven,
                file_name=f"heaven_backup_{today_date_str}.csv",
                mime="text/csv",
                use_container_width=True
            )
            
        df_9a = all_backup_tx[all_backup_tx["الفرع"] == "9A"]
        if not df_9a.empty:
            csv_9a = df_9a.to_csv(index=False).encode('utf-8-sig')
            col_b3.download_button(
                label="📥 مبيعات فرع 9A",
                data=csv_9a,
                file_name=f"9a_backup_{today_date_str}.csv",
                mime="text/csv",
                use_container_width=True
            )
