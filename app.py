import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import datetime
from io import BytesIO

st.set_page_config(page_title="Field Worker Tracker", layout="centered")

# --- CUSTOM WORKER NAMES LIST ---
WORKERS = [
    "Anand", 
    "Amit", 
    "Faisal", 
    "Sohan", 
    "Deepika", 
    "Dishant", 
    "Nitish",
    "Worker 8",   
    "Worker 9",
    "Worker 10",
    "Worker 11",
    "Worker 12"
]

EVENTS = ["Site Visit", "Delivery", "Maintenance", "Client Meeting", "Other"]

st.title("Worker Data Collection App")

# Connect to Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# Read existing data
try:
    df = conn.read(ttl="0d") # ttl="0d" ensures it always fetches fresh data instantly
except Exception:
    df = pd.DataFrame(columns=["Date", "Worker Name", "Event Type", "Fuel Allowance", "Food Allowance", "Status", "Activity"])

# --- FORM SECTION ---
st.header("📋 Log Daily Activity")
with st.form("activity_form", clear_on_submit=True):
    date_input = st.date_input("Date", datetime.date.today())
    worker = st.selectbox("Select Worker Name", WORKERS)
    event = st.selectbox("Event Type", EVENTS)
    fuel = st.number_input("Fuel Allowance Amount", min_value=0.0, step=5.0)
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
    
    # Combine old data with new entry
    updated_df = pd.concat([df, new_entry], ignore_index=True)
    
    # Update Google Sheet
    conn.update(data=updated_df)
    st.success(f"Successfully saved data for {worker}!")
    st.rerun()

# --- EXPORT SECTION ---
st.divider()
st.header("📊 Export Reports")

if not df.empty:
    st.subheader("Current Database View")
    st.dataframe(df)
    
    # Build Excel in memory
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        # Sheet 1: Master Log (All Workers together)
        df.to_excel(writer, sheet_name="All_Logs", index=False)
        
        # Dynamic Generation: Split each worker into their own individual sheet tab
        for worker_name in WORKERS:
            # Filter the master data to get only rows for this specific worker
            worker_data = df[df["Worker Name"] == worker_name]
            
            # Only create a sheet tab if the worker actually has logged data
            if not worker_data.empty:
                # Excel tab names are limited to 31 characters max
                safe_tab_name = str(worker_name)[:31]
                worker_data.to_excel(writer, sheet_name=safe_tab_name, index=False)
        
        # Summary Sheet 1: Worker-wise & Date-wise Summary Pivot Table
        try:
            worker_pivot = df.pivot_table(
                index="Worker Name", 
                columns="Date", 
                values="Event Type", 
                aggfunc="count", 
                fill_value=0
            )
            worker_pivot.to_excel(writer, sheet_name="Summary_Pivot")
        except Exception:
            pass
        
        # Summary Sheet 2: Financial Totals Breakdown
        try:
            df["Fuel Allowance"] = pd.to_numeric(df["Fuel Allowance"])
            df["Food Allowance"] = pd.to_numeric(df["Food Allowance"])
            financial_summary = df.groupby("Worker Name")[["Fuel Allowance", "Food Allowance"]].sum()
            financial_summary.to_excel(writer, sheet_name="Financial_Summary")
        except Exception:
            pass

    st.download_button(
        label="📥 Download Separated Excel Sheets",
        data=buffer.getvalue(),
        file_name=f"separated_worker_report_{datetime.date.today()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.info("No data logged in Google Sheets yet. Submit an entry to activate downloading.")
