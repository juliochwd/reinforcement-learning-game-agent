import customtkinter as ctk
import tkinter as tk
import queue
import logging
import re
import sys
import os
import time
from src.utils.logging_utils import setup_logging, log_audit
import webbrowser
from tkinter import filedialog
import subprocess

# --- Path Setup ---
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Zenith UI Concept Setup ---
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

# Try to use SF Pro Display, fallback to Helvetica Neue or Arial Rounded
try:
    FONT_FAMILY = "SF Pro Display"
    _ = ctk.CTkFont(family=FONT_FAMILY)
except Exception:
    try:
        FONT_FAMILY = "Helvetica Neue"
        _ = ctk.CTkFont(family=FONT_FAMILY)
    except Exception:
        FONT_FAMILY = "Arial Rounded MT Bold"

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
        # Inisialisasi default training_settings agar tidak error
        self.training_settings = {
            'split_ratio': 0.2,
            'window_sizes': [10, 30, 50],
            'n_lags': 10,
            'n_trials': 30,
            'threshold_corr': 0.65
        }

        # --- Font Definitions ---
        self.fonts = {
            "MAIN_TITLE": ctk.CTkFont(family=FONT_FAMILY, size=24, weight="bold"),
            "SUBTITLE": ctk.CTkFont(family=FONT_FAMILY, size=16),
            "BODY": ctk.CTkFont(family=FONT_FAMILY, size=14),
            "SMALL": ctk.CTkFont(family=FONT_FAMILY, size=12),
            "MONO": ctk.CTkFont(family="Courier New", size=12)
        }

        self.title("Zenith")
        self.geometry(self.ui_config.get('geometry', "1000x750"))
        self.minsize(900, 600)
        self.configure(bg="#F7F7FA")
        
        self.gui_queue = queue.Queue()
        setup_logging(gui_queue=self.gui_queue)  # Centralized logging setup
        self.task_orchestrator.set_gui_queue(self.gui_queue)
        self.active_log_widget = None
        
        # Enable resizing
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        self._create_sidebar()
        self._create_main_content_area()
        self.task_orchestrator.set_gui_controller(self)
        self.show_page("Data Management")
        self.process_gui_queue()

    def show_error_dialog(self, title, message):
        error_win = ctk.CTkToplevel(self)
        error_win.title(title)
        error_win.geometry("400x180")
        error_win.grab_set()
        error_win.resizable(False, False)
        ctk.CTkLabel(error_win, text=title, font=self.fonts["SUBTITLE"], text_color="#D32F2F").pack(pady=(20, 10))
        ctk.CTkLabel(error_win, text=message, font=self.fonts["BODY"], text_color="#222").pack(pady=(0, 20))
        ctk.CTkButton(error_win, text="OK", command=error_win.destroy, fg_color="#3A7EBF", text_color="#fff").pack(pady=(0, 10))

    def _create_sidebar(self):
        sidebar = ctk.CTkFrame(self, width=240, corner_radius=0, fg_color="#F2F3F7")
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.grid_rowconfigure(5, weight=1)

        # --- Header/Logo ---
        logo_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        logo_frame.grid(row=0, column=0, padx=20, pady=(24, 16), sticky="ew")
        logo_icon = ctk.CTkLabel(logo_frame, text="🟦", font=ctk.CTkFont(size=32))
        logo_icon.grid(row=0, column=0, sticky="w")
        logo_label = ctk.CTkLabel(logo_frame, text="ZENITH", font=self.fonts["MAIN_TITLE"], text_color="#222")
        logo_label.grid(row=0, column=1, padx=(10,0), sticky="w")

        # --- Sidebar Buttons ---
        sidebar_buttons = [
            ("Data Management", "📊"),
            ("Settings", "⚙️"),
            ("Logs", "📝")
        ]
        for i, (name, icon) in enumerate(sidebar_buttons):
            btn = ctk.CTkButton(
                sidebar,
                text=f"  {icon}  {name}",
                anchor="w",
                font=self.fonts["BODY"],
                command=lambda n=name: self.show_page(n),  # Penting: lambda n=name
                height=40,
                corner_radius=12,
                fg_color="#E6EAF2",
                hover_color="#D0D6E1",
                text_color="#222222"
            )
            btn.grid(row=i+1, column=0, padx=20, pady=8, sticky="ew")

    def _create_main_content_area(self):
        self.main_area = ctk.CTkFrame(self, corner_radius=0, fg_color="#FFFFFF")
        self.main_area.grid(row=0, column=1, sticky="nsew")
        self.main_area.grid_rowconfigure(0, weight=1)
        self.main_area.grid_columnconfigure(0, weight=1)
        self.pages = {}
        for PageClass in (PageData, PageSettings, PageLogs):
            page = PageClass(self.main_area, self)
            self.pages[PageClass.__name__] = page
            page.grid(row=0, column=0, sticky="nsew")  # Ganti pack menjadi grid

    def show_page(self, page_name_str):
        page_map = {
            "Data Management": "PageData",
            "Settings": "PageSettings",
            "Logs": "PageLogs"
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
                elif msg_type == "progress_indeterminate_start":
                    page = self.pages.get("PageData")
                    if page and hasattr(page, "progress_bar"):
                        page.progress_bar.configure(mode="indeterminate")
                        page.progress_bar.start()
                elif msg_type == "progress_indeterminate_stop":
                    page = self.pages.get("PageData")
                    if page and hasattr(page, "progress_bar"):
                        page.progress_bar.stop()
                        page.progress_bar.configure(mode="determinate")
                        page.progress_bar.set(0)
                elif msg_type == "bulk_scrape_started":
                    self.pages["PageData"].scrape_button.configure(state=tk.DISABLED)
                elif msg_type == "bulk_scrape_finished":
                    self.pages["PageData"].scrape_button.configure(state=tk.NORMAL)
                elif msg_type == "live_scrape_started":
                    self.pages["PageData"].toggle_live_scrape_button_state(is_running=True)
                elif msg_type == "live_scrape_finished":
                    self.pages["PageData"].toggle_live_scrape_button_state(is_running=False)
                elif msg_type == "log":
                    if self.active_log_widget and self.active_log_widget.winfo_exists():
                        self.active_log_widget.insert(tk.END, msg.get("record", "") + '\n')
                        self.active_log_widget.yview(tk.END)
                elif msg_type == "prediction_update":
                    self.pages["PageData"].update_prediction_display(msg['numbers'], msg['confidence'])
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
        title_label = ctk.CTkLabel(self, text="Data Management", font=self.controller.fonts["MAIN_TITLE"], text_color="#222")
        title_label.grid(row=0, column=0, sticky="w", pady=(0, 20))
        creds_frame = ctk.CTkFrame(self, corner_radius=12, fg_color="#F2F3F7")
        creds_frame.grid(row=1, column=0, sticky="ew", pady=10)
        creds_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(creds_frame, text="Phone Number", font=self.controller.fonts["BODY"], text_color="#222").grid(row=0, column=0, sticky="w", padx=20, pady=15)
        self.phone_entry = ctk.CTkEntry(creds_frame, placeholder_text="Enter phone number", font=self.controller.fonts["BODY"], height=35)
        self.phone_entry.grid(row=0, column=1, sticky="ew", padx=20, pady=15)
        ctk.CTkLabel(creds_frame, text="Password", font=self.controller.fonts["BODY"], text_color="#222").grid(row=1, column=0, sticky="w", padx=20, pady=15)
        self.password_entry = ctk.CTkEntry(creds_frame, show="*", font=self.controller.fonts["BODY"], height=35)
        self.password_entry.grid(row=1, column=1, sticky="ew", padx=20, pady=15)
        action_buttons_frame = ctk.CTkFrame(self, fg_color="transparent")
        action_buttons_frame.grid(row=2, column=0, sticky="ew", pady=(20, 0))
        action_buttons_frame.grid_columnconfigure(0, weight=1)
        action_buttons_frame.grid_columnconfigure(1, weight=1)
        # --- Styling tombol utama ---
        btn_style = dict(
            font=self.controller.fonts["BODY"],
            height=int(45),
            corner_radius=int(12),
            fg_color=str("#3A7EBF"),
            hover_color=str("#2563A6"),
            text_color=str("#ffffff")
        )
        btn_style2 = dict(
            font=self.controller.fonts["BODY"],
            height=int(45),
            corner_radius=int(12),
            fg_color=str("#E6EAF2"),
            hover_color=str("#D0D6E1"),
            text_color=str("#222222")
        )
        self.scrape_button = ctk.CTkButton(action_buttons_frame, text="Scrape Latest Data", command=self.start_scraping, font=self.controller.fonts["BODY"], height=45, corner_radius=12, fg_color="#E6EAF2", hover_color="#D0D6E1", text_color="#222222")
        self.scrape_button.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.live_scrape_button = ctk.CTkButton(action_buttons_frame, text="Start Live Scrape", command=self.toggle_live_scrape, font=self.controller.fonts["BODY"], height=45, corner_radius=12, fg_color="#E6EAF2", hover_color="#D0D6E1", text_color="#222222")
        self.live_scrape_button.grid(row=0, column=1, sticky="ew", padx=(10, 0))
        self.is_live_scraping = False
        self.train_ensemble_button = ctk.CTkButton(action_buttons_frame, text="Train Online Model", command=self.train_ensemble, font=self.controller.fonts["BODY"], height=45, corner_radius=12, fg_color="#3A7EBF", hover_color="#2563A6", text_color="#ffffff")
        self.train_ensemble_button.grid(row=1, column=0, sticky="ew", padx=(0, 10), pady=(10, 0))
        self.train_ensemble_button_tooltip = ctk.CTkLabel(self, text="Latih model online learning dengan data terbaru.", font=self.controller.fonts["SMALL"], fg_color="#222222", text_color="#ffffff", corner_radius=6)
        self.train_ensemble_button.bind("<Enter>", lambda e: self._show_tooltip(self.train_ensemble_button_tooltip, self.train_ensemble_button))
        self.train_ensemble_button.bind("<Leave>", lambda e: self._hide_tooltip(self.train_ensemble_button_tooltip))
        self.eval_ensemble_button = ctk.CTkButton(action_buttons_frame, text="Evaluate Online Model", command=self.evaluate_ensemble, font=self.controller.fonts["BODY"], height=45, corner_radius=12, fg_color="#3A7EBF", hover_color="#2563A6", text_color="#ffffff")
        self.eval_ensemble_button.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=(10, 0))
        self.eval_ensemble_button_tooltip = ctk.CTkLabel(self, text="Evaluasi performa model online learning.", font=self.controller.fonts["SMALL"], fg_color="#222222", text_color="#ffffff", corner_radius=6)
        self.eval_ensemble_button.bind("<Enter>", lambda e: self._show_tooltip(self.eval_ensemble_button_tooltip, self.eval_ensemble_button))
        self.eval_ensemble_button.bind("<Leave>", lambda e: self._hide_tooltip(self.eval_ensemble_button_tooltip))
        self.predict_ensemble_button = ctk.CTkButton(action_buttons_frame, text="Predict Next Number", command=self.predict_ensemble, font=self.controller.fonts["BODY"], height=45, corner_radius=12, fg_color="#3A7EBF", hover_color="#2563A6", text_color="#ffffff")
        self.predict_ensemble_button.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        self.predict_ensemble_button_tooltip = ctk.CTkLabel(self, text="Prediksi angka berikutnya berdasarkan model.", font=self.controller.fonts["SMALL"], fg_color="#222222", text_color="#ffffff", corner_radius=6)
        self.predict_ensemble_button.bind("<Enter>", lambda e: self._show_tooltip(self.predict_ensemble_button_tooltip, self.predict_ensemble_button))
        self.predict_ensemble_button.bind("<Leave>", lambda e: self._hide_tooltip(self.predict_ensemble_button_tooltip))
        self.feature_importance_button = ctk.CTkButton(action_buttons_frame, text="Show Feature Importance", command=self.feature_importance, font=self.controller.fonts["BODY"], height=45, corner_radius=12, fg_color="#E6EAF2", hover_color="#D0D6E1", text_color="#222222")
        self.feature_importance_button.grid(row=2, column=1, sticky="ew", pady=(10, 0))
        self.feature_importance_button_tooltip = ctk.CTkLabel(self, text="Lihat fitur paling berpengaruh pada model.", font=self.controller.fonts["SMALL"], fg_color="#222222", text_color="#ffffff", corner_radius=6)
        self.feature_importance_button.bind("<Enter>", lambda e: self._show_tooltip(self.feature_importance_button_tooltip, self.feature_importance_button))
        self.feature_importance_button.bind("<Leave>", lambda e: self._hide_tooltip(self.feature_importance_button_tooltip))
        self.ensemble_analysis_button = ctk.CTkButton(action_buttons_frame, text="Show Model Analysis", command=self.ensemble_analysis, font=self.controller.fonts["BODY"], height=45, corner_radius=12, fg_color="#E6EAF2", hover_color="#D0D6E1", text_color="#222222")
        self.ensemble_analysis_button.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        self.ensemble_analysis_button_tooltip = ctk.CTkLabel(self, text="Analisis mendalam performa model.", font=self.controller.fonts["SMALL"], fg_color="#222222", text_color="#ffffff", corner_radius=6)
        self.ensemble_analysis_button.bind("<Enter>", lambda e: self._show_tooltip(self.ensemble_analysis_button_tooltip, self.ensemble_analysis_button))
        self.ensemble_analysis_button.bind("<Leave>", lambda e: self._hide_tooltip(self.ensemble_analysis_button_tooltip))
        self.hyperparam_search_button = ctk.CTkButton(action_buttons_frame, text="Hyperparameter Search", command=self.hyperparameter_search, font=self.controller.fonts["BODY"], height=45, corner_radius=12, fg_color="#3A7EBF", hover_color="#2563A6", text_color="#ffffff")
        self.hyperparam_search_button.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        self.hyperparam_search_button_tooltip = ctk.CTkLabel(self, text="Cari kombinasi parameter terbaik untuk model online learning (Optuna)", font=self.controller.fonts["SMALL"], fg_color="#222222", text_color="#ffffff", corner_radius=6)
        self.hyperparam_search_button.bind("<Enter>", lambda e: self._show_tooltip(self.hyperparam_search_button_tooltip, self.hyperparam_search_button))
        self.hyperparam_search_button.bind("<Leave>", lambda e: self._hide_tooltip(self.hyperparam_search_button_tooltip))
        # Tambahkan tombol retrain final model pada seluruh data
        self.retrain_all_button = ctk.CTkButton(action_buttons_frame, text="Retrain Final Model (All Data)", command=self.retrain_on_all_data_button, font=self.controller.fonts["BODY"], height=45, corner_radius=12, fg_color="#3A7EBF", hover_color="#2563A6", text_color="#ffffff")
        self.retrain_all_button.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        self.retrain_all_button_tooltip = ctk.CTkLabel(self, text="Latih ulang model final pada seluruh data (train+val) dengan best params. Untuk deployment.", font=self.controller.fonts["SMALL"], fg_color="#222222", text_color="#ffffff", corner_radius=6)
        self.retrain_all_button.bind("<Enter>", lambda e: self._show_tooltip(self.retrain_all_button_tooltip, self.retrain_all_button))
        self.retrain_all_button.bind("<Leave>", lambda e: self._hide_tooltip(self.retrain_all_button_tooltip))
        # Combined progress and log area
        status_frame = ctk.CTkFrame(self, fg_color="transparent")
        status_frame.grid(row=3, column=0, sticky="nsew", pady=(20, 0))
        status_frame.grid_rowconfigure(1, weight=1)
        status_frame.grid_columnconfigure(0, weight=1)
        self.progress_bar, self.eta_label = self._create_progress_widgets(status_frame)
        self.log_widget = self._create_log_widget(status_frame)
        # Tambahkan label prediksi dinamis
        self.prediction_label = ctk.CTkLabel(self, text="Prediksi: -", font=self.controller.fonts["BODY"], text_color="#2563A6")
        self.prediction_label.grid(row=4, column=0, sticky="w", pady=(10, 0))

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
        # Phone validation
        if not phone or not phone.isdigit() or len(phone) < 8:
            self.controller.show_error_dialog("Input Error", "Phone number harus diisi dan berupa angka minimal 8 digit.")
            return
        # Password validation
        if not password or len(password) < 6:
            self.controller.show_error_dialog("Input Error", "Password harus diisi dan minimal 6 karakter.")
            return
        self.active_log_widget = self.log_widget
        try:
            log_audit("StartScraping", f"User started scraping with phone={phone}")
            self.controller.task_orchestrator.start_bulk_scrape(
                button=self.scrape_button, progress_bar=self.progress_bar,
                eta_label=self.eta_label, log_widget=self.log_widget,
                phone=phone, password=password
            )
        except Exception as e:
            import logging
            logging.error(f"Exception in start_scraping: {e}", exc_info=True)
            self.controller.show_error_dialog("Scraping Error", str(e))

    def toggle_live_scrape(self):
        phone = self.phone_entry.get()
        password = self.password_entry.get()
        # Phone validation
        if not phone or not phone.isdigit() or len(phone) < 8:
            self.controller.show_error_dialog("Input Error", "Phone number harus diisi dan berupa angka minimal 8 digit.")
            return
        # Password validation
        if not password or len(password) < 6:
            self.controller.show_error_dialog("Input Error", "Password harus diisi dan minimal 6 karakter.")
            return
        self.active_log_widget = self.log_widget
        if not self.is_live_scraping:
            try:
                log_audit("StartLiveScrape", f"User started live scraping with phone={phone}")
                self.controller.task_orchestrator.start_live_scrape(
                    button=self.live_scrape_button, progress_bar=None,
                    eta_label=None, log_widget=self.log_widget,
                    phone=phone, password=password
                )
            except Exception as e:
                import logging
                logging.error(f"Exception in start_live_scrape: {e}", exc_info=True)
                self.controller.show_error_dialog("Live Scrape Error", str(e))
        else:
            self.controller.task_orchestrator.stop_live_scrape(button=self.live_scrape_button)

    def toggle_live_scrape_button_state(self, is_running):
        self.is_live_scraping = is_running
        if is_running:
            self.live_scrape_button.configure(text="Stop Live Scrape", fg_color="#D32F2F", hover_color="#B71C1C")
            self.scrape_button.configure(state=tk.DISABLED) # Disable bulk scrape during live
        else:
            self.live_scrape_button.configure(text="Start Live Scrape", fg_color="#3a7ebf", hover_color="#325882")
            self.scrape_button.configure(state=tk.NORMAL)
        self.live_scrape_button.configure(state=tk.NORMAL)

    # Hapus handler RL/DDQN dan LightGBM forecaster
    # def start_hyperparameter_search(self): ...
    # def run_final_training(self): ...
    # def run_evaluation(self): ...
    # def train_lgbm_forecaster(self): ...
    # Tambahkan handler baru untuk tombol pipeline ensemble
    def train_ensemble(self):
        self.active_log_widget = self.log_widget
        try:
            log_audit("TrainEnsemble", "User triggered model training.")
            self.controller.task_orchestrator.start_task(
                task_name="train_ensemble",
                button=self.train_ensemble_button,
                progress_bar=self.progress_bar,
                eta_label=self.eta_label,
                log_widget=self.log_widget
            )
        except Exception as e:
            import logging
            logging.error(f"Exception in train_ensemble: {e}", exc_info=True)
            self.controller.show_error_dialog("Training Error", str(e))
    def evaluate_ensemble(self):
        self.active_log_widget = self.log_widget
        try:
            log_audit("EvaluateEnsemble", "User triggered model evaluation.")
            self.controller.task_orchestrator.start_task(
                task_name="evaluate_ensemble",
                button=self.eval_ensemble_button,
                progress_bar=self.progress_bar,
                eta_label=self.eta_label,
                log_widget=self.log_widget
            )
        except Exception as e:
            import logging
            logging.error(f"Exception in evaluate_ensemble: {e}", exc_info=True)
            self.controller.show_error_dialog("Evaluation Error", str(e))
    def predict_ensemble(self):
        self.active_log_widget = self.log_widget
        try:
            log_audit("PredictEnsemble", "User triggered prediction.")
            self.controller.task_orchestrator.start_task(
                task_name="predict_ensemble",
                button=self.predict_ensemble_button,
                progress_bar=self.progress_bar,
                eta_label=self.eta_label,
                log_widget=self.log_widget
            )
        except Exception as e:
            import logging
            logging.error(f"Exception in predict_ensemble: {e}", exc_info=True)
            self.controller.show_error_dialog("Prediction Error", str(e))
    def feature_importance(self):
        self.active_log_widget = self.log_widget
        try:
            log_audit("FeatureImportance", "User requested feature importance.")
            self.controller.task_orchestrator.start_task(
                task_name="feature_importance",
                button=self.feature_importance_button,
                progress_bar=self.progress_bar,
                eta_label=self.eta_label,
                log_widget=self.log_widget
            )
        except Exception as e:
            import logging
            logging.error(f"Exception in feature_importance: {e}", exc_info=True)
            self.controller.show_error_dialog("Feature Importance Error", str(e))
    def ensemble_analysis(self):
        self.active_log_widget = self.log_widget
        try:
            log_audit("EnsembleAnalysis", "User requested model analysis.")
            self.controller.task_orchestrator.start_task(
                task_name="ensemble_analysis",
                button=self.ensemble_analysis_button,
                progress_bar=self.progress_bar,
                eta_label=self.eta_label,
                log_widget=self.log_widget
            )
        except Exception as e:
            import logging
            logging.error(f"Exception in ensemble_analysis: {e}", exc_info=True)
            self.controller.show_error_dialog("Analysis Error", str(e))

    def hyperparameter_search(self):
        self.active_log_widget = self.log_widget
        try:
            log_audit("HyperparameterSearch", "User started hyperparameter search.")
            self.controller.task_orchestrator.start_task(
                task_name="hyperparameter_search",
                button=self.hyperparam_search_button,
                progress_bar=self.progress_bar,
                eta_label=self.eta_label,
                log_widget=self.log_widget
            )
        except Exception as e:
            import logging
            logging.error(f"Exception in hyperparameter_search: {e}", exc_info=True)
            self.controller.show_error_dialog("Hyperparameter Search Error", str(e))

    def update_prediction_display(self, numbers, confidence):
        self.prediction_label.configure(text=f"Prediksi: {numbers} (Conf: {confidence:.2f})")

    def _show_tooltip(self, tooltip, widget):
        x = widget.winfo_rootx() - widget.winfo_toplevel().winfo_rootx() + widget.winfo_width() + 10
        y = widget.winfo_rooty() - widget.winfo_toplevel().winfo_rooty()
        tooltip.place(x=x, y=y)
        tooltip.lift()
    def _hide_tooltip(self, tooltip):
        tooltip.place_forget()

    def retrain_on_all_data_button(self):
        self.active_log_widget = self.log_widget
        try:
            from src.utils.logging_utils import log_audit
            log_audit("RetrainAllData", "User triggered retrain on all data.")
            self.controller.task_orchestrator.start_task(
                task_name="retrain_on_all_data",
                button=self.retrain_all_button,
                progress_bar=self.progress_bar,
                eta_label=self.eta_label,
                log_widget=self.log_widget
            )
        except Exception as e:
            import logging
            logging.error(f"Exception in retrain_on_all_data_button: {e}", exc_info=True)
            self.controller.show_error_dialog("Retrain Error", str(e))

