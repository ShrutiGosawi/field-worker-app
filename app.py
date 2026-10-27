import streamlit as st
import pandas as pd
import datetime
from io import BytesIO

st.set_page_config(page_title="Field Worker Tracker", layout="wide")

# 🔑 PASSWORDS LOCK DEFINITIONS Matrix
APP_PASSWORD = "Manager2026"

# --- ONLY YOUR 7 ACTIVE TEAM MEMBER NAMES ---
WORKERS = [
    "Anand", 
    "Amit", 
    "Faisal", 
    "Sohan", 
    "Deepika", 
    "Dishant", 
    "Nitish"
]

EVENTS = ["Site Visit", "Delivery", "Maintenance", "Client Meeting", "Other"]

st.title("Worker Tracking & Analytics Portal (PostgreSQL Engine)")

# Connect natively to your local PostgreSQL Database container
conn = st.connection("sql")

# Ensure structural relation database tables exist on server startup init initialization
for w in WORKERS:
    t_name = str(w).lower()
    conn.query(f"""
        CREATE TABLE IF NOT EXISTS {t_name} (
            id SERIAL PRIMARY KEY,
            date TEXT,
            worker_name TEXT,
            event_type TEXT,
            fuel_allowance NUMERIC,
            food_allowance NUMERIC,
            status TEXT,
            activity TEXT,
            client TEXT
        );
    """, ttl="0d")

# --- CREATE SEPARATE PAGES/TABS ---
tab1, tab2 = st.tabs(["📋 Log Daily Activity", "🖥️ Manager Dashboard"])

# ==========================================
# TAB 1: WORKER DATA ENTRY FORM (PASSWORD PROTECTED)
# ==========================================
with tab1:
    st.header("Log Daily Activity")
    
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        user_password = st.text_input("Enter Password to Access the Form", type="password")
        if st.button("Unlock Form"):
            if user_password == APP_PASSWORD:
                st.session_state.authenticated = True
                st.success("Form Unlocked Successfully!")
                st.rerun()
            else:
                st.error("Incorrect Password. Please try again.")
    else:
        if st.button("🔒 Lock Form / Logout"):
            st.session_state.authenticated = False
            st.rerun()
            
        st.divider()
        
        date_input = st.date_input("Date", datetime.date.today(), key="entry_date")
        worker = st.selectbox("Select Worker Name", WORKERS, key="entry_worker")

        fuel_already_claimed = False
        food_already_claimed = False
        t_name = str(worker).lower()

        try:
            # Query history for the selected date straight from the PostgreSQL engine
            day_entries = conn.query(f"SELECT * FROM {t_name} WHERE date = :date", params={"date": str(date_input)}, ttl="0d")
            
            if not day_entries.empty:
                max_fuel = pd.to_numeric(day_entries["fuel_allowance"], errors='coerce').max()
                if max_fuel > 0:
                    fuel_already_claimed = True
                max_food = pd.to_numeric(day_entries["food_allowance"], errors='coerce').max()
                if max_food > 0:
                    food_already_claimed = True
        except Exception:
            pass

        if fuel_already_claimed and not food_already_claimed:
            st.warning(f"ℹ️ {worker} has already claimed Fuel Allowance for today. Food Allowance is still open.")
        elif food_already_claimed and not fuel_already_claimed:
            st.warning(f"ℹ️ {worker} has already claimed Food Allowance for today. Fuel Allowance is still open.")
        elif fuel_already_claimed and food_already_claimed:
            st.error(f"⚠️ Both Fuel and Food allowances for {worker} have already been claimed for today.")

        with st.form("activity_form", clear_on_submit=True):
            event = st.selectbox("Event Type", EVENTS)
            
            if fuel_already_claimed:
                fuel = st.number_input("Fuel Allowance Amount", value=0.0, disabled=True)
            else:
                fuel = st.number_input("Fuel Allowance Amount", min_value=0.0, step=5.0)
                
            if food_already_claimed:
                food = st.number_input("Food Allowance Amount", value=0.0, disabled=True)
            else:
                food = st.number_input("Food Allowance Amount", min_value=0.0, step=5.0)
                
            status = st.radio("Work Status", ["Completed", "Pending"], horizontal=True)
            activity = st.text_input("Describe Your Activity", placeholder="Enter notes or task details here...")
            client = st.text_input("Client Name", placeholder="Enter the client or company name here...")
            
            submit = st.form_submit_button("Submit Entry")

    if submit:
        # Write clean rows straight into relational SQL tables
        with conn.session as session:
            session.execute(
                f"""
                INSERT INTO {t_name} (date, worker_name, event_type, fuel_allowance, food_allowance, status, activity, client)
                VALUES (:date, :worker_name, :event_type, :fuel_allowance, :food_allowance, :status, :activity, :client);
                """,
                {
                    "date": str(date_input),
                    "worker_name": worker,
                    "event_type": event,
                    "fuel_allowance": float(fuel),
                    "food_allowance": float(food),
                    "status": status,
                    "activity": activity,
                    "client": client
                }
            )
            session.commit()
            
        st.cache_data.clear() # Clear dashboard layout state memory
        st.success(f"Successfully saved entry for {worker} to PostgreSQL database!")
        st.rerun()

