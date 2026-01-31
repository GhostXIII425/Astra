import dearpygui.dearpygui as dpg

class AuthUI:
    def __init__(self, api, on_login_success):
        self.api = api
        self.on_login_success = on_login_success

    def show_login(self, parent="main_window"):
        dpg.delete_item(parent, children_only=True)

        with dpg.group(parent=parent):
            dpg.add_text("Astra - Login")
            dpg.add_input_text(label="Username", tag="login_username")
            dpg.add_input_text(label="Password", tag="login_password", password=True)

            with dpg.group(horizontal=True):
                dpg.add_button(label="Login", callback=self._login_callback)
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("Log into your isolated personal account.")
                dpg.add_button(label="Register", callback=lambda: self.show_register(parent=parent))
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("Create a new isolated account.")

            dpg.add_text("", tag="login_error", color=[255, 0, 0])

    def show_register(self, parent="main_window"):
        dpg.delete_item(parent, children_only=True)

        with dpg.group(parent=parent):
            dpg.add_text("Astra - Create Account")
            dpg.add_input_text(label="Username", tag="reg_username")
            dpg.add_input_text(label="Password", tag="reg_password", password=True)
            dpg.add_input_text(label="Confirm Password", tag="reg_confirm", password=True)

            with dpg.group(horizontal=True):
                dpg.add_button(label="Create Account", callback=lambda: self._register_callback(parent))
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("Finalize account creation.")
                dpg.add_button(label="Back to Login", callback=lambda: self.show_login(parent=parent))
                with dpg.tooltip(dpg.last_item()):
                    dpg.add_text("Return to the login screen.")

            dpg.add_text("", tag="reg_error", color=[255, 0, 0])

    def _update_global_status(self, message, color=(0, 255, 0)):
        """Update the global status label in the main window."""
        if dpg.does_item_exist("global_status"):
            dpg.set_value("global_status", message)
            dpg.configure_item("global_status", color=color)

    def _login_callback(self):
        username = dpg.get_value("login_username")
        password = dpg.get_value("login_password")

        self._update_global_status("Attempting login...", color=(255, 255, 0))
        if self.api.login(username, password):
            self._update_global_status(f"Welcome, {username}", color=(0, 255, 0))
            self.on_login_success()
        else:
            self._update_global_status("Login failed", color=(255, 0, 0))
            dpg.set_value("login_error", "Invalid username or password")

    def _register_callback(self, parent):
        username = dpg.get_value("reg_username")
        password = dpg.get_value("reg_password")
        confirm = dpg.get_value("reg_confirm")

        if password != confirm:
            dpg.set_value("reg_error", "Passwords do not match")
            return

        self._update_global_status("Registering...", color=(255, 255, 0))
        if self.api.register(username, password):
            self._update_global_status("Registration successful", color=(0, 255, 0))
            self.show_login(parent=parent)
            dpg.set_value("login_error", "Registration successful! Please login.")
        else:
            self._update_global_status("Registration failed", color=(255, 0, 0))
            dpg.set_value("reg_error", "Username already exists or invalid")
