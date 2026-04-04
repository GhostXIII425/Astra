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
        self._parent = "main_window"
        self.import_ui = ImportUI(self.api, on_import_complete=lambda: self.show(parent=self._parent))

    def show(self, parent="main_window"):
        self._parent = parent
        dpg.delete_item(parent, children_only=True)

        with dpg.tab_bar(parent=parent):
            with dpg.tab(label="Overview"):
                self._render_overview()

            with dpg.tab(label="Transactions"):
                self._render_transactions()

            with dpg.tab(label="Accounts"):
                self._render_accounts()

            with dpg.tab(label="Charts"):
                self._render_charts()

            with dpg.tab(label="Settings"):
                self._render_settings()

    def _render_overview(self):
        summary = self.api.get_summary()
        dpg.add_text(f"Welcome to Astra")
        dpg.add_separator()

        with dpg.group(horizontal=True):
            dpg.add_text(f"Total Income: {summary.get('total_income', 0):.2f}")
            dpg.add_button(label="Refresh", callback=lambda: self.show(parent=self._parent))
            with dpg.tooltip(dpg.last_item()):
                dpg.add_text("Reload data from the backend and refresh all tabs.")

        dpg.add_text(f"Total Spent: {summary.get('total_spent', 0):.2f}")

    def _render_transactions(self):
        """Render the transactions table and manual/import controls."""
        with dpg.group():
            with dpg.group(horizontal=True):
                dpg.add_button(label="Manual Entry", callback=self._show_manual_entry)
                dpg.add_button(label="Import Transactions...", callback=self.import_ui.show)
            dpg.add_separator()

            txs = self.api.get_transactions()
            with dpg.table(header_row=True, resizable=True, policy=dpg.mvTable_SizingStretchProp):
                dpg.add_table_column(label="Date")
                dpg.add_table_column(label="Description")
                dpg.add_table_column(label="Amount")
                dpg.add_table_column(label="Category")
                dpg.add_table_column(label="Action")

                for tx in txs:
                    with dpg.table_row():
                        dpg.add_text(tx.date.strftime("%Y-%m-%d"))
                        dpg.add_text(tx.description)
                        dpg.add_text(f"{tx.amount:.2f}")

                        if tx.is_confirmed:
                            dpg.add_text(tx.category)
                            dpg.add_text("Confirmed")
                        else:
                            with dpg.group(horizontal=True):
                                dpg.add_text(f"{tx.category}")
                                dpg.add_button(label="Confirm", callback=lambda s, a, u=tx: self._confirm_callback(u))
                                with dpg.tooltip(dpg.last_item()):
                                    dpg.add_text("Confirm this category prediction to update rules.")

    def _render_accounts(self):
        with dpg.group():
            dpg.add_button(label="Add Account", callback=self._show_add_account)
            dpg.add_separator()

            accounts = self.api.get_accounts()
            with dpg.table(header_row=True, resizable=True):
                dpg.add_table_column(label="Name")
                dpg.add_table_column(label="Type")
                dpg.add_table_column(label="Balance")

                for acc in accounts:
                    with dpg.table_row():
                        dpg.add_text(acc.name)
                        dpg.add_text(acc.type.value)
                        dpg.add_text(f"{acc.balance:.2f}")

    def _render_charts(self):
        """Render charts using aggregated spending data."""
        categories = self.api.get_category_spending()
        if not categories:
            dpg.add_text("No data to display charts")
            return

        with dpg.plot(label="Spending by Category", height=400, width=-1):
            dpg.add_plot_legend()
            x_labels = list(categories.keys())
            x_indices = list(range(len(x_labels)))
            with dpg.plot_axis(dpg.mvXAxis, label="Category"):
                dpg.set_axis_ticks(dpg.last_item(), tuple((x_labels[i], x_indices[i]) for i in range(len(x_labels))))
            with dpg.plot_axis(dpg.mvYAxis, label="Amount"):
                dpg.add_bar_series(x_indices, list(categories.values()), label="Spending")

    def _render_settings(self):
        dpg.add_button(label="Toggle Light/Dark Mode", callback=self._toggle_theme)
        dpg.add_separator()
        dpg.add_button(label="Logout", callback=self.on_logout)
        dpg.add_button(label="Exit App", callback=dpg.stop_dearpygui)

    def _show_manual_entry(self):
        with dpg.window(label="Manual Transaction Entry", modal=True, width=400):
            dpg.add_input_text(label="Date (YYYY-MM-DD)", tag="m_date", default_value=datetime.now().strftime("%Y-%m-%d"))
            dpg.add_input_float(label="Amount", tag="m_amount")
            dpg.add_input_text(label="Description", tag="m_desc")
            dpg.add_input_text(label="Category", tag="m_cat")

            accounts = self.api.get_accounts()
            acc_names = [a.name for a in accounts]
            dpg.add_combo(label="Account", items=acc_names, tag="m_acc")

            with dpg.group(horizontal=True):
                dpg.add_button(label="Save", callback=self._save_manual_entry)
                dpg.add_button(label="Cancel", callback=lambda s, a, u: dpg.delete_item(dpg.get_item_parent(s)))

    def _save_manual_entry(self, sender, app_data):
        try:
            acc_name = dpg.get_value("m_acc")
            accounts = self.api.get_accounts()
            account = next((a for a in accounts if a.name == acc_name), None)

            tx = Transaction(
                date=datetime.fromisoformat(dpg.get_value("m_date")),
                amount=dpg.get_value("m_amount"),
                description=dpg.get_value("m_desc"),
                category=dpg.get_value("m_cat") or "Uncategorized",
                account_id=account.id if account else None
            )
            self.api.add_manual_transaction(tx)
            dpg.delete_item(dpg.get_item_parent(sender))
            self.show(parent=self._parent)
            self._update_global_status("Transaction added", color=(0, 255, 0))
        except Exception as e:
            self._update_global_status(f"Error: {e}", color=(255, 0, 0))

    def _show_add_account(self):
        with dpg.window(label="Add Account", modal=True, width=300):
            dpg.add_input_text(label="Account Name", tag="a_name")
            dpg.add_combo(label="Type", items=[t.value for t in AccountType], tag="a_type", default_value=AccountType.CHECKING.value)
            dpg.add_input_float(label="Initial Balance", tag="a_bal")

            with dpg.group(horizontal=True):
                dpg.add_button(label="Save", callback=self._save_account)
                dpg.add_button(label="Cancel", callback=lambda s, a, u: dpg.delete_item(dpg.get_item_parent(s)))

    def _save_account(self, sender, app_data):
        acc = Account(
            name=dpg.get_value("a_name"),
            type=AccountType(dpg.get_value("a_type")),
            balance=dpg.get_value("a_bal")
        )
        self.api.add_account(acc)
        dpg.delete_item(dpg.get_item_parent(sender))
        self.show(parent=self._parent)
        self._update_global_status("Account added", color=(0, 255, 0))

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
        self._update_global_status(f"Confirming {tx.id}...", color=(255, 255, 0))
        try:
            self.api.confirm_transaction(tx.id, tx.category)
            self._update_global_status(f"Confirmed: {tx.category}", color=(0, 255, 0))
            self.show(parent=self._parent)
        except Exception as e:
            self._update_global_status("Confirmation failed", color=(255, 0, 0))

    def _update_global_status(self, message, color=(0, 255, 0)):
        if dpg.does_item_exist("global_status"):
            dpg.set_value("global_status", message)
            dpg.configure_item("global_status", color=color)
