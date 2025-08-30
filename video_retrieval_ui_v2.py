import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from PIL import Image, ImageTk
import requests
from io import BytesIO
import csv
import json
import os
import numpy as np
from typing import List, Dict, Any
import threading
from datetime import datetime
import string  # Added for punctuation removal

class VideoRetrievalUI:
    def __init__(self, root):
        self.root = root
        self.root.title("USLibAI - Video Retrieval System")
        self.root.geometry("1200x800")
        
        # Backend configuration
        self.backend_url = "http://localhost:8000"  # Adjust as needed
        self.use_mock_data = True  # Will be set by configuration dialog

        # Get directory of current script
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.database_path = os.path.join(base_dir, "database")
        
        # State variables
        self.retrieved_images = []  # List of frame data with IDs and metadata
        self.selected_images = []   # List of selected frame IDs
        self.image_widgets = []     # Keep track of frame widgets
        self.current_task = tk.StringVar(value="KIS")
        self.uploaded_txt_file = None  # Store uploaded TXT file info
        self.uploaded_image_path = None  # Store uploaded image path
        
        self.setup_notebook()
        
    def setup_notebook(self):
        """Setup tabbed interface with PROCESS and DATABASE pages"""
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # PROCESS tab (original functionality)
        self.process_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.process_frame, text="PROCESS")
        
        # DATABASE tab (new functionality)
        self.database_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.database_frame, text="DATABASE")
        
        # Setup both tabs
        self.setup_process_tab()
        self.setup_database_tab()
        
    def setup_process_tab(self):
        """Setup the original UI in the PROCESS tab"""
        # Main container
        main_frame = ttk.Frame(self.process_frame, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Configure grid weights
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # Input section
        self.setup_input_section(main_frame)
        
        # Task selection section
        self.setup_task_section(main_frame)
        
        # Results section
        self.setup_results_section(main_frame)
        
        # Control buttons
        self.setup_control_buttons(main_frame)
        
    def setup_database_tab(self):
        """Setup the DATABASE tab for browsing database folders"""
        main_frame = ttk.Frame(self.database_frame, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="Database Browser", font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        path_frame = ttk.Frame(main_frame)
        path_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(path_frame, text="Database Path:").pack(side=tk.LEFT)
        self.db_path_var = tk.StringVar(value=self.database_path)
        path_entry = ttk.Entry(path_frame, textvariable=self.db_path_var, width=50)
        path_entry.pack(side=tk.LEFT, padx=(10, 10), fill=tk.X, expand=True)
        ttk.Button(path_frame, text="Browse", command=self.browse_database_path).pack(side=tk.LEFT)
        ttk.Button(path_frame, text="Refresh", command=self.refresh_database_view).pack(side=tk.LEFT, padx=(5, 0))
        
        # Database folders grid
        folders_frame = ttk.LabelFrame(main_frame, text="Database Folders", padding="10")
        folders_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create grid for the 6 folder types
        self.setup_database_folders(folders_frame)
        
    def setup_database_folders(self, parent):
        """Setup the 6 database folder browsers"""
        folder_types = [
            ("keyframes", "Keyframes\n(folders with .jpg files)", "folder"),
            ("videos", "Videos\n(.mp4 files)", "file"),
            ("clip-features-32", "Clip Features\n(.npy files)", "file"),
            ("map-keyframes", "Map Keyframes\n(.csv files)", "file"),
            ("media-info", "Media Info\n(.json files)", "file"),
            ("objects", "Objects\n(folders with .json files)", "folder")
        ]
        
        # Create 2x3 grid
        for i, (folder_name, display_name, content_type) in enumerate(folder_types):
            row = i // 3
            col = i % 3
            
            # Create frame for each folder type
            folder_frame = ttk.LabelFrame(parent, text=display_name, padding="10")
            folder_frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            
            # Create listbox with scrollbar
            list_frame = ttk.Frame(folder_frame)
            list_frame.pack(fill=tk.BOTH, expand=True)
            
            listbox = tk.Listbox(list_frame, height=8)
            scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=listbox.yview)
            listbox.configure(yscrollcommand=scrollbar.set)
            
            listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Buttons
            button_frame = ttk.Frame(folder_frame)
            button_frame.pack(fill=tk.X, pady=(10, 0))
            
            ttk.Button(button_frame, text="Open", 
                      command=lambda fn=folder_name, lb=listbox, ct=content_type: self.open_database_item(fn, lb, ct)).pack(side=tk.LEFT, padx=(0, 5))
            ttk.Button(button_frame, text="Refresh", 
                      command=lambda fn=folder_name, lb=listbox, ct=content_type: self.refresh_folder_list(fn, lb, ct)).pack(side=tk.LEFT)
            
            # Store references
            setattr(self, f"{folder_name}_listbox", listbox)
            
        # Configure grid weights
        for i in range(3):
            parent.columnconfigure(i, weight=1)
        for i in range(2):
            parent.rowconfigure(i, weight=1)
            
        # Initial load
        self.refresh_database_view()
        
    def browse_database_path(self):
        """Browse for database folder"""
        path = filedialog.askdirectory(title="Select Database Folder", initialdir=self.database_path)
        if path:
            self.database_path = path
            self.db_path_var.set(path)
            self.refresh_database_view()
            
    def refresh_database_view(self):
        """Refresh all database folder views"""
        folder_types = ["keyframes", "videos", "clip-features-32", "map-keyframes", "media-info", "objects"]
        content_types = ["folder", "file", "file", "file", "file", "folder"]
        
        for folder_name, content_type in zip(folder_types, content_types):
            listbox = getattr(self, f"{folder_name}_listbox")
            self.refresh_folder_list(folder_name, listbox, content_type)
            
    def refresh_folder_list(self, folder_name, listbox, content_type):
        """Refresh individual folder list"""
        listbox.delete(0, tk.END)
        
        folder_path = os.path.join(self.database_path, folder_name)
        if not os.path.exists(folder_path):
            listbox.insert(0, f"Folder '{folder_name}' not found")
            return
            
        try:
            items = os.listdir(folder_path)
            if content_type == "folder":
                # Show only directories
                items = [item for item in items if os.path.isdir(os.path.join(folder_path, item))]
            else:
                # Show only files with appropriate extensions
                if folder_name == "videos":
                    items = [item for item in items if item.lower().endswith('.mp4')]
                elif folder_name == "clip-features-32":
                    items = [item for item in items if item.lower().endswith('.npy')]
                elif folder_name == "map-keyframes":
                    items = [item for item in items if item.lower().endswith('.csv')]
                elif folder_name == "media-info":
                    items = [item for item in items if item.lower().endswith('.json')]
                    
            items.sort()
            for item in items:
                listbox.insert(tk.END, item)
                
            if not items:
                listbox.insert(0, "No items found")
                
        except Exception as e:
            listbox.insert(0, f"Error: {str(e)}")
            
    def open_database_item(self, folder_name, listbox, content_type):
        """Open selected database item"""
        selection = listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select an item to open")
            return
            
        item_name = listbox.get(selection[0])
        if item_name.startswith("Error:") or item_name.startswith("No items") or item_name.startswith("Folder"):
            return
            
        item_path = os.path.join(self.database_path, folder_name, item_name)
        
        try:
            if content_type == "folder":
                # Open folder browser
                self.open_folder_browser(item_path, f"{folder_name}/{item_name}")
            else:
                # Open file viewer
                self.open_file_viewer(item_path, item_name, folder_name)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open {item_name}: {str(e)}")
            
    def open_folder_browser(self, folder_path, title):
        """Open a browser window for folder contents"""
        browser_window = tk.Toplevel(self.root)
        browser_window.title(f"Browse: {title}")
        browser_window.geometry("600x400")
        
        main_frame = ttk.Frame(browser_window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # File list
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        file_listbox = tk.Listbox(list_frame)
        file_scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=file_listbox.yview)
        file_listbox.configure(yscrollcommand=file_scrollbar.set)
        
        file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        file_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Load files
        try:
            files = os.listdir(folder_path)
            files.sort()
            for file in files:
                file_listbox.insert(tk.END, file)
        except Exception as e:
            file_listbox.insert(0, f"Error loading folder: {str(e)}")
            
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        def open_selected_file():
            selection = file_listbox.curselection()
            if selection:
                filename = file_listbox.get(selection[0])
                file_path = os.path.join(folder_path, filename)
                self.open_file_viewer(file_path, filename, title)
                
        ttk.Button(button_frame, text="Open Selected", command=open_selected_file).pack(side=tk.LEFT)
        ttk.Button(button_frame, text="Close", command=browser_window.destroy).pack(side=tk.RIGHT)
        
    def open_file_viewer(self, file_path, filename, folder_type):
        """Open appropriate viewer for file type"""
        viewer_window = tk.Toplevel(self.root)
        viewer_window.title(f"View: {filename}")
        viewer_window.geometry("800x600")
        
        main_frame = ttk.Frame(viewer_window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        try:
            if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                # Image viewer
                self.show_image_viewer(main_frame, file_path)
            elif filename.lower().endswith('.json'):
                # JSON viewer
                self.show_json_viewer(main_frame, file_path)
            elif filename.lower().endswith('.csv'):
                # CSV viewer
                self.show_csv_viewer(main_frame, file_path)
            elif filename.lower().endswith('.npy'):
                # NumPy array viewer
                self.show_numpy_viewer(main_frame, file_path)
            elif filename.lower().endswith('.mp4'):
                # Video info (can't play video in tkinter easily)
                self.show_video_info(main_frame, file_path)
            else:
                # Text viewer for other files
                self.show_text_viewer(main_frame, file_path)
                
        except Exception as e:
            ttk.Label(main_frame, text=f"Error loading file: {str(e)}").pack()
            
        # Close button
        ttk.Button(main_frame, text="Close", command=viewer_window.destroy).pack(pady=(10, 0))
        
    def show_image_viewer(self, parent, file_path):
        """Show image in viewer"""
        try:
            img = Image.open(file_path)
            # Resize if too large
            img.thumbnail((600, 400), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            
            img_label = ttk.Label(parent, image=photo)
            img_label.image = photo  # Keep reference
            img_label.pack()
            
            # Image info
            info_text = f"Size: {img.size}\nMode: {img.mode}"
            ttk.Label(parent, text=info_text).pack(pady=(10, 0))
            
        except Exception as e:
            ttk.Label(parent, text=f"Error loading image: {str(e)}").pack()
            
    def show_json_viewer(self, parent, file_path):
        """Show JSON content"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            text_widget = scrolledtext.ScrolledText(parent, height=20, width=80)
            text_widget.pack(fill=tk.BOTH, expand=True)
            text_widget.insert('1.0', json.dumps(data, indent=2, ensure_ascii=False))
            text_widget.config(state='disabled')
            
        except Exception as e:
            ttk.Label(parent, text=f"Error loading JSON: {str(e)}").pack()
            
    def show_csv_viewer(self, parent, file_path):
        """Show CSV content in a table"""
        try:
            # Create treeview for CSV data
            tree_frame = ttk.Frame(parent)
            tree_frame.pack(fill=tk.BOTH, expand=True)
            
            tree = ttk.Treeview(tree_frame)
            tree_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
            tree.configure(yscrollcommand=tree_scroll.set)
            
            tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Read CSV
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                rows = list(reader)
                
            if rows:
                # Setup columns
                headers = rows[0]
                tree["columns"] = headers
                tree["show"] = "headings"
                
                for header in headers:
                    tree.heading(header, text=header)
                    tree.column(header, width=100)
                    
                # Add data
                for row in rows[1:]:
                    tree.insert("", "end", values=row)
                    
        except Exception as e:
            ttk.Label(parent, text=f"Error loading CSV: {str(e)}").pack()
            
    def show_numpy_viewer(self, parent, file_path):
        """Show NumPy array info"""
        try:
            data = np.load(file_path)
            
            info_text = f"Shape: {data.shape}\n"
            info_text += f"Data type: {data.dtype}\n"
            info_text += f"Size: {data.size}\n"
            info_text += f"Min: {data.min()}\n"
            info_text += f"Max: {data.max()}\n"
            info_text += f"Mean: {data.mean():.4f}\n"
            
            ttk.Label(parent, text=info_text, font=("Courier", 10)).pack(anchor=tk.W)
            
            # Show first few values if 1D or 2D
            if len(data.shape) <= 2:
                text_widget = scrolledtext.ScrolledText(parent, height=15, width=80)
                text_widget.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
                text_widget.insert('1.0', str(data))
                text_widget.config(state='disabled')
                
        except Exception as e:
            ttk.Label(parent, text=f"Error loading NumPy file: {str(e)}").pack()
            
    def show_video_info(self, parent, file_path):
        """Show video file information"""
        try:
            file_size = os.path.getsize(file_path)
            file_size_mb = file_size / (1024 * 1024)
            
            info_text = f"File: {os.path.basename(file_path)}\n"
            info_text += f"Size: {file_size_mb:.2f} MB\n"
            info_text += f"Path: {file_path}\n\n"
            info_text += "Note: Video playback not supported in this viewer.\n"
            info_text += "Use external video player to view content."
            
            ttk.Label(parent, text=info_text, font=("Courier", 10)).pack(anchor=tk.W)
            
        except Exception as e:
            ttk.Label(parent, text=f"Error getting video info: {str(e)}").pack()
            
    def show_text_viewer(self, parent, file_path):
        """Show text file content"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            text_widget = scrolledtext.ScrolledText(parent, height=20, width=80)
            text_widget.pack(fill=tk.BOTH, expand=True)
            text_widget.insert('1.0', content)
            text_widget.config(state='disabled')
            
        except Exception as e:
            ttk.Label(parent, text=f"Error loading text file: {str(e)}").pack()

    def setup_ui(self):
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # Input section
        self.setup_input_section(main_frame)
        
        # Task selection section
        self.setup_task_section(main_frame)
        
        # Results section
        self.setup_results_section(main_frame)
        
        # Control buttons
        self.setup_control_buttons(main_frame)
        
    def setup_input_section(self, parent):
        input_frame = ttk.LabelFrame(parent, text="Input", padding="10")
        input_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        input_frame.columnconfigure(1, weight=1)
        
        # Text input
        ttk.Label(input_frame, text="Text Query:").grid(row=0, column=0, sticky=(tk.W, tk.N), padx=(0, 10))
        
        text_frame = ttk.Frame(input_frame)
        text_frame.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        text_frame.columnconfigure(0, weight=1)
        
        self.text_entry = scrolledtext.ScrolledText(text_frame, height=3, width=50)
        self.text_entry.grid(row=0, column=0, sticky=(tk.W, tk.E))
        self.text_entry.bind('<Return>', lambda event: self.process_search())
        
        remove_punct_button = ttk.Button(text_frame, text="REMOVE PUNCTUATIONS", 
                                        command=self.remove_punctuations)
        remove_punct_button.grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        
        # Image upload
        ttk.Label(input_frame, text="Upload Image:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        self.image_upload_label = ttk.Label(input_frame, text="No image selected", foreground="gray")
        self.image_upload_label.grid(row=1, column=1, sticky=tk.W, pady=(10, 0), padx=(0, 10))
        ttk.Button(input_frame, text="Browse Image", 
                  command=self.upload_image).grid(row=1, column=2, pady=(10, 0))
        
        # TXT file upload
        ttk.Label(input_frame, text="Upload TXT File:").grid(row=2, column=0, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        self.txt_upload_label = ttk.Label(input_frame, text="No TXT file selected", foreground="gray")
        self.txt_upload_label.grid(row=2, column=1, sticky=tk.W, pady=(10, 0), padx=(0, 10))
        ttk.Button(input_frame, text="Browse TXT", 
                  command=self.upload_txt_file).grid(row=2, column=2, pady=(10, 0))
        
        # Search and Clear buttons
        button_frame = ttk.Frame(input_frame)
        button_frame.grid(row=3, column=0, columnspan=3, pady=(20, 0))
        
        search_button = ttk.Button(button_frame, text="SEARCH", command=self.process_search,
                                  style='Accent.TButton')
        search_button.pack(side=tk.LEFT, padx=(0, 10))
        
        clear_button = ttk.Button(button_frame, text="CLEAR INPUTS", command=self.clear_all_inputs)
        clear_button.pack(side=tk.LEFT)

    def setup_task_section(self, parent):
        task_frame = ttk.LabelFrame(parent, text="Task Selection", padding="10")
        task_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Task radio buttons
        ttk.Radiobutton(task_frame, text="Task 1 - KIS", variable=self.current_task, 
                       value="KIS").grid(row=0, column=0, sticky=tk.W, padx=(0, 20))
        ttk.Radiobutton(task_frame, text="Task 2 - QnA", variable=self.current_task, 
                       value="QnA").grid(row=0, column=1, sticky=tk.W, padx=(0, 20))
        ttk.Radiobutton(task_frame, text="Task 3 - TRAKE", variable=self.current_task, 
                       value="TRAKE").grid(row=0, column=2, sticky=tk.W)
        
        # Answer input for QnA task
        self.answer_label = ttk.Label(task_frame, text="Answer (for QnA):")
        self.answer_label.grid(row=1, column=0, sticky=tk.W, pady=(10, 0))
        self.answer_entry = ttk.Entry(task_frame, width=50)
        self.answer_entry.grid(row=1, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        
    def setup_results_section(self, parent):
        results_frame = ttk.LabelFrame(parent, text="Retrieved Frames", padding="10")
        results_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)
        
        # Create canvas with scrollbar for frame grid
        self.canvas = tk.Canvas(results_frame, bg="white")
        scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Bind mousewheel to canvas
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        
    def setup_control_buttons(self, parent):
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=3, column=0, columnspan=2, pady=(0, 10))
        
        ttk.Button(button_frame, text="Clear Selection", 
                  command=self.clear_selection).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Select All", 
                  command=self.select_all).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Generate CSV", 
                  command=self.generate_csv).pack(side=tk.LEFT, padx=(0, 10))
        
        # Status label
        self.status_label = ttk.Label(parent, text="Ready")
        self.status_label.grid(row=4, column=0, columnspan=2, sticky=tk.W)
        
    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
    def upload_txt_file(self):
        file_path = filedialog.askopenfilename(
            title="Select TXT File",
            filetypes=[("Text files", "*.txt")]
        )
        
        if file_path:
            try:
                # Read TXT file content
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                
                # Extract filename without extension for output naming
                filename = os.path.basename(file_path)
                self.uploaded_txt_file = {
                    'path': file_path,
                    'name': filename,
                    'base_name': os.path.splitext(filename)[0],  # For output CSV naming
                    'content': content
                }
                
                # Update label to show selected file
                self.txt_upload_label.config(text=filename, foreground="black")
                
                self.text_entry.config(state='normal')
                self.text_entry.delete('1.0', tk.END)
                self.text_entry.insert('1.0', content)
                # Keep text entry editable so user can modify the content
                
                # Auto-detect task type from filename
                filename_lower = filename.lower()
                if 'kis' in filename_lower:
                    self.current_task.set("KIS")
                elif 'qa' in filename_lower or 'qna' in filename_lower:
                    self.current_task.set("QnA")
                elif 'trake' in filename_lower:
                    self.current_task.set("TRAKE")
                    
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load TXT file: {str(e)}")

    def remove_punctuations(self):
        """Remove all punctuations from the text in User Query box"""
        current_text = self.text_entry.get('1.0', tk.END).strip()
        
        if not current_text:
            messagebox.showinfo("Info", "No text to process")
            return
        
        # Remove all punctuations using string.punctuation
        cleaned_text = ''.join(char for char in current_text if char not in string.punctuation)
        
        # Clean up extra spaces
        cleaned_text = ' '.join(cleaned_text.split())
        
        # Update the text entry with cleaned text
        self.text_entry.config(state='normal')
        self.text_entry.delete('1.0', tk.END)
        self.text_entry.insert('1.0', cleaned_text)
                
    def process_search(self):
        """Main search processing function"""
        text_query = self.text_entry.get('1.0', tk.END).strip()
        has_text = bool(text_query)
        has_image = self.uploaded_image_path is not None
        has_txt = self.uploaded_txt_file is not None
        
        if not has_text and not has_image and not has_txt:
            messagebox.showwarning("Warning", "Please provide at least one input: text, image, or TXT file")
            return
            
        self.status_label.config(text="Processing...")
        self.root.update()
        
        # Prepare query data
        query_data = {}
        if has_text:
            query_data["text"] = text_query
        if has_image:
            query_data["image_path"] = self.uploaded_image_path
        if has_txt:
            query_data["txt_file"] = self.uploaded_txt_file
            
        # Run search in background thread
        threading.Thread(target=self._run_search, args=(query_data,), daemon=True).start()
        
    def search_with_text(self):
        """Legacy method - redirects to process_search"""
        self.process_search()
        
    def upload_image(self):
        file_path = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp *.gif")]
        )
        
        if file_path:
            self.uploaded_image_path = file_path
            filename = os.path.basename(file_path)
            self.image_upload_label.config(text=filename, foreground="black")
            
    def _run_search(self, query_data):
        try:
            # Handle different input types
            if "txt_file" in query_data:
                result = self.call_backend_txt_file(query_data["txt_file"])
            elif "text" in query_data and "image_path" in query_data:
                result = self.call_backend_multimodal(query_data["text"], query_data["image_path"])
            elif "text" in query_data:
                result = self.call_backend_text(query_data["text"])
            elif "image_path" in query_data:
                result = self.call_backend_image(query_data["image_path"])
            else:
                raise ValueError("No valid input provided")
                
            # Update UI in main thread
            self.root.after(0, self._update_results, result)
            
        except Exception as e:
            self.root.after(0, lambda: self.status_label.config(text=f"Error: {str(e)}"))
            

    """
    Call your backend API with text query.
    Replace this with actual API call to your backend.
    """    
    def call_backend_text(self, text_query: str) -> List[Dict]:
        """
        Call your backend API with text query or use database files.
        """
        if not self.use_mock_data:
            return self.search_database_text(text_query)
        
        # Mock response for demonstration
        mock_results = []
        for i in range(20):  # Simulate 20 results for demo
            mock_results.append({
                "frame_id": f"img_{i:03d}",
                "video_name": f"video_{(i//5)+1}",
                "frame_id": f"frame_{i:04d}",
                "image_url": f"https://picsum.photos/200/150?random={i}",
                "metadata": {
                    "video_name": f"sample_video_{(i//5)+1}.mp4",
                    "frame_number": i * 10,
                    "timestamp": f"00:0{i//10}:{(i*6)%60:02d}"
                }
            })
        return mock_results
        
    """
    Call your backend API with TXT file content.
    Replace this with actual API call to your backend.
    """
    def call_backend_txt_file(self, txt_file_info: Dict) -> List[Dict]:
        """
        Call your backend API with TXT file content or use database files.
        """
        try:
            with open(txt_file_info['path'], 'r', encoding='utf-8') as f:
                content = f.read().strip()
                
            if not self.use_mock_data:
                return self.search_database_text(content)
            
            # Mock response for demonstration
            return self.call_backend_text(content)
            
        except Exception as e:
            raise Exception(f"Failed to process TXT file: {str(e)}")

    """
    Call your backend API with both text and image.
    Replace this with actual API call to your backend.
    """     
    def call_backend_multimodal(self, text_query: str, image_path: str) -> List[Dict]:
        """
        Call your backend API with both text and image or use database files.
        """
        if not self.use_mock_data:
            return self.search_database_multimodal(text_query, image_path)
        
        # Mock response for demonstration
        return self.call_backend_text(f"multimodal: {text_query}")
    
    """
    Call your backend API with image upload.
    Replace this with actual API call to your backend.
    """
    def call_backend_image(self, image_path: str) -> List[Dict]:
        """
        Call your backend API with image upload or use database files.
        """
        if not self.use_mock_data:
            return self.search_database_image(image_path)
        
        # Mock response for demonstration
        return self.call_backend_text("uploaded image")
        
    def search_database_text(self, text_query: str) -> List[Dict]:
        """Search database files based on text query"""
        results = []
        
        try:
            # Load media info to get video metadata
            media_info_path = os.path.join(self.database_path, "media-info")
            map_keyframes_path = os.path.join(self.database_path, "map-keyframes")
            keyframes_path = os.path.join(self.database_path, "keyframes")
            
            if not os.path.exists(media_info_path):
                raise Exception("Media info folder not found in database")
                
            # Get all media info files
            media_files = [f for f in os.listdir(media_info_path) if f.endswith('.json')]
            
            for media_file in media_files:
                media_file_path = os.path.join(media_info_path, media_file)
                
                try:
                    with open(media_file_path, 'r', encoding='utf-8') as f:
                        media_data = json.load(f)
                    
                    video_name = os.path.splitext(media_file)[0]
                    
                    # Simple text matching (you can implement more sophisticated search)
                    if text_query.lower() in str(media_data).lower():
                        # Find corresponding keyframes
                        keyframe_folder = os.path.join(keyframes_path, video_name)
                        if os.path.exists(keyframe_folder):
                            keyframe_files = [f for f in os.listdir(keyframe_folder) if f.endswith('.jpg')]
                            
                            for i, keyframe_file in enumerate(keyframe_files[:10]):  # Limit to 10 per video
                                frame_id = os.path.splitext(keyframe_file)[0]
                                keyframe_path = os.path.join(keyframe_folder, keyframe_file)
                                
                                results.append({
                                    "frame_id": frame_id,
                                    "video_name": video_name,
                                    "keyframe_path": keyframe_path,
                                    "metadata": {
                                        "video_name": f"{video_name}.mp4",
                                        "frame_number": i,
                                        "media_info": media_data
                                    }
                                })
                                
                except Exception as e:
                    print(f"Error processing {media_file}: {str(e)}")
                    continue
                    
        except Exception as e:
            raise Exception(f"Database search failed: {str(e)}")
            
        return results
        
    def search_database_image(self, image_path: str) -> List[Dict]:
        """Search database using image similarity (placeholder implementation)"""
        # This is a placeholder - you would implement actual image similarity search
        # For now, return some keyframes from the database
        return self.search_database_text("image_search")
        
    def search_database_multimodal(self, text_query: str, image_path: str) -> List[Dict]:
        """Search database using both text and image (placeholder implementation)"""
        # This is a placeholder - you would implement actual multimodal search
        # For now, combine text search results
        return self.search_database_text(text_query)

    def _update_results(self, results):
        self.retrieved_images = results
        self.selected_images = []
        self.display_images()
        self.status_label.config(text=f"Retrieved {len(results)} frames")
        
    def display_images(self):
        # Clear existing widgets
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.image_widgets = []
        
        if not self.retrieved_images:
            ttk.Label(self.scrollable_frame, text="No frames to display").pack()
            return
            
        # Create grid of images
        cols = 5
        for i, frame_data in enumerate(self.retrieved_images):
            row = i // cols
            col = i % cols
            
            frame = ttk.Frame(self.scrollable_frame, relief="solid", borderwidth=1)
            frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            
            # Load and display image
            try:
                self.load_image_widget(frame, frame_data, i)
            except Exception as e:
                ttk.Label(frame, text=f"Error loading frame\n{frame_data['frame_id']}").pack()
                
        # Configure grid weights
        for i in range(cols):
            self.scrollable_frame.columnconfigure(i, weight=1)
            
    def load_image_widget(self, parent_frame, frame_data, index):
        # Create image widget
        img_frame = ttk.Frame(parent_frame)
        img_frame.pack(fill=tk.BOTH, expand=True)
        
        # Checkbox for selection
        var = tk.BooleanVar()
        checkbox = ttk.Checkbutton(img_frame, variable=var, 
                                  command=lambda: self.toggle_selection(frame_data['frame_id'], var.get()))
        checkbox.pack()
        
        # Image display
        try:
            if not self.use_mock_data and 'keyframe_path' in frame_data:
                if os.path.exists(frame_data['keyframe_path']):
                    img = Image.open(frame_data['keyframe_path'])
                    img = img.resize((150, 100), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                    
                    img_label = ttk.Label(img_frame, image=photo)
                    img_label.image = photo  # Keep reference
                    img_label.pack()
                else:
                    # Fallback to placeholder
                    placeholder_img = Image.new('RGB', (150, 100), color=(200, 200, 200))
                    photo = ImageTk.PhotoImage(placeholder_img)
                    
                    img_label = ttk.Label(img_frame, image=photo)
                    img_label.image = photo
                    img_label.pack()
            else:
                # For demo purposes, create a placeholder image
                placeholder_img = Image.new('RGB', (150, 100), color=(200, 200, 200))
                photo = ImageTk.PhotoImage(placeholder_img)
                
                img_label = ttk.Label(img_frame, image=photo)
                img_label.image = photo  # Keep reference
                img_label.pack()
            
        except Exception as e:
            ttk.Label(img_frame, text="Frame\nError").pack()
            
        # Image info
        info_text = f"ID: {frame_data['frame_id']}\n"
        info_text += f"Video: {frame_data.get('video_name', 'N/A')}\n"
        info_text += f"Frame: {frame_data.get('frame_id', 'N/A')}"
        
        info_label = ttk.Label(img_frame, text=info_text, font=("Arial", 8))
        info_label.pack()
        
        self.image_widgets.append({
            'frame': parent_frame,
            'checkbox': checkbox,
            'var': var,
            'data': frame_data
        })
        
    def toggle_selection(self, frame_id, is_selected):
        if is_selected and frame_id not in self.selected_images:
            self.selected_images.append(frame_id)
        elif not is_selected and frame_id in self.selected_images:
            self.selected_images.remove(frame_id)
            
        self.update_selection_count()
        
    def update_selection_count(self):
        count = len(self.selected_images)
        self.status_label.config(text=f"Selected {count} frames")
        
    def clear_selection(self):
        self.selected_images = []
        for widget_data in self.image_widgets:
            widget_data['var'].set(False)
        self.update_selection_count()
        
    def clear_all_inputs(self):
        """Clear all input fields and uploaded files"""
        self.text_entry.config(state='normal')
        self.text_entry.delete('1.0', tk.END)
        self.answer_entry.delete(0, tk.END)
        self.uploaded_txt_file = None
        self.uploaded_image_path = None
        self.txt_upload_label.config(text="No TXT file selected", foreground="gray")
        self.image_upload_label.config(text="No image selected", foreground="gray")
        
        # Clear results
        self.retrieved_images = []
        self.selected_images = []
        self.display_images()
        self.status_label.config(text="Ready")
        
    def select_all(self):
        self.selected_images = [img['frame_id'] for img in self.retrieved_images]
        for widget_data in self.image_widgets:
            widget_data['var'].set(True)
        self.update_selection_count()
        
    def generate_csv(self):
        if not self.selected_images:
            messagebox.showwarning("Warning", "No frames selected")
            return
            
        task = self.current_task.get()
        
        # Validate task-specific requirements
        if task == "QnA" and not self.answer_entry.get().strip():
            messagebox.showwarning("Warning", "Answer is required for QnA task")
            return
            
        try:
            output_path = self.create_csv_file(task)
            messagebox.showinfo("Success", f"CSV file generated successfully:\n{output_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate CSV: {str(e)}")
            
    def create_csv_file(self, task):
        # Get directory of current script
        base_dir = os.path.dirname(os.path.abspath(__file__))
        output_base = os.path.join(base_dir, "output_csv")

        # Create output directory with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(output_base, f"{timestamp}-{task.lower()}")
        os.makedirs(output_dir, exist_ok=True)
        
        # Determine filename based on TXT file or timestamp
        if self.uploaded_txt_file:
            filename = f"{self.uploaded_txt_file['base_name']}.csv"
        else:
            filename = f"{timestamp}-{task.lower()}.csv"
            
        filepath = os.path.join(output_dir, filename)
        
        # Get selected image data
        selected_data = [img for img in self.retrieved_images if img['frame_id'] in self.selected_images]
        
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            if task == "KIS":
                # Format: <Video name>, <Frame ID>
                for img in selected_data:
                    video_name = img.get('metadata', {}).get('video_name', img.get('video_name', 'unknown'))
                    frame_id = img.get('frame_id', img.get('frame_id'))
                    writer.writerow([video_name, frame_id])
                    
            elif task == "QnA":
                # Format: <Video name>, <Frame ID>, <Answer>
                answer = self.answer_entry.get().strip()
                for img in selected_data:
                    video_name = img.get('metadata', {}).get('video_name', img.get('video_name', 'unknown'))
                    frame_id = img.get('frame_id', img.get('frame_id'))
                    writer.writerow([video_name, frame_id, answer])
                    
            elif task == "TRAKE":
                # Format: <Video name>, <Frame ID_1>, <Frame ID_2>, ..., <Frame ID_N>
                if selected_data:
                    # Group by video name for TRAKE format
                    videos = {}
                    for img in selected_data:
                        video_name = img.get('metadata', {}).get('video_name', img.get('video_name', 'unknown'))
                        frame_id = img.get('frame_id', img.get('frame_id'))
                        if video_name not in videos:
                            videos[video_name] = []
                        videos[video_name].append(frame_id)
                    
                    # Write header
                    max_frames = max(len(frames) for frames in videos.values())
                    
                    # Write data
                    for video_name, frame_ids in videos.items():
                        row = [video_name] + frame_ids + [''] * (max_frames - len(frame_ids))
                        writer.writerow(row)
        
        return filepath

class MockBackendDialog:
    """Dialog for configuring mock backend settings"""
    def __init__(self, parent):
        self.result = None
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Backend Configuration")
        self.dialog.geometry("400x350")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
        self.setup_dialog()
        
    def setup_dialog(self):
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="Backend Configuration", 
                 font=("Arial", 12, "bold")).pack(pady=(0, 20))
        
        # Backend URL
        url_frame = ttk.Frame(main_frame)
        url_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(url_frame, text="Backend URL:").pack(anchor=tk.W)
        self.url_entry = ttk.Entry(url_frame, width=50)
        self.url_entry.insert(0, "http://localhost:8000")
        self.url_entry.pack(fill=tk.X)
        
        db_frame = ttk.Frame(main_frame)
        db_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(db_frame, text="Database Path:").pack(anchor=tk.W)
        self.db_path_entry = ttk.Entry(db_frame, width=50)

        # Get directory of current script
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_path_entry.insert(0, os.path.join(base_dir, "database"))
        self.db_path_entry.pack(fill=tk.X, pady=(0, 5))
        ttk.Button(db_frame, text="Browse Database Folder", 
                  command=self.browse_database).pack()
        
        # Mock mode
        self.mock_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(main_frame, text="Use mock data (for testing)", 
                       variable=self.mock_var).pack(pady=(0, 20))
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack()
        ttk.Button(button_frame, text="OK", command=self.ok_clicked).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Cancel", command=self.cancel_clicked).pack(side=tk.LEFT)
        
    def browse_database(self):
        """Browse for database folder"""
        path = filedialog.askdirectory(title="Select Database Folder", 
                                     initialdir=self.db_path_entry.get())
        if path:
            self.db_path_entry.delete(0, tk.END)
            self.db_path_entry.insert(0, path)
        
    def ok_clicked(self):
        self.result = {
            "url": self.url_entry.get(),
            "database_path": self.db_path_entry.get(),
            "mock_mode": self.mock_var.get()
        }
        self.dialog.destroy()
        
    def cancel_clicked(self):
        self.result = None
        self.dialog.destroy()

def main():
    root = tk.Tk()
    
    # Show backend configuration dialog
    config_dialog = MockBackendDialog(root)
    root.wait_window(config_dialog.dialog)
    
    if config_dialog.result is None:
        root.destroy()
        return
        
    # Create main application
    app = VideoRetrievalUI(root)
    
    # Apply configuration
    if config_dialog.result:
        app.backend_url = config_dialog.result["url"]
        app.database_path = config_dialog.result["database_path"]
        app.use_mock_data = config_dialog.result["mock_mode"]
        
    root.mainloop()

if __name__ == "__main__":
    main()
