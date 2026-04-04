import dearpygui.dearpygui as dpg
import logging
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

            with dpg.tab(label="Charts"):
                self._render_charts()

            with dpg.tab(label="Settings"):
                self._render_settings()

    def _render_overview(self):
        summary = self.api.get_summary()
        dpg.add_text(f"Welcome, {self.api.get_current_user().username}!")
        dpg.add_separator()

        with dpg.group(horizontal=True):
            dpg.add_text(f"Total Income: {summary.get('total_income', 0):.2f}")
            dpg.add_button(label="Refresh", callback=lambda: self.show(parent=self._parent))

        dpg.add_text(f"Total Spent: {summary.get('total_spent', 0):.2f}")

    def _render_transactions(self):
        """Render the transactions table and import controls."""
        with dpg.group():
            with dpg.group(horizontal=True):
                # Replace old file path input with an "Import" button
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
                            # Show prediction and a confirm button
                            with dpg.group(horizontal=True):
                                dpg.add_text(f"{tx.category} ({tx.confidence:.1%})")
                                dpg.add_button(label="Confirm", callback=lambda s, a, u=tx: self._confirm_callback(u))

    def _render_charts(self):
        """Render charts using aggregated spending data."""
        categories = self.api.get_category_spending()

        if not categories:
            dpg.add_text("No data to display charts")
            return

        with dpg.plot(label="Spending by Category", height=400, width=-1):
            dpg.add_plot_legend()

            # Setup X Axis with category labels
            x_labels = list(categories.keys())
            x_indices = list(range(len(x_labels)))

            with dpg.plot_axis(dpg.mvXAxis, label="Category"):
                dpg.set_axis_ticks(dpg.last_item(), tuple((x_labels[i], x_indices[i]) for i in range(len(x_labels))))

            with dpg.plot_axis(dpg.mvYAxis, label="Amount"):
                dpg.add_bar_series(x_indices, list(categories.values()), label="Spending")

    def _render_settings(self):
        dpg.add_button(label="Toggle Light/Dark Mode", callback=self._toggle_theme)
        dpg.add_button(label="Manual Model Retrain", callback=self._retrain_callback)
        dpg.add_separator()
        dpg.add_button(label="Logout", callback=self.on_logout)

    def _toggle_theme(self):
        self._dark_mode = not self._dark_mode
        if self._dark_mode:
            dpg.bind_theme(0)  # Use DPG internal default
            logger.info("Switched to Dark Mode")
        else:
            # Simple light theme setup
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

    def _retrain_callback(self):
        logger.info("Manual retraining triggered")
        user_id = self.api.get_current_user().id
        txs = self.api.get_transactions()
        self.api.ml_engines[user_id].train(txs)
        logger.info("Model retrained successfully")

    def _confirm_callback(self, tx):
        """Callback to confirm a transaction's category."""
        self.api.confirm_transaction(tx.id, tx.category)
        logger.info(f"Confirmed transaction {tx.id} as {tx.category}")
        self.show(parent=self._parent)
