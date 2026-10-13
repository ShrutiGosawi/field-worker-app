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
    
    # Try reading from that specific worker's tab on Google Sheets
    try:
        # worksheet=worker tells it to read only that worker's specific tab name
        df_worker = conn.read(worksheet=worker, ttl="0d")
    except Exception:
        # If the worker's tab doesn't exist yet, start a fresh one with headers
        df_worker = pd.DataFrame(columns=["Date", "Worker Name", "Event Type", "Fuel Allowance", "Food Allowance", "Status", "Activity"])
    
    # Combine existing worker rows with the new entry
    updated_worker_df = pd.concat([df_worker, new_entry], ignore_index=True)
    
    # Save directly back to that worker's private sheet tab
    conn.update(worksheet=worker, data=updated_worker_df)
    st.success(f"Successfully saved data directly to {worker}'s Google Sheet!")
    st.rerun()

# --- EXPORT SECTION ---
st.divider()
st.header("📊 Export Reports")

# Build a multi-tab Excel download directly from the individual Google tabs
buffer = BytesIO()
has_data = False

with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
    for worker_name in WORKERS:
        try:
            # Read each worker's sheet from Google
            worker_df = conn.read(worksheet=worker_name, ttl="0d")
            if not worker_df.empty:
                # Write to corresponding tab in downloaded Excel
                worker_df.to_excel(writer, sheet_name=worker_name[:31], index=False)
                has_data = True
        except Exception:
            continue

if has_data:
    st.download_button(
        label="📥 Download Separated Excel Sheets",
        data=buffer.getvalue(),
        file_name=f"separated_worker_report_{datetime.date.today()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.info("No data logged in Google Sheets yet. Submit an entry to activate downloading.")
