import tkinter as tk
from tkinter import ttk, font, scrolledtext
import queue
import logging
import re
import sys
import os

# --- Path Setup ---
# Pastikan root proyek ada di path untuk impor modul kustom
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

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
            progress_percent = (current / total) * 100
            
            eta_str = self.default_eta_text
            if progress_percent > 1:
                elapsed_time = time.time() - self.start_time
                total_estimated_time = elapsed_time / (progress_percent / 100)
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

class App(tk.Tk):
    def __init__(self, config, task_orchestrator):
        super().__init__()
        self.config = config
        self.task_orchestrator = task_orchestrator
        self.ui_config = self.config.get('ui', {})
        self.colors = self.ui_config.get('colors', {})
        self.fonts_config = self.ui_config.get('fonts', {})

        self.title(self.ui_config.get('title', "Game Agent Control Center"))
        self.geometry(self.ui_config.get('geometry', "900x700"))
        self.configure(bg=self.colors.get('background', "#f0f2f5"))
        
        self.gui_queue = queue.Queue()
        self.task_orchestrator.set_gui_queue(self.gui_queue)
        self.active_log_widget = None
        
        self._create_fonts()
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self._create_sidebar()
        self._create_main_content_area()
        self.show_page("Dashboard")
        self.process_gui_queue()

    def _create_fonts(self):
        normal_cfg = self.fonts_config.get('normal', {})
        bold_cfg = self.fonts_config.get('bold', {})
        header_cfg = self.fonts_config.get('header', {})
        self.font_normal = font.Font(family=normal_cfg.get('family', 'Helvetica'), size=normal_cfg.get('size', 11))
        self.font_bold = font.Font(family=bold_cfg.get('family', 'Helvetica'), size=bold_cfg.get('size', 11), weight=bold_cfg.get('weight', 'bold'))
        self.font_header = font.Font(family=header_cfg.get('family', 'Helvetica'), size=header_cfg.get('size', 16), weight=header_cfg.get('weight', 'bold'))

    def _create_sidebar(self):
        sidebar_color = self.colors.get('sidebar', "#ffffff")
        accent_color = self.colors.get('accent', "#1877f2")
        text_color = self.colors.get('text', "#050505")
        
        sidebar = tk.Frame(self, bg=sidebar_color, width=200, relief="flat", borderwidth=1)
        sidebar.grid(row=0, column=0, sticky="ns")
        
        ttk.Label(sidebar, text="AGENT AI", font=self.font_header, background=sidebar_color, foreground=accent_color).pack(pady=20, padx=10)
        
        buttons = self.ui_config.get('sidebar_buttons', {})
        for name, icon in buttons.items():
            btn = tk.Button(sidebar, text=f" {icon} {name}", font=self.font_normal, bg=sidebar_color, fg=text_color, relief="flat", anchor="w", command=lambda n=name: self.show_page(n))
            btn.pack(fill="x", padx=10, pady=5)

    def _create_main_content_area(self):
        self.main_area = tk.Frame(self, bg=self.colors.get('background', "#f0f2f5"))
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
                try:
                    msg = self.gui_queue.get_nowait()
                    msg_type = msg.get("type")

                    if msg_type == "task_finished":
                        button = msg.get("button")
                        if button and button.winfo_exists():
                            button.config(state=tk.NORMAL)
                    elif msg_type == "progress_update":
                        bar = msg.get("bar")
                        label = msg.get("label")
                        if bar and label and bar.winfo_exists() and label.winfo_exists():
                            bar["value"] = msg.get("value", 0)
                            label.config(text=msg.get("eta", self.ui_config.get('default_eta_text', "ETA: --:--")))
                    elif msg_type == "agent_update":
                        self.pages["PageDashboard"].update_live_data(msg)
                    elif msg_type == "bulk_scrape_started":
                        self.pages["PageData"].scrape_button.config(state=tk.DISABLED)
                    elif msg_type == "bulk_scrape_finished":
                        self.pages["PageData"].scrape_button.config(state=tk.NORMAL)
                    elif msg_type == "agent_stopped":
                        self.pages["PageDashboard"].set_agent_stopped()
                    elif msg_type == "log":
                        if self.active_log_widget and self.active_log_widget.winfo_exists():
                            self.active_log_widget.config(state='normal')
                            self.active_log_widget.insert(tk.END, msg.get("record", "") + '\n')
                            self.active_log_widget.config(state='disabled')
                            self.active_log_widget.yview(tk.END)
                except Exception as e:
                    print(f"CRITICAL: Error processing GUI message: {msg}. Error: {e}")
        except queue.Empty:
            pass
        self.after(100, self.process_gui_queue)

class PageBase(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=controller.colors.get('background', "#f0f2f5"))
        self.controller = controller
        self.config = controller.config
        self.ui_config = controller.ui_config
        self.colors = controller.colors

    def _create_log_widget(self):
        log_frame = ttk.LabelFrame(self, text="Logs", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(10,0))
        log_text = scrolledtext.ScrolledText(log_frame, state='disabled', wrap=tk.WORD, 
                                             bg=self.colors.get('log_background', "#1e1e1e"), 
                                             fg=self.colors.get('log_foreground', "#d4d4d4"), 
                                             font=self.controller.font_normal)
        log_text.pack(fill=tk.BOTH, expand=True)
        return log_text

    def _create_progress_widgets(self):
        progress_frame = ttk.Frame(self)
        progress_frame.pack(pady=10, fill=tk.X)
        progress_bar = ttk.Progressbar(progress_frame, orient="horizontal", mode="determinate")
        progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        eta_label = ttk.Label(progress_frame, text=self.ui_config.get('default_eta_text', "ETA: --:--"), width=10)
        eta_label.pack(side=tk.LEFT)
        return progress_bar, eta_label