class PageSettings(PageBase):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        self.controller = controller
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        frame = ctk.CTkFrame(self, fg_color="#ffffff", corner_radius=12)
        frame.grid(row=0, column=0, sticky="nsew", padx=40, pady=40)
        frame.grid_columnconfigure(1, weight=1)
        # --- Input fields ---
        self.entries = {}
        # Split ratio
        ctk.CTkLabel(frame, text="Train/Val Split Ratio (0-1)", font=controller.fonts["BODY"], fg_color="transparent").grid(row=0, column=0, sticky="w", pady=5)
        self.entries['split_ratio'] = ctk.CTkEntry(frame)
        self.entries['split_ratio'].insert(0, str(controller.training_settings.get('split_ratio', 0.2)))
        self.entries['split_ratio'].grid(row=0, column=1, sticky="ew", pady=5)
        # Window sizes
        ctk.CTkLabel(frame, text="Window Sizes (comma, e.g. 10,30,50)", font=controller.fonts["BODY"], fg_color="transparent").grid(row=1, column=0, sticky="w", pady=5)
        self.entries['window_sizes'] = ctk.CTkEntry(frame)
        self.entries['window_sizes'].insert(0, ','.join(map(str, controller.training_settings.get('window_sizes', [10,30,50]))))
        self.entries['window_sizes'].grid(row=1, column=1, sticky="ew", pady=5)
        # n_lags
        ctk.CTkLabel(frame, text="Jumlah Lag (n_lags)", font=controller.fonts["BODY"], fg_color="transparent").grid(row=2, column=0, sticky="w", pady=5)
        self.entries['n_lags'] = ctk.CTkEntry(frame)
        self.entries['n_lags'].insert(0, str(controller.training_settings.get('n_lags', 10)))
        self.entries['n_lags'].grid(row=2, column=1, sticky="ew", pady=5)
        # n_trials
        ctk.CTkLabel(frame, text="Jumlah Trial Optuna (n_trials)", font=controller.fonts["BODY"], fg_color="transparent").grid(row=3, column=0, sticky="w", pady=5)
        self.entries['n_trials'] = ctk.CTkEntry(frame)
        self.entries['n_trials'].insert(0, str(controller.training_settings.get('n_trials', 30)))
        self.entries['n_trials'].grid(row=3, column=1, sticky="ew", pady=5)
        # threshold_corr
        ctk.CTkLabel(frame, text="Threshold Korelasi Fitur (0-1)", font=controller.fonts["BODY"], fg_color="transparent").grid(row=4, column=0, sticky="w", pady=5)
        self.entries['threshold_corr'] = ctk.CTkEntry(frame)
        self.entries['threshold_corr'].insert(0, str(controller.training_settings.get('threshold_corr', 0.65)))
        self.entries['threshold_corr'].grid(row=4, column=1, sticky="ew", pady=5)
        # Tombol Simpan
        self.save_btn = ctk.CTkButton(frame, text="Simpan/Apply", command=self.save_settings, fg_color="#3A7EBF", hover_color="#2563A6", text_color="#ffffff", height=40, corner_radius=10)
        self.save_btn.grid(row=5, column=0, columnspan=2, pady=20)
        # Tooltip/help
        self.help_label = ctk.CTkLabel(frame, text="Ubah parameter training di sini. Semua perubahan akan diterapkan ke pipeline.", font=controller.fonts["SMALL"], text_color="#2563A6", fg_color="transparent")
        self.help_label.grid(row=6, column=0, columnspan=2, pady=5)

    def save_settings(self):
        try:
            # Validasi dan simpan ke state
            split_ratio_str = self.entries['split_ratio'].get()
            window_sizes_str = self.entries['window_sizes'].get()
            n_lags_str = self.entries['n_lags'].get()
            n_trials_str = self.entries['n_trials'].get()
            threshold_corr_str = self.entries['threshold_corr'].get()

            # Split ratio
            try:
                split_ratio = float(split_ratio_str)
                assert 0 < split_ratio < 1, "Split ratio harus antara 0 dan 1."
            except Exception:
                raise ValueError("Split ratio harus berupa angka desimal antara 0 dan 1.")
            # Window sizes
            try:
                window_sizes = [int(x.strip()) for x in window_sizes_str.split(',') if x.strip()]
                assert all(w > 0 for w in window_sizes), "Semua window size harus > 0."
            except Exception:
                raise ValueError("Window sizes harus berupa daftar angka bulat positif, dipisahkan koma.")
            # n_lags
            try:
                n_lags = int(n_lags_str)
                assert n_lags > 0, "Jumlah lag harus > 0."
            except Exception:
                raise ValueError("Jumlah lag harus berupa angka bulat positif.")
            # n_trials
            try:
                n_trials = int(n_trials_str)
                assert n_trials > 0, "Jumlah trial harus > 0."
            except Exception:
                raise ValueError("Jumlah trial harus berupa angka bulat positif.")
            # threshold_corr
            try:
                threshold_corr = float(threshold_corr_str)
                assert 0 < threshold_corr < 1, "Threshold korelasi harus antara 0 dan 1."
            except Exception:
                raise ValueError("Threshold korelasi harus berupa angka desimal antara 0 dan 1.")

            self.controller.training_settings = {
                'split_ratio': split_ratio,
                'window_sizes': window_sizes,
                'n_lags': n_lags,
                'n_trials': n_trials,
                'threshold_corr': threshold_corr
            }
            log_audit("SaveSettings", "User updated pipeline settings.")
            self.help_label.configure(text="Setting berhasil disimpan dan akan diterapkan ke pipeline.", text_color="#2563A6")
        except Exception as e:
            import logging
            logging.error(f"Validation error in save_settings: {e}", exc_info=True)
            self.controller.show_error_dialog("Settings Error", str(e))

