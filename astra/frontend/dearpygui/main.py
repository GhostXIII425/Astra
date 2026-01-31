import dearpygui.dearpygui as dpg
import logging
from astra.backend.services.api import AstraAPI
from astra.frontend.dearpygui.auth_ui import AuthUI
from astra.frontend.dearpygui.dashboard_ui import DashboardUI
from astra.frontend.dearpygui.logger import setup_gui_logging

logger = logging.getLogger(__name__)

class AstraApp:
    def __init__(self):
        self.api = AstraAPI()

        dpg.create_context()

        self.auth_ui = AuthUI(self.api, self.on_login_success)
        self.dashboard_ui = DashboardUI(self.api, self.on_logout)

        with dpg.window(tag="main_window", label="Astra", width=800, height=600, no_title_bar=False):
            with dpg.group(tag="content_group"):
                pass

            dpg.add_separator()
            with dpg.collapsing_header(label="Debug Console", default_open=False):
                dpg.add_input_text(multiline=True, readonly=True, tag="debug_console", width=-1, height=150)

        setup_gui_logging("debug_console")
        logger.info("Astra application initialized")

        # Hotkeys
        with dpg.handler_registry():
            dpg.add_key_press_handler(dpg.mvKey_R, callback=self._hotkey_handler)

        dpg.create_viewport(title='Astra - Personal Finance', width=800, height=600)
        dpg.setup_dearpygui()
        dpg.show_viewport()
        dpg.set_primary_window("main_window", True)

        self.auth_ui.show_login(parent="content_group")

    def on_login_success(self):
        dpg.delete_item("content_group", children_only=True)
        self.dashboard_ui.show(parent="content_group")
        logger.info(f"User {self.api.get_current_user().username} logged in")

    def on_logout(self):
        username = self.api.get_current_user().username
        self.api.logout()
        dpg.delete_item("content_group", children_only=True)
        self.auth_ui.show_login(parent="content_group")
        logger.info(f"User {username} logged out")

    def _hotkey_handler(self, sender, app_data):
        # Check if Ctrl is pressed
        if dpg.is_key_down(dpg.mvKey_Control):
            # Ctrl+R: Refresh
            if app_data == dpg.mvKey_R:
                logger.info("Hotkey triggered: Refresh")
                if self.api.get_current_user():
                    self.on_login_success()

    def run(self):
        # In a headless environment, this might fail or do nothing
        # But for the skeleton, we provide the run logic
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
