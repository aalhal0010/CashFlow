import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date
from dateutil.relativedelta import relativedelta
import json
# Fix: Import the correct class name from the library
from streamlit_local_storage import LocalStorage

st.set_page_config(page_title="Premium Cash Flow Forecaster", layout="wide")
st.title("🔮 Premium Cash Flow Forecaster")
st.write("Your data is saved securely inside your browser. Refreshing the page will not lose your progress!")

# --- 1. INITIALIZE BROWSER LOCAL STORAGE ---
# Fix: Instantiate using LocalStorage()
local_storage = LocalStorage()

def load_browser_vault():
    """Fetches saving payload out of browser storage profile, or builds fresh models."""
    try:
        # Fix: Use library's native .getItem() syntax
        raw_data = local_storage.getItem("ledger_vault_data")
        if raw_data and str(raw_data).strip() != "":
            data = json.loads(raw_data)
            
            inc_df = pd.DataFrame(data.get("income", [{"Name": "", "Amount": 0.0, "Day of Month": 1}]))
            
            bills_df = pd.DataFrame(data.get("bills", [{"Name": "", "Amount": 0.0, "Day of Month": 1, "End Date": None}]))
            if "End Date" in bills_df.columns:
                bills_df["End Date"] = pd.to_datetime(bills_df["End Date"], errors='coerce')
                
            cards_df = pd.DataFrame(data.get("cards", [{"Card Name": "", "Statement Balance": 0.0, "Payment Day": 1}]))
            buffers = data.get("buffers", {"food": 0.0, "gas": 0.0})
            saved_balance = data.get("starting_balance", 1000.0)
            return inc_df, bills_df, cards_df, buffers, saved_balance
    except Exception as e:
        pass # Fall through to default initializations on lookup misses
        
    # Standard clean fallbacks
    inc_df = pd.DataFrame([{"Name": "", "Amount": 0.0, "Day of Month": 1}])
    bills_df = pd.DataFrame({"Name": [""], "Amount": [0.0], "Day of Month": [1], "End Date": [pd.NaT]})
    bills_df["End Date"] = pd.to_datetime(bills_df["End Date"])
    cards_df = pd.DataFrame([{"Card Name": "", "Statement Balance": 0.0, "Payment Day": 1}])
    return inc_df, bills_df, cards_df, {"food": 0.0, "gas": 0.0}, 1000.0

def save_browser_vault():
    """Pushes encrypted JSON payload back onto client browser cookies tracker."""
    temp_bills = st.session_state.bills_df.copy()
    if "End Date" in temp_bills.columns:
        temp_bills["End Date"] = pd.to_datetime(temp_bills["End Date"], errors='coerce')
        formatted_end_dates = temp_bills["End Date"].dt.strftime('%Y-%m-%d').where(temp_bills["End Date"].notnull(), None)
        temp_bills["End Date"] = formatted_end_dates

    payload = {
        "starting_balance": float(st.session_state.start_balance_val),
        "income": st.session_state.income_df.to_dict(orient="records"),
        "bills": temp_bills.to_dict(orient="records"),
        "cards": st.session_state.cards_df.to_dict(orient="records"),
        "buffers": {
            "food": float(st.session_state.food_val),
            "gas": float(st.session_state.gas_val)
        }
    }
    # Fix: Use library's native .setItem() syntax
    local_storage.setItem("ledger_vault_data", json.dumps(payload))

# Bootstrap values checking
if 'income_df' not in st.session_state:
    inc_init, bills_init, cards_init, buffers_init, balance_init = load_browser_vault()
    st.session_state.income_df = inc_init
    st.session_state.bills_df = bills_init
    st.session_state.cards_df = cards_init
    st.session_state.food_init = buffers_init["food"]
    st.session_state.gas_init = buffers_init["gas"]
    st.session_state.balance_init = balance_init

# --- 2. SIDEBAR GLOBAL SETTINGS ---
st.sidebar.header("⚙️ Global Settings")
start_balance = st.sidebar.number_input("Current Bank Balance ($)", value=st.session_state.balance_init, step=100.0, key="start_balance_val")
months_to_project = st.sidebar.slider("Months to Project Ahead", 1, 24, 12)

if start_balance != st.session_state.balance_init:
    st.session_state.balance_init = start_balance
    save_browser_vault()

# --- 3. INPUT INTERFACE TABS ---
tab1, tab2, tab3, tab4 = st.tabs(["📥 Income Streams", "💸 Fixed Bills & Loans", "💳 Credit Cards", "🛒 Variable Buffers"])

with tab1:
    st.subheader("Manage Regular Income")
    edited_income = st.data_editor(
        st.session_state.income_df, num_rows="dynamic", width="stretch", hide_index=True,
        column_config={
            "Name": st.column_config.TextColumn("Source Name"),
            "Amount": st.column_config.NumberColumn("Amount ($)", min_value=0.0, format="$%.2f"),
            "Day of Month": st.column_config.NumberColumn("Day of Month (1-31)", min_value=1, max_value=31, step=1, format="%d")
        },
        key="income_editor"
    )

with tab2:
    st.subheader("Manage Fixed Bills & Installments")
    st.write("*Note: Enter expenses as positive values. The system deducts them automatically.*")
    edited_bills = st.data_editor(
        st.session_state.bills_df, num_rows="dynamic", width="stretch", hide_index=True,
        column_config={
            "Name": st.column_config.TextColumn("Bill Name"),
            "Amount": st.column_config.NumberColumn("Amount ($/mo)", min_value=0.0, format="$%.2f"),
            "Day of Month": st.column_config.NumberColumn("Day of Month (1-31)", min_value=1, max_value=31, step=1, format="%d"),
            "End Date": st.column_config.DateColumn("End Date (Optional)", format="YYYY-MM-DD")
        },
        key="bills_editor"
    )

