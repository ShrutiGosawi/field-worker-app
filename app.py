import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import datetime
from io import BytesIO

st.set_page_config(page_title="Field Worker Tracker", layout="centered")

WORKERS = [f"Worker {i}" for i in range(1, 13)]
EVENTS = ["Site Visit", "Delivery", "Maintenance", "Client Meeting", "Other"]

st.title("Worker Data Collection App")

# Connect to Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# Read existing data
try:
    df = conn.read(ttl="0d") # ttl="0d" ensures it always fetches fresh data instantly
except Exception:
    df = pd.DataFrame(columns=["Date", "Worker Name", "Event Type", "Fuel Allowance", "Food Allowance", "Status"])

# --- FORM SECTION ---
st.header("📋 Log Daily Activity")
with st.form("activity_form", clear_on_submit=True):
    date_input = st.date_input("Date", datetime.date.today())
    worker = st.selectbox("Select Worker Name", WORKERS)
    event = st.selectbox("Event Type", EVENTS)
    fuel = st.number_input("Fuel Allowance Amount", min_value=0.0, step=5.0)
    food = st.number_input("Food Allowance Amount", min_value=0.0, step=5.0)
    status = st.radio("Work Status", ["Completed", "Pending"], horizontal=True)
    
    submit = st.form_submit_button("Submit Entry")

if submit:
    new_entry = pd.DataFrame([{
        "Date": str(date_input),
        "Worker Name": worker,
        "Event Type": event,
        "Fuel Allowance": float(fuel),
        "Food Allowance": float(food),
        "Status": status
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
        # Sheet 1: Raw Data
        df.to_excel(writer, sheet_name="All_Logs", index=False)
        
        # Sheet 2: Worker-wise & Date-wise Summary Pivot
        try:
            worker_pivot = df.pivot_table(
                index="Worker Name", 
                columns="Date", 
                values="Event Type", 
                aggfunc="count", 
                fill_value=0
            )
            worker_pivot.to_excel(writer, sheet_name="Worker_vs_Date_Events")
        except Exception:
            pass
        
        # Sheet 3: Financial Totals
        try:
            df["Fuel Allowance"] = pd.to_numeric(df["Fuel Allowance"])
            df["Food Allowance"] = pd.to_numeric(df["Food Allowance"])
            financial_summary = df.groupby("Worker Name")[["Fuel Allowance", "Food Allowance"]].sum()
            financial_summary.to_excel(writer, sheet_name="Financial_Summary")
        except Exception:
            pass

    st.download_button(
        label="📥 Download Structured Excel Sheet",
        data=buffer.getvalue(),
        file_name=f"field_worker_report_{datetime.date.today()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.info("No data logged in Google Sheets yet. Submit an entry to activate downloading.")
