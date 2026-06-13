import os
import sqlite3
import random
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# ---- Appearance and Theme Settings ----
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ---- Smart Local Database Routing ----
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(SCRIPT_DIR, "apero_grotte_nimes_web.db")

def get_db_connection():
    return sqlite3.connect(DB_FILE, timeout=10)

def init_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                name TEXT PRIMARY KEY,
                color TEXT,
                joined_index INTEGER,
                is_contributor INTEGER DEFAULT 0
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
        
        # Run structural migration check for older databases
        cursor.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]
        if "is_contributor" not in columns:
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN is_contributor INTEGER DEFAULT 0")
                conn.commit()
            except sqlite3.OperationalError:
                pass
                
        conn.close()
    except Exception as e:
        print(f"Database setup notice: {e}")

# Initialize Database Structures safely
init_db()

# =========================================================
# 🛑 PHASE 1: SECURE GATE WINDOW (CustomTkinter)
# =========================================================
class LoginWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Access Required")
        self.geometry("450x320")
        self.resizable(False, False)
        
        # Default fallback permission context
        self.user_role = "Viewer"
        self.authenticated = False
        
        # Safe Window Centering
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
        
        # User Interface Components
        self.label_title = ctk.CTkLabel(self, text="🔒 APERO GROTTE NIMES", font=("Arial", 20, "bold"))
        self.label_title.pack(pady=(35, 5))
        
        self.label_sub = ctk.CTkLabel(self, text="Please enter group password:", font=("Arial", 14), text_color="gray")
        self.label_sub.pack(pady=(0, 20))
        
        self.entry_password = ctk.CTkEntry(self, width=280, show="*", placeholder_text="Password or Username...")
        self.entry_password.pack(pady=10)
        self.entry_password.focus_set()
        
        # Bind the Enter key directly to the unlock action
        self.entry_password.bind("<Return>", lambda event: self.verify_password())
        
        self.btn_unlock = ctk.CTkButton(self, text="Unlock App", width=180, height=40, font=("Arial", 14, "bold"), command=self.verify_password)
        self.btn_unlock.pack(pady=25)
        
    def verify_password(self):
        pwd = self.entry_password.get().strip()
        
        if pwd == "light":
            self.user_role = "Admin"
            self.authenticated = True
            self.destroy()
        elif pwd == "guest" or pwd == "":
            self.user_role = "Viewer"
            self.authenticated = True
            self.destroy()
        else:
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT is_contributor FROM users WHERE name = ?", (pwd,))
                row = cursor.fetchone()
                conn.close()
                
                if row and row[0] == 1:
                    self.user_role = f"Contributor ({pwd})"
                    self.authenticated = True
                    self.destroy()
                    return
            except Exception as e:
                print(f"Login Check Error: {e}")
                
            messagebox.showerror("Access Denied", "Invalid or unauthorized keyphrase.")

