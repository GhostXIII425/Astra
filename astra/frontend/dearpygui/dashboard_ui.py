import dearpygui.dearpygui as dpg
import logging
from datetime import datetime
from astra.backend.storage.models import Transaction, Account, AccountType
from astra.frontend.dearpygui.import_ui import ImportUI

logger = logging.getLogger(__name__)

class DashboardUI:
    def __init__(self, api, on_logout):
        self.api = api
        self.on_logout = on_logout
        self._dark_mode = True
        self._parent = "content_group"
        self.import_ui = ImportUI(self.api, on_import_complete=self._on_import_complete)

    def show(self, parent="content_group"):
        self._parent = parent
        if not dpg.does_item_exist(parent):
            logger.error(f"Dashboard parent {parent} does not exist.")
            return

        # Clear parent carefully
        children = dpg.get_item_children(parent, 1)
        for child in children:
            dpg.delete_item(child)

        with dpg.tab_bar(parent=parent, tag="dashboard_tabs"):
            with dpg.tab(label="Overview", tag="tab_overview"):
                self._render_overview()

            with dpg.tab(label="Transactions", tag="tab_transactions"):
                self._render_transactions()

            with dpg.tab(label="Accounts", tag="tab_accounts"):
                self._render_accounts()

            with dpg.tab(label="Settings", tag="tab_settings"):
                self._render_settings()

    def _render_overview(self):
        summary = self.api.get_summary()
        dpg.add_text("Astra Financial Overview", parent="tab_overview")
        dpg.add_separator(parent="tab_overview")

        with dpg.group(horizontal=True, parent="tab_overview"):
            dpg.add_text("Total Income: ")
            dpg.add_text(f"{summary.get('total_income', 0):.2f}", color=(0, 255, 0))

            dpg.add_spacer(width=20)

            dpg.add_text("Total Spent: ")
            dpg.add_text(f"{summary.get('total_spent', 0):.2f}", color=(255, 100, 100))

            dpg.add_spacer(width=40)
            dpg.add_button(label="Refresh All", callback=lambda: self.show(parent=self._parent))
            with dpg.tooltip(dpg.last_item()):
                dpg.add_text("Sync with database and refresh all views.")

    def _render_transactions(self):
        """Render the transactions table and manual/import controls."""
        with dpg.group(parent="tab_transactions"):
            with dpg.group(horizontal=True):
                dpg.add_button(label="Manual Entry", callback=self._show_manual_entry)
                dpg.add_button(label="Import Transactions...", callback=self.import_ui.show)
            dpg.add_separator()

            txs = self.api.get_transactions()
            accounts = self.api.get_accounts()
            acc_map = {a.id: a.name for a in accounts}

            with dpg.table(header_row=True, resizable=True, policy=dpg.mvTable_SizingStretchProp,
                          borders_outerH=True, borders_innerV=True, borders_innerH=True):
                dpg.add_table_column(label="Date", width_fixed=True)
                dpg.add_table_column(label="Account")
                dpg.add_table_column(label="Description")
                dpg.add_table_column(label="Amount", width_fixed=True)
                dpg.add_table_column(label="Category")
                dpg.add_table_column(label="Status")
                dpg.add_table_column(label="Actions", width_fixed=True)

                for tx in txs:
                    with dpg.table_row():
                        dpg.add_text(tx.date.strftime("%Y-%m-%d"))
                        dpg.add_text(acc_map.get(tx.account_id, "Unknown"))
                        dpg.add_text(tx.description)

                        amount_color = (255, 100, 100) if tx.amount < 0 else (0, 255, 0)
                        dpg.add_text(f"{tx.amount:.2f}", color=amount_color)

                        if tx.is_confirmed:
                            dpg.add_text(tx.category)
                            dpg.add_text("Confirmed", color=(0, 255, 0))
                        else:
                            dpg.add_text(tx.category, color=(200, 200, 100))
                            dpg.add_text("Predicted", color=(200, 200, 100))

                        with dpg.group(horizontal=True):
                            if not tx.is_confirmed:
                                dpg.add_button(label="Confirm", callback=lambda s, a, u=tx: self._confirm_callback(u))
                                with dpg.tooltip(dpg.last_item()):
                                    dpg.add_text("Accept this categorization.")

                            dpg.add_button(label="Delete", callback=lambda s, a, u=tx: self._show_delete_tx_modal(u))
                            with dpg.tooltip(dpg.last_item()):
                                dpg.add_text("Permanently remove this transaction.")

    def _render_accounts(self):
        with dpg.group(parent="tab_accounts"):
            dpg.add_button(label="Add New Account", callback=self._show_add_account)
            dpg.add_separator()

            accounts = self.api.get_accounts()
            if not accounts:
                dpg.add_text("No accounts found. Create one to get started!")
                return

            with dpg.table(header_row=True, resizable=True, borders_outerH=True, borders_innerV=True):
                dpg.add_table_column(label="Account Name")
                dpg.add_table_column(label="Type")
                dpg.add_table_column(label="Institution")
                dpg.add_table_column(label="Current Balance")
                dpg.add_table_column(label="Actions")

                for acc in accounts:
                    with dpg.table_row():
                        dpg.add_text(acc.name)
                        dpg.add_text(acc.type.value)
                        dpg.add_text(acc.institution)
                        dpg.add_text(f"{acc.balance:.2f}", color=(0, 255, 0) if acc.balance >= 0 else (255, 100, 100))
                        with dpg.group(horizontal=True):
                            dpg.add_button(label="Clear Data", callback=lambda s, a, u=acc: self._show_clear_account_modal(u))
                            with dpg.tooltip(dpg.last_item()):
                                dpg.add_text("Delete all transactions for this account.")

                            dpg.add_button(label="Delete", callback=lambda s, a, u=acc: self._show_delete_account_modal(u))
                            with dpg.tooltip(dpg.last_item()):
                                dpg.add_text("Delete account and all its transactions.")

    def _render_settings(self):
        with dpg.group(width=300, parent="tab_settings"):
            dpg.add_button(label="Toggle Light/Dark Mode", callback=self._toggle_theme, width=-1)
            dpg.add_spacer(height=10)
            dpg.add_button(label="Lock Vault & Logout", callback=self.on_logout, width=-1)
            dpg.add_separator()
            dpg.add_button(label="Exit Astra", callback=dpg.stop_dearpygui, width=-1)

    def _show_delete_tx_modal(self, tx):
        if dpg.does_item_exist("modal_confirm"):
            dpg.delete_item("modal_confirm")

        with dpg.window(label="Confirm Deletion", modal=True, tag="modal_confirm", width=300):
            dpg.add_text(f"Delete transaction: {tx.description}?")
            with dpg.group(horizontal=True):
                dpg.add_button(label="Delete", width=100, callback=lambda: self._delete_tx_callback(tx))
                dpg.add_button(label="Cancel", width=100, callback=lambda: dpg.delete_item("modal_confirm"))

    def _delete_tx_callback(self, tx):
        self.api.delete_transaction(tx.id)
        dpg.delete_item("modal_confirm")
        self.show(parent=self._parent)
        self._update_global_status("Transaction deleted", color=(255, 200, 0))

    def _show_clear_account_modal(self, acc):
        if dpg.does_item_exist("modal_confirm"):
            dpg.delete_item("modal_confirm")

        with dpg.window(label="Clear Account Data", modal=True, tag="modal_confirm", width=350):
            dpg.add_text(f"Delete ALL transactions for account '{acc.name}'?")
            dpg.add_text("This action cannot be undone.", color=(255, 0, 0))
            with dpg.group(horizontal=True):
                dpg.add_button(label="Clear All", width=100, callback=lambda: self._clear_account_callback(acc))
                dpg.add_button(label="Cancel", width=100, callback=lambda: dpg.delete_item("modal_confirm"))

    def _clear_account_callback(self, acc):
        self.api.clear_account_data(acc.id)
        dpg.delete_item("modal_confirm")
        self.show(parent=self._parent)
        self._update_global_status(f"Cleared data for '{acc.name}'", color=(255, 200, 0))

    def _show_delete_account_modal(self, acc):
        if dpg.does_item_exist("modal_confirm"):
            dpg.delete_item("modal_confirm")

        with dpg.window(label="Delete Account", modal=True, tag="modal_confirm", width=350):
            dpg.add_text(f"Delete account '{acc.name}' and all its data?")
            dpg.add_text("This action cannot be undone.", color=(255, 0, 0))
            with dpg.group(horizontal=True):
                dpg.add_button(label="Delete Account", width=120, callback=lambda: self._delete_account_callback(acc))
                dpg.add_button(label="Cancel", width=100, callback=lambda: dpg.delete_item("modal_confirm"))

    def _delete_account_callback(self, acc):
        self.api.delete_account(acc.id)
        dpg.delete_item("modal_confirm")
        self.show(parent=self._parent)
        self._update_global_status(f"Account '{acc.name}' deleted", color=(255, 100, 100))

    def _show_manual_entry(self):
        if dpg.does_item_exist("modal_manual_entry"):
            dpg.delete_item("modal_manual_entry")

        with dpg.window(label="Manual Transaction Entry", modal=True, width=400, tag="modal_manual_entry"):
            dpg.add_input_text(label="Date (YYYY-MM-DD)", tag="m_date", default_value=datetime.now().strftime("%Y-%m-%d"))
            dpg.add_input_float(label="Amount", tag="m_amount")
            dpg.add_input_text(label="Description", tag="m_desc")
            dpg.add_input_text(label="Category (Optional)", tag="m_cat")

            accounts = self.api.get_accounts()
            acc_names = [a.name for a in accounts]
            dpg.add_combo(label="Account", items=acc_names, tag="m_acc")
            if acc_names:
                dpg.set_value("m_acc", acc_names[0])

            with dpg.group(horizontal=True):
                dpg.add_button(label="Save", width=100, callback=self._save_manual_entry)
                dpg.add_button(label="Cancel", width=100, callback=lambda: dpg.delete_item("modal_manual_entry"))

    def _save_manual_entry(self, sender, app_data):
        try:
            desc = dpg.get_value("m_desc")
            if not desc:
                self._update_global_status("Description is required", color=(255, 0, 0))
                return

            acc_name = dpg.get_value("m_acc")
            accounts = self.api.get_accounts()
            account = next((a for a in accounts if a.name == acc_name), None)

            tx = Transaction(
                date=datetime.fromisoformat(dpg.get_value("m_date")),
                amount=dpg.get_value("m_amount"),
                description=desc,
                category=dpg.get_value("m_cat") or "Uncategorized",
                account_id=account.id if account else None
            )
            self.api.add_manual_transaction(tx)
            dpg.delete_item("modal_manual_entry")
            self.show(parent=self._parent)
            self._update_global_status("Transaction added", color=(0, 255, 0))
        except Exception as e:
            self._update_global_status(f"Error: {e}", color=(255, 0, 0))

    def _show_add_account(self):
        if dpg.does_item_exist("modal_add_account"):
            dpg.delete_item("modal_add_account")

        with dpg.window(label="Add Account", modal=True, width=300, tag="modal_add_account"):
            dpg.add_input_text(label="Account Name", tag="a_name")
            dpg.add_combo(label="Type", items=[t.value for t in AccountType], tag="a_type", default_value=AccountType.CHECKING.value)
            dpg.add_input_text(label="Institution", tag="a_inst")
            dpg.add_input_float(label="Initial Balance", tag="a_bal")

            with dpg.group(horizontal=True):
                dpg.add_button(label="Save", width=100, callback=self._save_account)
                dpg.add_button(label="Cancel", width=100, callback=lambda: dpg.delete_item("modal_add_account"))

    def _save_account(self, sender, app_data):
        name = dpg.get_value("a_name")
        if not name:
            self._update_global_status("Account name is required", color=(255, 0, 0))
            return

        acc = Account(
            name=name,
            type=AccountType(dpg.get_value("a_type")),
            institution=dpg.get_value("a_inst"),
            balance=dpg.get_value("a_bal")
        )
        self.api.add_account(acc)
        dpg.delete_item("modal_add_account")
        self.show(parent=self._parent)
        self._update_global_status(f"Account '{name}' added", color=(0, 255, 0))

    def _toggle_theme(self):
        self._dark_mode = not self._dark_mode
        if self._dark_mode:
            dpg.bind_theme(0)
            logger.info("Switched to Dark Mode")
        else:
            with dpg.theme() as light_theme:
                with dpg.theme_component(dpg.mvAll):
                    dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (240, 240, 240))
                    dpg.add_theme_color(dpg.mvThemeCol_ChildBg, (240, 240, 240))
                    dpg.add_theme_color(dpg.mvThemeCol_Text, (0, 0, 0))
                    dpg.add_theme_color(dpg.mvThemeCol_Button, (200, 200, 200))
                    dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (180, 180, 180))
                    dpg.add_theme_color(dpg.mvThemeCol_Header, (170, 170, 170))
                    dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (255, 255, 255))
            dpg.bind_theme(light_theme)
            logger.info("Switched to Light Mode")

    def _confirm_callback(self, tx):
        self._update_global_status(f"Confirming...", color=(255, 255, 0))
        try:
            self.api.confirm_transaction(tx.id, tx.category)
            self._update_global_status(f"Confirmed: {tx.category}", color=(0, 255, 0))
            self.show(parent=self._parent)
        except Exception as e:
            self._update_global_status("Confirmation failed", color=(255, 0, 0))

    def _on_import_complete(self, count):
        self._update_global_status(f"Imported {count} transactions successfully", color=(0, 255, 0))
        self.show(parent=self._parent)

    def _update_global_status(self, message, color=(0, 255, 0)):
        if dpg.does_item_exist("global_status"):
            dpg.set_value("global_status", message)
            dpg.configure_item("global_status", color=color)
