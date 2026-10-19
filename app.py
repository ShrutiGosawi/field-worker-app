import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import datetime
from io import BytesIO

st.set_page_config(page_title="Field Worker Tracker", layout="wide")

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

st.title("Worker Tracking & Analytics Portal")

# Connect to Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- CREATE SEPARATE PAGES/TABS ---
tab1, tab2 = st.tabs(["📋 Log Daily Activity", "🖥️ Manager Dashboard"])

# ==========================================
# TAB 1: WORKER DATA ENTRY FORM
# ==========================================
with tab1:
    st.header("Log Daily Activity")
    
    date_input = st.date_input("Date", datetime.date.today(), key="entry_date")
    worker = st.selectbox("Select Worker Name", WORKERS, key="entry_worker")

    fuel_already_claimed = False
    food_already_claimed = False

    try:
        df_worker_check = conn.read(worksheet=worker, ttl="0d")
        if not df_worker_check.empty:
            # Safely clean and convert history dates to text strings for validation lookup
            df_worker_check["Date"] = pd.to_datetime(df_worker_check["Date"]).dt.strftime('%Y-%m-%d')
            day_entries = df_worker_check[df_worker_check["Date"] == str(date_input)]
            
            if not day_entries.empty:
                max_fuel = pd.to_numeric(day_entries["Fuel Allowance"]).max()
                if max_fuel > 0:
                    fuel_already_claimed = True
                max_food = pd.to_numeric(day_entries["Food Allowance"]).max()
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
        
        submit = st.form_submit_button("Submit Entry")

    if submit:
        new_entry = pd.DataFrame([{
            "Date": str(date_input),
            "Worker Name": worker,
            "Event Type": event,
            "Fuel Allowance": float(fuel),
            "Food Allowance": float(food),
            "Status": status,
            "Activity": activity
        }])
        
        try:
            df_worker = conn.read(worksheet=worker, ttl="0d")
        except Exception:
            df_worker = pd.DataFrame(columns=["Date", "Worker Name", "Event Type", "Fuel Allowance", "Food Allowance", "Status", "Activity"])
        
        updated_worker_df = pd.concat([df_worker, new_entry], ignore_index=True)
        conn.update(worksheet=worker, data=updated_worker_df)
        st.success(f"Successfully saved entry for {worker}!")
        st.rerun()

# ==========================================
# TAB 2: CENTRAL MANAGER DASHBOARD (FIXED DATE HANDLING)
# ==========================================
with tab2:
    st.header("🖥️ All Field Workers Database View")
    
    if st.button("🔄 Clear Cache & Sync Fresh Google Sheets Data"):
        st.cache_data.clear()
        st.rerun()
        
    master_list = []
    
    # Compile history rows from all worker sheets
    for worker_name in WORKERS:
        try:
            w_df = conn.read(worksheet=worker_name, ttl="10m")
            if w_df is not None and not w_df.empty:
                # Force clean text string format for dates on import
                w_df["Date"] = pd.to_datetime(w_df["Date"]).dt.strftime('%Y-%m-%d')
                master_list.append(w_df)
        except Exception:
            continue
            
    if master_list:
        df_all_workers = pd.concat(master_list, ignore_index=True)
        
        st.divider()
        st.subheader("🔍 Filter Records")
        
        filter_col1, filter_col2 = st.columns(2)
        
        selected_dash_worker = filter_col1.selectbox(
            "Filter by Worker Name", 
            ["All Workers"] + WORKERS
        )
        
        # Pull drop-down items from clean string values array
        available_dates = sorted(df_all_workers["Date"].dropna().unique(), reverse=True)
        selected_dash_date = filter_col2.selectbox(
            "Filter by Particular Date", 
            ["All Dates"] + available_dates
        )
        
        # Apply data filtering actions
        df_filtered = df_all_workers.copy()
        
        if selected_dash_worker != "All Workers":
            df_filtered = df_filtered[df_filtered["Worker Name"] == selected_dash_worker]
            
        if selected_dash_date != "All Dates":
            df_filtered = df_filtered[df_filtered["Date"] == selected_dash_date]
            
        st.divider()
        
        # Render dynamic view only if the active filter returns data rows
        if not df_filtered.empty:
            # 1. Total Metrics Banners
            total_fuel = pd.to_numeric(df_filtered["Fuel Allowance"]).sum()
            total_food = pd.to_numeric(df_filtered["Food Allowance"]).sum()
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Logged Rows", len(df_filtered))
            col2.metric("Total Fuel Payouts", f"Rs. {total_fuel:,.2f}")
            col3.metric("Total Food Payouts", f"Rs. {total_food:,.2f}")
            
            # 2. Main Live Data Table Grid
            st.subheader("📋 Filtered Log History")
            st.dataframe(df_filtered.sort_values(by="Date", ascending=False), use_container_width=True)
        else:
            st.info("No records found matching this particular Worker and Date combination.")
        
        # 3. Master Excel Export Operation
        st.divider()
        st.subheader("📊 Export Complete Reports to Excel")
        
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df_all_workers.to_excel(writer, sheet_name="All_Logs", index=False)
            
            for worker_name in WORKERS:
                worker_data = df_all_workers[df_all_workers["Worker Name"] == worker_name]
                if not worker_data.empty:
                    worker_data.to_excel(writer, sheet_name=worker_name[:31], index=False)
                    
        st.download_button(
            label="📥 Download Comprehensive Multi-Tab Excel Workbook",
            data=buffer.getvalue(),
            file_name=f"company_master_report_{datetime.date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("No active data entries found in any Google Sheet worker tabs yet.")
