#!/usr/bin/env python3
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GdkPixbuf
import json
import os
import sys
import locale
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

# === 🌍 Sistema de Traducción ===
# Método alternativo de importación
try:
    sys.path.insert(0, '/usr/local/bin')
    from pymenupuplang import TranslationManager
except ModuleNotFoundError:
    # Si falla, cargar directamente el archivo
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "pymenupuplang", 
        "/usr/local/bin/pymenupuplang.py"
    )
    if spec and spec.loader:
        pymenupuplang = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(pymenupuplang)
        TranslationManager = pymenupuplang.TranslationManager
    else:
        print("ERROR: No se pudo cargar pymenupuplang.py")
        sys.exit(1)

TR = TranslationManager()

CONFIG_FILE = "/root/.config/pymenu.json"

class ConfigManager:
    """Clase para cargar y guardar la configuración."""
    def __init__(self, config_file=CONFIG_FILE):
        self.config_file = config_file
        self.config = self.load_config()

    def get_default_config(self):
        """Devuelve una configuración predeterminada."""
        return {
            "window": {
                "width": 477,
                "height": 527,
                "decorated_window": False,
                "hide_header": False,
                "hide_profile_pic": False,
                "search_bar_position": "bottom",
                "hide_quick_access": True,
                "hide_social_networks": True,
                "halign": "center",
                "icon_size": 32,
                "profile_pic_size": 64,
                "profile_pic_shape": "square", 
                "hide_category_text": False,
                "category_icon_size": 16,
                "header_layout": "left",
                "header_text_align": "left",
                "hide_os_name": False,
                "hide_kernel": False,
                "hide_hostname": False
            },
            "font": {
                "family": "Sans",
                "family_categories": "Sans",
                "size_categories": 16000,
                "size_names": 14000,
                "size_header": 12000
            },
            "colors": {
                "use_gtk_theme": True,
                "background_opacity": 0.7,
                "background": "rgba(0, 0, 0, 0.7)",
                "border": "rgba(255, 255, 255, 0.1)",
                "text_normal": "#D8DEE9",
                "text_header_os": "#D8DEE9",
                "text_header_kernel": "#D0883A",
                "text_header_hostname": "#88C0D0",
                "hover_background": "rgba(255, 255, 255, 0.1)",
                "selected_background": "rgba(255, 255, 255, 0.2)",
                "selected_text": "#ECEFF4",
                "button_normal_background": "rgba(0,0,0,0.6)",
                "button_text": "#ECEFF4",
                "categories_background": "rgba(0,0,0,0.4)"
            },
            "paths": {
                "profile_pic": "",
                "profile_manager": "",
                "shutdown_cmd": "",
                "jwmrc_tray": "/root/.jwmrc-tray",          
                "tint2rc": "/root/.config/tint2/tint2rc"    
            },
            "search_engine": {
                "engine": "duckduckgo"
            },
            "tray": {
                "use_tint2": False
            },
            "categories": {
                "excluded": []
            }
        }

    def load_config(self):
        if not os.path.exists(self.config_file):
            print(TR['Config file not found. Creating default config.'])
            self.save_config(self.get_default_config())
            return self.get_default_config()
        
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                default_config = self.get_default_config()
                for key in default_config:
                    if key not in config:
                        config[key] = default_config[key]
                    elif isinstance(config[key], dict) and isinstance(default_config[key], dict):
                        for sub_key in default_config[key]:
                            if sub_key not in config[key]:
                                config[key][sub_key] = default_config[key][sub_key]
                return config
        except (IOError, json.JSONDecodeError) as e:
            print(f"{TR['Error loading config file:']} {e}. {TR['Using default config.']}")
            return self.get_default_config()

    def save_config(self, config_data):
        config_dir = os.path.dirname(self.config_file)
        if not os.path.exists(config_dir):
            os.makedirs(config_dir, exist_ok=True)
        with open(self.config_file, 'w') as f:
            json.dump(config_data, f, indent=4)

class ConfigWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title=TR['PyMenu Configurator'])
        self.set_default_size(500, 600)
        self.set_resizable(True)
        self.connect("destroy", Gtk.main_quit)
        
        self.config_manager = ConfigManager()
        self.config = self.config_manager.config
        
        main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        main_vbox.set_border_width(10)
        self.add(main_vbox)
        
        # [CORRECCIÓN] Se elimina el scrolled window que no se usaba aquí.
        
        notebook = Gtk.Notebook()
        main_vbox.pack_start(notebook, True, True, 0)
        
        # [CORRECCIÓN] Las funciones de creación de pestaña ahora devuelven un Gtk.ScrolledWindow
        notebook.append_page(self.create_window_tab(), Gtk.Label(label=TR['Window']))
        notebook.append_page(self.create_colors_tab(), Gtk.Label(label=TR['Colors']))
        notebook.append_page(self.create_font_tab(), Gtk.Label(label=TR['Font']))
        notebook.append_page(self.create_paths_tab(), Gtk.Label(label=TR['Paths']))
        notebook.append_page(self.create_categories_tab(), Gtk.Label(label=TR['Categories']))
        
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        button_box.set_halign(Gtk.Align.CENTER)
        
        save_button = Gtk.Button(label=TR['Save'])
        save_button.set_size_request(100, 30)
        save_button.connect("clicked", self.on_save_only_clicked)
        button_box.pack_start(save_button, False, False, 0)
        
        exit_button = Gtk.Button(label=TR['Exit'])
        exit_button.set_size_request(100, 30)
        exit_button.connect("clicked", self.on_exit_clicked)
        button_box.pack_start(exit_button, False, False, 0)
        
        main_vbox.pack_end(button_box, False, False, 0)
        
    def on_gtk_theme_toggled(self, check_button):
        """Manejar el toggle del checkbox de tema GTK"""
        self.config['colors']['use_gtk_theme'] = check_button.get_active()
        self.config_manager.save_config(self.config)
        self.update_color_widgets_sensitivity()
    
    def update_color_widgets_sensitivity(self):
        """Habilitar/deshabilitar widgets de color según el estado del tema GTK"""
        use_gtk_theme = self.config['colors'].get('use_gtk_theme', False)
        
        # Deshabilitar todos los widgets de color si se usa tema GTK
        if hasattr(self, 'color_widgets'):
            for widget in self.color_widgets:
                widget.set_sensitive(not use_gtk_theme)        

    def create_window_tab(self):
        grid = Gtk.Grid(row_spacing=10, column_spacing=10)
        grid.set_border_width(10)

        grid.attach(Gtk.Label(label=TR['Window width:']), 0, 0, 1, 1)
        width_spin = Gtk.SpinButton.new_with_range(100, 1500, 10)
        width_spin.set_value(self.config['window']['width'])
        width_spin.connect("value-changed", self.on_spin_button_changed, "window", "width")
        grid.attach(width_spin, 1, 0, 1, 1)

        grid.attach(Gtk.Label(label=TR['Window height:']), 0, 1, 1, 1)
        height_spin = Gtk.SpinButton.new_with_range(100, 1500, 10)
        height_spin.set_value(self.config['window']['height'])
        height_spin.connect("value-changed", self.on_spin_button_changed, "window", "height")
        grid.attach(height_spin, 1, 1, 1, 1)

        # Show window frame
        frame_label_text = TR['Show window frame:'] + '\n' + TR['(No transparency)']
        frame_label = Gtk.Label(label=frame_label_text)
        frame_label.set_halign(Gtk.Align.START)
        frame_label.set_line_wrap(True)
        grid.attach(frame_label, 0, 2, 1, 1)

        decorated_check = Gtk.CheckButton()
        decorated_check.set_active(self.config['window'].get('decorated_window', True))
        decorated_check.connect("toggled", self.on_check_toggled, "window", "decorated_window")
        grid.attach(decorated_check, 1, 2, 1, 1)

        # Hide header - NUEVA OPCIÓN AÑADIDA
        grid.attach(Gtk.Label(label=TR['Hide header:']), 0, 3, 1, 1)
        hide_header_check = Gtk.CheckButton()
        hide_header_check.set_active(self.config['window'].get('hide_header', False))
        hide_header_check.connect("toggled", self.on_check_toggled, "window", "hide_header")
        grid.attach(hide_header_check, 1, 3, 1, 1)
        
        grid.attach(Gtk.Label(label=TR['Hide profile picture:']), 0, 4, 1, 1)
        hide_profile_check = Gtk.CheckButton()
        hide_profile_check.set_active(self.config['window'].get('hide_profile_pic', False))
        hide_profile_check.connect("toggled", self.on_check_toggled, "window", "hide_profile_pic")
        grid.attach(hide_profile_check, 1, 4, 1, 1)
        
        # Header layout
        grid.attach(Gtk.Label(label=TR['Header layout:']), 0, 5, 1, 1)
        header_layout_combo = Gtk.ComboBoxText()
        header_layout_combo.append("left", TR['Avatar left'])
        header_layout_combo.append("center", TR['Avatar center']) 
        header_layout_combo.append("right", TR['Avatar right'])
        current_layout = self.config['window'].get('header_layout', 'left')
        header_layout_combo.set_active_id(current_layout)
        header_layout_combo.connect("changed", self.on_combobox_changed, 'window', 'header_layout')
        grid.attach(header_layout_combo, 1, 5, 1, 1)
        
        # Header text alignment
        grid.attach(Gtk.Label(label=TR['Header text alignment:']), 0, 6, 1, 1)
        header_text_align_combo = Gtk.ComboBoxText()
        header_text_align_combo.append("left", TR['left'])
        header_text_align_combo.append("center", TR['center'])
        header_text_align_combo.append("right", TR['right'])
        current_text_align = self.config['window'].get('header_text_align', 'left')
        header_text_align_combo.set_active_id(current_text_align)
        header_text_align_combo.connect("changed", self.on_combobox_changed, 'window', 'header_text_align')
        grid.attach(header_text_align_combo, 1, 6, 1, 1)
        
                # Hide OS name
        grid.attach(Gtk.Label(label=TR['Hide OS name:']), 0, 7, 1, 1)
        hide_os_check = Gtk.CheckButton()
        hide_os_check.set_active(self.config['window'].get('hide_os_name', False))
        hide_os_check.connect("toggled", self.on_check_toggled, "window", "hide_os_name")
        grid.attach(hide_os_check, 1, 7, 1, 1)
        
        # Hide kernel
        grid.attach(Gtk.Label(label=TR['Hide kernel:']), 0, 8, 1, 1)
        hide_kernel_check = Gtk.CheckButton()
        hide_kernel_check.set_active(self.config['window'].get('hide_kernel', False))
        hide_kernel_check.connect("toggled", self.on_check_toggled, "window", "hide_kernel")
        grid.attach(hide_kernel_check, 1, 8, 1, 1)
        
        # Hide hostname
        grid.attach(Gtk.Label(label=TR['Hide hostname:']), 0, 9, 1, 1)
        hide_hostname_check = Gtk.CheckButton()
        hide_hostname_check.set_active(self.config['window'].get('hide_hostname', False))
        hide_hostname_check.connect("toggled", self.on_check_toggled, "window", "hide_hostname")
        grid.attach(hide_hostname_check, 1, 9, 1, 1)
        
        grid.attach(Gtk.Label(label=TR['Hide categories text:']), 0, 10, 1, 1)
        hide_cat_text_check = Gtk.CheckButton()
        hide_cat_text_check.set_active(self.config['window'].get('hide_category_text', False))
        hide_cat_text_check.connect("toggled", self.on_checkbox_toggled, 'window', 'hide_category_text')
        grid.attach(hide_cat_text_check, 1, 10, 1, 1)
        
        grid.attach(Gtk.Label(label=TR['Hide app names:']), 0, 11, 1, 1)
        hide_app_names_check = Gtk.CheckButton()
        hide_app_names_check.set_active(self.config['window'].get('hide_app_names', False))
        hide_app_names_check.connect("toggled", self.on_checkbox_toggled, 'window', 'hide_app_names')
        grid.attach(hide_app_names_check, 1, 11, 1, 1)
        
        grid.attach(Gtk.Label(label=TR['Hide quick access:']), 0, 12, 1, 1)
        hide_quick_check = Gtk.CheckButton()
        hide_quick_check.set_active(self.config['window'].get('hide_quick_access', False))
        hide_quick_check.connect("toggled", self.on_check_toggled, "window", "hide_quick_access")
        grid.attach(hide_quick_check, 1, 12, 1, 1)
        
        grid.attach(Gtk.Label(label=TR['Hide social networks:']), 0, 13, 1, 1)
        hide_social_check = Gtk.CheckButton()
        hide_social_check.set_active(self.config['window'].get('hide_social_networks', False))
        hide_social_check.connect("toggled", self.on_check_toggled, "window", "hide_social_networks")
        grid.attach(hide_social_check, 1, 13, 1, 1)        

        # Los demás widgets ahora tienen posiciones actualizadas
        grid.attach(Gtk.Label(label=TR['Icon size:']), 0, 14, 1, 1)
        icon_size_spin = Gtk.SpinButton.new_with_range(16, 64, 8)
        icon_size_spin.set_value(self.config['window'].get('icon_size', 32))
        icon_size_spin.connect("value-changed", self.on_spin_button_changed, "window", "icon_size")
        grid.attach(icon_size_spin, 1, 14, 1, 1)

        grid.attach(Gtk.Label(label=TR['Category icon size:']), 0, 15, 1, 1)
        category_icon_size_spin = Gtk.SpinButton.new_with_range(16, 64, 8)
        category_icon_size_spin.set_value(self.config['window'].get('category_icon_size', 24))
        category_icon_size_spin.connect("value-changed", self.on_spin_button_changed, "window", "category_icon_size")
        grid.attach(category_icon_size_spin, 1, 15, 1, 1)

        grid.attach(Gtk.Label(label=TR['Profile pic size:']), 0, 16, 1, 1)
        profile_pic_size_spin = Gtk.SpinButton.new_with_range(64, 256, 8)
        profile_pic_size_spin.set_value(self.config['window'].get('profile_pic_size', 128))
        profile_pic_size_spin.connect("value-changed", self.on_spin_button_changed, "window", "profile_pic_size")
        grid.attach(profile_pic_size_spin, 1, 16, 1, 1)
        
        
        grid.attach(Gtk.Label(label=TR['Profile pic shape:']), 0, 17, 1, 1)    
        combobox = Gtk.ComboBoxText()
        combobox.append("square", TR.get('square', 'Cuadrada'))
        combobox.append("circular", TR.get('circular', 'Circular'))       
        current_shape = self.config['window'].get('profile_pic_shape', 'square')
        combobox.set_active_id(current_shape)
        combobox.connect("changed", self.on_combobox_changed, 'window', 'profile_pic_shape')
        grid.attach(combobox, 1, 17, 1, 1)

        grid.attach(Gtk.Label(label=TR['Horizontal alignment:']), 0, 18, 1, 1) 
        halign_combo = Gtk.ComboBoxText()
        halign_options = ["center", "left", "right"]
        for option in halign_options:
            halign_combo.append_text(TR[option])
        current_halign = self.config['window'].get('halign', 'center')
        try:
            index = halign_options.index(current_halign)
            halign_combo.set_active(index)
        except ValueError:
            halign_combo.set_active(0)
        halign_combo.connect("changed", self.on_combo_changed, "window", "halign")
        grid.attach(halign_combo, 1, 18, 1, 1) 
        
        grid.attach(Gtk.Label(label=TR['Search bar position:']), 0, 19, 1, 1)
        searchbar_combo = Gtk.ComboBoxText()
        searchbar_combo.append("top", TR['top'])
        searchbar_combo.append("bottom", TR['bottom'])
        current_searchbar = self.config['window'].get('search_bar_position', 'bottom')
        searchbar_combo.set_active_id(current_searchbar)
        searchbar_combo.connect("changed", self.on_combobox_changed, 'window', 'search_bar_position')
        grid.attach(searchbar_combo, 1, 19, 1, 1)

        # [CORRECCIÓN] Envolver el grid en un ScrolledWindow
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.add(grid)
        return scrolled_window # Devolver el ScrolledWindow
        
    def on_check_toggled(self, check_button, category, key):
        """Handle Gtk.CheckButton toggle events and save the state."""
        self.config[category][key] = check_button.get_active()
        self.config_manager.save_config(self.config)  
        
    def on_combobox_changed(self, combobox, category, key):
        """Manejar el cambio en un Gtk.ComboBoxText y guarda la nueva configuración,
           usando el ID activo ('square' o 'circular')."""
        selected_id = combobox.get_active_id()
        if selected_id is not None:
            # Esto guarda 'square' o 'circular' en self.config['window']['profile_pic_shape']
            self.config[category][key] = selected_id
            self.config_manager.save_config(self.config)              

    def create_colors_tab(self):
        grid = Gtk.Grid(row_spacing=10, column_spacing=10)
        grid.set_border_width(10)
        
        # NUEVO: Checkbox para usar tema GTK
        grid.attach(Gtk.Label(label=TR['Use system theme:']), 0, 0, 1, 1)
        gtk_theme_check = Gtk.CheckButton()
        gtk_theme_check.set_active(self.config['colors'].get('use_gtk_theme', False))
        gtk_theme_check.connect("toggled", self.on_gtk_theme_toggled)
        grid.attach(gtk_theme_check, 1, 0, 1, 1)
        
        # Separador visual
        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        grid.attach(separator, 0, 1, 2, 1)
        
        colors_to_config = {
            "text_header_os": TR['Header (OS):'],
            "text_header_kernel": TR['Header (Kernel):'],
            "text_header_hostname": TR['Header (Hostname):'],
            "background": TR['Background color:'],
            "border": TR['Border color:'],
            "categories_background": TR['Categories background:'],
            "text_normal": TR['Text normal:'],
            "button_normal_background": TR['Button background:'],
            "button_text": TR['Button text:'],
            "hover_background": TR['Hover background:'],            
        }        
        
        # Almacenar referencia a los widgets de color para poder deshabilitarlos
        self.color_widgets = []
        
        # Definimos las claves que solo aceptarán formato hexadecimal
        keys_for_hex_only = ["text_header_os", "text_header_kernel", "text_header_hostname", "text_normal", "button_text"]
        
        for i, (key, label) in enumerate(colors_to_config.items()):
            row = i + 2  # +2 porque agregamos checkbox y separador
            color_label = Gtk.Label(label=label)
            grid.attach(color_label, 0, row, 1, 1)
            
            color_button = Gtk.ColorButton()
            
            # Si la clave es una de las especiales, deshabilitamos el selector de opacidad
            if key in keys_for_hex_only:
                color_button.set_use_alpha(False)
            else:
                color_button.set_use_alpha(True)
    
            rgba = self.hex_to_rgba(self.config['colors'][key])
            if rgba:
                color_button.set_rgba(rgba)
            color_button.connect("color-set", self.on_color_set, "colors", key)
            grid.attach(color_button, 1, row, 1, 1)
            
            # Guardar referencias para poder deshabilitarlos
            self.color_widgets.extend([color_label, color_button])
        
        # Deshabilitar widgets si está activo el tema GTK
        self.update_color_widgets_sensitivity()
        
        # [CORRECCIÓN] Envolver el grid en un ScrolledWindow
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.add(grid)
        return scrolled_window # Devolver el ScrolledWindow
        
    def create_font_tab(self):
        grid = Gtk.Grid(row_spacing=10, column_spacing=10)
        grid.set_border_width(10)
        
        grid.attach(Gtk.Label(label=TR['Font family:']), 0, 0, 1, 1)
        font_button = Gtk.FontButton()
        font_button.set_font(self.config['font']['family'])
        font_button.set_show_size(False)
        font_button.connect("font-set", self.on_font_set, "font", "family")
        grid.attach(font_button, 1, 0, 1, 1)
        
        # Nueva opción: Fuente para categorías
        grid.attach(Gtk.Label(label=TR['Category font:']), 0, 1, 1, 1)
        category_font_button = Gtk.FontButton()
        category_font_button.set_font(self.config['font'].get('family_categories', self.config['font']['family']))
        category_font_button.set_show_size(False)
        category_font_button.connect("font-set", self.on_font_set, "font", "family_categories")
        grid.attach(category_font_button, 1, 1, 1, 1)
        
        sizes_to_config = {
            "size_categories": TR['Category size:'],
            "size_names": TR['App name size:'],
            "size_header": TR['Header size:']
        }
        
        for i, (key, label) in enumerate(sizes_to_config.items(), start=2):
            grid.attach(Gtk.Label(label=label), 0, i, 1, 1)
            size_spin = Gtk.SpinButton.new_with_range(5000, 50000, 1000)
            size_spin.set_value(self.config['font'][key])
            size_spin.connect("value-changed", self.on_spin_button_changed, "font", key)
            grid.attach(size_spin, 1, i, 1, 1)
            
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.add(grid)
        return scrolled_window

    def create_paths_tab(self):
        grid = Gtk.Grid(row_spacing=10, column_spacing=10)
        grid.set_border_width(10)
        
        paths_to_config = {
            "profile_pic": TR['Profile pic path:'],
            "profile_manager": TR['Profile manager:'],
            "shutdown_cmd": TR['Shutdown command:'],
            "jwmrc_tray": TR['JWM Tray config:'],
            "tint2rc": TR['Tint2 config:']
        }
        
        # Crear la entrada para la foto de perfil
        grid.attach(Gtk.Label(label=paths_to_config["profile_pic"]), 0, 0, 1, 1)
        entry_profile_pic = Gtk.Entry()
        entry_profile_pic.set_text(self.config['paths']["profile_pic"])
        entry_profile_pic.connect("changed", self.on_path_changed, "paths", "profile_pic")
        grid.attach(entry_profile_pic, 1, 0, 1, 1)
        browse_profile_pic = Gtk.Button(label="...")
        browse_profile_pic.connect("clicked", self.on_browse_file, entry_profile_pic, TR['Select profile picture'])
        grid.attach(browse_profile_pic, 2, 0, 1, 1)
        
        # Crear la entrada para el gestor de perfil
        grid.attach(Gtk.Label(label=paths_to_config["profile_manager"]), 0, 1, 1, 1)
        entry_profile_manager = Gtk.Entry()
        entry_profile_manager.set_text(self.config['paths']["profile_manager"])
        entry_profile_manager.connect("changed", self.on_path_changed, "paths", "profile_manager")
        grid.attach(entry_profile_manager, 1, 1, 1, 1)
        browse_profile_manager = Gtk.Button(label="...")
        browse_profile_manager.connect("clicked", self.on_browse_file, entry_profile_manager, TR['Select profile manager'])
        grid.attach(browse_profile_manager, 2, 1, 1, 1)        
        
        # Crear la entrada para el comando de apagado
        grid.attach(Gtk.Label(label=paths_to_config["shutdown_cmd"]), 0, 2, 1, 1)
        entry_shutdown_cmd = Gtk.Entry()
        entry_shutdown_cmd.set_text(self.config['paths']["shutdown_cmd"])
        entry_shutdown_cmd.connect("changed", self.on_path_changed, "paths", "shutdown_cmd")
        grid.attach(entry_shutdown_cmd, 1, 2, 1, 1)
        browse_shutdown_cmd = Gtk.Button(label="...")
        browse_shutdown_cmd.connect("clicked", self.on_browse_file, entry_shutdown_cmd, TR['Select shutdown command'])
        grid.attach(browse_shutdown_cmd, 2, 2, 1, 1)
        
        # Separador
        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        grid.attach(separator, 0, 3, 17, 1)
        
        # Checkbox para usar Tint2
        grid.attach(Gtk.Label(label=TR['Use Tint2 (instead of JWM):']), 0, 4, 1, 1)
        self.tint2_checkbox = Gtk.CheckButton()
        self.tint2_checkbox.set_active(self.config.get('tray', {}).get('use_tint2', False))
        self.tint2_checkbox.connect("toggled", self.on_tint2_toggled)
        grid.attach(self.tint2_checkbox, 1, 4, 1, 1)
        
        # Entrada para JWM Tray config
        self.jwm_label = Gtk.Label(label=paths_to_config["jwmrc_tray"])
        grid.attach(self.jwm_label, 0, 5, 1, 1)
        self.entry_jwmrc_tray = Gtk.Entry()
        self.entry_jwmrc_tray.set_text(self.config['paths'].get("jwmrc_tray", "/root/.jwmrc-tray"))
        self.entry_jwmrc_tray.connect("changed", self.on_path_changed, "paths", "jwmrc_tray")
        grid.attach(self.entry_jwmrc_tray, 1, 5, 1, 1)

        browse_jwm = Gtk.Button(label="...")
        browse_jwm.connect("clicked", self.on_browse_file, self.entry_jwmrc_tray, TR['Select JWM config'])
        grid.attach(browse_jwm, 2, 5, 1, 1)
        
        # Entrada para Tint2 config
        self.tint2_label = Gtk.Label(label=paths_to_config["tint2rc"])
        grid.attach(self.tint2_label, 0, 6, 1, 1)
        self.entry_tint2rc = Gtk.Entry()
        self.entry_tint2rc.set_text(self.config['paths'].get("tint2rc", "/root/.config/tint2/tint2rc"))
        self.entry_tint2rc.connect("changed", self.on_path_changed, "paths", "tint2rc")
        grid.attach(self.entry_tint2rc, 1, 6, 1, 1)
        browse_tint2 = Gtk.Button(label="...")
        browse_tint2.connect("clicked", self.on_browse_file, self.entry_tint2rc, TR['Select Tint2 config'])
        grid.attach(browse_tint2, 2, 6, 1, 1)
        
        separator2 = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        
        grid.attach(separator2, 0, 7, 17, 1)
        
        # Selector de motor de búsqueda
        grid.attach(Gtk.Label(label=TR['Search engine:']), 0, 8, 1, 1)
        search_engine_combo = Gtk.ComboBoxText()
        search_engine_combo.append("google", "Google")
        search_engine_combo.append("duckduckgo", "DuckDuckGo")
        search_engine_combo.append("brave", "Brave Search")
        search_engine_combo.append("searxng", "SearXNG")
        search_engine_combo.append("librex", "LibreX")
        
        current_engine = self.config.get('search_engine', {}).get('engine', 'google')
        search_engine_combo.set_active_id(current_engine)
        search_engine_combo.connect("changed", self.on_search_engine_changed)
        grid.attach(search_engine_combo, 1, 8, 16, 1)
        
        # Actualizar el estado de los widgets según el checkbox
        self.update_tray_widgets_sensitivity()
        
        # [CORRECCIÓN] Envolver el grid en un ScrolledWindow
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.add(grid)
        return scrolled_window # Devolver el ScrolledWindow
        
    def on_browse_file(self, button, entry, dialog_title):
        """Abrir diálogo para seleccionar un archivo"""
        dialog = Gtk.FileChooserDialog(
            title=dialog_title,
            parent=self,
            action=Gtk.FileChooserAction.OPEN
        )
        dialog.add_buttons(
            TR['Cancel'], Gtk.ResponseType.CANCEL,
            TR['Select'], Gtk.ResponseType.OK
        )
        
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            selected_file = dialog.get_filename()
            entry.set_text(selected_file)
        
        dialog.destroy()      
        
    def on_tint2_toggled(self, checkbox):
        """Manejar el toggle del checkbox de Tint2"""
        if 'tray' not in self.config:
            self.config['tray'] = {}
        self.config['tray']['use_tint2'] = checkbox.get_active()
        self.config_manager.save_config(self.config)
        self.update_tray_widgets_sensitivity()
    
    def update_tray_widgets_sensitivity(self):
        """Actualizar la sensibilidad de los widgets según el checkbox de Tint2"""
        use_tint2 = self.config.get('tray', {}).get('use_tint2', False)
        
        # Si usa Tint2, deshabilitar JWM y viceversa
        self.jwm_label.set_sensitive(not use_tint2)
        self.entry_jwmrc_tray.set_sensitive(not use_tint2)
        self.tint2_label.set_sensitive(use_tint2)
        self.entry_tint2rc.set_sensitive(use_tint2)  
        
    def on_search_engine_changed(self, combobox):
        """Manejar el cambio de motor de búsqueda"""
        if 'search_engine' not in self.config:
            self.config['search_engine'] = {}
        self.config['search_engine']['engine'] = combobox.get_active_id()
        self.config_manager.save_config(self.config)              
        
    def create_categories_tab(self):
        """Crear tab para excluir categorías"""
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        main_box.set_border_width(10)
    
        # Título descriptivo
        label = Gtk.Label(label=TR['Select categories to hide from menu'])
        label.set_halign(Gtk.Align.START)
        main_box.pack_start(label, False, False, 0)
    
        # Contenedor con scroll para los checkboxes
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_size_request(-1, 300)
    
        # con un espacio entre columnas de 10 píxeles.
        checkbox_grid = Gtk.Grid(row_spacing=6, column_spacing=100)
        checkbox_grid.set_border_width(10)
    
        # Lista de todas las categorías disponibles
        available_categories = [
            'Desktop', 'System', 'Setup', 'Utility', 'Filesystem', 
            'Graphic', 'Document', 'Business', 'Personal', 
            'Network', 'Internet', 'Multimedia', 'Fun', 'Help', 'Rectify', 'Shutdown',
             'Leave'
        ]
    
        # Crear labels y checkboxes para cada categoría y colocarlos en el grid
        # Create checkboxes for each category
        self.category_checkboxes = {}
        excluded_list = self.config.get('categories', {}).get('excluded', [])
            
        for i, category in enumerate(available_categories):
            # Get the translated name, defaulting to the original category name if no translation exists
            translated_name = TR.get(category, category)
                       
            # Create the label widget
            cat_label = Gtk.Label(label=translated_name)
            cat_label.set_halign(Gtk.Align.START) # Cambia START a CENTER aquí
            
            # Create the checkbox
            checkbox = Gtk.CheckButton()
            checkbox.set_active(category in excluded_list)
            checkbox.connect("toggled", self.on_category_checkbox_toggled, category)
            
            # Add the label and checkbox to the grid
            checkbox_grid.attach(cat_label, 0, i, 1, 1)
            checkbox_grid.attach(checkbox, 1, i, 1, 1)
        
            self.category_checkboxes[category] = checkbox
    
        scrolled.add(checkbox_grid)
        main_box.pack_start(scrolled, True, True, 0)
    
        return main_box
    
    def on_category_checkbox_toggled(self, checkbox, category):
        """Manejar cambios en checkboxes de categorías"""
        if 'categories' not in self.config:
            self.config['categories'] = {'excluded': []}
        
        excluded_list = self.config['categories']['excluded']
        
        if checkbox.get_active():
            # Agregar a la lista de excluidas si no está
            if category not in excluded_list:
                excluded_list.append(category)
        else:
            # Quitar de la lista de excluidas si está
            if category in excluded_list:
                excluded_list.remove(category)
        
        # Guardar configuración
        self.config_manager.save_config(self.config)       
            
    def on_spin_button_changed(self, spin_button, category, key):
        self.config[category][key] = int(spin_button.get_value())
        self.config_manager.save_config(self.config)
        print(f"DEBUG: Guardado {category}.{key} = {value}")
        
    def on_combo_changed(self, combo, category, key):
        selected_text = combo.get_active_text()
        for k, v in TR.translations.items():
            if v == selected_text:
                self.config[category][key] = k
                break
        self.config_manager.save_config(self.config)        

    def on_path_changed(self, entry, category, key):
        self.config[category][key] = entry.get_text()
        self.config_manager.save_config(self.config)

    def on_color_set(self, color_button, category, key):
        # --- INICIO DEL CAMBIO 2 ---
        rgba = color_button.get_rgba()
        keys_for_hex_only = ["text_header_os", "text_header_kernel", "text_header_hostname", "text_normal"]

        # Si la clave actual requiere formato HEX, usamos la función de conversión a HEX
        if key in keys_for_hex_only:
            self.config[category][key] = self.rgba_to_hex(rgba)
        # De lo contrario, usamos la función normal para mantener el RGBA
        else:
            self.config[category][key] = self.rgba_to_string(rgba)
        # --- FIN DEL CAMBIO 2 ---
        self.config_manager.save_config(self.config)

    def on_font_set(self, font_button, category, key):
        # Extraer solo la familia de fuente, sin el tamaño
        font_desc = font_button.get_font()
        # Separar la familia del tamaño (el tamaño viene al final)
        parts = font_desc.rsplit(' ', 1)
        font_family = parts[0] if len(parts) > 0 else font_desc
        self.config[category][key] = font_family
        self.config_manager.save_config(self.config)
        
    def on_checkbox_toggled(self, button, category, key):
        self.config[category][key] = button.get_active()    
        self.config_manager.save_config(self.config)
        
    def on_save_only_clicked(self, button):
        self.config_manager.save_config(self.config)
        print(TR['Config saved (without closing).'])
    
    def on_exit_clicked(self, button):
        Gtk.main_quit()

    def hex_to_rgba(self, hex_or_rgba_string):
        rgba = Gdk.RGBA()
        try:
            rgba.parse(hex_or_rgba_string)
            return rgba
        except ValueError:
            return None
    
    def rgba_to_string(self, rgba):
        r = int(rgba.red * 255)
        g = int(rgba.green * 255)
        b = int(rgba.blue * 255)
        return f"rgba({r}, {g}, {b}, {rgba.alpha:.2f})"

    # --- INICIO DEL CAMBIO 3 ---
    # Nueva función para convertir RGBA a formato de string Hexadecimal
    def rgba_to_hex(self, rgba):
        r = int(rgba.red * 255)
        g = int(rgba.green * 255)
        b = int(rgba.blue * 255)
        return f"#{r:02x}{g:02x}{b:02x}"
    # --- FIN DEL CAMBIO 3 ---

def main():
    try:
        win = ConfigWindow()
        win.show_all()
        Gtk.main()
    except Exception as e:
        print(f"{TR['An error occurred:']} {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
