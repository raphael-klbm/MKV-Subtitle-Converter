import os
import tkinter as tk
from tkinter import ttk
from config import Config

class LicensesWindow(tk.Toplevel):
    
    def __init__(self, parent):
        super().__init__()
        self.config = Config()
        self.translate = self.config.translate

        self.title(self.translate("Licenses"))
        self.geometry("500x500")
        self.resizable(True, True)

        self.wait_visibility()
        x = parent.window.winfo_x() + parent.window.winfo_width()//2 - self.winfo_width()//2
        y = parent.window.winfo_y() + parent.window.winfo_height()//2 - self.winfo_height()//2
        self.geometry(f"+{x}+{y}")

        # ---------------- SIDEBAR -----------------------
        self.sidebar = tk.Frame(self)
        self.sidebar.place(relx=0, rely=0, relwidth=0.3, relheight=1)

        theme_license = SidebarOption(self.sidebar, "Forest-ttk-theme", lambda: self.show_frame(ThemeLicense))
        theme_license.grid(row=0, column=0, padx=5, pady=(5, 0), sticky="w")

        # --------------------  MULTI PAGE LICENSES ----------------------------

        licenses_frames_container = tk.Frame(self)
        licenses_frames_container.config(highlightbackground="#808080", highlightthickness=0.5)
        licenses_frames_container.place(relx=0.3, rely=0, relwidth=0.7, relheight=0.9)

        self.frames = {}

        for F in {ThemeLicense}:
            frame = F(licenses_frames_container)
            self.frames[F] = frame
            frame.place(relx=0, rely=0, relwidth=1, relheight=1)


    def show_frame(self, cont):
        '''
        Show a frame for the given class in the licenses window.
        If not called, the first frame is shown.
        '''

        frame = self.frames[cont]
        frame.tkraise()

# ------------------------ MULTIPAGE FRAMES ------------------------------------

class LicenseFrame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.config = Config()
        self.translate = self.config.translate


class ThemeLicense(LicenseFrame):
    def __init__(self, parent):
        super().__init__(parent)

        # variables
        license_path = self.config.get_resource_path(os.path.join("licenses", "Forest-ttk-theme.txt"))
        with open(license_path, "r", encoding="utf-8") as f:
            license = f.read()

        # gui
        license_text = tk.Text(self, wrap="word", font=("Arial", 10), bd=0)
        license_text.insert("0.0", license)
        license_text.config(state="disabled")
        license_text.pack(fill="both", expand=True)

        # scrollbar
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=license_text.yview)
        scrollbar.pack(side="right", fill="y")
        license_text.config(yscrollcommand=scrollbar.set)

        license_text.place(relx=0, rely=0, relwidth=1, relheight=1)

# ----------------------------- CUSTOM WIDGETS ---------------------------------

class SidebarSubMenu(tk.Frame):
    """
    A submenu which can have multiple options and these can be linked with
    functions.
    """
    def __init__(self, parent, sub_menu_heading, sub_menu_options):
        """
        parent: The frame where submenu is to be placed
        sub_menu_heading: Heading for the options provided
        sub_menu_operations: Options to be included in sub_menu
        """
        tk.Frame.__init__(self, parent)
        self.sub_menu_heading_label = tk.Label(self,
                                               text=sub_menu_heading,
                                               font=("Arial", 10, "bold"),
                                               )
        self.sub_menu_heading_label.place(x=30, y=10, anchor="w")

        sub_menu_sep = ttk.Separator(self, orient='horizontal')
        sub_menu_sep.place(x=30, y=30, relwidth=0.8, anchor="w")

        self.options = {}
        for n, x in enumerate(sub_menu_options):
            self.options[x] = ttk.Button(self,
                                        text=x,
                                        font=("Arial", 9, "normal"),
                                        bd=0,
                                        cursor='hand2',
                                        activebackground='#ffffff',
                                        )
            self.options[x].place(x=30, y=45 * (n + 1), anchor="w")


class SidebarOption(tk.Frame):
    """
    A single option in the sidebar
    """
    def __init__(self, parent, option_text, command):
        """
        parent: The frame where option is to be placed
        option_text: Text to be displayed in the option
        """
        tk.Frame.__init__(self, parent)
        self.option_label = tk.Button(self,
                                      text=option_text,
                                      font=("Arial", 9, "normal"),
                                      bd=0,
                                      cursor='hand2',
                                      activebackground='#ffffff',
                                      command=command,
                                     )
        self.option_label.pack()
    