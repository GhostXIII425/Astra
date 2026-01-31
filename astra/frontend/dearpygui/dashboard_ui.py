import dearpygui.dearpygui as dpg

class DashboardUI:
    def __init__(self, api, on_logout):
        self.api = api
        self.on_logout = on_logout

    def show(self):
        dpg.delete_item("main_window", children_only=True)

        with dpg.tab_bar(parent="main_window"):
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
        dpg.add_text(f"Total Income: {summary.get('total_income', 0):.2f}")
        dpg.add_text(f"Total Spent: {summary.get('total_spent', 0):.2f}")

    def _render_transactions(self):
        """Render the transactions table and import controls."""
        with dpg.group():
            with dpg.group(horizontal=True):
                dpg.add_input_text(label="File Path", tag="import_path", width=300)
                dpg.add_button(label="Import", callback=self._import_callback)
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
        summary = self.api.get_summary()
        categories = summary.get("categories", {})

        if not categories:
            dpg.add_text("No data to display charts")
            return

        with dpg.plot(label="Spending by Category", height=400, width=-1):
            dpg.add_plot_legend()
            dpg.add_plot_axis(dpg.mvXAxis, label="Category")
            with dpg.plot_axis(dpg.mvYAxis, label="Amount"):
                # Simplified bar chart
                x = list(range(len(categories)))
                y = list(categories.values())
                labels = list(categories.keys())
                dpg.add_bar_series(x, y, label="Spending")

    def _render_settings(self):
        dpg.add_button(label="Logout", callback=self.on_logout)

    def _confirm_callback(self, tx):
        """Callback to confirm a transaction's category."""
        self.api.confirm_transaction(tx.id, tx.category)
        self.show() # Refresh

    def _import_callback(self):
        """Callback to import transactions from a file path."""
        path = dpg.get_value("import_path")
        if path:
            self.api.import_transactions(path)
            self.show() # Refresh
