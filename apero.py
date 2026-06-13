import os
# Force Streamlit to bypass WebSocket restrictions that cause cloud freezing
os.environ["STREAMLIT_SERVER_ENABLE_WEBSOCKET_COMPRESSION"] = "false"
os.environ["STREAMLIT_SERVER_ENABLE_CORS"] = "false"

import streamlit as plt  # Standardized alias mapping
import streamlit as st
import sqlite3
import random

# ---- Layout Optimization Settings ----
st.set_page_config(
    page_title="APERO GROTTE NIMES - Smart Wallet & Tracker v3.8",
    page_icon="🍻",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ---- Smart Path Fix for SQLite ----
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(SCRIPT_DIR, "apero_grotte_nimes_web.db")

def get_db_connection():
    return sqlite3.connect(DB_FILE, isolation_level=None)

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            name TEXT PRIMARY KEY,
            color TEXT,
            joined_index INTEGER
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT,
            amount REAL,
            paid_by TEXT,
            participants TEXT,
            is_deposit INTEGER
        )
    """)
    conn.close()

init_db()

# ---- Authentication State Logic ----
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.markdown("<h2 style='text-align: center;'>🔒 APERO GROTTE NIMES</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Please enter the group password to access the app tracker:</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        password_input = st.text_input("Password", type="password", label_visibility="collapsed", placeholder="Enter Password Here...")
        unlock_btn = st.button("Unlock App", use_container_width=True)
        
        if unlock_btn or password_input:
            if password_input.strip() == "light":
                st.session_state["authenticated"] = True
                st.rerun()
            elif password_input:
                st.error("Access Denied: Incorrect password. Try again.")
    st.stop()

# ---- Data Engine Handlers ----
def load_data():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    users = {}
    cursor.execute("SELECT name, color, joined_index FROM users")
    for row in cursor.fetchall():
        users[row[0]] = {"color": row[1], "joined_at_expense_idx": row[2]}
        
    expenses = []
    cursor.execute("SELECT id, description, amount, paid_by, participants, is_deposit FROM expenses")
    for row in cursor.fetchall():
        expenses.append({
            "db_id": row[0],
            "desc": row[1],
            "amount": row[2],
            "paid_by": row[3],
            "participants": row[4].split(";") if row[4] else [],
            "is_deposit": True if row[5] == 1 else False
        })
    conn.close()
    return users, expenses

users, expenses = load_data()

# ---- Real-Time Accounting Calculations ----
wallet_balance = 0.0
for exp in expenses:
    if exp["is_deposit"]:
        wallet_balance += exp["amount"]
    elif exp["paid_by"] == "[WALLET]":
        wallet_balance -= exp["amount"]

net_balances = {user: 0.0 for user in users}
for exp in expenses:
    amount = exp["amount"]
    payer = exp["paid_by"]
    if exp["is_deposit"]:
        if payer in net_balances:
            net_balances[payer] += amount
    else:
        splitting_members = [m for m in exp["participants"] if m in net_balances]
        if not splitting_members:
            splitting_members = list(users.keys())
        if not splitting_members:
            continue
        share = amount / len(splitting_members)
        if payer != "[WALLET]" and payer in net_balances:
            net_balances[payer] += amount
        for user in splitting_members:
            if user in net_balances:
                net_balances[user] -= share

# ---- Main Layout Presentation View ----
st.markdown("<h1 style='text-align: center;'>🍻 APERO GROTTE NIMES 🍻</h1>", unsafe_allow_html=True)

# Common Wallet Bar Display
st.metric(label="Cagnotte / Common Wallet Balance", value=f"{wallet_balance:.2f} €/$")
st.markdown("---")

left_col, right_col = st.columns([1, 1.2])

# ---- LEFT COLUMN: ACTIONS & MANAGEMENT PANEL ----
with left_col:
    st.subheader("👥 Group Management")
    
    # 1. Add User Section
    with st.container(border=True):
        st.markdown("**Add New Participant**")
        new_user = st.text_input("Participant Name", label_visibility="collapsed", placeholder="Name (e.g., Alice)").strip()
        if st.button("Add User", use_container_width=True):
            if new_user and new_user.upper() != "[WALLET]" and new_user not in users:
                joined_idx = len(expenses)
                colors = ["#3A7EBB", "#2E9A67", "#D9534F", "#F0AD4E", "#9B59B6", "#5BC0DE"]
                color_picked = random.choice(colors)
                
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("INSERT OR REPLACE INTO users (name, color, joined_index) VALUES (?, ?, ?)", (new_user, color_picked, joined_idx))
                conn.close()
                st.success(f"Added {new_user} to the roster!")
                st.rerun()
            elif new_user in users:
                st.warning("That name already exists in the ledger.")

    # 2. Deposit Cash into Common Cagnotte
    with st.container(border=True):
        st.markdown("💰 **Put Cash into Common Cagnotte (Deposit)**")
        dep_amount = st.text_input("Deposit Amount", placeholder="0.00")
        user_options = list(users.keys())
        dep_payer = st.selectbox("Who is providing this cash deposit?", options=user_options if user_options else ["No users logged yet"])
        
        if st.button("Deposit Cash", use_container_width=True):
            try:
                amt = float(dep_amount)
                if amt <= 0: raise ValueError
                if dep_payer == "No users logged yet": raise TypeError
                
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("INSERT INTO expenses (description, amount, paid_by, participants, is_deposit) VALUES (?, ?, ?, ?, ?)",
                               (f"Deposit into Wallet by {dep_payer}", amt, dep_payer, "", 1))
                conn.close()
                st.success("Deposit registered cleanly!")
                st.rerun()
            except ValueError:
                st.error("Please enter a valid positive number.")
            except TypeError:
                st.error("Add a participant before making deposits.")

    # 3. Log a Spent Expense
    with st.container(border=True):
        st.markdown("🛒 **Buy Something / Log Expense**")
        exp_desc = st.text_input("Item Description", placeholder="e.g., Drinks, Ice, Snacks")
        exp_amount = st.text_input("Cost Amount Value", placeholder="0.00")
        
        spending_options = ["[WALLET]"] + user_options if user_options else ["[WALLET]"]
        exp_payer = st.selectbox("Paid using whose money?", options=spending_options)
        
        if st.button("Log Spent Expense", use_container_width=True):
            try:
                amt = float(exp_amount)
                if amt <= 0: raise ValueError
                if not exp_desc: raise IndexError
                
                if exp_payer == "[WALLET]" and amt > wallet_balance:
                    st.error(f"Insufficient Wallet Balance! Remainder: {wallet_balance:.2f}")
                else:
                    current_idx = len(expenses)
                    allowed = [name for name, info in users.items() if info["joined_at_expense_idx"] <= current_idx]
                    parts_str = ";".join(allowed)
                    
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO expenses (description, amount, paid_by, participants, is_deposit) VALUES (?, ?, ?, ?, ?)",
                                   (exp_desc, amt, exp_payer, parts_str, 0))
                    conn.close()
                    st.success(f"Logged entry: {exp_desc}")
                    st.rerun()
            except ValueError:
                st.error("Please enter a valid cost entry amount.")
            except IndexError:
                st.error("Description fields cannot be blank.")

# ---- RIGHT COLUMN: BALANCES & LEDGER LOGS ----
with right_col:
    st.subheader("📊 Live Ledger Status")
    
    # Roster List Display
    with st.expander("👥 Group Members Profiles Roster", expanded=True):
        if not users:
            st.info("No active participants logged yet.")
        for name, info in users.items():
            rc1, rc2 = st.columns([4, 1])
            strategy = "From start" if info["joined_at_expense_idx"] == 0 else f"Late arrival (Exp #{info['joined_at_expense_idx']})"
            rc1.markdown(f"• **{name}** ({strategy})")
            if rc2.button("Kick", key=f"del_u_{name}"):
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM users WHERE name = ?", (name,))
                cursor.execute("DELETE FROM expenses WHERE paid_by = ?", (name,))
                conn.close()
                st.rerun()

    # Interactive Transaction History Log
    with st.expander("📜 Itemized Transaction History Rows", expanded=True):
        if not expenses:
            st.info("No logs saved to current workspace database.")
        for exp in expenses:
            hc1, hc2 = st.columns([5, 1])
            prefix = "💰 [DEPOSIT]" if exp["is_deposit"] else f"🛒 [SPENT BY {exp['paid_by']}]"
            hc1.markdown(f"{prefix} *{exp['desc']}*: **{exp['amount']:.2f} €/$**")
            if hc2.button("🗑️", key=f"del_tx_{exp['db_id']}"):
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM expenses WHERE id = ?", (exp["db_id"],))
                conn.close()
                st.rerun()

    # Tricount Settlement Output Container Block
    st.markdown("**Tricount Balance & Settlement Dashboard**")
    
    display_text = "=========================================\n"
    display_text += "        INDIVIDUAL NET STATUS            \n"
    display_text += "=========================================\n"
    for user, bal in net_balances.items():
        if bal > 0.005:
            display_text += f"• {user:<12} : +{bal:.2f} €/$ (Owed money)\n"
        elif bal < -0.005:
            display_text += f"• {user:<12} :  {bal:.2f} €/$ (Owes money)\n"
        else:
            display_text += f"• {user:<12} :   0.00 €/$ (Even)\n"

    display_text += "\n=========================================\n"
    display_text += "        WHO OWES WHO HOW MUCH            \n"
    display_text += "=========================================\n"

    debtors = [[u, b] for u, b in net_balances.items() if b < -0.005]
    creditors = [[u, b] for u, b in net_balances.items() if b > 0.005]
    debtors.sort(key=lambda x: x[1])
    creditors.sort(key=lambda x: x[1], reverse=True)

    transactions = []
    while debtors and creditors:
        debtor = debtors[0]
        creditor = creditors[0]
        settle_amount = min(abs(debtor[1]), creditor[1])
        transactions.append(f" 🔴 {debtor[0]:<10} owes {settle_amount:>6.2f} €/$ ➡️ to {creditor[0]}")
        debtor[1] += settle_amount
        creditor[1] -= settle_amount
        if abs(debtor[1]) < 0.005: debtors.pop(0)
        if creditor[1] < 0.005: creditors.pop(0)

    if not transactions and len(expenses) > 0:
        display_text += " 🎉 Everyone is perfectly even and settled!\n"
    elif not transactions:
        display_text += " ℹ️ No records logged yet.\n"
    else:
        display_text += "\n".join(transactions) + "\n"
    display_text += "=========================================\n"

    st.code(display_text, language="text")
