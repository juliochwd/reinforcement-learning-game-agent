import customtkinter as ctk
import tkinter as tk
import queue
import logging
import re
import sys
import os
import time

# --- Path Setup ---
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Zenith UI Concept Setup ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

class ModernConsoleLogger(logging.StreamHandler):
    def __init__(self):
        super().__init__(sys.stdout)
        self.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

class ModernProgressbarHandler(logging.Handler):
    def __init__(self, gui_queue, progress_bar, eta_label, default_eta_text="ETA: --:--"):
        super().__init__()
        self.gui_queue = gui_queue
        self.progress_bar = progress_bar
        self.eta_label = eta_label
        self.start_time = None
        self.default_eta_text = default_eta_text

    def format_eta(self, seconds):
        if seconds is None or seconds < 0:
            return self.default_eta_text.split(':')[1].strip()
        mins, secs = divmod(int(seconds), 60)
        return f"{mins:02d}:{secs:02d}"

    def emit(self, record):
        msg = self.format(record)
        match = re.search(r'(\d+)/(\d+)', msg)
        if match:
            if self.start_time is None:
                self.start_time = time.time()

            current, total = map(int, match.groups())
            progress_percent = current / total
            
            eta_str = self.default_eta_text
            if progress_percent > 0.01:
                elapsed_time = time.time() - self.start_time
                total_estimated_time = elapsed_time / progress_percent
                remaining_time = total_estimated_time - elapsed_time
                eta_str = f"ETA: {self.format_eta(remaining_time)}"

            if self.progress_bar:
                self.gui_queue.put({
                    "type": "progress_update",
                    "value": progress_percent,
                    "eta": eta_str,
                    "bar": self.progress_bar,
                    "label": self.eta_label
                })
        else:
            self.gui_queue.put({"type": "log", "record": msg})

class App(ctk.CTk):
    def __init__(self, config, task_orchestrator):
        super().__init__()
        self.config = config
        self.task_orchestrator = task_orchestrator
        self.ui_config = self.config.get('ui', {})

        # --- Font Definitions ---
        FONT_FAMILY = "Segoe UI"
        self.fonts = {
            "MAIN_TITLE": ctk.CTkFont(family=FONT_FAMILY, size=24, weight="bold"),
            "SUBTITLE": ctk.CTkFont(family=FONT_FAMILY, size=16),
            "BODY": ctk.CTkFont(family=FONT_FAMILY, size=14),
            "SMALL": ctk.CTkFont(family=FONT_FAMILY, size=12),
            "MONO": ctk.CTkFont(family="Courier New", size=12)
        }

        self.title("Zenith")
        self.geometry(self.ui_config.get('geometry', "900x700"))
        
        self.gui_queue = queue.Queue()
        self.task_orchestrator.set_gui_queue(self.gui_queue)
        self.active_log_widget = None
        
        # Enable resizing
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        self._create_sidebar()
        self._create_main_content_area()
        
        self.show_page("Data Management")
        self.process_gui_queue()

    def _create_sidebar(self):
        sidebar = ctk.CTkFrame(self, width=240, corner_radius=0, fg_color="#212121")
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.grid_rowconfigure(4, weight=1)

        logo_label = ctk.CTkLabel(sidebar, text="ZENITH", font=self.fonts["MAIN_TITLE"])
        logo_label.grid(row=0, column=0, padx=20, pady=(20, 20))

        buttons = self.ui_config.get('sidebar_buttons', {})
        for i, (name, icon) in enumerate(buttons.items()):
            btn = ctk.CTkButton(sidebar, text=f" {icon}  {name}", anchor="w", 
                                font=self.fonts["BODY"],
                                command=lambda n=name: self.show_page(n),
                                height=40, corner_radius=8)
            btn.grid(row=i+1, column=0, padx=20, pady=10, sticky="ew")

    def _create_main_content_area(self):
        self.main_area = ctk.CTkFrame(self, corner_radius=0, fg_color="#2B2B2B")
        self.main_area.grid(row=0, column=1, sticky="nsew")
        self.pages = {}
        for PageClass in (PageData,):
            page = PageClass(self.main_area, self)
            self.pages[PageClass.__name__] = page
            page.pack(fill="both", expand=True, padx=30, pady=30)

    def show_page(self, page_name_str):
        page_map = { "Data Management": "PageData" }
        page_name = page_map.get(page_name_str)
        if page_name and page_name in self.pages:
            self.pages[page_name].tkraise()

    def process_gui_queue(self):
        try:
            while not self.gui_queue.empty():
                msg = self.gui_queue.get_nowait()
                msg_type = msg.get("type")

                if msg_type == "task_finished":
                    button = msg.get("button")
                    if button and button.winfo_exists():
                        button.configure(state=tk.NORMAL)
                elif msg_type == "progress_update":
                    bar = msg.get("bar")
                    label = msg.get("label")
                    if bar and label and bar.winfo_exists() and label.winfo_exists():
                        bar.set(msg.get("value", 0))
                        label.configure(text=msg.get("eta", self.ui_config.get('default_eta_text', "ETA: --:--")))
                elif msg_type == "bulk_scrape_started":
                    self.pages["PageData"].scrape_button.configure(state=tk.DISABLED)
                elif msg_type == "bulk_scrape_finished":
                    self.pages["PageData"].scrape_button.configure(state=tk.NORMAL)
                elif msg_type == "log":
                    if self.active_log_widget and self.active_log_widget.winfo_exists():
                        self.active_log_widget.insert(tk.END, msg.get("record", "") + '\n')
                        self.active_log_widget.yview(tk.END)
        except queue.Empty:
            pass
        self.after(100, self.process_gui_queue)

