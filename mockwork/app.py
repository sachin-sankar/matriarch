import os

import customtkinter as ctk

ctk.set_widget_scaling(1.2)


class FileManagerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Cloud Native File Manager")
        self.geometry("900x550")

        # Main Layout: 2 Columns (Sidebar + Content)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main_content()

    def _build_sidebar(self):
        """Constructs the navigation sidebar."""
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(6, weight=1)

        # App Brand Title
        self.logo_label = ctk.CTkLabel(
            self.sidebar, text="File Flow", font=ctk.CTkFont(size=20, weight="bold")
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        # Navigation Buttons
        self.btn_my_files = ctk.CTkButton(self.sidebar, text="My Files", anchor="w")
        self.btn_my_files.grid(row=1, column=0, padx=20, pady=5, sticky="ew")

        self.btn_shared = ctk.CTkButton(
            self.sidebar,
            text="Shared",
            anchor="w",
            fg_color="transparent",
            text_color=("gray10", "gray90"),
        )
        self.btn_shared.grid(row=2, column=0, padx=20, pady=5, sticky="ew")

        self.btn_trash = ctk.CTkButton(
            self.sidebar,
            text="Trash",
            anchor="w",
            fg_color="transparent",
            text_color=("gray10", "gray90"),
        )
        self.btn_trash.grid(row=3, column=0, padx=20, pady=5, sticky="ew")

        # Sidebar Controls
        self.show_hidden_chk = ctk.CTkCheckBox(self.sidebar, text="Show Hidden")
        self.show_hidden_chk.grid(row=4, column=0, padx=20, pady=(20, 10), sticky="w")

        self.read_only_chk = ctk.CTkSwitch(self.sidebar, text="Read-Only Mode")
        self.read_only_chk.grid(row=5, column=0, padx=20, pady=10, sticky="w")

        # System Theme Selector
        self.theme_option = ctk.CTkOptionMenu(
            self.sidebar, values=["Dark", "Light", "System"], command=self._change_theme
        )
        self.theme_option.grid(row=7, column=0, padx=20, pady=(10, 20), sticky="ew")

    def _build_main_content(self):
        """Constructs the main directory browser area."""
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(2, weight=1)

        # Search Bar & Path Header
        self.top_bar = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.top_bar.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        self.top_bar.grid_columnconfigure(0, weight=1)

        self.path_entry = ctk.CTkEntry(
            self.top_bar, placeholder_text="/home/user/documents"
        )
        self.path_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.path_entry.insert(0, os.path.expanduser("~"))

        self.btn_search = ctk.CTkButton(self.top_bar, text="Go", width=60)
        self.btn_search.grid(row=0, column=1)

        # Filter Section
        self.filter_bar = ctk.CTkFrame(self.main_frame, height=40)
        self.filter_bar.grid(row=1, column=0, sticky="ew", pady=(0, 15))

        self.type_filter = ctk.CTkOptionMenu(
            self.filter_bar, values=["All Files", "Images", "Documents", "Archives"]
        )
        self.type_filter.pack(side="left", padx=10, pady=5)

        self.slider_zoom = ctk.CTkSlider(
            self.filter_bar, from_=10, to=100, number_of_steps=9
        )
        self.slider_zoom.pack(side="right", padx=10, pady=5)

        # Workspace File Canvas / Textbox List
        self.file_list_box = ctk.CTkTextbox(self.main_frame)
        self.file_list_box.grid(row=2, column=0, sticky="nsew")
        self.file_list_box.insert(
            "1.0",
            "📁 Documents/\n📁 Downloads/\n📁 Pictures/\n📄 project_manifest.json\n📄 notes.txt",
        )

    def _change_theme(self, new_theme: str):
        ctk.set_appearance_mode(new_theme)
