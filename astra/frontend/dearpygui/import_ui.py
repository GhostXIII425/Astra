import dearpygui.dearpygui as dpg
import logging
import os
from typing import Dict, Any, List

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
        if not dpg.does_item_exist("import_modal"):
            self._create_modal()
        dpg.configure_item("import_modal", show=True)

    def _create_modal(self):
        with dpg.window(label="Import Transactions", tag="import_modal", modal=True, show=False, width=700, height=600, no_scrollbar=False):
            with dpg.group(horizontal=True):
                dpg.add_button(label="Select File...", callback=self._open_file_dialog)
                dpg.add_text("No file selected", tag="selected_file_text")

            dpg.add_separator()

            with dpg.group(tag="mapping_group", show=False):
                dpg.add_text("Map Columns")
                with dpg.group(horizontal=True):
                    with dpg.group():
                        dpg.add_text("Date Column:")
                        dpg.add_text("Description Column:")
                        dpg.add_text("Amount Column:")
                        dpg.add_text("Category Column (Optional):")
                    with dpg.group():
                        dpg.add_combo(tag="mapping_date", width=200, callback=self._update_mapping)
                        dpg.add_combo(tag="mapping_desc", width=200, callback=self._update_mapping)
                        dpg.add_combo(tag="mapping_amount", width=200, callback=self._update_mapping)
                        dpg.add_combo(tag="mapping_cat", width=200, callback=self._update_mapping)

                dpg.add_input_text(label="Date Format (e.g. %Y-%m-%d)", tag="import_date_format", default_value="%Y-%m-%d")

                dpg.add_separator()
                dpg.add_text("Data Preview (First 10 rows)")
                with dpg.child_window(height=200, tag="preview_container"):
                    pass # Table will be added here

                dpg.add_separator()
                with dpg.group(horizontal=True):
                    dpg.add_button(label="Import", width=100, callback=self._import_callback)
                    dpg.add_button(label="Cancel", width=100, callback=lambda: dpg.configure_item("import_modal", show=False))

        # File Dialog
        with dpg.file_dialog(directory_selector=False, show=False, callback=self._file_selected_callback, tag="file_dialog_tag", width=600, height=400):
            dpg.add_file_extension(".csv", color=(255, 255, 0, 255))
            dpg.add_file_extension(".xlsx", color=(0, 255, 0, 255))
            dpg.add_file_extension(".xls", color=(0, 255, 0, 255))
            dpg.add_file_extension(".*", color=(255, 255, 255, 255))

    def _open_file_dialog(self):
        dpg.show_item("file_dialog_tag")

    def _file_selected_callback(self, sender, app_data):
        self.selected_file = app_data['file_path_name']
        dpg.set_value("selected_file_text", f"File: {os.path.basename(self.selected_file)}")

        # Load preview
        self.preview_data = self.api.get_import_preview(self.selected_file)
        if "error" in self.preview_data:
            logger.error(f"Preview error: {self.preview_data['error']}")
            return

        self.columns = self.preview_data["columns"]

        # Update combos
        items = [""] + self.columns
        dpg.configure_item("mapping_date", items=items)
        dpg.configure_item("mapping_desc", items=items)
        dpg.configure_item("mapping_amount", items=items)
        dpg.configure_item("mapping_cat", items=items)

        # Auto-mapping heuristic
        self._auto_map()

        # Show mapping group and update preview table
        dpg.show_item("mapping_group")
        self._render_preview_table()

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

        # Ensure required fields are mapped
        if not mapping.get("date") or not mapping.get("description") or not mapping.get("amount"):
            logger.error("Required fields (Date, Description, Amount) must be mapped.")
            # We should probably show a UI warning here
            return

        logger.info(f"Starting import of {self.selected_file}")
        self.api.import_transactions(self.selected_file, mapping=mapping, date_format=date_format)

        dpg.configure_item("import_modal", show=False)
        if self.on_import_complete:
            self.on_import_complete()
