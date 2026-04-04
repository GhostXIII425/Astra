import dearpygui.dearpygui as dpg
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
