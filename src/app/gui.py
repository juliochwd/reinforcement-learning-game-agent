import customtkinter as ctk
import tkinter as tk
from tkinter import scrolledtext
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

# Set appearance and theme
ctk.set_appearance_mode("System")  # Modes: "System" (default), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (default), "green", "dark-blue"

class ConsoleLogger(logging.StreamHandler):
    def __init__(self):
        super().__init__(sys.stdout)
        self.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

class ProgressbarHandler(logging.Handler):
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

        self.title(self.ui_config.get('title', "Game Agent Control Center"))
        self.geometry(self.ui_config.get('geometry', "900x700"))
        
        self.gui_queue = queue.Queue()
        self.task_orchestrator.set_gui_queue(self.gui_queue)
        self.active_log_widget = None
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self._create_sidebar()
        self._create_main_content_area()
        self.show_page("Dashboard")
        self.process_gui_queue()

    def _create_sidebar(self):
        sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="ns")
        
        ctk.CTkLabel(sidebar, text="AGENT AI", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=20, padx=10)
        
        buttons = self.ui_config.get('sidebar_buttons', {})
        for name, icon in buttons.items():
            btn = ctk.CTkButton(sidebar, text=f" {icon} {name}", anchor="w", command=lambda n=name: self.show_page(n))
            btn.pack(fill="x", padx=10, pady=5)

    def _create_main_content_area(self):
        self.main_area = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_area.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.pages = {}
        for PageClass in (PageDashboard, PageData, PageTrain, PageEval):
            page = PageClass(self.main_area, self)
            self.pages[PageClass.__name__] = page
            page.grid(row=0, column=0, sticky="nsew")

    def show_page(self, page_name_str):
        page_map = {
            "Dashboard": "PageDashboard",
            "Data Management": "PageData",
            "Train & Validate": "PageTrain",
            "Test Best Model": "PageEval"
        }
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
                elif msg_type == "agent_update":
                    self.pages["PageDashboard"].update_live_data(msg)
                elif msg_type == "bulk_scrape_started":
                    self.pages["PageData"].scrape_button.configure(state=tk.DISABLED)
                elif msg_type == "bulk_scrape_finished":
                    self.pages["PageData"].scrape_button.configure(state=tk.NORMAL)
                elif msg_type == "agent_stopped":
                    self.pages["PageDashboard"].set_agent_stopped()
                elif msg_type == "log":
                    if self.active_log_widget and self.active_log_widget.winfo_exists():
                        # CTkTextbox does not need state changes to insert text
                        self.active_log_widget.insert(tk.END, msg.get("record", "") + '\n')
                        self.active_log_widget.yview(tk.END)
        except queue.Empty:
            pass
        self.after(100, self.process_gui_queue)

class PageBase(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller

    def _create_log_widget(self):
        log_frame = ctk.CTkFrame(self, fg_color="transparent")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(10,0))
        log_text = ctk.CTkTextbox(log_frame, wrap=tk.WORD, corner_radius=6)
        log_text.pack(fill=tk.BOTH, expand=True)
        return log_text

    def _create_progress_widgets(self):
        progress_frame = ctk.CTkFrame(self, fg_color="transparent")
        progress_frame.pack(pady=10, fill=tk.X)
        progress_bar = ctk.CTkProgressBar(progress_frame, orientation="horizontal", mode="determinate")
        progress_bar.set(0)
        progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        eta_label = ctk.CTkLabel(progress_frame, text=self.controller.ui_config.get('default_eta_text', "ETA: --:--"), width=100)
        eta_label.pack(side=tk.LEFT)
        return progress_bar, eta_label

class PageDashboard(PageBase):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        controls_frame = ctk.CTkFrame(self, fg_color="transparent")
        controls_frame.pack(fill=tk.X, pady=5)
        self.start_button = ctk.CTkButton(controls_frame, text="Start Agent", command=self.start_agent)
        self.start_button.pack(side=tk.LEFT)
        self.stop_button = ctk.CTkButton(controls_frame, text="Stop Agent", command=self.stop_agent, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=10)
        
        pred_frame = ctk.CTkFrame(self)
        pred_frame.pack(fill=tk.X, pady=10, ipady=10)
        
        self.pred_period_label = ctk.CTkLabel(pred_frame, text="Predicting Period: -")
        self.pred_period_label.pack(anchor="w", padx=10)
        self.action_label = ctk.CTkLabel(pred_frame, text="Action: -", font=ctk.CTkFont(size=14, weight="bold"))
        self.action_label.pack(anchor="w", pady=5, padx=10)
        self.bet_amount_label = ctk.CTkLabel(pred_frame, text="Bet Amount: 0.00")
        self.bet_amount_label.pack(anchor="w", padx=10)
        
        initial_balance = self.controller.ui_config.get('initial_balance_display', "2,000,000.00")
        self.balance_label = ctk.CTkLabel(pred_frame, text=f"Current Balance: {initial_balance}")
        self.balance_label.pack(anchor="w", pady=(5,0), padx=10)
        
        self.reward_label = ctk.CTkLabel(pred_frame, text="Total Profit: 0.00")
        self.reward_label.pack(anchor="w", padx=10)
        self.log_widget = self._create_log_widget()

    def start_agent(self):
        self.start_button.configure(state=tk.DISABLED)
        self.stop_button.configure(state=tk.NORMAL)
        self.controller.active_log_widget = self.log_widget
        self.controller.task_orchestrator.start_agent_task(self.start_button, None, None, self.log_widget)

    def stop_agent(self):
        self.controller.task_orchestrator.stop_agent_task()
        self.stop_button.configure(state=tk.DISABLED)

    def set_agent_stopped(self):
        self.start_button.configure(state=tk.NORMAL)
        self.stop_button.configure(state=tk.DISABLED)

    def update_live_data(self, msg):
        action_str = msg['action_str']
        bet_amount = msg.get('bet_amount', 0)
        
        self.action_label.configure(text=f"Action: {action_str}")
        self.bet_amount_label.configure(text=f"Bet Amount: {bet_amount:,.2f}")
        self.balance_label.configure(text=f"Current Balance: {msg['balance']:,.2f}")
        self.reward_label.configure(text=f"Total Profit: {msg['total_reward']:,.2f}")
        self.pred_period_label.configure(text=f"Predicting Period: {msg['period']}")

