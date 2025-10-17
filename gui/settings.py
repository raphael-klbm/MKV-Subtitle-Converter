import tkinter as tk
from tkinter import ttk
from config import Config

class SettingsWindow(tk.Toplevel):
    
    def __init__(self, parent):
        super().__init__()
        self.config = Config()
        self.translate = self.config.translate
        self.parent = parent

        self.title(self.translate("Settings"))
        self.geometry("500x500")
        self.resizable(True, True)

        self.wait_visibility()
        x = parent.window.winfo_x() + parent.window.winfo_width()//2 - self.winfo_width()//2
        y = parent.window.winfo_y() + parent.window.winfo_height()//2 - self.winfo_height()//2
        self.geometry(f"+{x}+{y}")

        # ---------------- SIDEBAR -----------------------
        self.sidebar = tk.Frame(self)
        self.sidebar.place(relx=0, rely=0, relwidth=0.3, relheight=1)

        general_settings = SidebarOption(self.sidebar, self.translate("General"), lambda: self.show_frame(GeneralSettings))
        graphics_settings = SidebarOption(self.sidebar, self.translate("Graphics"), lambda: self.show_frame(GraphicsSettings))
        general_settings.grid(row=0, column=0, padx=5, pady=(5, 0), sticky="w")
        graphics_settings.grid(row=1, column=0, padx=5, pady=(5, 0), sticky="w")

        # --------------------  MULTI PAGE SETTINGS ----------------------------

        settings_frames_container = tk.Frame(self)
        settings_frames_container.config(highlightbackground="#808080", highlightthickness=0.5)
        settings_frames_container.place(relx=0.3, rely=0, relwidth=0.7, relheight=0.9)

        self.frames = {}

        for F in {GeneralSettings, GraphicsSettings}:
            frame = F(settings_frames_container)
            self.frames[F] = frame
            frame.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.show_frame(GeneralSettings)

        # -----------------  FOOTER ----------------------------
        footer = tk.Frame(self)
        save_button = ttk.Button(footer, text=self.translate("Save"), command=self.save_settings)
        save_button.place(relx=0.3, rely=0.25, relwidth=0.2, relheight=0.5)
        exit_button = ttk.Button(footer, text=self.translate("Exit"), command=self.destroy)
        exit_button.place(relx=0.6, rely=0.25, relwidth=0.2, relheight=0.5)
        footer.place(relx=0.3, rely=0.9, relwidth=0.7, relheight=0.1)


    def show_frame(self, cont):
        '''
        Show a frame for the given class in the settings window.
        If not called, the first frame is shown.
        '''

        frame = self.frames[cont]
        frame.tkraise()

    def save_settings(self):
        
        for frame in self.frames.values():
            frame.save_settings()

        # save changes to config file
        config = Config()
        language_changed = config.get_language() != self.frames[GeneralSettings].language.get()
        theme_changed = config.get_value(Config.Settings.THEME) != self.frames[GraphicsSettings].theme.get()
        config.save_config()
        
        self.destroy()

        if language_changed or theme_changed:
            self.parent.reload()

# ------------------------ MULTIPAGE FRAMES ------------------------------------

class SettingsFrame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.config = Config()
        self.translate = self.config.translate

    # TODO: define as abstract method
    def save_settings(self):
        raise NotImplementedError('Method \"save_settings\" not implemented in subclass.')


class GeneralSettings(SettingsFrame):
    def __init__(self, parent):
        super().__init__(parent)

        # variables
        self.check_for_updates = tk.BooleanVar()
        self.language = tk.StringVar()

        self.check_for_updates.set(self.config.get_value(Config.Settings.CHECK_FOR_UPDATES))
        self.language.set(self.config.get_language())

        # gui
        language_label = ttk.Label(self, text=self.translate("Language:"))
        language_label.grid(row=0, column=0, padx=5, pady=(5, 0), sticky="w")

        language_list = ttk.Combobox(self, values=self.config.get_languages(), textvariable=self.language, state="readonly")
        language_list.grid(row=0, column=1, padx=5, pady=(5, 0), sticky="w")

        check_for_updates = ttk.Checkbutton(self, text=self.translate("Check for updates"), variable=self.check_for_updates)
        check_for_updates.grid(row=1, column=0, padx=5, pady=(5, 0), sticky="w", columnspan=2)

    def save_settings(self):
        settings = {
            Config.Settings.LANGUAGE: self.config.convert_language_to_code(self.language.get()),
            Config.Settings.CHECK_FOR_UPDATES: self.check_for_updates.get()
        }

        self.config.save_settings(settings)


class GraphicsSettings(SettingsFrame):
    def __init__(self, parent):
        super().__init__(parent)

        # variables
        self.theme = tk.StringVar()

        # Map from config value to translated value for display
        theme_value = self.config.get_value(Config.Settings.THEME)
        if theme_value == 'light':
            self.theme.set(self.translate("Light"))
        elif theme_value == 'dark':
            self.theme.set(self.translate("Dark"))
        else:
            self.theme.set(self.translate("Auto"))

        # gui
        theme_label = ttk.Label(self, text=self.translate("Theme:"))
        theme_label.grid(row=0, column=0, padx=5, pady=(5, 0), sticky="w")

        theme_list = ttk.Combobox(self, values=[self.translate("Light"), self.translate("Dark"), self.translate("Auto")], textvariable=self.theme, state="readonly")
        theme_list.grid(row=0, column=1, padx=5, pady=(5, 0), sticky="w")

    def save_settings(self):
        # Map from translated value back to config value for saving
        theme_value = self.theme.get()
        if theme_value == self.translate("Light"):
            theme_to_save = "light"
        elif theme_value == self.translate("Dark"):
            theme_to_save = "dark"
        else:
            theme_to_save = "auto"

        settings = {
            Config.Settings.THEME: theme_to_save
        }

        self.config.save_settings(settings)

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
    