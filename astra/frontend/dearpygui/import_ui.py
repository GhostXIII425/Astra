import dearpygui.dearpygui as dpg
import logging
import os
from typing import Dict, Any, List
from astra.backend.storage.models import Transaction

logger = logging.getLogger(__name__)

class ImportUI:
    def __init__(self, api, on_import_complete):
        self.api = api
        self.on_import_complete = on_import_complete
        self.selected_file = None
        self.preview_data = None
        self.columns = []
        self.mapping = {"date": "", "description": "", "amount": "", "category": ""}

    def show(self):
        # Trigger file dialog
        if not dpg.does_item_exist("file_dialog_tag"):
            self._create_file_dialog()
        dpg.show_item("file_dialog_tag")

    def _create_file_dialog(self):
        with dpg.file_dialog(directory_selector=False, show=False, callback=self._file_selected_callback, tag="file_dialog_tag", width=600, height=400):
            dpg.add_file_extension(".csv", color=(255, 255, 0, 255))
            dpg.add_file_extension(".xlsx", color=(0, 255, 0, 255))
            dpg.add_file_extension(".xls", color=(0, 255, 0, 255))
            dpg.add_file_extension(".*", color=(255, 255, 255, 255))

    def _file_selected_callback(self, sender, app_data):
        self.selected_file = app_data['file_path_name']

        # Load preview
        self.preview_data = self.api.get_import_preview(self.selected_file)
        if "error" in self.preview_data:
            logger.error(f"Preview error: {self.preview_data['error']}")
            return

        self.columns = self.preview_data["columns"]
        self._show_mapping_modal()

    def _show_mapping_modal(self):
        if dpg.does_item_exist("import_modal"):
            dpg.delete_item("import_modal")

        with dpg.window(label="Map Columns", tag="import_modal", modal=True, width=700, height=600):
            dpg.add_text(f"File: {os.path.basename(self.selected_file)}")
            dpg.add_separator()

            with dpg.group(tag="mapping_group"):
                dpg.add_text("Map Columns")
                items = [""] + self.columns

                with dpg.group(horizontal=True):
                    with dpg.group():
                        dpg.add_text("Date Column:")
                        dpg.add_text("Description Column:")
                        dpg.add_text("Amount Column:")
                        dpg.add_text("Category Column (Optional):")
                    with dpg.group():
                        dpg.add_combo(items=items, tag="mapping_date", width=200, callback=self._update_mapping)
                        dpg.add_combo(items=items, tag="mapping_desc", width=200, callback=self._update_mapping)
                        dpg.add_combo(items=items, tag="mapping_amount", width=200, callback=self._update_mapping)
                        dpg.add_combo(items=items, tag="mapping_cat", width=200, callback=self._update_mapping)

                dpg.add_input_text(label="Date Format (e.g. %Y-%m-%d)", tag="import_date_format", default_value="%Y-%m-%d")

                # Resolve account selection
                accounts = self.api.get_accounts()
                acc_names = [a.name for a in accounts]
                dpg.add_combo(label="Import into Account", items=acc_names, tag="import_account_combo", width=200)
                if acc_names:
                    dpg.set_value("import_account_combo", acc_names[0])

                dpg.add_separator()
                dpg.add_text("Data Preview (First 10 rows)")
                with dpg.child_window(height=200, tag="preview_container"):
                    self._render_preview_table()

                dpg.add_separator()
                with dpg.group(horizontal=True):
                    dpg.add_button(label="Import", width=100, callback=self._import_callback)
                    dpg.add_button(label="Cancel", width=100, callback=lambda: dpg.delete_item("import_modal"))

        self._auto_map()

    def _auto_map(self):
        cols_lower = [c.lower() for c in self.columns]

        def find_match(targets):
            for i, c in enumerate(cols_lower):
                if any(t in c for t in targets):
                    return self.columns[i]
            return ""

        dpg.set_value("mapping_date", find_match(['date', 'time']))
        dpg.set_value("mapping_desc", find_match(['desc', 'memo', 'details', 'payee']))
        dpg.set_value("mapping_amount", find_match(['amount', 'value', 'total']))
        dpg.set_value("mapping_cat", find_match(['cat', 'type']))

        self._update_mapping()

    def _update_mapping(self):
        self.mapping["date"] = dpg.get_value("mapping_date")
        self.mapping["description"] = dpg.get_value("mapping_desc")
        self.mapping["amount"] = dpg.get_value("mapping_amount")
        self.mapping["category"] = dpg.get_value("mapping_cat")

    def _render_preview_table(self):
        if dpg.does_item_exist("preview_table"):
            dpg.delete_item("preview_table")

        rows = self.preview_data["rows"]
        with dpg.table(header_row=True, parent="preview_container", tag="preview_table", resizable=True, scrollX=True, scrollY=True):
            for col in self.columns:
                dpg.add_table_column(label=col)

            for row in rows:
                with dpg.table_row():
                    for col in self.columns:
                        dpg.add_text(str(row.get(col, "")))

    def _import_callback(self):
        if not self.selected_file:
            return

        mapping = {k: v for k, v in self.mapping.items() if v}
        date_format = dpg.get_value("import_date_format")
        acc_name = dpg.get_value("import_account_combo")

        # Ensure required fields are mapped
        if not mapping.get("date") or not mapping.get("description") or not mapping.get("amount"):
            logger.error("Required fields (Date, Description, Amount) must be mapped.")
            return

        # Resolve account_id
        accounts = self.api.get_accounts()
        account = next((a for a in accounts if a.name == acc_name), None)

        logger.info(f"Starting import of {self.selected_file} into {acc_name}")

        # Count transactions (this is a simplified count for the callback)
        # In a real app we might get the exact count from the parser
        count = len(self.preview_data.get("rows", []))

        self.api.import_transactions(self.selected_file, mapping=mapping, date_format=date_format, account_id=account.id if account else None)

        dpg.delete_item("import_modal")
        if self.on_import_complete:
            self.on_import_complete(count)
