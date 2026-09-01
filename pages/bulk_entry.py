import streamlit as st
import pandas as pd
from datetime import date, timedelta
from sqlalchemy import create_engine, text

st.set_page_config(page_title="أداة استرجاع البيانات القديمة", page_icon="⏳", layout="centered")

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

# ----------------- SESSION STATE -----------------
if 'bulk_date' not in st.session_state:
    st.session_state.bulk_date = date(2026, 6, 12)

# ----------------- HELPER FUNCTION -----------------
def insert_bulk_day(branch: str, target_date_str: str, prints_count: int, amount_paid: float):
    tx_timestamp = f"{target_date_str} 21:00:00"
    with engine.begin() as conn:
        row = conn.execute(text("SELECT id FROM days WHERE date = :date"), {"date": target_date_str}).fetchone()
        if not row:
            if IS_POSTGRES:
                res = conn.execute(text("INSERT INTO days (date) VALUES (:date) RETURNING id"), {"date": target_date_str}).fetchone()
                day_id = res[0]
            else:
                conn.execute(text("INSERT INTO days (date) VALUES (:date)"), {"date": target_date_str})
                res = conn.execute(text("SELECT last_insert_rowid()")).fetchone()
                day_id = res[0]
        else:
            day_id = row[0]
            
        conn.execute(text('''
            INSERT INTO transactions (day_id, timestamp, prints_count, amount_paid, branch)
            VALUES (:day_id, :ts, :prints, :amount, :branch)
        '''), {
            "day_id": day_id,
            "ts": tx_timestamp,
            "prints": prints_count,
            "amount": amount_paid,
            "branch": branch
        })

# ----------------- UI -----------------
st.title("⏳ تفريغ البيانات القديمة (دون المساس بالمخزون)")
st.caption("أداة مخصصة لإدخال الأيام المتتالية القديمة وتجاوز الإجازات بسرعة.")

selected_branch = st.selectbox("اختر الفرع المراد إدخال بياناته:", ["Heaven", "9A"])

AR_DAYS = {
    "Monday": "الإثنين", "Tuesday": "الثلاثاء", "Wednesday": "الأربعاء",
    "Thursday": "الخميس", "Friday": "الجمعة", "Saturday": "السبت", "Sunday": "الأحد"
}
curr_date = st.session_state.bulk_date
day_name_ar = AR_DAYS.get(curr_date.strftime("%A"), "")
curr_date_str = curr_date.strftime("%Y-%m-%d")

st.markdown(f"### 📅 التاريخ الحالي: **{day_name_ar} {curr_date_str}**")

with st.form("quick_bulk_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        prints = st.number_input("عدد الورق المطبوع في هذا اليوم:", min_value=0, max_value=5000, value=None, step=1, placeholder="أدخل عدد الورق...")
    with col2:
        amount = st.number_input("إجمالي المبلغ (ج.م):", min_value=0.0, value=None, step=10.0, placeholder="أدخل المبلغ...")
        
    submitted = st.form_submit_button("💾 حفظ اليوم والانتقال لليوم التالي ⬅️", use_container_width=True)
    
    if submitted:
        if prints is None or amount is None:
            st.error("⚠️ يرجى إدخال البيانات أولاً!")
        else:
            insert_bulk_day(selected_branch, curr_date_str, int(prints), float(amount))
            st.session_state.bulk_date += timedelta(days=1)
            st.success(f"✅ تم حفظ {curr_date_str} والانتقال لليوم التالي.")
            st.rerun()

col_btn1, col_btn2 = st.columns(2)
with col_btn1:
    if st.button("🏖️ هذا اليوم كان إجازة (تخطي لليوم التالي) ⏭️", use_container_width=True):
        st.session_state.bulk_date += timedelta(days=1)
        st.warning(f"⏩ تم تخطي يوم {curr_date_str}.")
        st.rerun()

with col_btn2:
    new_date = st.date_input("تعديل التاريخ يدوي:", value=st.session_state.bulk_date)
    if new_date != st.session_state.bulk_date:
        st.session_state.bulk_date = new_date
        st.rerun()

st.markdown("---")
st.subheader("📋 آخر 10 أيام تم تسجيلها في هذا الفرع")
with engine.connect() as conn:
    df_logged = pd.read_sql_query(
        text('''
        SELECT d.date as "التاريخ", t.prints_count as "عدد الورق", t.amount_paid as "المبلغ (ج.م)"
        FROM transactions t
        JOIN days d ON t.day_id = d.id
        WHERE t.branch = :branch
        ORDER BY d.date DESC LIMIT 10
        '''),
        conn,
        params={"branch": selected_branch}
    )
    if not df_logged.empty:
        st.dataframe(df_logged, use_container_width=True, hide_index=True)
    else:
        st.info("لا توجد بيانات مسجلة بعد.")

