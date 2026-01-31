import dearpygui.dearpygui as dpg
from astra.backend.services.api import AstraAPI
from astra.frontend.dearpygui.auth_ui import AuthUI
from astra.frontend.dearpygui.dashboard_ui import DashboardUI

class AstraApp:
    def __init__(self):
        self.api = AstraAPI()

        dpg.create_context()

        self.auth_ui = AuthUI(self.api, self.on_login_success)
        self.dashboard_ui = DashboardUI(self.api, self.on_logout)

        with dpg.window(tag="main_window", label="Astra", width=800, height=600, no_title_bar=False):
            pass

        dpg.create_viewport(title='Astra - Personal Finance', width=800, height=600)
        dpg.setup_dearpygui()
        dpg.show_viewport()
        dpg.set_primary_window("main_window", True)

        self.auth_ui.show_login()

    def on_login_success(self):
        self.dashboard_ui.show()

    def on_logout(self):
        self.api.logout()
        self.auth_ui.show_login()

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
