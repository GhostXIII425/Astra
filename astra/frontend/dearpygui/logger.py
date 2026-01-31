import logging
import dearpygui.dearpygui as dpg

class DPGLogHandler(logging.Handler):
    def __init__(self, tag):
        super().__init__()
        self.tag = tag

    def emit(self, record):
        log_entry = self.format(record)
        if dpg.is_dearpygui_running():
            try:
                # Add to the text component
                current_logs = dpg.get_value(self.tag)
                new_logs = current_logs + "\n" + log_entry
                # Limit log size
                if len(new_logs) > 10000:
                    new_logs = new_logs[-10000:]
                dpg.set_value(self.tag, new_logs)
            except Exception:
                pass

def setup_gui_logging(tag):
    logger = logging.getLogger()
    handler = DPGLogHandler(tag)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return handler
