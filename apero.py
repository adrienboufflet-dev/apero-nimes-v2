import os
# Force Streamlit to bypass WebSocket restrictions that cause cloud freezing
os.environ["STREAMLIT_SERVER_ENABLE_WEBSOCKET_COMPRESSION"] = "false"
os.environ["STREAMLIT_SERVER_ENABLE_CORS"] = "false"
import sys
import os
import sqlite3
import traceback
import random

try:
    import customtkinter as ctk
    from tkinter import messagebox, simpledialog
except ImportError:
    print("\n[ERROR] 'customtkinter' is not installed properly.")
    print("Please run: py -m pip install customtkinter\n")
    sys.exit(1)

ctk.set_appearance_mode("System")  
ctk.set_default_color_theme("blue")

# Smart path fix: Always create the database file in the exact folder where this script lives
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(SCRIPT_DIR, "apero_grotte_nimes.db")

class PasswordDialog(ctk.CTkToplevel):
    """Secure startup modal window that halts application access until unlocked."""
    def __init__(self, parent, correct_password="light"):
        super().__init__(parent)
        self.parent = parent
        self.correct_password = correct_password
        
        self.title("Access Required")
        self.geometry("340x180")
        self.resizable(False, False)
        
        # Lift modal window to the very top hierarchy
        self.lift()
        self.attributes("-topmost", True)
        self.grab_set()
        
        # Center the dialog manually relative to its parent geometry
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (340 // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (180 // 2)
        self.geometry(f"+{x}+{y}")
        
        # Handle manual user closure attempts safely
        self.protocol("WM_DELETE_WINDOW", self.on_close_attempt)

        self.label = ctk.CTkLabel(self, text="🔒 APERO GROTTE NIMES\nPlease enter group password:", font=ctk.CTkFont(size=14, weight="bold"))
        self.label.pack(pady=(20, 10))

        self.password_entry = ctk.CTkEntry(self, show="*", placeholder_text="Password", width=200)
        self.password_entry.pack(pady=5)
        self.password_entry.focus_set()
        self.password_entry.bind("<Return>", lambda event: self.verify_password())

        self.submit_btn = ctk.CTkButton(self, text="Unlock App", command=self.verify_password, width=120)
        self.submit_btn.pack(pady=15)

    def verify_password(self):
        entered = self.password_entry.get().strip()
        if entered == self.correct_password:
            self.grab_release()
            self.destroy()
            self.parent.deiconify() # Reveal master application frame
        else:
            messagebox.showerror("Access Denied", "Incorrect password. Try again.")
            self.password_entry.delete(0, 'end')

    def on_close_attempt(self):
        # Kill the entire python sequence if they attempt to bypass by clicking 'X'
        self.parent.destroy()
        sys.exit(0)


class EditTransactionDialog(ctk.CTkToplevel):
    """Inline modal to edit descriptions and amount properties safely."""
    def __init__(self, parent, tx_data):
        super().__init__(parent)
        self.parent = parent
        self.tx_data = tx_data
        self.confirmed = False

        self.title("Edit Transaction Entry")
        self.geometry("360x220")
        self.resizable(False, False)
        
        self.lift()
        self.attributes("-topmost", True)
        self.grab_set()
        
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (360 // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (220 // 2)
        self.geometry(f"+{x}+{y}")

        self.lbl = ctk.CTkLabel(self, text=f"Modifying Entry Details", font=ctk.CTkFont(weight="bold", size=14))
        self.lbl.pack(pady=(15, 10))

        self.desc_entry = ctk.CTkEntry(self, width=260, placeholder_text="Description")
        self.desc_entry.insert(0, tx_data["desc"])
        self.desc_entry.pack(pady=5)

        self.amount_entry = ctk.CTkEntry(self, width=260, placeholder_text="Amount")
        self.amount_entry.insert(0, f"{tx_data['amount']:.2f}")
        self.amount_entry.pack(pady=5)

        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.pack(pady=15)

        self.cancel_btn = ctk.CTkButton(self.btn_frame, text="Cancel", width=90, fg_color="gray", command=self.destroy)
        self.cancel_btn.pack(side="left", padx=5)

        self.save_btn = ctk.CTkButton(self.btn_frame, text="Save Changes", width=120, fg_color="#2E9A67", hover_color="#23774F", command=self.save_modifications)
        self.save_btn.pack(side="right", padx=5)

    def save_modifications(self):
        new_desc = self.desc_entry.get().strip()
        new_amount_str = self.amount_entry.get().strip()

        if not new_desc:
            messagebox.showwarning("Input Error", "Description fields cannot be completely empty.")
            return
        try:
            new_amount = float(new_amount_str)
            if new_amount <= 0: raise ValueError
        except ValueError:
            messagebox.showwarning("Input Error", "Please input a valid positive cost amount structure.")
            return

        try:
            conn = sqlite3.connect(DB_FILE, isolation_level=None)
            cursor = conn.cursor()
            cursor.execute("UPDATE expenses SET description = ?, amount = ? WHERE id = ?", (new_desc, new_amount, self.tx_data["db_id"]))
            conn.close()
            self.confirmed = True
            self.destroy()
            self.parent.load_data_from_db()
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed saving update attributes: {e}")


class TricountCloneApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("APERO GROTTE NIMES - Smart Wallet & Tracker v3.8")
        self.geometry("1100x750")

        # Hide application initialization workspace frames temporarily until authentication passes
        self.withdraw()

        # ---- Core Data Structures ----
        self.users = {}        
        self.expenses = []     
        self.wallet_balance = 0.0

        # Setup Database Infrastructure
        self.init_db()

        # Setup GUI Grid Layout
        self.grid_columnconfigure(0, weight=4)
        self.grid_columnconfigure(1, weight=6)
        self.grid_rowconfigure(2, weight=1)

        # ---- Row 0: Title Header ----
        self.title_label = ctk.CTkLabel(self, text="🍻 APERO GROTTE NIMES 🍻", font=ctk.CTkFont(size=26, weight="bold"))
        self.title_label.grid(row=0, column=0, columnspan=2, padx=20, pady=(20, 10), sticky="ew")

        # ---- Row 1: Dedicated Bank Account / Wallet Bar ----
        self.wallet_frame = ctk.CTkFrame(self, fg_color="#2B2B2B", border_width=2, border_color="#1F6AA5")
        self.wallet_frame.grid(row=1, column=0, columnspan=2, padx=20, pady=10, sticky="ew")
        
        self.wallet_lbl = ctk.CTkLabel(self.wallet_frame, text="Cagnotte / Common Wallet Balance:", font=ctk.CTkFont(size=16, weight="bold"))
        self.wallet_lbl.pack(side="left", padx=20, pady=15)
        
        self.wallet_val_lbl = ctk.CTkLabel(self.wallet_frame, text="0.00 €/$", font=ctk.CTkFont(size=18, weight="bold", family="Courier"), text_color="#5CB85C")
        self.wallet_val_lbl.pack(side="left", padx=5, pady=15)

        # ---- Row 2: Left Panel (Inputs) ----
        self.left_panel = ctk.CTkFrame(self)
        self.left_panel.grid(row=2, column=0, padx=(20, 10), pady=10, sticky="nsew")
        self.left_panel.grid_columnconfigure(0, weight=1)

        # 1. Add User Section
        self.user_frame = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        self.user_frame.pack(fill="x", padx=15, pady=10)
        
        self.user_label = ctk.CTkLabel(self.user_frame, text="Add Participant:", font=ctk.CTkFont(weight="bold"))
        self.user_label.pack(anchor="w", pady=(0, 5)) 
        
        self.user_entry = ctk.CTkEntry(self.user_frame, placeholder_text="Name (e.g., Alice)")
        self.user_entry.pack(fill="x", side="left", expand=True, padx=(0, 5))
        
        self.user_btn = ctk.CTkButton(self.user_frame, text="Add User", width=80, command=self.add_user)
        self.user_btn.pack(side="right")

        # Divider 1
        self.div1 = ctk.CTkFrame(self.left_panel, height=2, fg_color="gray")
        self.div1.pack(fill="x", padx=15, pady=5)

        # 2. Deposit Cash into Wallet Section
        self.deposit_frame = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        self.deposit_frame.pack(fill="x", padx=15, pady=10)

        self.dep_title = ctk.CTkLabel(self.deposit_frame, text="Put Money into Common Cagnotte (Deposit):", font=ctk.CTkFont(weight="bold"))
        self.dep_title.pack(anchor="w", pady=(0, 5))

        self.dep_amount_entry = ctk.CTkEntry(self.deposit_frame, placeholder_text="Amount to put in (e.g., 50)")
        self.dep_amount_entry.pack(fill="x", pady=2)

        self.dep_payer_label = ctk.CTkLabel(self.deposit_frame, text="Who is giving this money?")
        self.dep_payer_label.pack(anchor="w", pady=(2, 0))

        self.dep_dropdown = ctk.CTkOptionMenu(self.deposit_frame, values=["No users added yet"])
        self.dep_dropdown.pack(fill="x", pady=2)

        self.dep_btn = ctk.CTkButton(self.deposit_frame, text="Deposit Cash", fg_color="#2E9A67", hover_color="#23774F", command=self.add_deposit)
        self.dep_btn.pack(fill="x", pady=5)

        # Divider 2
        self.div2 = ctk.CTkFrame(self.left_panel, height=2, fg_color="gray")
        self.div2.pack(fill="x", padx=15, pady=5)

        # 3. Add Expense Section (Buying items)
        self.expense_frame = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        self.expense_frame.pack(fill="both", expand=True, padx=15, pady=10)

        self.exp_label = ctk.CTkLabel(self.expense_frame, text="Buy Something / Log Expense:", font=ctk.CTkFont(weight="bold"))
        self.exp_label.pack(anchor="w", pady=(0, 5)) 

        self.desc_entry = ctk.CTkEntry(self.expense_frame, placeholder_text="Description (e.g., Drinks, Ice, Snacks)")
        self.desc_entry.pack(fill="x", pady=3)

        self.amount_entry = ctk.CTkEntry(self.expense_frame, placeholder_text="Cost Amount")
        self.amount_entry.pack(fill="x", pady=3)

        self.payer_label = ctk.CTkLabel(self.expense_frame, text="Paid using whose money?")
        self.payer_label.pack(anchor="w", pady=(3, 0))
        
        self.payer_dropdown = ctk.CTkOptionMenu(self.expense_frame, values=["No users added yet"])
        self.payer_dropdown.pack(fill="x", pady=3)

        self.expense_btn = ctk.CTkButton(self.expense_frame, text="Log Spent Expense", command=self.add_expense)
        self.expense_btn.pack(fill="x", pady=10)

        # ---- Row 2: Right Panel (Status Display & Live Log) ----
        self.right_panel = ctk.CTkFrame(self)
        self.right_panel.grid(row=2, column=1, padx=(10, 20), pady=10, sticky="nsew")
        self.right_panel.grid_columnconfigure(0, weight=1)
        
        self.right_panel.grid_rowconfigure(1, weight=1)  # Members profiles scrollable
        self.right_panel.grid_rowconfigure(3, weight=2)  # History list log scrollable
        self.right_panel.grid_rowconfigure(5, weight=2)  # Calculations text display

        # 1. Visual Participants Display
        self.active_users_title = ctk.CTkLabel(self.right_panel, text="Group Members Profiles:", font=ctk.CTkFont(weight="bold"))
        self.active_users_title.grid(row=0, column=0, padx=15, pady=(10, 2), sticky="w")
        
        self.users_scroll_frame = ctk.CTkScrollableFrame(self.right_panel, height=100)
        self.users_scroll_frame.grid(row=1, column=0, padx=15, pady=2, sticky="nsew")

        # 2. Interactive Itemized History Log (Delete/Edit Mistakes Here!)
        self.history_title = ctk.CTkLabel(self.right_panel, text="Interactive History Log (Edit or Delete Entry Rows):", font=ctk.CTkFont(weight="bold"))
        self.history_title.grid(row=2, column=0, padx=15, pady=(10, 2), sticky="w")
        
        self.history_scroll_frame = ctk.CTkScrollableFrame(self.right_panel, height=140)
        self.history_scroll_frame.grid(row=3, column=0, padx=15, pady=2, sticky="nsew")

        # 3. Balance Ledger Calculations
        self.balances_title = ctk.CTkLabel(self.right_panel, text="Tricount Balance & Settlement Dashboard:", font=ctk.CTkFont(weight="bold"))
        self.balances_title.grid(row=4, column=0, padx=15, pady=(10, 2), sticky="w")

        self.balances_textbox = ctk.CTkTextbox(self.right_panel, activate_scrollbars=True, font=ctk.CTkFont(family="Courier", size=12))
        self.balances_textbox.grid(row=5, column=0, padx=15, pady=(2, 15), sticky="nsew")
        self.balances_textbox.configure(state="disabled")

        # Force execution block inside data loop stack initialization
        self.load_data_from_db()

        # Fire security lock modal immediately over runtime instance frame layout safely
        self.ask_password_protection()

    # ---- Password Verification Hook ----
    
    def ask_password_protection(self):
        self.update_idletasks()
        PasswordDialog(self, correct_password="light")

    # ---- Database Infrastructure Engine ----

    def get_db_connection(self):
        """Helper to open connection with strict real-time isolation parameters."""
        return sqlite3.connect(DB_FILE, isolation_level=None)

    def init_db(self):
        """Creates database schema securely on start."""
        try:
            conn = self.get_db_connection()
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
        except Exception as e:
            print(f"[Database Error] Initializing schema failed: {e}")

    # ---- Application Core Logic ----

    def generate_random_color(self):
        return random.choice(["#3A7EBB", "#2E9A67", "#D9534F", "#F0AD4E", "#9B59B6", "#5BC0DE"])

    def add_user(self):
        user_name = self.user_entry.get().strip()
        if not user_name or user_name.upper() == "[WALLET]":
            messagebox.showwarning("Input Error", "Please enter a valid, non-protected name.")
            return
        if user_name in self.users:
            messagebox.showwarning("Input Error", f"'{user_name}' is already in the group.")
            return

        joined_at_idx = 0
        if len(self.expenses) > 0:
            msg = f"How should {user_name}'s expenses be calculated?\n\n" \
                  f"Click 'YES' to start from FRESH ZERO (Only split future expenses).\n" \
                  f"Click 'NO' to split HISTORICAL costs (Include all past expenses)."
            
            fresh_start = messagebox.askyesno("New Member Strategy", msg)
            if fresh_start:
                joined_at_idx = len(self.expenses)

        color_picked = self.generate_random_color()
        
        self.users[user_name] = {
            "color": color_picked,
            "joined_at_expense_idx": joined_at_idx
        }
        
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO users (name, color, joined_index) VALUES (?, ?, ?)", 
                           (user_name, color_picked, joined_at_idx))
            conn.close()
        except Exception as e:
            print(f"[Database Error] Save user failed: {e}")

        self.user_entry.delete(0, 'end')
        self.update_dropdowns()
        self.update_users_display()
        self.calculate_balances()

    def remove_user(self, name_to_remove):
        """Completely drops a participant and updates calculations safely."""
        confirm = messagebox.askyesno("Confirm Removal", f"Are you sure you want to remove '{name_to_remove}'?\n\nThis will clear them from the group and wipe any transactions they explicitly paid for.")
        if not confirm:
            return

        if name_to_remove in self.users:
            del self.users[name_to_remove]

        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE name = ?", (name_to_remove,))
            cursor.execute("DELETE FROM expenses WHERE paid_by = ?", (name_to_remove,))
            conn.close()
        except Exception as e:
            print(f"[Database Error] Removal operations failed: {e}")

        self.expenses.clear()
        self.load_data_from_db()

    def remove_transaction(self, tx_id):
        """Deletes a specific misclicked expense or deposit from the database completely."""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM expenses WHERE id = ?", (tx_id,))
            conn.close()
        except Exception as e:
            print(f"[Database Error] Failed to delete transaction: {e}")

        self.load_data_from_db()

    def edit_transaction(self, tx_data):
        """Launches editing prompt overlay frame safely."""
        EditTransactionDialog(self, tx_data)

    def update_dropdowns(self):
        user_list = list(self.users.keys())
        
        if user_list:
            self.dep_dropdown.configure(values=user_list)
            self.dep_dropdown.set(user_list[0])
            
            spending_options = ["[WALLET]"] + user_list
            self.payer_dropdown.configure(values=spending_options)
            self.payer_dropdown.set(spending_options[0])
        else:
            self.dep_dropdown.configure(values=["No users added yet"])
            self.dep_dropdown.set("No users added yet")
            self.payer_dropdown.configure(values=["No users added yet"])
            self.payer_dropdown.set("No users added yet")

    def update_users_display(self):
        for widget in self.users_scroll_frame.winfo_children():
            widget.destroy()

        if not self.users:
            lbl = ctk.CTkLabel(self.users_scroll_frame, text="No participants yet.", font=ctk.CTkFont(style="italic"))
            lbl.pack(pady=10)
            return

        for name, profile in self.users.items():
            u_frame = ctk.CTkFrame(self.users_scroll_frame, fg_color="transparent")
            u_frame.pack(fill="x", pady=2, padx=5)

            avatar = ctk.CTkLabel(u_frame, text=name[0].upper(), width=28, height=28, 
                                  fg_color=profile["color"], text_color="white", 
                                  font=ctk.CTkFont(weight="bold"), corner_radius=14)
            avatar.pack(side="left", padx=(0, 10))

            strategy_text = "From start" if profile["joined_at_expense_idx"] == 0 else f"Late (Exp #{profile['joined_at_expense_idx']})"
            lbl = ctk.CTkLabel(u_frame, text=f"{name} ({strategy_text})", font=ctk.CTkFont(size=13))
            lbl.pack(side="left")

            remove_btn = ctk.CTkButton(u_frame, text="Remove", fg_color="#D9534F", hover_color="#B53F3B", 
                                       width=60, height=22, font=ctk.CTkFont(size=11),
                                       command=lambda n=name: self.remove_user(n))
            remove_btn.pack(side="right", padx=5)

    def update_history_display(self):
        """Renders an interactive list layout with inline Edit and Delete operations."""
        for widget in self.history_scroll_frame.winfo_children():
            widget.destroy()

        if not self.expenses:
            lbl = ctk.CTkLabel(self.history_scroll_frame, text="No transaction history logged yet.", font=ctk.CTkFont(style="italic"))
            lbl.pack(pady=15)
            return

        for exp in self.expenses:
            tx_frame = ctk.CTkFrame(self.history_scroll_frame, fg_color="#2D2D2D" if exp["is_deposit"] else "#242424")
            tx_frame.pack(fill="x", pady=3, padx=5)

            prefix = "💰 [DEPOSIT]" if exp["is_deposit"] else f"🛒 [SPENT BY {exp['paid_by']}]"
            label_text = f"{prefix} {exp['desc']}: {exp['amount']:.2f} €/$"
            
            tx_lbl = ctk.CTkLabel(tx_frame, text=label_text, font=ctk.CTkFont(size=12))
            tx_lbl.pack(side="left", padx=10, pady=5)

            # Inline configuration command action buttons block frame
            btn_actions_frame = ctk.CTkFrame(tx_frame, fg_color="transparent")
            btn_actions_frame.pack(side="right", padx=5)

            edit_tx_btn = ctk.CTkButton(btn_actions_frame, text="Edit", fg_color="#1F6AA5", hover_color="#144A73",
                                       width=50, height=20, font=ctk.CTkFont(size=11),
                                       command=lambda e_data=exp: self.edit_transaction(e_data))
            edit_tx_btn.pack(side="left", padx=2, pady=5)

            del_tx_btn = ctk.CTkButton(btn_actions_frame, text="Delete", fg_color="#A94442", hover_color="#8A3331",
                                       width=50, height=20, font=ctk.CTkFont(size=11),
                                       command=lambda t_id=exp["db_id"]: self.remove_transaction(t_id))
            del_tx_btn.pack(side="left", padx=2, pady=5)

    def add_deposit(self):
        amount_str = self.dep_amount_entry.get().strip()
        payer = self.dep_dropdown.get()

        if not self.users or payer == "No users added yet":
            messagebox.showwarning("Logic Error", "Please add a real participant before depositing.")
            return

        try:
            amount = float(amount_str)
            if amount <= 0: raise ValueError
        except ValueError:
            messagebox.showwarning("Input Error", "Please enter a valid positive deposit amount.")
            return

        desc_str = f"Deposit into Wallet by {payer}"
        
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO expenses (description, amount, paid_by, participants, is_deposit) VALUES (?, ?, ?, ?, ?)",
                           (desc_str, amount, payer, "", 1))
            conn.close()
        except Exception as e:
            print(f"[Database Error] Save deposit failed: {e}")

        self.dep_amount_entry.delete(0, 'end')
        self.load_data_from_db()

    def add_expense(self):
        desc = self.desc_entry.get().strip()
        amount_str = self.amount_entry.get().strip()
        payer = self.payer_dropdown.get()

        if not self.users or payer == "No users added yet":
            messagebox.showwarning("Logic Error", "Add participants before tracking expenses.")
            return
        if not desc:
            messagebox.showwarning("Input Error", "Enter an item description.")
            return
        
        try:
            amount = float(amount_str)
            if amount <= 0: raise ValueError
        except ValueError:
            messagebox.showwarning("Input Error", "Enter a positive number for amount.")
            return

        if payer == "[WALLET]" and amount > self.wallet_balance:
            messagebox.showerror("Insufficient Funds", f"Wallet balance is too low ({self.wallet_balance:.2f}) to pay for this {amount:.2f} expense!")
            return

        current_expense_idx = len(self.expenses)
        allowed_participants = []
        for name, info in self.users.items():
            if info["joined_at_expense_idx"] <= current_expense_idx:
                allowed_participants.append(name)

        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            parts_str = ";".join(allowed_participants)
            cursor.execute("INSERT INTO expenses (description, amount, paid_by, participants, is_deposit) VALUES (?, ?, ?, ?, ?)",
                           (desc, amount, payer, parts_str, 0))
            conn.close()
        except Exception as e:
            print(f"[Database Error] Save expense failed: {e}")

        self.desc_entry.delete(0, 'end')
        self.amount_entry.delete(0, 'end')
        self.load_data_from_db()

    def calculate_balances(self):
        self.balances_textbox.configure(state="normal")
        self.balances_textbox.delete("1.0", "end")

        # Step 1: Evaluate Wallet Balance
        self.wallet_balance = 0.0
        for exp in self.expenses:
            if exp["is_deposit"]:
                self.wallet_balance += exp["amount"]
            elif exp["paid_by"] == "[WALLET]":
                self.wallet_balance -= exp["amount"]

        self.wallet_val_lbl.configure(text=f"{self.wallet_balance:.2f} €/$")

        if not self.users:
            self.balances_textbox.insert("end", "Add participants to see calculation balances.")
            self.balances_textbox.configure(state="disabled")
            return

        # Step 2: Accounting net logs
        net_balances = {user: 0.0 for user in self.users}

        for exp in self.expenses:
            amount = exp["amount"]
            payer = exp["paid_by"]

            if exp["is_deposit"]:
                if payer in net_balances:
                    net_balances[payer] += amount
            else:
                splitting_members = [m for m in exp["participants"] if m in net_balances]
                if not splitting_members:
                    splitting_members = list(self.users.keys())

                if not splitting_members: 
                    continue

                share = amount / len(splitting_members)

                if payer != "[WALLET]" and payer in net_balances:
                    net_balances[payer] += amount

                for user in splitting_members:
                    if user in net_balances:
                        net_balances[user] -= share

        # Step 3: Format the Output EXACTLY like Tricount
        display_text = "=========================================\n"
        display_text += "        INDIVIDUAL NET STATUS            \n"
        display_text += "=========================================\n"
        for user, balance in net_balances.items():
            if balance > 0.005:
                display_text += f"• {user:<12} : +{balance:.2f} €/$ (Owed money)\n"
            elif balance < -0.005:
                display_text += f"• {user:<12} :  {balance:.2f} €/$ (Owes money)\n"
            else:
                display_text += f"• {user:<12} :   0.00 €/$ (Even)\n"

        display_text += "\n=========================================\n"
        display_text += "         WHO OWES WHO HOW MUCH           \n"
        display_text += "=========================================\n"

        debtors = [[user, bal] for user, bal in net_balances.items() if bal < -0.005]
        creditors = [[user, bal] for user, bal in net_balances.items() if bal > 0.005]

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

        if not transactions and len(self.expenses) > 0:
            display_text += " 🎉 Everyone is perfectly even and settled!\n"
        elif not transactions:
            display_text += " ℹ️ No records logged yet.\n"
        else:
            display_text += "\n".join(transactions) + "\n"

        display_text += "=========================================\n"

        self.balances_textbox.insert("end", display_text)
        self.balances_textbox.configure(state="disabled")

    # ---- SQL Reload Handlers ----

    def load_data_from_db(self):
        """Brings back all data seamlessly from the SQLite database."""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # 1. Load users
            self.users.clear()
            cursor.execute("SELECT name, color, joined_index FROM users")
            for row in cursor.fetchall():
                self.users[row[0]] = {"color": row[1], "joined_at_expense_idx": row[2]}
                
            # 2. Load expenses
            self.expenses.clear()
            cursor.execute("SELECT id, description, amount, paid_by, participants, is_deposit FROM expenses")
            for row in cursor.fetchall():
                self.expenses.append({
                    "db_id": row[0],
                    "desc": row[1],
                    "amount": row[2],
                    "paid_by": row[3],
                    "participants": row[4].split(";") if row[4] else [],
                    "is_deposit": True if row[5] == 1 else False
                })
                
            conn.close()
            
            self.update_dropdowns()
            self.update_users_display()
            self.update_history_display()
            self.calculate_balances()
        except Exception as e:
            print(f"[Database Error] Reload data failed: {e}")


if __name__ == "__main__":
    try:
        app = TricountCloneApp()
        app.mainloop()
    except Exception as e:
        print("\n" + "="*50)
        print("CRITICAL RUNTIME ERROR DETECTED:")
        print("="*50)
        traceback.print_exc()
        print("="*50 + "\n")
        input("Press Enter to close this window...")