class PageDashboard(PageBase):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        controls_frame = ttk.Frame(self)
        controls_frame.pack(fill=tk.X, pady=5)
        self.start_button = ttk.Button(controls_frame, text="Start Agent", command=self.start_agent)
        self.start_button.pack(side=tk.LEFT)
        self.stop_button = ttk.Button(controls_frame, text="Stop Agent", command=self.stop_agent, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        pred_frame = ttk.LabelFrame(self, text="Live Prediction", padding=10)
        pred_frame.pack(fill=tk.X, pady=10)
        
        self.pred_period_label = ttk.Label(pred_frame, text="Predicting Period: -")
        self.pred_period_label.pack(anchor="w")
        self.action_label = ttk.Label(pred_frame, text="Action: -", font=self.controller.font_bold)
        self.action_label.pack(anchor="w", pady=5)
        self.bet_amount_label = ttk.Label(pred_frame, text="Bet Amount: 0.00")
        self.bet_amount_label.pack(anchor="w")
        
        initial_balance = self.ui_config.get('initial_balance_display', "2,000,000.00")
        self.balance_label = ttk.Label(pred_frame, text=f"Current Balance: {initial_balance}")
        self.balance_label.pack(anchor="w", pady=(5,0))
        
        self.reward_label = ttk.Label(pred_frame, text="Total Profit: 0.00")
        self.reward_label.pack(anchor="w")
        self.log_widget = self._create_log_widget()

    def start_agent(self):
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.controller.active_log_widget = self.log_widget
        self.controller.task_orchestrator.start_agent_task(self.start_button, None, None, self.log_widget)

    def stop_agent(self):
        self.controller.task_orchestrator.stop_agent_task()
        self.stop_button.config(state=tk.DISABLED)

    def set_agent_stopped(self):
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)

    def update_live_data(self, msg):
        action_str = msg['action_str']
        bet_amount = msg.get('bet_amount', 0)
        
        if bet_amount > 0:
            self.action_label.config(text=f"Action: {action_str}")
            self.bet_amount_label.config(text=f"Bet Amount: {bet_amount:,.2f}")
        else:
            self.action_label.config(text=f"Action: {action_str}")
            self.bet_amount_label.config(text="Bet Amount: 0.00")

        self.balance_label.config(text=f"Current Balance: {msg['balance']:,.2f}")
        self.reward_label.config(text=f"Total Profit: {msg['total_reward']:,.2f}")
        self.pred_period_label.config(text=f"Predicting Period: {msg['period']}")

class PageData(PageBase):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, pady=5)
        self.scrape_button = ttk.Button(button_frame, text="Scrape Latest Data", command=self.start_scraping)
        self.scrape_button.pack(fill=tk.X)
        self.random_test_button = ttk.Button(button_frame, text="Run Randomness Test", command=self.start_random_test)
        self.random_test_button.pack(fill=tk.X, pady=5)
        self.progress_bar, self.eta_label = self._create_progress_widgets()
        self.log_widget = self._create_log_widget()

    def start_scraping(self):
        self.controller.active_log_widget = self.log_widget
        self.controller.task_orchestrator.start_bulk_scrape()

    def start_random_test(self):
        self.controller.active_log_widget = self.log_widget
        self.controller.task_orchestrator.start_task(
            'randomness_test', 
            self.random_test_button, 
            self.progress_bar, 
            self.eta_label, 
            self.log_widget
        )

class PageTrain(PageBase):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        
        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, pady=5)

        self.search_button = ttk.Button(button_frame, text="1. Find Best Hyperparameters (Optuna)", command=self.start_hyperparameter_search)
        self.search_button.pack(fill=tk.X, pady=(0, 5))

        self.train_button = ttk.Button(button_frame, text="2. Start Training Final Model", command=self.start_training)
        self.train_button.pack(fill=tk.X)

        self.progress_bar, self.eta_label = self._create_progress_widgets()
        self.log_widget = self._create_log_widget()

    def start_training(self):
        self.controller.active_log_widget = self.log_widget
        self.controller.task_orchestrator.start_task(
            'train', 
            self.train_button, 
            self.progress_bar, 
            self.eta_label, 
            self.log_widget
        )

    def start_hyperparameter_search(self):
        self.controller.active_log_widget = self.log_widget
        self.controller.task_orchestrator.start_task(
            'hyperparameter_search', 
            self.search_button, 
            self.progress_bar, 
            self.eta_label, 
            self.log_widget
        )

class PageEval(PageBase):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        self.eval_button = ttk.Button(self, text="Test Best Model on Unseen Data", command=self.start_evaluation)
        self.eval_button.pack(pady=5, fill=tk.X)
        self.progress_bar, self.eta_label = self._create_progress_widgets()
        self.log_widget = self._create_log_widget()

    def start_evaluation(self):
        self.controller.active_log_widget = self.log_widget
        self.controller.task_orchestrator.start_task(
            'evaluate', 
            self.eval_button, 
            self.progress_bar, 
            self.eta_label, 
            self.log_widget
        )