class PageBase(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller

class PageData(PageBase):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)
        
        title_label = ctk.CTkLabel(self, text="Data Management", font=self.controller.fonts["MAIN_TITLE"])
        title_label.grid(row=0, column=0, sticky="w", pady=(0, 20))

        creds_frame = ctk.CTkFrame(self, corner_radius=8, fg_color="#212121")
        creds_frame.grid(row=1, column=0, sticky="ew", pady=10)
        creds_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(creds_frame, text="Phone Number", font=self.controller.fonts["BODY"]).grid(row=0, column=0, sticky="w", padx=20, pady=15)
        self.phone_entry = ctk.CTkEntry(creds_frame, placeholder_text="Enter phone number", font=self.controller.fonts["BODY"], height=35)
        self.phone_entry.grid(row=0, column=1, sticky="ew", padx=20, pady=15)
        
        ctk.CTkLabel(creds_frame, text="Password", font=self.controller.fonts["BODY"]).grid(row=1, column=0, sticky="w", padx=20, pady=15)
        self.password_entry = ctk.CTkEntry(creds_frame, show="*", font=self.controller.fonts["BODY"], height=35)
        self.password_entry.grid(row=1, column=1, sticky="ew", padx=20, pady=15)
        
        self.scrape_button = ctk.CTkButton(self, text="Scrape Latest Data", 
                                           font=self.controller.fonts["BODY"],
                                           command=self.start_scraping, height=45, corner_radius=8)
        self.scrape_button.grid(row=2, column=0, sticky="ew", pady=(20, 0))
        
        # Combined progress and log area
        status_frame = ctk.CTkFrame(self, fg_color="transparent")
        status_frame.grid(row=3, column=0, sticky="nsew", pady=(20, 0))
        status_frame.grid_rowconfigure(1, weight=1)
        status_frame.grid_columnconfigure(0, weight=1)

        self.progress_bar, self.eta_label = self._create_progress_widgets(status_frame)
        self.log_widget = self._create_log_widget(status_frame)

    def _create_log_widget(self, parent):
        log_frame = ctk.CTkFrame(parent, fg_color="#212121", corner_radius=8)
        log_frame.grid(row=1, column=0, sticky="nsew", pady=(10,0))
        log_frame.grid_rowconfigure(0, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)
        
        log_text = ctk.CTkTextbox(log_frame, wrap=tk.WORD, corner_radius=8, 
                                  font=self.controller.fonts["MONO"],
                                  border_width=0, fg_color="transparent")
        log_text.grid(row=0, column=0, sticky="nsew", padx=15, pady=15)
        return log_text

    def _create_progress_widgets(self, parent):
        progress_frame = ctk.CTkFrame(parent, fg_color="transparent")
        progress_frame.grid(row=0, column=0, sticky="ew")
        progress_frame.grid_columnconfigure(0, weight=1)

        progress_bar = ctk.CTkProgressBar(progress_frame, orientation="horizontal", mode="determinate")
        progress_bar.grid(row=0, column=0, sticky="ew", padx=(0, 15))
        
        eta_label = ctk.CTkLabel(progress_frame, text=self.controller.ui_config.get('default_eta_text', "ETA: --:--"), 
                                 width=100, font=self.controller.fonts["SMALL"])
        eta_label.grid(row=0, column=1, sticky="e")
        return progress_bar, eta_label

    def start_scraping(self):
        phone = self.phone_entry.get()
        password = self.password_entry.get()
        if not phone or not password:
            logging.error("Phone number and password cannot be empty.")
            return
        self.active_log_widget = self.log_widget
        self.controller.task_orchestrator.start_bulk_scrape(
            button=self.scrape_button, progress_bar=self.progress_bar,
            eta_label=self.eta_label, log_widget=self.log_widget,
            phone=phone, password=password
        )
