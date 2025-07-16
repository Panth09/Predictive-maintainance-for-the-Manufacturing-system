import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pandas as pd
import numpy as np
import pickle
import os
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import threading
import json
import subprocess
import webbrowser  # Import webbrowser to open the default browser

# Try to import pyttsx3 for text-to-speech
try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False


class PredictionApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Manufacturing 6G Efficiency Prediction")
        self.root.state('zoomed')  # Maximize window

        # Set theme
        self.style = ttk.Style()
        self.style.theme_use('clam')

        # Configure colors
        self.bg_color = "#f0f0f0"
        self.accent_color = "#4a86e8"
        self.secondary_color = "#34a853"

        # Apply styles
        self.style.configure('TFrame', background=self.bg_color)
        self.style.configure('TLabel', background=self.bg_color, font=('Helvetica', 11))
        self.style.configure('TButton', font=('Helvetica', 11))
        self.style.configure('Accent.TButton', background=self.accent_color, foreground='white')
        self.style.configure('Header.TLabel', font=('Helvetica', 18, 'bold'))
        self.style.configure('Result.TLabel', font=('Helvetica', 14, 'bold'))

        # Initialize TTS engine if available
        self.tts_engine = None
        if TTS_AVAILABLE:
            try:
                self.tts_engine = pyttsx3.init()
                self.tts_engine.setProperty('rate', 150)
            except:
                pass

        # Load model
        self.model = None
        self.scaler = None
        self.feature_names = None
        self.try_load_model()

        # Create UI
        self.create_main_ui()

        # Welcome message
        self.root.after(500, self.speak_welcome)

    def try_load_model(self):
        """Try to load the saved model and scaler"""
        try:
            # Check if model files exist
            if os.path.exists("efficiency_model.pkl") and os.path.exists("efficiency_scaler.pkl"):
                with open("efficiency_model.pkl", "rb") as f:
                    self.model = pickle.load(f)
                with open("efficiency_scaler.pkl", "rb") as f:
                    self.scaler = pickle.load(f)
                with open("feature_names.json", "r") as f:
                    self.feature_names = json.load(f)
        except Exception as e:
            print(f"Error loading model: {e}")
            pass

    def speak_welcome(self):
        """Speak welcome message if TTS is available"""
        if self.tts_engine:
            def speak():
                self.tts_engine.say("Welcome to Manufacturing 6G Efficiency Prediction System")
                self.tts_engine.say("Please enter the parameters or load a dataset for prediction")
                self.tts_engine.runAndWait()

            # Run TTS in a thread to avoid UI freeze
            thread = threading.Thread(target=speak)
            thread.daemon = True
            thread.start()

    def create_main_ui(self):
        """Create the main UI components"""
        # Main container with notebook for tabs
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create tabs
        self.create_single_prediction_tab()
        self.create_batch_prediction_tab()
        self.create_model_info_tab()

        # Status bar at bottom
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def create_single_prediction_tab(self):
        """Create the tab for single instance prediction"""
        single_tab = ttk.Frame(self.notebook)
        self.notebook.add(single_tab, text="Single Prediction")

        # Title
        title = ttk.Label(single_tab, text="Predict Manufacturing Efficiency", style="Header.TLabel")
        title.pack(pady=(20, 10))

        # Scrollable input frame
        canvas = tk.Canvas(single_tab, bg=self.bg_color, highlightthickness=0)
        scrollbar = ttk.Scrollbar(single_tab, orient="vertical", command=canvas.yview)
        input_frame_outer = ttk.Frame(canvas)

        input_frame_outer.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=input_frame_outer, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, padx=(20, 0))
        scrollbar.pack(side="right", fill="y", padx=(0, 20))

        # Input frame with fields
        input_frame = ttk.Frame(input_frame_outer)
        input_frame.pack(pady=10, fill=tk.X, padx=10)

        # Fields dictionary: field_name -> (label_text, input_type, default, options, min_val, max_val)
        self.fields = {
            "Machine_ID": ("Machine ID", "int", 100, None, 1, 1000),
            "Operation_Mode": ("Operation Mode", "combo", "Active", ["Idle", "Active", "Maintenance"], None, None),
            "Temperature_C": ("Temperature (°C)", "float", 55.0, None, 20.0, 100.0),
            "Vibration_Hz": ("Vibration (Hz)", "float", 2.5, None, 0.0, 10.0),
            "Power_Consumption_kW": ("Power Consumption (kW)", "float", 5.0, None, 1.0, 20.0),
            "Network_Latency_ms": ("Network Latency (ms)", "float", 30.0, None, 1.0, 200.0),
            "Packet_Loss_%": ("Packet Loss (%)", "float", 2.0, None, 0.0, 10.0),
            "Quality_Control_Defect_Rate_%": ("Quality Control Defect Rate (%)", "float", 1.5, None, 0.0, 5.0),
            "Production_Speed_units_per_hr": ("Production Speed (units/hr)", "float", 500.0, None, 100.0, 1000.0),
            "Predictive_Maintenance_Score": ("Predictive Maintenance Score", "float", 60.0, None, 0.0, 100.0),
            "Error_Rate_%": ("Error Rate (%)", "float", 2.0, None, 0.0, 5.0)
        }

        # Create input fields
        self.entries = {}
        for i, (field, (label_text, input_type, default, options, min_val, max_val)) in enumerate(self.fields.items()):
            # Create label
            label = ttk.Label(input_frame, text=f"{label_text}:", width=25, anchor=tk.E)
            label.grid(row=i, column=0, padx=(10, 5), pady=5, sticky=tk.E)

            # Create input based on type
            if input_type == "combo":
                var = tk.StringVar(value=default)
                entry = ttk.Combobox(input_frame, textvariable=var, values=options, width=40, font=("Helvetica", 16))
                entry.grid(row=i, column=1, padx=5, pady=20, sticky=tk.W)
                self.entries[field] = entry
            else:
                var = tk.StringVar(value=str(default))
                entry = ttk.Entry(input_frame, textvariable=var, width=40, font=("Helvetica", 16))  
                entry.grid(row=i, column=1, padx=5, pady=20, sticky=tk.W)
                self.entries[field] = entry

            # Add min/max value label if applicable
            if min_val is not None and max_val is not None:
                range_label = ttk.Label(input_frame,
                                        text=f"Range: {min_val} - {max_val}",
                                        font=("Helvetica", 9),
                                        foreground="gray")
                range_label.grid(row=i, column=2, padx=5, pady=5, sticky=tk.W)

            # Bind Enter key
            entry.bind("<Return>", lambda event, field=field: self.focus_next(event, field))

        # Buttons frame
        button_frame = ttk.Frame(single_tab)
        button_frame.pack(pady=20)

        # Predict button
        predict_btn = ttk.Button(
            button_frame, 
            text="Predict", 
            command=self.predict_single,
            style="Accent.TButton",
            width=15
        )
        predict_btn.pack(side=tk.LEFT, padx=10)
        
        # Clear button
        clear_btn = ttk.Button(
            button_frame, 
            text="Clear", 
            command=self.clear_single_form,
            width=15
        )
        clear_btn.pack(side=tk.LEFT, padx=10)
        
        # Result frame
        result_frame = ttk.LabelFrame(single_tab, text="Prediction Result", padding=10)
        result_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self.result_var = tk.StringVar(value="No prediction yet")
        self.result_label = ttk.Label(
            result_frame, 
            textvariable=self.result_var,
            style="Result.TLabel",
            foreground=self.secondary_color
        )
        self.result_label.pack(pady=10)
        
        # Parameter impact display frame
        self.impact_frame = ttk.Frame(result_frame)
        self.impact_frame.pack(fill=tk.X, pady=5)
        
        # Create canvas for displaying a gauge or other visualization
        self.fig = plt.Figure(figsize=(5, 2), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, result_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(fill=tk.X, expand=True)
        
        # Initial empty plot
        self.update_gauge(0)
    
    def create_batch_prediction_tab(self):
        """Create the tab for batch prediction"""
        batch_tab = ttk.Frame(self.notebook)
        self.notebook.add(batch_tab, text="Batch Prediction")
        
        # Title
        title = ttk.Label(batch_tab, text="Batch Manufacturing Efficiency Prediction", style="Header.TLabel")
        title.pack(pady=(20,10))
        
        # File selection frame
        file_frame = ttk.Frame(batch_tab)
        file_frame.pack(pady=10, fill=tk.X, padx=20)
        
        # File path
        ttk.Label(file_frame, text="Dataset:").grid(row=0, column=0, padx=5, pady=10)
        self.file_path_var = tk.StringVar()
        file_entry = ttk.Entry(file_frame, textvariable=self.file_path_var, width=50)
        file_entry.grid(row=0, column=1, padx=5, pady=10)
        
        browse_btn = ttk.Button(
            file_frame, 
            text="Browse", 
            command=self.browse_file
        )
        browse_btn.grid(row=0, column=2, padx=5, pady=10)
        
        # Buttons
        button_frame = ttk.Frame(batch_tab)
        button_frame.pack(pady=10)
        
        load_btn = ttk.Button(
            button_frame, 
            text="Load & Preview", 
            command=self.load_preview_data,
            width=15
        )
        load_btn.pack(side=tk.LEFT, padx=10)
        
        predict_batch_btn = ttk.Button(
            button_frame, 
            text="Predict All", 
            command=self.predict_batch,
            style="Accent.TButton",
            width=15
        )
        predict_batch_btn.pack(side=tk.LEFT, padx=10)
        
        save_btn = ttk.Button(
            button_frame, 
            text="Save Results", 
            command=self.save_batch_results,
            width=15
        )
        save_btn.pack(side=tk.LEFT, padx=10)
        
        # Preview frame
        preview_frame = ttk.LabelFrame(batch_tab, text="Data Preview", padding=10)
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Treeview for data display
        self.tree = ttk.Treeview(preview_frame)
        tree_scroll_y = ttk.Scrollbar(preview_frame, orient="vertical", command=self.tree.yview)
        tree_scroll_x = ttk.Scrollbar(preview_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)
        
        tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        tree_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        # Batch data
        self.batch_data = None
        self.batch_results = None
    
    def create_model_info_tab(self):
        """Create the tab for model information"""
        info_tab = ttk.Frame(self.notebook)
        self.notebook.add(info_tab, text="Model Information")
        
        # Title
        title = ttk.Label(info_tab, text="Machine Learning Model Information", style="Header.TLabel")
        title.pack(pady=(20, 10))
        
        # Model info frame
        info_frame = ttk.LabelFrame(info_tab, text="Model Details", padding=10)
        info_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Description text
        description = """
        This application uses machine learning to predict manufacturing efficiency in a 6G-enabled environment.
        
        The model is trained on various parameters that affect manufacturing processes:
        
        Basic Manufacturing Parameters:
        - Machine ID: Unique identifier for each machine
        - Operation Mode: Current operational state (Idle, Active, Maintenance)
        - Temperature: Operating temperature in Celsius
        - Vibration: Vibration level in Hz
        - Power Consumption: Energy usage in kilowatts
        
        Network and Communication Parameters:
        - Network Latency: Communication delay in milliseconds
        - Packet Loss: Data transmission loss percentage
        
        Quality and Performance Parameters:
        - Quality Control Defect Rate: Percentage of defective products
        - Production Speed: Units produced per hour
        - Predictive Maintenance Score: System health indicator (0-100)
        - Error Rate: Process error percentage
        
        The prediction classifies efficiency as LOW, MEDIUM, or HIGH based on 
        these parameters.
        
        You can make individual predictions or process an entire dataset in batch mode.
        """
        
        info_text = tk.Text(info_frame, wrap=tk.WORD, height=20, width=60)
        info_text.insert(tk.END, description)
        info_text.config(state=tk.DISABLED)  # Make read-only
        info_text.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        # Buttons frame
        button_frame = ttk.Frame(info_tab)
        button_frame.pack(pady=20)
        
        # Training button
        train_btn = ttk.Button(
            button_frame, 
            text="Train New Model", 
            command=self.train_model_dialog,
            width=20
        )
        train_btn.pack(side=tk.LEFT, padx=10)
        
        # Open Dashboard button
        dashboard_btn = ttk.Button(
            button_frame,
            text="Open Dashboard",
            command=self.open_dashboard,
            width=20
        )
        dashboard_btn.pack(side=tk.LEFT, padx=10)

        # Open App button
        app_btn = ttk.Button(
            button_frame,
            text="Open App",
            command=self.open_app,
            width=20
        )
        app_btn.pack(side=tk.LEFT, padx=10)

    def open_dashboard(self):
        """Open the dashboard in a new process"""
        try:
            # Replace 'dashboard.py' with the script or command to start your dashboard
            subprocess.Popen(["python", "c:/Users/uttam/OneDrive/Desktop/final_api/dashboard.py"])
            messagebox.showinfo("Dashboard", "Dashboard is opening...")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open the dashboard: {str(e)}")

    def open_app(self):
        """Open the Flask app (app.py) and redirect to its web interface"""
        try:
            # Start the Flask app in a new subprocess
            subprocess.Popen(["python", "c:/Users/uttam/OneDrive/Desktop/final_api/app.py"])

            # Open the default web browser to the Flask app's URL
            webbrowser.open("http://127.0.0.1:5000")  # Adjust the port if necessary
            messagebox.showinfo("App", "The app is opening in your browser...")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open the app: {str(e)}")

    def focus_next(self, event, current_field):
        """Move focus to next field or submit on last field"""
        fields_list = list(self.fields.keys())
        current_index = fields_list.index(current_field)
        
        if current_index < len(fields_list) - 1:
            # Move to next field
            next_field = fields_list[current_index + 1]
            self.entries[next_field].focus_set()
        else:
            # Last field, trigger prediction
            self.predict_single()
        
        return "break"
    
    def clear_single_form(self):
        """Clear all fields in the single prediction form"""
        for field, (_, _, default, _, _, _) in self.fields.items():
            if isinstance(self.entries[field], ttk.Combobox):
                self.entries[field].set(default)
            else:
                self.entries[field].delete(0, tk.END)
                self.entries[field].insert(0, str(default))
        
        self.result_var.set("No prediction yet")
        
        # Clear previous impact display
        for widget in self.impact_frame.winfo_children():
            widget.destroy()
            
        self.update_gauge(0)
    
    def predict_single(self):
        """Predict efficiency for a single input"""
        # Get values from form
        data = {}
        for field, (_, input_type, _, _, min_val, max_val) in self.fields.items():
            value = self.entries[field].get().strip()
            
            # Validate and convert
            try:
                if input_type == "int":
                    data[field] = int(value)
                    # Validate min/max
                    if min_val is not None and data[field] < min_val:
                        messagebox.showerror("Invalid Input", f"{field} must be at least {min_val}.")
                        return
                    if max_val is not None and data[field] > max_val:
                        messagebox.showerror("Invalid Input", f"{field} must be at most {max_val}.")
                        return
                elif input_type == "float":
                    data[field] = float(value)
                    # Validate min/max
                    if min_val is not None and data[field] < min_val:
                        messagebox.showerror("Invalid Input", f"{field} must be at least {min_val}.")
                        return
                    if max_val is not None and data[field] > max_val:
                        messagebox.showerror("Invalid Input", f"{field} must be at most {max_val}.")
                        return
                else:
                    data[field] = value
            except ValueError:
                messagebox.showerror("Invalid Input", f"{field} must be a valid {input_type}.")
                return
        
        # Clear previous impact display
        for widget in self.impact_frame.winfo_children():
            widget.destroy()
        
        # Check if model is loaded
        if self.model is None:
            # If no model, use the improved prediction logic with all parameters
            base_efficiency, impacts = self.calculate_parameter_impacts(data)
            
            # Ensure the final score is within 0-10 range
            final_score = max(0, min(10, base_efficiency))
            
            # Determine status based on score
            if final_score < 4:
                status = "LOW"
                color = "red"
                gauge_value = 25
            elif final_score < 7:
                status = "MEDIUM" 
                color = "orange"
                gauge_value = 60
            else:
                status = "HIGH"
                color = "green"
                gauge_value = 90
                
            # Display parameter impacts
            ttk.Label(self.impact_frame, text="Parameter Impacts:", font=("Helvetica", 10, "bold")).pack(anchor=tk.W, pady=(5,2))
            
            # Create a 2-column layout for impacts (to save space)
            impact_columns_frame = ttk.Frame(self.impact_frame)
            impact_columns_frame.pack(fill=tk.X, expand=True)
            
            left_col = ttk.Frame(impact_columns_frame)
            right_col = ttk.Frame(impact_columns_frame)
            left_col.pack(side=tk.LEFT, fill=tk.X, expand=True)
            right_col.pack(side=tk.RIGHT, fill=tk.X, expand=True)
            
            # Split impacts between the two columns
            cols = [left_col, right_col]
            for i, (param, impact) in enumerate(impacts.items()):
                col = cols[i % 2]  # Alternate between columns
                impact_text = f"{param}: {impact:+.1f}"
                color = "green" if impact > 0 else "red" if impact < 0 else "black"
                impact_label = ttk.Label(
                    col, 
                    text=impact_text,
                    foreground=color
                )
                impact_label.pack(anchor=tk.W, padx=10, pady=2)
            
        else:
            # Use the loaded ML model
            try:
                # Prepare input for the model
                X = self.prepare_input_for_model(data)
                status = self.model.predict(X)[0]
                
                # Calculate impacts for display
                base_efficiency, impacts = self.calculate_parameter_impacts(data)
                final_score = max(0, min(10, base_efficiency))
                
                # Set color and gauge value
                if status == "LOW":
                    color = "red"
                    gauge_value = 25
                elif status == "MEDIUM":
                    color = "orange"
                    gauge_value = 60
                else:  # HIGH
                    color = "green"
                    gauge_value = 90
                
                # Display parameter impacts
                ttk.Label(self.impact_frame, text="Parameter Impacts:", font=("Helvetica", 10, "bold")).pack(anchor=tk.W, pady=(5,2))
                
                # Create a 2-column layout for impacts
                impact_columns_frame = ttk.Frame(self.impact_frame)
                impact_columns_frame.pack(fill=tk.X, expand=True)
                
                left_col = ttk.Frame(impact_columns_frame)
                right_col = ttk.Frame(impact_columns_frame)
                left_col.pack(side=tk.LEFT, fill=tk.X, expand=True)
                right_col.pack(side=tk.RIGHT, fill=tk.X, expand=True)
                
                # Split impacts between the two columns
                cols = [left_col, right_col]
                for i, (param, impact) in enumerate(impacts.items()):
                    col = cols[i % 2]  # Alternate between columns
                    impact_text = f"{param}: {impact:+.1f}"
                    color = "green" if impact > 0 else "red" if impact < 0 else "black"
                    impact_label = ttk.Label(
                        col, 
                        text=impact_text,
                        foreground=color
                    )
                    impact_label.pack(anchor=tk.W, padx=10, pady=2)
                
            except Exception as e:
                messagebox.showerror("Prediction Error", f"Error during prediction: {str(e)}")
                return
        
        # Update UI with prediction
        self.result_var.set(f"Efficiency Status: {status} (Score: {final_score:.1f}/10)")
        
        # Update gauge visualization
        self.update_gauge(gauge_value, color)
        
        # Speak result if TTS is available
        if self.tts_engine:
            def speak():
                self.tts_engine.say(f"The predicted efficiency status is {status}")
                self.tts_engine.runAndWait()
            
            thread = threading.Thread(target=speak)
            thread.daemon = True
            thread.start()
    
    def calculate_parameter_impacts(self, data):
        """Calculate direct impacts from each parameter using a comprehensive model"""
        # Initialize a starting efficiency of 5 (middle of 0-10 scale)
        base_efficiency = 5.0
        
        # Track parameter impacts for debugging/transparency
        impacts = {}
        
        # === Machine ID impact ===
        if "Machine_ID" in data:
            machine_id = data["Machine_ID"]
            if machine_id <= 200:
                impact = +1.0  # Newer machines
            elif machine_id <= 500:
                impact = 0.0   # Average age machines
            else:
                impact = -1.0  # Older machines
            
            impacts["Machine_ID"] = impact
            base_efficiency += impact
        
        # === Operation Mode direct impact ===
        if "Operation_Mode" in data:
            mode = data["Operation_Mode"]
            if mode == "Active":
                impact = +1.5  # Active mode is most efficient
            elif mode == "Idle":
                impact = 0.0   # Idle is neutral
            else:  # Maintenance
                impact = -1.5  # Maintenance mode is least efficient
                
            impacts["Operation_Mode"] = impact
            base_efficiency += impact
        
        # === Temperature direct impact ===
        if "Temperature_C" in data:
            temp = data["Temperature_C"]
            if 40 <= temp <= 70:
                impact = +1.0  # Optimal temperature range
            elif temp < 40:
                impact = -0.5  # Too cold
            else:  # temp > 70
                impact = -1.0  # Too hot
            
            impacts["Temperature_C"] = impact
            base_efficiency += impact
        
        # === Vibration direct impact ===
        if "Vibration_Hz" in data:
            vib = data["Vibration_Hz"]
            if vib < 2.0:
                impact = +1.0  # Low vibration
            elif vib < 5.0:
                impact = 0.0   # Acceptable vibration
            else:
                impact = -1.0  # High vibration
            
            impacts["Vibration_Hz"] = impact
            base_efficiency += impact
        
        # === Power Consumption direct impact ===
        if "Power_Consumption_kW" in data:
            power = data["Power_Consumption_kW"]
            if power < 5.0:
                impact = +1.0  # Efficient power use
            elif power < 10.0:
                impact = 0.0   # Average power use
            else:
                impact = -1.0  # High power use
            
            impacts["Power_Consumption_kW"] = impact
            base_efficiency += impact
        
        # === Network Latency direct impact ===
        if "Network_Latency_ms" in data:
            latency = data["Network_Latency_ms"]
            if latency < 20.0:
                impact = +1.0  # Excellent latency
            elif latency < 50.0:
                impact = 0.0   # Acceptable latency
            else:
                impact = -1.0  # Poor latency
            
            impacts["Network_Latency_ms"] = impact
            base_efficiency += impact
        
        # === Packet Loss direct impact ===
        if "Packet_Loss_%" in data:
            loss = data["Packet_Loss_%"]
            if loss < 1.0:
                impact = +1.0  # Minimal packet loss
            elif loss < 3.0:
                impact = 0.0   # Acceptable packet loss
            else:
                impact = -1.0  # High packet loss
            
            impacts["Packet_Loss_%"] = impact
            base_efficiency += impact
        
        # === Quality Control Defect Rate impact ===
        if "Quality_Control_Defect_Rate_%" in data:
            defect = data["Quality_Control_Defect_Rate_%"]
            if defect < 1.0:
                impact = +1.5  # Excellent quality
            elif defect < 2.0:
                impact = +0.5  # Good quality
            elif defect < 3.0:
                impact = 0.0   # Average quality
            else:
                impact = -1.5  # Poor quality
            
            impacts["Quality_Control_Defect_Rate_%"] = impact
            base_efficiency += impact
        
        # === Production Speed impact ===
        if "Production_Speed_units_per_hr" in data:
            speed = data["Production_Speed_units_per_hr"]
            if speed > 600:
                impact = +1.0  # High production speed
            elif speed > 300:
                impact = 0.0   # Average production speed
            else:
                impact = -1.0  # Low production speed
            
            impacts["Production_Speed_units_per_hr"] = impact
            base_efficiency += impact
        
        # === Predictive Maintenance Score impact ===
        if "Predictive_Maintenance_Score" in data:
            score = data["Predictive_Maintenance_Score"]
            if score > 70:
                impact = +1.0  # Well-maintained
            elif score > 40:
                impact = 0.0   # Adequately maintained
            else:
                impact = -1.0  # Poorly maintained
            
            impacts["Predictive_Maintenance_Score"] = impact
            base_efficiency += impact
        
        # === Error Rate impact ===
        if "Error_Rate_%" in data:
            error = data["Error_Rate_%"]
            if error < 1.0:
                impact = +1.0  # Minimal errors
            elif error < 3.0:
                impact = 0.0   # Acceptable error rate
            else:
                impact = -1.0  # High error rate
            
            impacts["Error_Rate_%"] = impact
            base_efficiency += impact
            
        return base_efficiency, impacts
    
    def predict_efficiency_simplified(self, data):
        """Simplified prediction logic with impacts from all parameters"""
        # Calculate parameter impacts
        base_efficiency, _ = self.calculate_parameter_impacts(data)
        
        # Ensure the final score is within 0-10 range
        final_score = max(0, min(10, base_efficiency))
        
        # Classify based on score
        if final_score < 4:
            return "LOW"
        elif final_score < 7:
            return "MEDIUM"
        else:
            return "HIGH"
    
    def get_efficiency_score(self, data):
        """Get a numerical efficiency score for visualization"""
        # Calculate parameter impacts
        base_efficiency, _ = self.calculate_parameter_impacts(data)
        
        # Convert 0-10 scale to 0-100 scale for gauge
        percentage = (base_efficiency / 10) * 100
        
        # Ensure within 0-100 range
        return max(0, min(100, percentage))
    
    def prepare_input_for_model(self, data):
        """Prepare input data for the ML model"""
        # This might need adjustment based on your actual model's requirements
        if self.feature_names is None:
            # Fallback if feature names not available
            # Create a list of features in the expected order
            expected_features = [
                "Machine_ID",
                "Operation_Mode_Active", "Operation_Mode_Idle", "Operation_Mode_Maintenance", # One-hot encoded
                "Temperature_C",
                "Vibration_Hz",
                "Power_Consumption_kW",
                "Network_Latency_ms",
                "Packet_Loss_%",
                "Quality_Control_Defect_Rate_%",
                "Production_Speed_units_per_hr",
                "Predictive_Maintenance_Score",
                "Error_Rate_%"
            ]
            
            # Create feature vector
            features = []
            for feature in expected_features:
                if feature == "Operation_Mode_Active":
                    features.append(1 if data.get("Operation_Mode") == "Active" else 0)
                elif feature == "Operation_Mode_Idle":
                    features.append(1 if data.get("Operation_Mode") == "Idle" else 0)
                elif feature == "Operation_Mode_Maintenance":
                    features.append(1 if data.get("Operation_Mode") == "Maintenance" else 0)
                elif feature in data:
                    features.append(data[feature])
                else:
                    # Use default value for missing features
                    features.append(0)
            
            X = np.array([features])
        else:
            # Use feature names to ensure correct ordering
            features = []
            for feature in self.feature_names:
                if feature in data:
                    features.append(data[feature])
                else:
                    # Handle one-hot encoding for categorical variables
                    prefix = feature.split('_')[0]
                    if prefix in data and '_' in feature:
                        # This is likely a one-hot encoded feature
                        suffix = feature.split('_', 1)[1]
                        if data[prefix] == suffix:
                            features.append(1)
                        else:
                            features.append(0)
                    else:
                        # Use default value for missing features
                        features.append(0)
            
            X = np.array([features])
        
        # Apply scaling if available
        if self.scaler is not None:
            X = self.scaler.transform(X)
        
        return X
    
    def update_gauge(self, value, color="blue"):
        """Update the gauge visualization"""
        self.ax.clear()
        
        # Create gauge as a horizontal bar
        self.ax.barh([0], [100], color='lightgray', height=0.3)
        self.ax.barh([0], [value], color=color, height=0.3)
        
        # Add percentage text
        self.ax.text(50, 0, f"{value}%", 
                    horizontalalignment='center',
                    verticalalignment='center',
                    fontsize=12, fontweight='bold')
        
        # Remove axes
        self.ax.axis('off')
        
        # Update canvas
        self.fig.tight_layout()
        self.canvas.draw()
    
    def browse_file(self):
        """Open file dialog to select dataset"""
        file_path = filedialog.askopenfilename(
            title="Select Dataset",
            filetypes=[("CSV files", ".csv"), ("All files", ".*")]
        )
        if file_path:
            self.file_path_var.set(file_path)
    
    def load_preview_data(self):
        """Load and preview the selected dataset"""
        file_path = self.file_path_var.get().strip()
        if not file_path:
            messagebox.showerror("Error", "Please select a file first.")
            return
        
        try:
            # Update status
            self.status_var.set(f"Loading {os.path.basename(file_path)}...")
            self.root.update_idletasks()
            
            # Load data
            self.batch_data = pd.read_csv(file_path)
            
            # Clear existing tree
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # Configure columns
            columns = list(self.batch_data.columns)
            self.tree["columns"] = columns
            self.tree["show"] = "headings"
            
            for col in columns:
                self.tree.heading(col, text=col)
                self.tree.column(col, width=100)
            
            # Add data rows (limit to first 100 rows for performance)
            preview_data = self.batch_data.head(100)
            for i, row in preview_data.iterrows():
                values = [str(row[col]) for col in columns]
                self.tree.insert("", "end", values=values)
            
            # Update status
            self.status_var.set(f"Loaded {len(self.batch_data)} rows from {os.path.basename(file_path)}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load file: {str(e)}")
            self.status_var.set("Ready")
    
    def predict_batch(self):
        """Predict for all rows in the batch dataset"""
        if self.batch_data is None or len(self.batch_data) == 0:
            messagebox.showerror("Error", "No data loaded for batch prediction.")
            return
        
        try:
            # Update status
            self.status_var.set("Running batch prediction...")
            self.root.update_idletasks()
            
            # Make a copy of the data
            result_df = self.batch_data.copy()
            
            # Check if model is loaded
            if self.model is None:
                # Use simplified prediction logic
                result_df['Predicted_Efficiency'] = result_df.apply(
                    lambda row: self.predict_efficiency_simplified(row.to_dict()), axis=1
                )
            else:
                # Use the loaded ML model
                try:
                    # Prepare input features
                    if self.feature_names is None:
                        # Assuming all columns except the target are features
                        features = [col for col in result_df.columns if col != 'Efficiency_Status']
                        X = result_df[features].values
                    else:
                        # Use only the columns that are in feature_names
                        available_features = [f for f in self.feature_names if f in result_df.columns]
                        X = result_df[available_features].values
                    
                    # Apply scaling if available
                    if self.scaler is not None:
                        X = self.scaler.transform(X)
                    
                    # Make predictions
                    predictions = self.model.predict(X)
                    result_df['Predicted_Efficiency'] = predictions
                    
                except Exception as e:
                    messagebox.showerror("Prediction Error", f"Error during batch prediction: {str(e)}")
                    self.status_var.set("Ready")
                    return
            
            # Store results
            self.batch_results = result_df
            
            # Update tree view with predictions
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # Configure columns including the prediction column
            columns = list(self.batch_results.columns)
            self.tree["columns"] = columns
            self.tree["show"] = "headings"
            
            for col in columns:
                self.tree.heading(col, text=col)
                self.tree.column(col, width=100)
            
            # Add data rows (limit to first 100 rows for performance)
            preview_data = self.batch_results.head(100)
            for i, row in preview_data.iterrows():
                values = [str(row[col]) for col in columns]
                self.tree.insert("", "end", values=values)
            
            # Count prediction results
            low_count = sum(self.batch_results['Predicted_Efficiency'] == 'LOW')
            med_count = sum(self.batch_results['Predicted_Efficiency'] == 'MEDIUM')
            high_count = sum(self.batch_results['Predicted_Efficiency'] == 'HIGH')
            
            # Update status
            self.status_var.set(
                f"Prediction complete. Results: LOW: {low_count}, MEDIUM: {med_count}, HIGH: {high_count}")
            
            # Show summary in message box
            messagebox.showinfo(
                "Batch Prediction Complete", 
                f"Processed {len(self.batch_results)} records.\n\n"
                f"Results Summary:\n"
                f"- LOW: {low_count} ({low_count/len(self.batch_results)*100:.1f}%)\n"
                f"- MEDIUM: {med_count} ({med_count/len(self.batch_results)*100:.1f}%)\n"
                f"- HIGH: {high_count} ({high_count/len(self.batch_results)*100:.1f}%)\n\n"
                f"Use 'Save Results' to export the complete dataset with predictions."
            )
            
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred during batch prediction: {str(e)}")
            self.status_var.set("Ready")
    
    def save_batch_results(self):
        """Save batch prediction results to CSV"""
        if self.batch_results is None:
            messagebox.showerror("Error", "No prediction results to save.")
            return
        
        try:
            file_path = filedialog.asksaveasfilename(
                title="Save Results",
                defaultextension=".csv",
                filetypes=[("CSV files", ".csv"), ("All files", ".*")]
            )
            
            if file_path:
                self.batch_results.to_csv(file_path, index=False)
                messagebox.showinfo("Success", f"Results saved to {file_path}")
                self.status_var.set(f"Results saved to {os.path.basename(file_path)}")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save results: {str(e)}")
    
    def train_model_dialog(self):
        """Open dialog for training a new model"""
        # Create a toplevel window
        train_window = tk.Toplevel(self.root)
        train_window.title("Train New Model")
        train_window.geometry("500x350")
        train_window.transient(self.root)
        train_window.grab_set()
        
        # Training options frame
        options_frame = ttk.LabelFrame(train_window, text="Training Options")
        options_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Dataset selection
        ttk.Label(options_frame, text="Training Dataset:").grid(row=0, column=0, padx=5, pady=10, sticky=tk.W)
        train_file_var = tk.StringVar()
        train_file_entry = ttk.Entry(options_frame, textvariable=train_file_var, width=40)
        train_file_entry.grid(row=0, column=1, padx=5, pady=10)
        
        browse_train_btn = ttk.Button(
            options_frame, 
            text="Browse", 
            command=lambda: self.browse_file_for_entry(train_file_var)
        )
        browse_train_btn.grid(row=0, column=2, padx=5, pady=10)
        
        # Model selection
        ttk.Label(options_frame, text="Model Type:").grid(row=1, column=0, padx=5, pady=10, sticky=tk.W)
        model_type_var = tk.StringVar(value="Random Forest")
        model_combo = ttk.Combobox(
            options_frame, 
            textvariable=model_type_var, 
            values=["Logistic Regression", "Random Forest", "Gradient Boosting", "XGBoost"],
            width=20
        )
        model_combo.grid(row=1, column=1, padx=5, pady=10, sticky=tk.W)
        
        # Target variable
        ttk.Label(options_frame, text="Target Column:").grid(row=2, column=0, padx=5, pady=10, sticky=tk.W)
        target_var = tk.StringVar(value="Efficiency_Status")
        target_entry = ttk.Entry(options_frame, textvariable=target_var, width=20)
        target_entry.grid(row=2, column=1, padx=5, pady=10, sticky=tk.W)
        
        # Test size
        ttk.Label(options_frame, text="Test Size:").grid(row=3, column=0, padx=5, pady=10, sticky=tk.W)
        test_size_var = tk.StringVar(value="0.2")
        test_size_entry = ttk.Entry(options_frame, textvariable=test_size_var, width=10)
        test_size_entry.grid(row=3, column=1, padx=5, pady=10, sticky=tk.W)
        
        # Buttons frame
        button_frame = ttk.Frame(train_window)
        button_frame.pack(pady=20)
        
        # Train button
        train_btn = ttk.Button(
            button_frame, 
            text="Train Model", 
            command=lambda: self.train_new_model(
                train_file_var.get(),
                model_type_var.get(),
                target_var.get(),
                float(test_size_var.get()),
                train_window
            ),
            style="Accent.TButton",
            width=15
        )
        train_btn.pack(side=tk.LEFT, padx=10)
        
        # Cancel button
        cancel_btn = ttk.Button(
            button_frame, 
            text="Cancel", 
            command=train_window.destroy,
            width=15
        )
        cancel_btn.pack(side=tk.LEFT, padx=10)
    
    def browse_file_for_entry(self, string_var):
        """Browse for file and update entry"""
        file_path = filedialog.askopenfilename(
            title="Select File",
            filetypes=[("CSV files", ".csv"), ("All files", ".*")]
        )
        if file_path:
            string_var.set(file_path)
    
    def train_new_model(self, file_path, model_type, target_column, test_size, window):
        """Train a new model with the given parameters"""
        if not file_path:
            messagebox.showerror("Error", "Please select a training dataset.")
            return
        
        try:
            # Update status
            self.status_var.set("Training new model, please wait...")
            window.update_idletasks()
            
            # Load data
            df = pd.read_csv(file_path)
            
            # Check if target column exists
            if target_column not in df.columns:
                messagebox.showerror("Error", f"Target column '{target_column}' not found in the dataset.")
                self.status_var.set("Ready")
                return
            
            from sklearn.model_selection import train_test_split
            from sklearn.preprocessing import StandardScaler, LabelEncoder
            from sklearn.metrics import accuracy_score
            
            # Prepare data
            X = df.drop(target_column, axis=1)
            y = df[target_column]
            
            # Handle categorical variables
            categorical_columns = X.select_dtypes(include=['object']).columns
            
            # Create a copy to avoid warnings
            X_processed = X.copy()
            
            # Apply label encoding to each categorical column
            label_encoders = {}
            for col in categorical_columns:
                le = LabelEncoder()
                X_processed[col] = le.fit_transform(X_processed[col])
                label_encoders[col] = le
            
            # Save feature names
            feature_names = list(X_processed.columns)
            with open("feature_names.json", "w") as f:
                json.dump(feature_names, f)
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X_processed, y, test_size=test_size, random_state=42
            )
            
            # Scale features
            scaler = StandardScaler()
            X_train = scaler.fit_transform(X_train)
            X_test = scaler.transform(X_test)
            
            # Save scaler
            with open("efficiency_scaler.pkl", "wb") as f:
                pickle.dump(scaler, f)
            
            # Select model
            try:
                from sklearn.linear_model import LogisticRegression
                from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
                import xgboost as xgb
                
                if model_type == "Logistic Regression":
                    model = LogisticRegression(max_iter=1000, random_state=42)
                elif model_type == "Random Forest":
                    model = RandomForestClassifier(n_estimators=100, random_state=42)
                elif model_type == "Gradient Boosting":
                    model = GradientBoostingClassifier(random_state=42)
                elif model_type == "XGBoost":
                    model = xgb.XGBClassifier(random_state=42)
                else:
                    model = RandomForestClassifier(n_estimators=100, random_state=42)
                
            except ImportError:
                # Fallback to RandomForest if XGBoost not available
                from sklearn.ensemble import RandomForestClassifier
                model = RandomForestClassifier(n_estimators=100, random_state=42)
                messagebox.showwarning(
                    "Model Selection", 
                    f"{model_type} is not available, using Random Forest instead."
                )
            
            # Train model
            model.fit(X_train, y_train)
            
            # Evaluate
            y_pred = model.predict(X_test)
            accuracy = accuracy_score(y_test, y_pred)
            
            # Save model
            with open("efficiency_model.pkl", "wb") as f:
                pickle.dump(model, f)
            
            # Load the model
            self.model = model
            self.scaler = scaler
            self.feature_names = feature_names
            
            # Close window
            window.destroy()
            
            # Show results
            messagebox.showinfo(
                "Training Complete", 
                f"Model trained successfully!\n\n"
                f"Model type: {model_type}\n"
                f"Test Accuracy: {accuracy:.4f}\n\n"
                f"The model has been saved and is now active."
            )
            
            self.status_var.set(f"New {model_type} model trained with accuracy {accuracy:.4f}")
            
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred during model training: {str(e)}")
            self.status_var.set("Ready")

if __name__ == "__main__":
    try:
        # Set app DPI awareness (Windows)
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except:
            pass
        
        root = tk.Tk()
        app = PredictionApp(root)
        root.mainloop()
    except Exception as e:
        print(f"Application error: {e}")
        import traceback
        traceback.print_exc()