# =========================================================
# 🔓 PHASE 2: CORE LEDGER APPLICATION WINDOW
# =========================================================
class TrackerDashboard(ctk.CTk):
    def __init__(self, role):
        super().__init__()
        self.role = role
        self.title(f"APERO GROTTE NIMES v4.5 - [{self.role} Mode]")
        self.geometry("1100x700")
        
        # Access Boolean Calculations
        self.is_admin = self.role == "Admin"
        self.has_write_access = self.is_admin or self.role.startswith("Contributor")
        
        # Top Heading Label Panel
        self.header = ctk.CTkLabel(self, text="🍻 APERO GROTTE NIMES LEDGER 🍻", font=("Arial", 24, "bold"))
        self.header.pack(pady=15)
        
        self.sub_header = ctk.CTkLabel(self, text=f"Active Permission Level: {self.role}", font=("Arial", 13, "italic"), text_color="gray")
        self.sub_header.pack(pady=(0, 10))
        
        # Container Main Split Frames
        self.main_container = ctk.CTkFrame(self)
        self.main_container.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.left_frame = ctk.CTkFrame(self.main_container, width=450)
        self.left_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        
        self.right_frame = ctk.CTkFrame(self.main_container)
        self.right_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        
        # Set up Left Action Panel
        self.setup_left_panel()

        # Set up Right Tabbed View
        self.tab_view = ctk.CTkTabview(self.right_frame)
        self.tab_view.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.tab_view.add("👥 Group Roster")
        self.tab_view.add("📜 History Logs")
        self.tab_view.add("📊 Tricount Balance Sheets")
        self.tab_view.add("📈 Trends")
        
        # Bind the tab change event to dynamically load the graph
        self.tab_view.configure(command=self.on_tab_change)
        
        self.scroll_roster = ctk.CTkScrollableFrame(self.tab_view.tab("👥 Group Roster"))
        self.scroll_roster.pack(fill="both", expand=True)
        
        self.scroll_history = ctk.CTkScrollableFrame(self.tab_view.tab("📜 History Logs"))
        self.scroll_history.pack(fill="both", expand=True)
        
        self.txt_tricount = ctk.CTkTextbox(self.tab_view.tab("📊 Tricount Balance Sheets"), font=("Courier New", 12))
        self.txt_tricount.pack(fill="both", expand=True, padx=10, pady=10)

        self.graph_frame = ctk.CTkFrame(self.tab_view.tab("📈 Trends"))
        self.graph_frame.pack(fill="both", expand=True)

        self.refresh_all_data()

    def setup_left_panel(self):
        # 1. Metric Display Box
        self.wallet_frame = ctk.CTkFrame(self.left_frame, fg_color="#1f2c3f")
        self.wallet_frame.pack(fill="x", padx=15, pady=15)
        
        self.lbl_wallet_title = ctk.CTkLabel(self.wallet_frame, text="CAGNOTTE WALLET BALANCE", font=("Arial", 12, "bold"))
        self.lbl_wallet_title.pack(pady=(10, 0))
        
        self.lbl_wallet_val = ctk.CTkLabel(self.wallet_frame, text="0.00 €/$", font=("Arial", 28, "bold"), text_color="#2E9A67")
        self.lbl_wallet_val.pack(pady=(0, 10))

        # Action Intercept Notice for Viewers
        if not self.has_write_access:
            notice = ctk.CTkLabel(self.left_frame, text="🔒 VIEW-ONLY GUEST MODE\nYou cannot add or modify operations.", font=("Arial", 13, "bold"), text_color="#D9534F")
            notice.pack(pady=20)
            return

        # 2. Add Participant Block
        self.f_add_u = ctk.CTkFrame(self.left_frame)
        self.f_add_u.pack(fill="x", padx=15, pady=10)
        ctk.CTkLabel(self.f_add_u, text="👥 Add New Participant", font=("Arial", 13, "bold")).pack(pady=5)
        self.ent_new_user = ctk.CTkEntry(self.f_add_u, placeholder_text="Name (e.g. Alice)")
        self.ent_new_user.pack(fill="x", padx=15, pady=5)
        ctk.CTkButton(self.f_add_u, text="Register User", command=self.add_user_action).pack(fill="x", padx=15, pady=10)

        # 3. Log Cash Deposit Block
        self.f_dep = ctk.CTkFrame(self.left_frame)
        self.f_dep.pack(fill="x", padx=15, pady=10)
        ctk.CTkLabel(self.f_dep, text="💰 Put Cash into Cagnotte (Deposit)", font=("Arial", 13, "bold")).pack(pady=5)
        self.ent_dep_amt = ctk.CTkEntry(self.f_dep, placeholder_text="Amount (0.00)")
        self.ent_dep_amt.pack(fill="x", padx=15, pady=3)
        self.combo_dep_payer = ctk.CTkComboBox(self.f_dep, values=[])
        self.combo_dep_payer.pack(fill="x", padx=15, pady=3)
        ctk.CTkButton(self.f_dep, text="Log Cash Deposit", command=self.log_deposit_action).pack(fill="x", padx=15, pady=10)

        # 4. Log General Expense Block
        self.f_exp = ctk.CTkFrame(self.left_frame)
        self.f_exp.pack(fill="x", padx=15, pady=10)
        ctk.CTkLabel(self.f_exp, text="🛒 Buy Something / Log Expense", font=("Arial", 13, "bold")).pack(pady=5)
        self.ent_exp_desc = ctk.CTkEntry(self.f_exp, placeholder_text="Description (Snacks, Ice...)")
        self.ent_exp_desc.pack(fill="x", padx=15, pady=3)
        self.ent_exp_amt = ctk.CTkEntry(self.f_exp, placeholder_text="Cost Value (0.00)")
        self.ent_exp_amt.pack(fill="x", padx=15, pady=3)
        self.combo_exp_payer = ctk.CTkComboBox(self.f_exp, values=[])
        self.combo_exp_payer.pack(fill="x", padx=15, pady=3)
        ctk.CTkButton(self.f_exp, text="Log Spent Expense", command=self.log_expense_action).pack(fill="x", padx=15, pady=10)

    # ---- Actions Mechanics Callbacks ----
    def add_user_action(self):
        name = self.ent_new_user.get().strip()
        if not name or name.upper() == "[WALLET]": return
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM expenses")
        current_idx = cursor.fetchone()[0]
        color = random.choice(["#3A7EBB", "#2E9A67", "#D9534F", "#F0AD4E", "#9B59B6"])
        
        try:
            cursor.execute("INSERT INTO users (name, color, joined_index, is_contributor) VALUES (?, ?, ?, 0)", (name, color, current_idx))
            conn.commit()
            self.ent_new_user.delete(0, "end")
        except sqlite3.IntegrityError:
            messagebox.showwarning("Error", "User name already exists inside the ledger database.")
        conn.close()
        self.refresh_all_data()

    def log_deposit_action(self):
        try:
            amt = float(self.ent_dep_amt.get().strip())
            payer = self.combo_dep_payer.get()
            if amt <= 0 or not payer: raise ValueError
            
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO expenses (description, amount, paid_by, participants, is_deposit) VALUES (?, ?, ?, '', 1)",
                           (f"Deposit into Wallet by {payer}", amt, payer))
            conn.commit()
            conn.close()
            self.ent_dep_amt.delete(0, "end")
            self.refresh_all_data()
        except ValueError:
            messagebox.showerror("Invalid Input", "Provide a valid positive money amount value.")

    def log_expense_action(self):
        try:
            desc = self.ent_exp_desc.get().strip()
            amt = float(self.ent_exp_amt.get().strip())
            payer = self.combo_exp_payer.get()
            if amt <= 0 or not desc or not payer: raise ValueError
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM expenses")
            cur_idx = cursor.fetchone()[0]
            cursor.execute("SELECT name FROM users WHERE joined_index <= ?", (cur_idx,))
            allowed = [r[0] for r in cursor.fetchall()]
            
            cursor.execute("INSERT INTO expenses (description, amount, paid_by, participants, is_deposit) VALUES (?, ?, ?, ?, 0)",
                           (desc, amt, payer, ";".join(allowed)))
            conn.commit()
            conn.close()
            
            self.ent_exp_desc.delete(0, "end")
            self.ent_exp_amt.delete(0, "end")
            self.refresh_all_data()
        except ValueError:
            messagebox.showerror("Invalid Input", "Check fields and ensure pricing amounts are positive.")

    def toggle_contributor(self, name):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT is_contributor FROM users WHERE name = ?", (name,))
        current = cursor.fetchone()[0]
        cursor.execute("UPDATE users SET is_contributor = ? WHERE name = ?", (1 if current == 0 else 0, name))
        conn.commit()
        conn.close()
        self.refresh_all_data()

    def kick_user(self, name):
        if messagebox.askyesno("Confirm Kick", f"Permanently remove {name} and clear their payments?"):
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE name = ?", (name,))
            cursor.execute("DELETE FROM expenses WHERE paid_by = ?", (name,))
            conn.commit()
            conn.close()
            self.refresh_all_data()

    def delete_expense(self, e_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM expenses WHERE id = ?", (e_id,))
        conn.commit()
        conn.close()
        self.refresh_all_data()

    def modify_expense_popup(self, exp):
        popup = ctk.CTkToplevel(self)
        popup.title("Modify Transaction")
        popup.geometry("350x250")
        popup.resizable(False, False)
        
        ctk.CTkLabel(popup, text="Update Description:").pack(pady=5)
        e_desc = ctk.CTkEntry(popup, width=250)
        e_desc.insert(0, exp["desc"])
        e_desc.pack()
        
        ctk.CTkLabel(popup, text="Update Amount:").pack(pady=5)
        e_amt = ctk.CTkEntry(popup, width=250)
        e_amt.insert(0, f"{exp['amount']:.2f}")
        e_amt.pack()
        
        def save_changes():
            try:
                new_desc = e_desc.get().strip()
                new_amt = float(e_amt.get().strip())
                if new_amt <= 0 or not new_desc: raise ValueError
                
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("UPDATE expenses SET description = ?, amount = ? WHERE id = ?", (new_desc, new_amt, exp["id"]))
                conn.commit()
                conn.close()
                popup.destroy()
                self.refresh_all_data()
            except ValueError:
                messagebox.showerror("Error", "Invalid field validation configurations.")

        ctk.CTkButton(popup, text="Save Changes", command=save_changes).pack(pady=20)

    # ---- Graph Rendering Logic ----
    def on_tab_change(self):
        if self.tab_view.get() == "📈 Trends":
            self.render_graph()

    def render_graph(self):
        for widget in self.graph_frame.winfo_children():
            widget.destroy()
            
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT amount, is_deposit FROM expenses ORDER BY id ASC")
            data = cur.fetchall()
            conn.close()

            fig, ax = plt.subplots(figsize=(5, 3), dpi=100)
            fig.patch.set_facecolor('#2b2b2b')
            ax.set_facecolor('#2b2b2b')
            
            balances = [0]
            curr = 0
            for amt, is_dep in data:
                curr += amt if is_dep == 1 else -amt
                balances.append(curr)
                
            ax.plot(balances, color='#2E9A67', marker='o', linewidth=2)
            ax.tick_params(colors='white')
            ax.spines['bottom'].set_color('white')
            ax.spines['left'].set_color('white')
            
            canvas = FigureCanvasTkAgg(fig, master=self.graph_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)
            
            # Prevent memory leaks by properly closing the plot
            plt.close(fig)
            
        except Exception as e:
            print(f"Error rendering graph: {e}")

    # ---- Data Processing Logic Engine ----
    def refresh_all_data(self):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            users = {}
            cursor.execute("SELECT name, color, joined_index, is_contributor FROM users")
            for row in cursor.fetchall():
                users[row[0]] = {"color": row[1], "idx": row[2], "is_contrib": bool(row[3])}
                
            expenses = []
            cursor.execute("SELECT id, description, amount, paid_by, participants, is_deposit FROM expenses")
            for row in cursor.fetchall():
                expenses.append({
                    "id": row[0], "desc": row[1], "amount": row[2],
                    "paid_by": row[3], "parts": row[4].split(";") if row[4] else [],
                    "is_deposit": bool(row[5])
                })
            conn.close()
        except Exception as e:
            print(f"Error loading cache frames: {e}")
            return

        # Update Form ComboBox Dropdowns safely if present
        if self.has_write_access:
            user_list = list(users.keys())
            self.combo_dep_payer.configure(values=user_list)
            self.combo_exp_payer.configure(values=["[WALLET]"] + user_list)

        # 1. Balance Calculations
        wallet_val = 0.0
        for exp in expenses:
            if exp["is_deposit"]: wallet_val += exp["amount"]
            elif exp["paid_by"] == "[WALLET]": wallet_val -= exp["amount"]
        self.lbl_wallet_val.configure(text=f"{wallet_val:.2f} €/$")

        # 2. Re-render Interactive Member Cards
        for widget in self.scroll_roster.winfo_children():
            widget.destroy()
            
        for name, info in users.items():
            row_f = ctk.CTkFrame(self.scroll_roster, fg_color="transparent")
            row_f.pack(fill="x", pady=4, padx=5)
            
            lbl_name = ctk.CTkLabel(row_f, text=f"• {name}", font=("Arial", 14, "bold"), anchor="w", width=200)
            lbl_name.pack(side="left", padx=10)
            
            if self.is_admin:
                cb = ctk.CTkCheckBox(row_f, text="Contributor Role", command=lambda n=name: self.toggle_contributor(n))
                cb.pack(side="left", padx=15)
                if info["is_contrib"]: cb.select()
                
                btn_kick = ctk.CTkButton(row_f, text="Kick", fg_color="#D9534F", hover_color="#C9302C", width=60, command=lambda n=name: self.kick_user(n))
                btn_kick.pack(side="right", padx=10)
            else:
                lbl_role = ctk.CTkLabel(row_f, text="Contributor" if info["is_contrib"] else "Viewer Only", font=("Arial", 12, "italic"))
                lbl_role.pack(side="left", padx=15)

        # 3. Re-render Interactive History Rows
        for widget in self.scroll_history.winfo_children():
            widget.destroy()
            
        for exp in expenses:
            row_f = ctk.CTkFrame(self.scroll_history)
            row_f.pack(fill="x", pady=4, padx=5)
            
            prefix = "💰 [DEP]" if exp["is_deposit"] else f"🛒 [{exp['paid_by']}]"
            lbl_txt = ctk.CTkLabel(row_f, text=f"{prefix} {exp['desc']}: {exp['amount']:.2f} €/$", font=("Arial", 13), anchor="w")
            lbl_txt.pack(side="left", padx=10, fill="x", expand=True)
            
            if self.is_admin:
                btn_del = ctk.CTkButton(row_f, text="🗑️", fg_color="#D9534F", hover_color="#C9302C", width=40, command=lambda e_id=exp["id"]: self.delete_expense(e_id))
                btn_del.pack(side="right", padx=5)
                btn_mod = ctk.CTkButton(row_f, text="Modifier", width=70, command=lambda e=exp: self.modify_expense_popup(e))
                btn_mod.pack(side="right", padx=5)

        # 4. Process and Display Settlement Logic Matrix
        net_balances = {user: 0.0 for user in users}
        for exp in expenses:
            amt = exp["amount"]
            payer = exp["paid_by"]
            if exp["is_deposit"]:
                if payer in net_balances: net_balances[payer] += amt
            else:
                splitting = [m for m in exp["parts"] if m in net_balances]
                if not splitting: splitting = list(users.keys())
                if not splitting: continue
                share = amt / len(splitting)
                if payer != "[WALLET]" and payer in net_balances: net_balances[payer] += amt
                for user in splitting:
                    if user in net_balances: net_balances[user] -= share

        display_text = "=========================================\n"
        display_text += "        INDIVIDUAL NET WALLET STATUS     \n"
        display_text += "=========================================\n"
        for user, bal in net_balances.items():
            if bal > 0.005: display_text += f"• {user:<12} : +{bal:.2f} €/$ (Owed)\n"
            elif bal < -0.005: display_text += f"• {user:<12} :  {bal:.2f} €/$ (Owes)\n"
            else: display_text += f"• {user:<12} :   0.00 €/$ (Even)\n"

        display_text += "\n=========================================\n"
        display_text += "        WHO OWES WHO HOW MUCH            \n"
        display_text += "=========================================\n"
        
        debtors = [[u, b] for u, b in net_balances.items() if b < -0.005]
        creditors = [[u, b] for u, b in net_balances.items() if b > 0.005]
        debtors.sort(key=lambda x: x[1])
        creditors.sort(key=lambda x: x[1], reverse=True)

        tx_list = []
        while debtors and creditors:
            deb, cred = debtors[0], creditors[0]
            settle_amount = min(abs(deb[1]), cred[1])
            tx_list.append(f" 🔴 {deb[0]:<10} owes {settle_amount:>6.2f} €/$ ➡️ to {cred[0]}")
            deb[1] += settle_amount
            cred[1] -= settle_amount
            if abs(deb[1]) < 0.005: debtors.pop(0)
            if cred[1] < 0.005: creditors.pop(0)

        if not tx_list and expenses: display_text += " 🎉 Everyone is completely settled!\n"
        elif not tx_list: display_text += " ℹ️ No logging records available.\n"
        else: display_text += "\n".join(tx_list) + "\n"
        
        self.txt_tricount.configure(state="normal")
        self.txt_tricount.delete("1.0", "end")
        self.txt_tricount.insert("1.0", display_text)
        self.txt_tricount.configure(state="disabled")
        
        # Always update the graph if its tab is currently open during a refresh
        if self.tab_view.get() == "📈 Trends":
            self.render_graph()

# =========================================================
# 🚀 CORE SYSTEM LAUNCH EXECUTION SEQUENCER
# =========================================================
if __name__ == "__main__":
    gate = LoginWindow()
    gate.mainloop()
    
    if gate.authenticated:
        app = TrackerDashboard(role=gate.user_role)
        app.mainloop()