class PageData(PageBase):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        
        creds_frame = ctk.CTkFrame(self)
        creds_frame.pack(fill=tk.X, pady=5, ipady=10)
        creds_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(creds_frame, text="Phone Number:").grid(row=0, column=0, sticky="w", padx=10, pady=5)
        self.phone_entry = ctk.CTkEntry(creds_frame, placeholder_text="Enter phone number")
        self.phone_entry.grid(row=0, column=1, sticky="ew", padx=10, pady=5)
        
        ctk.CTkLabel(creds_frame, text="Password:").grid(row=1, column=0, sticky="w", padx=10, pady=5)
        self.password_entry = ctk.CTkEntry(creds_frame, show="*")
        self.password_entry.grid(row=1, column=1, sticky="ew", padx=10, pady=5)
        
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(fill=tk.X, pady=5)
        self.scrape_button = ctk.CTkButton(button_frame, text="Scrape Latest Data", command=self.start_scraping)
        self.scrape_button.pack(fill=tk.X)
        self.random_test_button = ctk.CTkButton(button_frame, text="Run Randomness Test", command=self.start_random_test)
        self.random_test_button.pack(fill=tk.X, pady=5)
        
        self.progress_bar, self.eta_label = self._create_progress_widgets()
        self.log_widget = self._create_log_widget()

    def start_scraping(self):
        phone = self.phone_entry.get()
        password = self.password_entry.get()
        if not phone or not password:
            logging.error("Phone number and password cannot be empty.")
            return
        self.controller.active_log_widget = self.log_widget
        self.controller.task_orchestrator.start_bulk_scrape(
            button=self.scrape_button, progress_bar=self.progress_bar,
            eta_label=self.eta_label, log_widget=self.log_widget,
            phone=phone, password=password
        )

    def start_random_test(self):
        self.controller.active_log_widget = self.log_widget
        self.controller.task_orchestrator.start_task(
            'randomness_test', self.random_test_button, self.progress_bar, 
            self.eta_label, self.log_widget
        )

class PageTrain(PageBase):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(fill=tk.X, pady=5)

        self.full_train_button = ctk.CTkButton(button_frame, text="Run Full Pipeline (HPT + Final Training)", command=lambda: self.start_task_by_name('full_train', self.full_train_button))
        self.full_train_button.pack(fill=tk.X, pady=2)

        self.vm_train_button = ctk.CTkButton(button_frame, text="Run Full Pipeline on VM", command=lambda: self.start_task_by_name('full_train_vm', self.vm_train_button))
        self.vm_train_button.pack(fill=tk.X, pady=2)

        self.single_train_button = ctk.CTkButton(button_frame, text="Run Single Training Session", command=lambda: self.start_task_by_name('single_train', self.single_train_button))
        self.single_train_button.pack(fill=tk.X, pady=2)

        self.hpt_button = ctk.CTkButton(button_frame, text="Run Hyperparameter Search Only", command=lambda: self.start_task_by_name('hpt', self.hpt_button))
        self.hpt_button.pack(fill=tk.X, pady=2)

        self.final_train_button = ctk.CTkButton(button_frame, text="Train Final Model with Best Params", command=lambda: self.start_task_by_name('final_train', self.final_train_button))
        self.final_train_button.pack(fill=tk.X, pady=2)
        
        self.estimate_button = ctk.CTkButton(button_frame, text="Estimate Training Time", command=lambda: self.start_task_by_name('estimate_time', self.estimate_button))
        self.estimate_button.pack(fill=tk.X, pady=2)

        self.headless_button = ctk.CTkButton(button_frame, text="Run Headless Prediction", command=lambda: self.start_task_by_name('predict_headless', self.headless_button))
        self.headless_button.pack(fill=tk.X, pady=2)

        self.progress_bar, self.eta_label = self._create_progress_widgets()
        self.log_widget = self._create_log_widget()

    def start_task_by_name(self, task_name, button):
        self.controller.active_log_widget = self.log_widget
        self.controller.task_orchestrator.start_task(
            task_name, button, self.progress_bar, self.eta_label, self.log_widget
        )

class PageEval(PageBase):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        self.eval_button = ctk.CTkButton(self, text="Test Best Model on Unseen Data", command=self.start_evaluation)
        self.eval_button.pack(pady=5, fill=tk.X)
        self.progress_bar, self.eta_label = self._create_progress_widgets()
        self.log_widget = self._create_log_widget()

    def start_evaluation(self):
        self.controller.active_log_widget = self.log_widget
        self.controller.task_orchestrator.start_task(
            'evaluate', self.eval_button, self.progress_bar, self.eta_label, self.log_widget
        )