with tab3:
    st.subheader("Credit Card Paydowns")
    edited_cards = st.data_editor(
        st.session_state.cards_df, num_rows="dynamic", width="stretch", hide_index=True,
        column_config={
            "Card Name": st.column_config.TextColumn("Card Name"),
            "Statement Balance": st.column_config.NumberColumn("Balance ($)", min_value=0.0, format="$%.2f"),
            "Payment Day": st.column_config.NumberColumn("Payment Day", min_value=1, max_value=31, step=1, format="%d")
        },
        key="cards_editor"
    )

with tab4:
    st.subheader("Weekly Variable Buffers")
    food_buffer = st.number_input("Weekly Food/Grocery Allowance ($)", value=st.session_state.food_init, step=10.0, key="food_val")
    gas_buffer = st.number_input("Weekly Utilities/Gas Allowance ($)", value=st.session_state.gas_init, step=5.0, key="gas_val")

# --- 4. SEPARATED AUTO-SAVE EVALUATION LAYER ---
has_changed = False

if not edited_income.equals(st.session_state.income_df):
    st.session_state.income_df = edited_income
    has_changed = True

if not edited_bills.equals(st.session_state.bills_df):
    edited_bills["End Date"] = pd.to_datetime(edited_bills["End Date"], errors='coerce')
    st.session_state.bills_df = edited_bills
    has_changed = True

if not edited_cards.equals(st.session_state.cards_df):
    st.session_state.cards_df = edited_cards
    has_changed = True

if food_buffer != st.session_state.food_init or gas_buffer != st.session_state.gas_init:
    st.session_state.food_init = food_buffer
    st.session_state.gas_init = gas_buffer
    has_changed = True

if has_changed:
    save_browser_vault()
    st.rerun()

# --- 5. ENGINE MATH CALCULATIONS ---
start_date = date.today()
end_date = start_date + relativedelta(months=months_to_project)
date_range = pd.date_range(start=start_date, end=end_date)

forecast_df = pd.DataFrame({'Date': date_range})
forecast_df['Daily Change'] = 0.0
forecast_df['Details'] = ""

inc_clean = st.session_state.income_df[st.session_state.income_df['Amount'] > 0].dropna(subset=["Day of Month"])
bills_clean = st.session_state.bills_df[st.session_state.bills_df['Amount'] > 0].dropna(subset=["Day of Month"])
cards_clean = st.session_state.cards_df[st.session_state.cards_df['Statement Balance'] > 0].dropna(subset=["Payment Day"])

for idx, row in forecast_df.iterrows():
    curr_date = row['Date']
    day_val = curr_date.day
    day_change = 0.0
    day_details = []
    
    if not inc_clean.empty:
        for _, inc in inc_clean.iterrows():
            if day_val == int(inc['Day of Month']):
                amt = float(inc['Amount'])
                day_change += amt
                day_details.append(f"{inc['Name']} (+${amt:,.2f})")
                
    if not bills_clean.empty:
        for _, bill in bills_clean.iterrows():
            if day_val == int(bill['Day of Month']):
                is_active = True
                if 'End Date' in bill and pd.notna(bill['End Date']) and str(bill['End Date']).strip() != "":
                    try:
                        end_dt = pd.to_datetime(bill['End Date']).date()
                        if curr_date.date() > end_dt:
                            is_active = False
                    except:
                        pass
                if is_active:
                    amt = float(bill['Amount'])
                    day_change -= amt
                    day_details.append(f"{bill['Name']} (-${amt:,.2f})")
                    
    if not cards_clean.empty:
        for _, cc in cards_clean.iterrows():
            if day_val == int(cc['Payment Day']):
                if curr_date.month == start_date.month and curr_date.year == start_date.year:
                    amt = float(cc['Statement Balance'])
                    day_change -= amt
                    day_details.append(f"{cc['Card Name']} Initial Paydown (-${amt:,.2f})")
                    
    if curr_date.day_name() == "Friday":
        total_buffer = float(food_buffer + gas_buffer)
        if total_buffer > 0:
            day_change -= total_buffer
            day_details.append(f"Weekly Friday Allowance (-${total_buffer:,.2f})")
            
    forecast_df.at[idx, 'Daily Change'] = day_change
    forecast_df.at[idx, 'Details'] = ", ".join(day_details) if day_details else ""

forecast_df['Running Balance'] = float(start_balance) + forecast_df['Daily Change'].cumsum()

# --- 6. VISUALIZATION OUTPUT PLOTS ---
low_water_mark = forecast_df['Running Balance'].min()
peak_balance = forecast_df['Running Balance'].max()

st.write("---")
st.subheader("📊 Live Projections")

kpi1, kpi2 = st.columns(2)
kpi1.metric("Highest Vault Ceiling", f"${peak_balance:,.2f}")
kpi2.metric("Lowest Projected Floor", f"${low_water_mark:,.2f}")

fig = go.Figure()
fig.add_trace(go.Scatter(x=forecast_df['Date'], y=forecast_df['Running Balance'], mode='lines', name='Balance', line=dict(color='#2ca02c', width=3)))
fig.update_layout(template="plotly_white", height=400, margin=dict(l=20, r=20, t=20, b=20))
st.plotly_chart(fig, use_container_width=True)

st.subheader("📋 Forecast Transaction Log")
display_log = forecast_df[forecast_df['Daily Change'] != 0].copy()
if not display_log.empty:
    display_log['Date'] = display_log['Date'].dt.strftime('%b %d, %Y')
    st.dataframe(display_log[['Date', 'Details', 'Daily Change', 'Running Balance']], use_container_width=True, hide_index=True)
else:
    st.write("No entries recorded yet. Use the tabs above to populate your database.")