class PageLogs(PageBase):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        self.controller = controller
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # --- Title ---
        title = ctk.CTkLabel(self, text="Log Viewer", font=self.controller.fonts["MAIN_TITLE"], text_color="#222")
        title.grid(row=0, column=0, sticky="w", pady=(0, 10), padx=(0, 0))

        # --- Controls ---
        controls_frame = ctk.CTkFrame(self, fg_color="transparent")
        controls_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        controls_frame.grid_columnconfigure(6, weight=1)

        ctk.CTkLabel(controls_frame, text="Level:", font=self.controller.fonts["BODY"], text_color="#222").grid(row=0, column=0, padx=(0, 4))
        self.level_var = tk.StringVar(value="ALL")
        level_menu = ctk.CTkOptionMenu(controls_frame, variable=self.level_var, values=["ALL", "INFO", "WARNING", "ERROR", "CRITICAL"], width=100, command=self.filter_logs)
        level_menu.grid(row=0, column=1, padx=(0, 10))

        ctk.CTkLabel(controls_frame, text="Search:", font=self.controller.fonts["BODY"], text_color="#222").grid(row=0, column=2, padx=(0, 4))
        self.search_var = tk.StringVar()
        search_entry = ctk.CTkEntry(controls_frame, textvariable=self.search_var, width=180)
        search_entry.grid(row=0, column=3, padx=(0, 10))
        search_entry.bind('<KeyRelease>', lambda e: self.filter_logs())

        open_btn = ctk.CTkButton(controls_frame, text="Open Log Folder", command=self.open_log_folder, height=32, corner_radius=8, fg_color="#E6EAF2", text_color="#222")
        open_btn.grid(row=0, column=4, padx=(0, 10))
        clear_btn = ctk.CTkButton(controls_frame, text="Clear Logs", command=self.clear_logs, height=32, corner_radius=8, fg_color="#D32F2F", text_color="#fff", hover_color="#B71C1C")
        clear_btn.grid(row=0, column=5, padx=(0, 10))

        # --- Log Textbox ---
        log_frame = ctk.CTkFrame(self, fg_color="#212121", corner_radius=8)
        log_frame.grid(row=2, column=0, sticky="nsew")
        log_frame.grid_rowconfigure(0, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)
        self.log_text = ctk.CTkTextbox(log_frame, wrap=tk.WORD, corner_radius=8, font=self.controller.fonts["MONO"], border_width=0, fg_color="transparent")
        self.log_text.grid(row=0, column=0, sticky="nsew", padx=15, pady=15)
        self.log_text.configure(state="disabled")

        # --- Internal log buffer ---
        self.log_buffer = []  # List of (level, msg) tuples
        self.max_log_lines = 2000
        self.last_filter = ("ALL", "")

        # --- Real-time log update integration ---
        self.after(200, self.poll_log_queue)

    def poll_log_queue(self):
        # Pull from the main GUI queue for new logs
        while not self.controller.gui_queue.empty():
            msg = self.controller.gui_queue.get_nowait()
            if msg.get("type") == "log":
                record = msg.get("record", "")
                level = self.extract_level(record)
                self.log_buffer.append((level, record))
                if len(self.log_buffer) > self.max_log_lines:
                    self.log_buffer = self.log_buffer[-self.max_log_lines:]
        self.filter_logs()
        self.after(200, self.poll_log_queue)

    def extract_level(self, record):
        # Extract log level from the log string
        for lvl in ("CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"):
            if f"- {lvl} -" in record:
                return lvl
        return "INFO"

    def filter_logs(self, *_):
        level = self.level_var.get()
        keyword = self.search_var.get().lower()
        if (level, keyword) == self.last_filter:
            return
        self.last_filter = (level, keyword)
        self.log_text.configure(state="normal")
        self.log_text.delete(1.0, tk.END)
        for lvl, msg in self.log_buffer:
            if (level == "ALL" or lvl == level) and (keyword in msg.lower()):
                self.log_text.insert(tk.END, msg + "\n")
        self.log_text.yview(tk.END)
        self.log_text.configure(state="disabled")

    def open_log_folder(self):
        import platform
        from src.utils.logging_utils import LOG_DIR
        if platform.system() == "Windows":
            os.startfile(LOG_DIR)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", LOG_DIR])
        else:
            subprocess.Popen(["xdg-open", LOG_DIR])

    def clear_logs(self):
        from src.utils.logging_utils import LOG_FILE
        self.log_buffer.clear()
        self.filter_logs()
        try:
            with open(LOG_FILE, "w", encoding="utf-8") as f:
                f.write("")
        except Exception as e:
            import logging
            logging.error(f"Failed to clear log file: {e}")
