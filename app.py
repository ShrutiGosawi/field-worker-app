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
    
    # Date and Worker selection inside the form tab
    date_input = st.date_input("Date", datetime.date.today())
    worker = st.selectbox("Select Worker Name", WORKERS)

    fuel_already_claimed = False
    food_already_claimed = False

    # Fetch active worker data for live validation lookup
    try:
        df_worker_check = conn.read(worksheet=worker, ttl="0d")
        if not df_worker_check.empty:
            day_entries = df_worker_check[df_worker_check["Date"].astype(str) == str(date_input)]
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
# TAB 2: CENTRAL MANAGER DASHBOARD
# ==========================================
with tab2:
    st.header("🖥️ All Field Workers Database View")
    
    # Button to compile all worker data down from Google Sheets tabs
    if st.button("🔄 Refresh Master Dashboard Board"):
        st.rerun()
        
    master_list = []
    
    # Read each individual tab and stack them together
    for worker_name in WORKERS:
        try:
            w_df = conn.read(worksheet=worker_name, ttl="0d")
            if not w_df.empty:
                master_list.append(w_df)
        except Exception:
            continue
            
    if master_list:
        # Combine all separate dataframes into one comprehensive view
        df_all_workers = pd.concat(master_list, ignore_index=True)
        
        # 1. Total Metrics Banners
        total_fuel = pd.to_numeric(df_all_workers["Fuel Allowance"]).sum()
        total_food = pd.to_numeric(df_all_workers["Food Allowance"]).sum()
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Logged Rows", len(df_all_workers))
        col2.metric("Total Fuel Payouts", f"${total_fuel:,.2f}")
        col3.metric("Total Food Payouts", f"${total_food:,.2f}")
        
        # 2. Main Live Data Table showing everyone grouped chronologically
        st.subheader("📋 Comprehensive Log History")
        st.dataframe(df_all_workers.sort_values(by="Date", ascending=False), use_container_width=True)
        
        # 3. Dedicated Excel Generation Panel
        st.divider()
        st.subheader("📊 Export Reports to Excel")
        
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            # Sheet 1: Master All_Logs list inside Excel file
            df_all_workers.to_excel(writer, sheet_name="All_Logs", index=False)
            
            # Dynamic Worker Sheet tabs generation inside same download
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