import pandas as pd
import os
from datetime import datetime
from astra.backend.storage.models import Transaction

class ImportUI:
    def __init__(self, api, on_complete):
        self.api = api
        self.on_complete = on_complete
        self.df = None
        self.mapping = {}

    def show_mapping(self, file_path):
        """Load the file and show the column mapping window."""
        ext = os.path.splitext(file_path)[1].lower()
        try:
            if ext == '.csv':
                self.df = pd.read_csv(file_path)
            elif ext in ['.xls', '.xlsx']:
                self.df = pd.read_excel(file_path)
            else:
                self.df = pd.read_csv(file_path, sep=None, engine='python')

            cols = list(self.df.columns)
        except Exception as e:
            print(f"Error loading file for mapping: {e}")
            return

        if dpg.does_item_exist("mapping_window"):
            dpg.delete_item("mapping_window")

        with dpg.window(label=f"Map Columns: {os.path.basename(file_path)}", modal=True, width=500, tag="mapping_window"):
            dpg.add_text("Select corresponding columns from your file:")

            dpg.add_combo(label="Date Column", items=cols, tag="map_date")
            dpg.add_combo(label="Amount Column", items=cols, tag="map_amount")
            dpg.add_combo(label="Description Column", items=cols, tag="map_desc")
            dpg.add_combo(label="Category Column (Optional)", items=cols + ["None"], tag="map_cat", default_value="None")

            with dpg.group(horizontal=True):
                dpg.add_button(label="Preview Import", callback=self._show_preview)
                dpg.add_button(label="Cancel", callback=lambda: dpg.delete_item("mapping_window"))

    def _show_preview(self):
        self.mapping = {
            "date": dpg.get_value("map_date"),
            "amount": dpg.get_value("map_amount"),
            "description": dpg.get_value("map_desc"),
            "category": dpg.get_value("map_cat")
        }

        if not self.mapping["date"] or not self.mapping["amount"] or not self.mapping["description"]:
            return

        # Build preview list
        preview_data = []
        for i, row in self.df.head(5).iterrows():
            preview_data.append({
                "date": str(row[self.mapping["date"]]),
                "amount": str(row[self.mapping["amount"]]),
                "desc": str(row[self.mapping["description"]])
            })

        if dpg.does_item_exist("preview_window"):
            dpg.delete_item("preview_window")

        with dpg.window(label="Import Preview", modal=True, width=600, tag="preview_window"):
            dpg.add_text("Top 5 records to be imported:")
            with dpg.table(header_row=True, resizable=True):
                dpg.add_table_column(label="Date")
                dpg.add_table_column(label="Description")
                dpg.add_table_column(label="Amount")
                for item in preview_data:
                    with dpg.table_row():
                        dpg.add_text(item["date"])
                        dpg.add_text(item["desc"])
                        dpg.add_text(item["amount"])

            with dpg.group(horizontal=True):
                dpg.add_button(label="Confirm Import", callback=self._finalize_import)
                dpg.add_button(label="Back", callback=lambda: dpg.delete_item("preview_window"))

    def _finalize_import(self, sender, app_data):
        count = 0
        for _, row in self.df.iterrows():
            try:
                date_val = row[self.mapping["date"]]
                amount_val = float(row[self.mapping["amount"]])
                desc_val = str(row[self.mapping["description"]])
                cat_val = str(row[self.mapping["category"]]) if self.mapping["category"] != "None" else "Uncategorized"

                tx = Transaction(
                    date=pd.to_datetime(date_val).to_pydatetime(),
                    amount=amount_val,
                    description=desc_val,
                    category=cat_val
                )
                self.api.add_manual_transaction(tx)
                count += 1
            except Exception:
                continue

        dpg.delete_item("preview_window")
        dpg.delete_item("mapping_window")
        self.on_complete(count)
