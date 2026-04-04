import dearpygui.dearpygui as dpg
import logging
from astra.backend.services.api import AstraAPI
from astra.frontend.dearpygui.dashboard_ui import DashboardUI
from astra.frontend.dearpygui.logger import setup_gui_logging

logger = logging.getLogger(__name__)

class AstraApp:
    def __init__(self):
        self.api = AstraAPI()

        dpg.create_context()
        self.dashboard_ui = DashboardUI(self.api, self.on_logout)

        with dpg.window(tag="main_window", label="Astra - Offline Budgeting", width=800, height=600, no_title_bar=False):
            with dpg.group(tag="content_group"):
                pass

            dpg.add_spacer(height=10)
            dpg.add_separator()
            with dpg.group(horizontal=True):
                dpg.add_text("Status:")
                dpg.add_text("Ready", tag="global_status", color=(0, 255, 0))

            dpg.add_separator()
            with dpg.collapsing_header(label="Debug Console", default_open=False):
                dpg.add_input_text(multiline=True, readonly=True, tag="debug_console", width=-1, height=150)

        setup_gui_logging("debug_console")
        logger.info("Astra application initialized in offline mode")

        # Hotkeys
        with dpg.handler_registry():
            dpg.add_key_press_handler(dpg.mvKey_R, callback=self._hotkey_handler)

        dpg.create_viewport(title='Astra - Personal Finance', width=800, height=600)
        dpg.setup_dearpygui()
        dpg.show_viewport()
        dpg.set_primary_window("main_window", True)

        self.show_unlock()

    def show_unlock(self):
        dpg.delete_item("content_group", children_only=True)
        with dpg.group(parent="content_group"):
            dpg.add_text("Astra Vault is Locked")
            dpg.add_input_text(label="Vault Key", tag="vault_key", password=True)
            dpg.add_button(label="Unlock", callback=self._unlock_callback)

    def _unlock_callback(self):
        key = dpg.get_value("vault_key")
        if self.api.unlock(key):
            logger.info("Vault unlocked successfully")
            self.dashboard_ui.show(parent="content_group")
        else:
            logger.error("Failed to unlock vault")

    def on_logout(self):
        logger.info("Application session ended, locking vault")
        self.api.db_manager.encryption = None
        self.show_unlock()
        # Go straight to dashboard
        self.dashboard_ui.show(parent="content_group")

    def on_logout(self):
        # In offline mode, logout might just lock the app with PIN
        # For now, we'll just exit or log
        logger.info("Application session ended")

    def _hotkey_handler(self, sender, app_data):
        if dpg.is_key_down(dpg.mvKey_Control):
            if app_data == dpg.mvKey_R:
                logger.info("Hotkey triggered: Refresh")
                if self.api.is_unlocked():
                    self.dashboard_ui.show(parent="content_group")
                self.dashboard_ui.show(parent="content_group")

    def run(self):
        try:
            while dpg.is_dearpygui_running():
                dpg.render_dearpygui_frame()
        except Exception:
            pass
        finally:
            dpg.destroy_context()

if __name__ == "__main__":
    app = AstraApp()
    app.run()