# ==========================================
# TAB 2: CENTRAL MANAGER DASHBOARD (RELATIONAL AGGREGATION)
# ==========================================
with tab2:
    st.header("🖥️ All Field Workers Database View")
    
    if st.button("🔄 Clear Cache & Sync Fresh Database Records"):
        st.cache_data.clear()
        st.rerun()
        
    master_list = []
    
    # Read each matching user table and compile them inside system memory arrays
    for worker_name in WORKERS:
        try:
            w_df = conn.query(f"SELECT * FROM {str(worker_name).lower()};", ttl="5m")
            if w_df is not None and not w_df.empty:
                master_list.append(w_df)
        except Exception:
            continue
            
    if master_list:
        df_all_workers = pd.concat(master_list, ignore_index=True)
        # Standardize column visualization header metrics
        df_all_workers.columns = [str(c).strip().lower() for c in df_all_workers.columns]
        
        st.divider()
        st.subheader("🔍 Filter Records")
        
        filter_col1, filter_col2 = st.columns(2)
        
        selected_dash_worker = filter_col1.selectbox(
            "Filter by Worker Name", 
            ["All Workers"] + WORKERS
        )
        
        available_dates = sorted(df_all_workers["date"].dropna().unique(), reverse=True)
        selected_dash_date = filter_col2.selectbox(
            "Filter by Particular Date", 
            ["All Dates"] + available_dates
        )
        
        df_filtered = df_all_workers.copy()
        
        if selected_dash_worker != "All Workers":
            df_filtered = df_filtered[df_filtered["worker_name"] == selected_dash_worker]
            
        if selected_dash_date != "All Dates":
            df_filtered = df_filtered[df_filtered["date"] == selected_dash_date]
            
        st.divider()
        
        total_fuel = pd.to_numeric(df_filtered["fuel_allowance"], errors='coerce').sum()
        total_food = pd.to_numeric(df_filtered["food_allowance"], errors='coerce').sum()
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Logged Rows", len(df_filtered))
        col2.metric("Total Fuel Payouts", f"Rs. {total_fuel:,.2f}")
        col3.metric("Total Food Payouts", f"Rs. {total_food:,.2f}")
        
        if not df_filtered.empty:
            st.subheader("📋 Filtered Log History")
            display_cols = ["date", "worker_name", "event_type", "fuel_allowance", "food_allowance", "status", "activity", "client"]
            st.dataframe(df_filtered[display_cols].sort_values(by="date", ascending=False), use_container_width=True)
        else:
            st.info("No records found matching this particular Worker and Date filter setup.")
        
        st.divider()
        st.subheader("📊 Export Complete Reports to Excel")
        
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df_all_workers.to_excel(writer, sheet_name="All_Logs", index=False)
            
            for worker_name in WORKERS:
                worker_data = df_all_workers[df_all_workers["worker_name"] == worker_name]
                if not worker_data.empty:
                    worker_data.to_excel(writer, sheet_name=worker_name[:31], index=False)
                    
        st.download_button(
            label="📥 Download Comprehensive Multi-Tab Excel Workbook",
            data=buffer.getvalue(),
            file_name=f"company_master_report_{datetime.date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("No active relational records tracked inside your server database tables yet.")
