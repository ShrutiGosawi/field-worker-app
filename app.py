import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import datetime
from io import BytesIO

st.set_page_config(page_title="Field Worker Tracker", layout="centered")

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

st.title("Worker Data Collection App")

# Connect to Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FORM SECTION ---
st.header("📋 Log Daily Activity")

# Date and Worker selection placed outside the form for live verification lookup
date_input = st.date_input("Date", datetime.date.today())
worker = st.selectbox("Select Worker Name", WORKERS)

# Track allowance statuses independently
fuel_already_claimed = False
food_already_claimed = False

# Fetch active worker data once to use for validation and dashboard rendering
df_worker_display = pd.DataFrame()
try:
    df_worker_display = conn.read(worksheet=worker, ttl="0d")
    if not df_worker_display.empty:
        # Filter history for only the selected date
        day_entries = df_worker_display[df_worker_display["Date"].astype(str) == str(date_input)]
        
        if not day_entries.empty:
            # Check Fuel Allowance history for today
            max_fuel = pd.to_numeric(day_entries["Fuel Allowance"]).max()
            if max_fuel > 0:
                fuel_already_claimed = True
                
            # Check Food Allowance history for today
            max_food = pd.to_numeric(day_entries["Food Allowance"]).max()
            if max_food > 0:
                food_already_claimed = True
except Exception:
    pass

# Display clear notification banners based on what has been claimed
if fuel_already_claimed and not food_already_claimed:
    st.warning(f"ℹ️ {worker} has already claimed Fuel Allowance for today. Food Allowance is still open.")
elif food_already_claimed and not fuel_already_claimed:
    st.warning(f"ℹ️ {worker} has already claimed Food Allowance for today. Fuel Allowance is still open.")
elif fuel_already_claimed and food_already_claimed:
    st.error(f"⚠️ Both Fuel and Food allowances for {worker} have already been claimed for today.")

with st.form("activity_form", clear_on_submit=True):
    event = st.selectbox("Event Type", EVENTS)
    
    # Handle Fuel Field Independently
    if fuel_already_claimed:
        fuel = st.number_input("Fuel Allowance Amount", value=0.0, disabled=True, help="Fuel already claimed today.")
    else:
        fuel = st.number_input("Fuel Allowance Amount", min_value=0.0, step=5.0)
        
    # Handle Food Field Independently
    if food_already_claimed:
        food = st.number_input("Food Allowance Amount", value=0.0, disabled=True, help="Food already claimed today.")
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

# --- LIVE DASHBOARD DISPLAY SECTION ---
st.divider()
st.header(f"🖥️ Live Dashboard View: {worker}")

if not df_worker_display.empty:
    st.subheader(f"All Logged Entries inside {worker}'s Sheet")
    # Displays the entire matching row array directly from the selected worker's Google Sheet tab
    st.dataframe(df_worker_display, use_container_width=True)
else:
    st.info(f"No entry rows found inside the database for {worker} yet.")

# --- EXPORT SECTION ---
st.divider()
st.header("📊 Export Reports")

if st.button("📥 Prepare Excel Workbook"):
    try:
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            if not df_worker_display.empty:
                df_worker_display.to_excel(writer, sheet_name=str(worker)[:31], index=False)
                
                st.download_button(
                    label=f"Click to Download {worker}_report.xlsx",
                    data=buffer.getvalue(),
                    file_name=f"{worker}_report_{datetime.date.today()}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.info(f"No logged data historical rows found for {worker} yet.")
    except Exception as e:
        st.error("Google database busy. Please wait 10 seconds and click Prepare button again.")
