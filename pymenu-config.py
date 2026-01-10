#!/usr/bin/env python3
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib
import json
import os
import sys
import locale
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

# === 🌍 Sistema de Traducción ===
try:
    sys.path.insert(0, '/usr/local/bin')
    from pymenupuplang import TranslationManager
    TR = TranslationManager(app_name="pymenupup") 
except:
    # Si no existe pymenupuplang.py, usar inglés
    class FallbackTranslator:
        def __getitem__(self, key):
            return key
        def get(self, key, default=None):
            return default or key
        def get_category_map(self):
            return {}
    
    TR = FallbackTranslator()

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
                "profile_in_places": True,
                "hide_places": False,
                "hide_favorites": False, 
                "search_bar_position": "bottom",
                "search_bar_container": "apps_column",
                "hide_social_networks": True,
                "halign": "left",
                "icon_size": 32,
                "profile_pic_size": 64,
                "profile_pic_shape": "square", 
                "hide_category_text": False,
                "category_icon_size": 16,
                "header_layout": "left",
                "header_text_align": "center",
                "hide_os_name": False,
                "hide_kernel": False,
                "hide_hostname": False,
                "hide_app_names": False
            },
            "font": {
                "family": "Sans",
                "family_categories": "Sans",
                "size_categories": 13000,
                "size_names": 11000,
                "size_header": 17000
            },
            "colors": {
                "use_gtk_theme": True,
                "background_opacity": 0.7,
                "background": "rgba(0, 0, 0, 0.88)",
                "border": "rgba(255, 255, 255, 0.1)",
                "text_normal": "#deddda",
                "text_header_os": "#D8DEE9",
                "text_header_kernel": "#deddda",
                "text_header_hostname": "#deddda",
                "hover_background": "rgba(255, 255, 255, 0.10)",
                "selected_background": "rgba(255, 255, 255, 0.2)",
                "selected_text": "#ECEFF4",
                "button_normal_background": "rgba(191, 63, 63, 0.00)",
                "button_text": "rgba(222, 221, 218, 1.00)",
                "categories_background": "rgba(191, 63, 63, 0.00)"
            },
            "paths": {
                "profile_pic": "",
                "profile_manager": "",
                "shutdown_cmd": "",
                "jwmrc_tray": "/root/.jwmrc-tray",          
                "tint2rc": "/root/.config/tint2/tint2rc",
                "xfce_panel": "/root/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-panel.xml",
			    "lxde_panel": "/root/.config/lxpanel/LXDE/panels/panel"
            },
            "search_engine": {
                "engine": "duckduckgo"
            },
            "tray": {
                "type": "jwm"  
            },
            "categories": {
                "excluded": []
            },
            "favorites": [],
            "places": {
                 "visible_folders": ["Home", "Downloads", "Documents", "Music", "Pictures", "Videos"],
                 "all_available": ["Home", "Downloads", "Documents", "Music", "Pictures", "Videos"]
            },     
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
        
        notebook = Gtk.Notebook()
        main_vbox.pack_start(notebook, True, True, 0)
     
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

        # Hide header
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
        hide_cat_text_check.connect("toggled", self.on_check_toggled, 'window', 'hide_category_text')
        grid.attach(hide_cat_text_check, 1, 10, 1, 1)
        
        grid.attach(Gtk.Label(label=TR['Hide app names:']), 0, 11, 1, 1)
        hide_app_names_check = Gtk.CheckButton()
        hide_app_names_check.set_active(self.config['window'].get('hide_app_names', False))
        hide_app_names_check.connect("toggled", self.on_check_toggled, 'window', 'hide_app_names')
        grid.attach(hide_app_names_check, 1, 11, 1, 1)
                
        grid.attach(Gtk.Label(label=TR['Hide social networks:']), 0, 12, 1, 1)
        hide_social_check = Gtk.CheckButton()
        hide_social_check.set_active(self.config['window'].get('hide_social_networks', False))
        hide_social_check.connect("toggled", self.on_check_toggled, "window", "hide_social_networks")
        grid.attach(hide_social_check, 1, 12, 1, 1)
        
        # ===== NUEVAS OPCIONES COMBINADAS =====
        
        # Hide places sidebar
        places_label_text = TR['Hide places sidebar:'] + '\n' + TR['(Hides both places and favorites)']
        places_label = Gtk.Label(label=places_label_text)
        places_label.set_halign(Gtk.Align.START)
        places_label.set_line_wrap(True)
        grid.attach(places_label, 0, 13, 1, 1)
        
        hide_places_check = Gtk.CheckButton()
        hide_places_check.set_active(self.config['window'].get('hide_places', False))
        hide_places_check.connect("toggled", self.on_check_toggled, "window", "hide_places")
        grid.attach(hide_places_check, 1, 13, 1, 1)
        
        # Hide favorites only (solo si places está visible)
        favorites_label_text = TR['Hide favorites only:'] + '\n' + TR['(Show places but hide favorites)']
        favorites_label = Gtk.Label(label=favorites_label_text)
        favorites_label.set_halign(Gtk.Align.START)
        favorites_label.set_line_wrap(True)
        grid.attach(favorites_label, 0, 14, 1, 1)
        
        hide_favorites_check = Gtk.CheckButton()
        hide_favorites_check.set_active(self.config['window'].get('hide_favorites', False))
        hide_favorites_check.connect("toggled", self.on_check_toggled, "window", "hide_favorites")
        grid.attach(hide_favorites_check, 1, 14, 1, 1)
        
        # Profile in places (mover perfil a la columna Places)
        profile_places_label_text = TR['Show profile in places sidebar:'] + '\n' + TR['(Instead of header)']
        profile_places_label = Gtk.Label(label=profile_places_label_text)
        profile_places_label.set_halign(Gtk.Align.START)
        profile_places_label.set_line_wrap(True)
        grid.attach(profile_places_label, 0, 15, 1, 1)
        
        profile_in_places_check = Gtk.CheckButton()
        profile_in_places_check.set_active(self.config['window'].get('profile_in_places', True))
        profile_in_places_check.connect("toggled", self.on_check_toggled, "window", "profile_in_places")
        grid.attach(profile_in_places_check, 1, 15, 1, 1)

        # Icon size (FALTANTE - AGREGADA)
        grid.attach(Gtk.Label(label=TR['Icon size:']), 0, 16, 1, 1)
        icon_size_spin = Gtk.SpinButton.new_with_range(16, 64, 8)
        icon_size_spin.set_value(self.config['window'].get('icon_size', 32))
        icon_size_spin.connect("value-changed", self.on_spin_button_changed, "window", "icon_size")
        grid.attach(icon_size_spin, 1, 16, 1, 1)

        grid.attach(Gtk.Label(label=TR['Category icon size:']), 0, 17, 1, 1)
        category_icon_size_spin = Gtk.SpinButton.new_with_range(16, 64, 8)
        category_icon_size_spin.set_value(self.config['window'].get('category_icon_size', 24))
        category_icon_size_spin.connect("value-changed", self.on_spin_button_changed, "window", "category_icon_size")
        grid.attach(category_icon_size_spin, 1, 17, 1, 1)

        grid.attach(Gtk.Label(label=TR['Profile pic size:']), 0, 18, 1, 1)
        profile_pic_size_spin = Gtk.SpinButton.new_with_range(64, 256, 8)
        profile_pic_size_spin.set_value(self.config['window'].get('profile_pic_size', 128))
        profile_pic_size_spin.connect("value-changed", self.on_spin_button_changed, "window", "profile_pic_size")
        grid.attach(profile_pic_size_spin, 1, 18, 1, 1)
        
        grid.attach(Gtk.Label(label=TR['Profile pic shape:']), 0, 19, 1, 1)    
        combobox = Gtk.ComboBoxText()
        combobox.append("square", TR.get('square', 'Cuadrada'))
        combobox.append("circular", TR.get('circular', 'Circular'))       
        current_shape = self.config['window'].get('profile_pic_shape', 'square')
        combobox.set_active_id(current_shape)
        combobox.connect("changed", self.on_combobox_changed, 'window', 'profile_pic_shape')
        grid.attach(combobox, 1, 19, 1, 1)

        grid.attach(Gtk.Label(label=TR['Horizontal alignment:']), 0, 20, 1, 1) 
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
        grid.attach(halign_combo, 1, 20, 1, 1) 
        
        grid.attach(Gtk.Label(label=TR['Search bar position:']), 0, 21, 1, 1)
        searchbar_combo = Gtk.ComboBoxText()
        searchbar_combo.append("top", TR['top'])
        searchbar_combo.append("bottom", TR['bottom'])
        current_searchbar = self.config['window'].get('search_bar_position', 'bottom')
        searchbar_combo.set_active_id(current_searchbar)
        searchbar_combo.connect("changed", self.on_combobox_changed, 'window', 'search_bar_position')
        grid.attach(searchbar_combo, 1, 21, 1, 1)
        
# ← NUEVO: Control para search_bar_container
        grid.attach(Gtk.Label(label=TR['Search bar container:']), 0, 22, 1, 1)
        container_combo = Gtk.ComboBoxText()
        container_combo.append("window", TR['In window'])
        container_combo.append("apps_column", TR['In applications column'])
        current_container = self.config['window'].get('search_bar_container', 'window')
        container_combo.set_active_id(current_container)
        container_combo.connect("changed", self.on_combobox_changed, 'window', 'search_bar_container')
        grid.attach(container_combo, 1, 22, 1, 1)      

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
        
        # AÑADIR LXDE AL DICCIONARIO
        paths_to_config = {
            "profile_pic": TR['Profile pic path:'],
            "profile_manager": TR['Profile manager:'],
            "shutdown_cmd": TR['Shutdown command:'],
            "jwmrc_tray": TR['JWM Tray config:'],
            "tint2rc": TR['Tint2 config:'],
            "xfce_panel": TR['XFCE panel config:'],
            "lxde_panel": TR['LXDE panel config:']  # ← AÑADIDO
        }
        
        # --- Configuración de Rutas Generales ---
        grid.attach(Gtk.Label(label=paths_to_config["profile_pic"]), 0, 0, 1, 1)
        entry_profile_pic = Gtk.Entry()
        entry_profile_pic.set_text(self.config['paths']["profile_pic"])
        entry_profile_pic.connect("changed", self.on_path_changed, "paths", "profile_pic")
        grid.attach(entry_profile_pic, 1, 0, 1, 1)
        browse_profile_pic = Gtk.Button(label="...")
        browse_profile_pic.connect("clicked", self.on_browse_file, entry_profile_pic, TR['Select profile picture'])
        grid.attach(browse_profile_pic, 2, 0, 1, 1)
    
        grid.attach(Gtk.Label(label=paths_to_config["profile_manager"]), 0, 1, 1, 1)
        entry_profile_manager = Gtk.Entry()
        entry_profile_manager.set_text(self.config['paths']["profile_manager"])
        entry_profile_manager.connect("changed", self.on_path_changed, "paths", "profile_manager")
        grid.attach(entry_profile_manager, 1, 1, 1, 1)
        browse_profile_manager = Gtk.Button(label="...")
        browse_profile_manager.connect("clicked", self.on_browse_file, entry_profile_manager, TR['Select profile manager'])
        grid.attach(browse_profile_manager, 2, 1, 1, 1)        
        
        grid.attach(Gtk.Label(label=paths_to_config["shutdown_cmd"]), 0, 2, 1, 1)
        entry_shutdown_cmd = Gtk.Entry()
        entry_shutdown_cmd.set_text(self.config['paths']["shutdown_cmd"])
        entry_shutdown_cmd.connect("changed", self.on_path_changed, "paths", "shutdown_cmd")
        grid.attach(entry_shutdown_cmd, 1, 2, 1, 1)
        browse_shutdown_cmd = Gtk.Button(label="...")
        browse_shutdown_cmd.connect("clicked", self.on_browse_file, entry_shutdown_cmd, TR['Select shutdown command'])
        grid.attach(browse_shutdown_cmd, 2, 2, 1, 1)
        
        grid.attach(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), 0, 3, 3, 1)
        
        # === MOTOR DE BÚSQUEDA (ANTES DEL TRAY) ===
        grid.attach(Gtk.Label(label=TR['Search engine:']), 0, 4, 1, 1)
        search_engine_combo = Gtk.ComboBoxText()
        
        # Agregar los 9 motores de búsqueda disponibles
        search_engine_combo.append("duckduckgo", "DuckDuckGo")
        search_engine_combo.append("google", "Google")
        search_engine_combo.append("brave", "Brave Search")
        search_engine_combo.append("searxng", "SearXNG")
        search_engine_combo.append("librex", "LibreX")
        search_engine_combo.append("bing", "Bing")
        search_engine_combo.append("yahoo", "Yahoo")
        search_engine_combo.append("startpage", "Startpage")
        search_engine_combo.append("ecosia", "Ecosia")
        
        # Establecer el motor actual (si existe)
        current_engine = self.config.get('search_engine', {}).get('engine', 'duckduckgo')
        search_engine_combo.set_active_id(current_engine)
        search_engine_combo.connect("changed", self.on_search_engine_changed)
        grid.attach(search_engine_combo, 1, 4, 1, 1)
        
        grid.attach(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), 0, 5, 3, 1)  # CORREGIDO
        
        grid.attach(Gtk.Label(label=TR['Tray/Panel type:']), 0, 6, 1, 1)  # CORREGIDO
        tray_type_combo = Gtk.ComboBoxText()
        tray_type_combo.append("jwm", TR['JWM Tray'])
        tray_type_combo.append("tint2", TR['Tint2 Panel'])
        tray_type_combo.append("xfce", TR['XFCE Panel'])
        tray_type_combo.append("lxde", TR['LXDE Panel'])
        
        current_tray_type = self.config.get('tray', {}).get('type', 'jwm')
        tray_type_combo.set_active_id(current_tray_type)
        tray_type_combo.connect("changed", self.on_tray_type_changed)
        grid.attach(tray_type_combo, 1, 6, 1, 1)  # CORREGIDO
        
        # Configuración de tray (unificada)
        tray_grid = Gtk.Grid(row_spacing=10, column_spacing=10)
        grid.attach(tray_grid, 0, 7, 3, 1)  # CORREGIDO
        
        # JWM Tray config
        self.jwm_label = Gtk.Label(label=TR['JWM Tray config:'])
        tray_grid.attach(self.jwm_label, 0, 0, 1, 1)
        self.entry_jwmrc_tray = Gtk.Entry()
        self.entry_jwmrc_tray.set_text(self.config['paths'].get("jwmrc_tray", "/root/.jwmrc-tray"))
        self.entry_jwmrc_tray.connect("changed", self.on_path_changed, "paths", "jwmrc_tray")
        tray_grid.attach(self.entry_jwmrc_tray, 1, 0, 1, 1)
        browse_jwm = Gtk.Button(label="...")
        browse_jwm.connect("clicked", self.on_browse_file, self.entry_jwmrc_tray, TR['Select JWM config'])
        tray_grid.attach(browse_jwm, 2, 0, 1, 1)
        
        # Tint2 config
        self.tint2_label = Gtk.Label(label=TR['Tint2 config:'])
        tray_grid.attach(self.tint2_label, 0, 1, 1, 1)
        self.entry_tint2rc = Gtk.Entry()
        self.entry_tint2rc.set_text(self.config['paths'].get("tint2rc", "/root/.config/tint2/tint2rc"))
        self.entry_tint2rc.connect("changed", self.on_path_changed, "paths", "tint2rc")
        tray_grid.attach(self.entry_tint2rc, 1, 1, 1, 1)
        browse_tint2 = Gtk.Button(label="...")
        browse_tint2.connect("clicked", self.on_browse_file, self.entry_tint2rc, TR['Select Tint2 config'])
        tray_grid.attach(browse_tint2, 2, 1, 1, 1)
        
        # XFCE config
        self.xfce_label = Gtk.Label(label=TR['XFCE panel config:'])
        tray_grid.attach(self.xfce_label, 0, 2, 1, 1)
        self.entry_xfce_panel = Gtk.Entry()
        self.entry_xfce_panel.set_text(self.config['paths'].get("xfce_panel", "/root/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-panel.xml"))
        self.entry_xfce_panel.connect("changed", self.on_path_changed, "paths", "xfce_panel")
        tray_grid.attach(self.entry_xfce_panel, 1, 2, 1, 1)
        browse_xfce = Gtk.Button(label="...")
        browse_xfce.connect("clicked", self.on_browse_file, self.entry_xfce_panel, TR['Select XFCE panel config'])
        tray_grid.attach(browse_xfce, 2, 2, 1, 1)
        
        # LXDE Panel config
        self.lxde_label = Gtk.Label(label=TR['LXDE panel config:'])
        tray_grid.attach(self.lxde_label, 0, 3, 1, 1)
        self.entry_lxde_panel = Gtk.Entry()
        self.entry_lxde_panel.set_text(self.config['paths'].get("lxde_panel", "/root/.config/lxpanel/LXDE/panels/panel"))
        self.entry_lxde_panel.connect("changed", self.on_path_changed, "paths", "lxde_panel")
        tray_grid.attach(self.entry_lxde_panel, 1, 3, 1, 1)
        browse_lxde = Gtk.Button(label="...")
        browse_lxde.connect("clicked", self.on_browse_file, self.entry_lxde_panel, TR['Select LXDE panel config'])
        tray_grid.attach(browse_lxde, 2, 3, 1, 1)
        
        # Actualizar visibilidad inicial
        self.update_tray_widgets_sensitivity()
        
        # Separador antes de la sección de carpetas visibles
        grid.attach(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), 0, 8, 3, 1)  # CORREGIDO
        
        # === NUEVA SECCIÓN: CARPETAS VISIBLES EN PLACES ===
        # Asegurar que existe la configuración de carpetas
        if 'places' not in self.config:
            self.config['places'] = {}
        if 'visible_folders' not in self.config['places']:
            # Configuración predeterminada
            self.config['places']['visible_folders'] = ["Home", "Downloads", "Documents", "Music", "Pictures", "Videos"]
        if 'all_available' not in self.config['places']:
            self.config['places']['all_available'] = ["Home", "Downloads", "Documents", "Music", "Pictures", "Videos", "Desktop", "Templates", "Public", "Recent"]
        
        # Título de la sección
        places_title_label = Gtk.Label()
        places_title_label.set_markup(f"<b>{TR['Visible Folders in Places Sidebar']}</b>")
        places_title_label.set_halign(Gtk.Align.START)
        grid.attach(places_title_label, 0, 9, 3, 1)  # CORREGIDO
        
        # Descripción
        desc_label = Gtk.Label(label=TR['Select which folders to show in the Places sidebar:'])
        desc_label.set_halign(Gtk.Align.START)
        desc_label.set_line_wrap(True)
        grid.attach(desc_label, 0, 10, 3, 1)  # CORREGIDO
        
        # Contenedor para checkboxes con scroll
        scrolled_places = Gtk.ScrolledWindow()
        scrolled_places.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled_places.set_size_request(-1, 150)
        grid.attach(scrolled_places, 0, 11, 3, 1)  # CORREGIDO
        
        # Grid para checkboxes
        places_checkbox_grid = Gtk.Grid(row_spacing=6, column_spacing=15)
        places_checkbox_grid.set_border_width(10)
        
        # Diccionario de traducciones para nombres de carpetas
        folder_translations = {
            "Home": TR.get("Home", "Home"),
            "Downloads": TR.get("Downloads", "Downloads"),
            "Documents": TR.get("Documents", "Documents"),
            "Music": TR.get("Music", "Music"),
            "Pictures": TR.get("Pictures", "Pictures"),
            "Videos": TR.get("Videos", "Videos"),
            "Desktop": TR.get("Desktop", "Desktop"),
            "Templates": TR.get("Templates", "Templates"),
            "Public": TR.get("Public", "Public"),
            "Recent": TR.get("Recent", "Recent")
        }
        
        # Crear checkboxes para cada carpeta disponible
        self.places_checkboxes = {}
        visible_folders = self.config['places']['visible_folders']
        all_folders = self.config['places']['all_available']
        
        for i, folder_key in enumerate(all_folders):
            # Obtener nombre traducido
            folder_name = folder_translations.get(folder_key, folder_key)
            
            # Crear label
            label = Gtk.Label(label=folder_name)
            label.set_halign(Gtk.Align.START)
            
            # Crear checkbox
            checkbox = Gtk.CheckButton()
            checkbox.set_active(folder_key in visible_folders)
            checkbox.connect("toggled", self.on_places_checkbox_toggled, folder_key)
            
            # Calcular posición (2 columnas)
            col = i % 2
            row = i // 2
            
            places_checkbox_grid.attach(label, col * 2, row, 1, 1)
            places_checkbox_grid.attach(checkbox, col * 2 + 1, row, 1, 1)
            
            self.places_checkboxes[folder_key] = checkbox
        
        scrolled_places.add(places_checkbox_grid)
        
        # Separador antes de favoritos
        grid.attach(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), 0, 12, 3, 1)  
    
        # === FIXED FAVORITES SECTION ===
        fav_title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        favorites_label = Gtk.Label(label=f"<b>{TR['Favorites']}</b>")
        favorites_label.set_use_markup(True)
        fav_title_box.pack_start(favorites_label, False, False, 0)
        
        # Add button above the list so it NEVER disappears
        btn_always_add = Gtk.Button(label=TR.get('Add favorite', 'Add favorite'))
        btn_always_add.connect("clicked", self.on_add_favorite_clicked)
        fav_title_box.pack_end(btn_always_add, False, False, 0)
        
        grid.attach(fav_title_box, 0, 13, 3, 1)  # CORREGIDO
        
        # Favorites list
        self.favorites_listbox = Gtk.ListBox()
        self.favorites_listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        
        # The list area has its own scroll
        fav_scroll = Gtk.ScrolledWindow()
        fav_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        fav_scroll.set_size_request(-1, 200) # Minimum list height
        fav_scroll.add(self.favorites_listbox)
        
        grid.attach(fav_scroll, 0, 14, 3, 1)  # CORREGIDO
    
        # Wrap everything in a main scroll for Puppy Linux (small screens)
        main_scrolled = Gtk.ScrolledWindow()
        main_scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        main_scrolled.add(grid)
     
        GLib.idle_add(self.load_favorites_list)
        
        return main_scrolled
        
    def on_places_checkbox_toggled(self, checkbox, folder_key):
        """Manejar cambios en checkboxes de carpetas visibles"""
        # Asegurar que existe la sección places
        if 'places' not in self.config:
            self.config['places'] = {}
        if 'visible_folders' not in self.config['places']:
            self.config['places']['visible_folders'] = []
        
        visible_folders = self.config['places']['visible_folders']
        
        if checkbox.get_active():
            # Agregar a la lista de visibles si no está
            if folder_key not in visible_folders:
                visible_folders.append(folder_key)
        else:
            # Quitar de la lista de visibles si está
            if folder_key in visible_folders:
                visible_folders.remove(folder_key)
        
        # Guardar configuración
        self.config_manager.save_config(self.config)
        print(f"Carpeta '{folder_key}' {'visible' if checkbox.get_active() else 'oculta'}")                
    
    def update_tray_widgets_sensitivity(self):
        """Actualizar la visibilidad de los widgets según el tipo de tray seleccionado"""
        tray_type = self.config.get('tray', {}).get('type', 'jwm')
        
        # Mostrar solo la configuración correspondiente al tipo seleccionado
        self.jwm_label.set_visible(tray_type == 'jwm')
        self.entry_jwmrc_tray.set_visible(tray_type == 'jwm')
        
        self.tint2_label.set_visible(tray_type == 'tint2')
        self.entry_tint2rc.set_visible(tray_type == 'tint2')
        
        self.xfce_label.set_visible(tray_type == 'xfce')
        self.entry_xfce_panel.set_visible(tray_type == 'xfce')
        
        self.lxde_label.set_visible(tray_type == 'lxde')        
        self.entry_lxde_panel.set_visible(tray_type == 'lxde')  
        
    def on_tray_type_changed(self, combobox):
        """Manejar el cambio de tipo de tray"""
        tray_type = combobox.get_active_id()
        
        if 'tray' not in self.config:
            self.config['tray'] = {}
        
        self.config['tray']['type'] = tray_type
        self.config_manager.save_config(self.config)
        self.update_tray_widgets_sensitivity()               
        
    def load_favorites_list(self):
            """Load and display the current favorites list"""
            # Clear current list
            for child in self.favorites_listbox.get_children():
                self.favorites_listbox.remove(child)
            
            favorites = self.config.get('favorites', [])
            
            if not favorites:
                # Create a special row
                row = Gtk.ListBoxRow()
                
                # We use a Button instead of Label so it responds to click
                # We remove the relief (set_relief) to make it look like simple text
                btn_empty = Gtk.Button(label=TR.get('No favorites yet. Click here to add one.', 'No favorites yet. Click here to add one.'))
                btn_empty.set_relief(Gtk.ReliefStyle.NONE)
                
                # Connect the text click directly to the add function
                btn_empty.connect("clicked", self.on_add_favorite_clicked)
                
                row.add(btn_empty)
                self.favorites_listbox.add(row)
            else:
                for fav in favorites:
                    row = self.create_favorite_row(fav)
                    self.favorites_listbox.add(row)
            
            self.favorites_listbox.show_all()
        
    def create_favorite_row(self, fav):
            """Create a row to display a favorite with action buttons"""
            row = Gtk.ListBoxRow()
            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            hbox.set_margin_top(5)
            hbox.set_margin_bottom(5)
            hbox.set_margin_start(10)
            hbox.set_margin_end(10)
            
            # CORRECTED: Use the name directly from JSON
            name = fav.get('name', 'Unnamed')
            exec_cmd = fav.get('exec', '')
            icon_name = fav.get('icon', 'application-x-executable')
            
            # Determine icon based on command type
            if 'gtk-launch' in exec_cmd:
                icon_text = "📱"
            elif any(x in exec_cmd for x in ['pcmanfm', 'rox', 'thunar', 'nautilus']):
                icon_text = "📁"
            else:
                icon_text = "⚙️"
            
            # Icon
            icon_label = Gtk.Label(label=icon_text)
            hbox.pack_start(icon_label, False, False, 0)
            
            # REAL favorite name
            name_button = Gtk.Button(label=name)
            name_button.set_relief(Gtk.ReliefStyle.NONE)  # Sin borde de botón
            name_button.set_halign(Gtk.Align.START)
            name_button.connect("clicked", self.on_edit_favorite_clicked, fav)
            hbox.pack_start(name_button, True, True, 0)
            
            # Command (truncated)
            cmd_preview = exec_cmd[:30] + "..." if len(exec_cmd) > 30 else exec_cmd
            cmd_label = Gtk.Label()
            cmd_label.set_markup(f"<small><i>{cmd_preview}</i></small>")
            hbox.pack_start(cmd_label, False, False, 0)
            
            # Delete button
            delete_button = Gtk.Button(label="🗑️")
            delete_button.set_relief(Gtk.ReliefStyle.NONE)
            delete_button.connect("clicked", self.on_delete_favorite_clicked, fav)
            hbox.pack_start(delete_button, False, False, 0)
            
            row.add(hbox)
            return row
        
    def on_add_favorite_clicked(self, button):
            """Show dialog to add a new favorite"""
            dialog = Gtk.Dialog(
                title=TR.get('Add Favorite', 'Add Favorite'),
                parent=self,
                flags=0
            )
            dialog.add_buttons(
                TR['Cancel'], Gtk.ResponseType.CANCEL,
                TR.get('Add', 'Add'), Gtk.ResponseType.OK
            )
            dialog.set_default_size(500, 400)
            
            content = dialog.get_content_area()
            content.set_spacing(10)
            content.set_border_width(10)
            
            # Notebook with tabs for each type
            notebook = Gtk.Notebook()
            content.pack_start(notebook, True, True, 0)
            
# === TAB 1: APPLICATION (WITH SEARCH) ===
            app_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
            app_box.set_border_width(10)
            
            app_label = Gtk.Label(label=TR.get('Select an application:', 'Select an application:'))
            app_label.set_halign(Gtk.Align.START)
            app_box.pack_start(app_label, False, False, 0)
            
            # NEW: Search box
            search_entry = Gtk.SearchEntry()
            search_entry.set_placeholder_text(TR.get('Search applications...', 'Search applications...'))
            app_box.pack_start(search_entry, False, False, 0)
            
            app_scrolled = Gtk.ScrolledWindow()
            app_scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            
            app_listbox = Gtk.ListBox()
            app_listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
            
            # Load applications from /usr/share/applications
            desktop_files = self.get_desktop_files()
            all_rows = []  # Save all rows for filtering
            
            for desktop_file in sorted(desktop_files):
                display_name = os.path.basename(desktop_file).replace('.desktop', '')
                row = Gtk.ListBoxRow()
                label = Gtk.Label(label=display_name)
                label.set_halign(Gtk.Align.START)
                label.set_margin_start(10)
                label.set_margin_top(5)
                label.set_margin_bottom(5)
                row.add(label)
                row.desktop_path = desktop_file
                row.display_name = display_name
                app_listbox.add(row)
                all_rows.append(row)
            
            # Filter function
            def on_search_changed(entry):
                search_text = entry.get_text().lower()
                for row in all_rows:
                    if search_text in row.display_name.lower():
                        row.show()
                    else:
                        row.hide()
            
            search_entry.connect("search-changed", on_search_changed)
            
            app_scrolled.add(app_listbox)
            app_box.pack_start(app_scrolled, True, True, 0)
            notebook.append_page(app_box, Gtk.Label(label=TR.get('Application', 'Application')))
            
            # === TAB 2: DIRECTORY ===
            dir_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
            dir_box.set_border_width(10)
            dir_label = Gtk.Label(label=TR.get('Select a directory:', 'Select a directory:'))
            dir_label.set_halign(Gtk.Align.START)
            dir_box.pack_start(dir_label, False, False, 0)
            
            dir_entry = Gtk.Entry()
            dir_entry.set_placeholder_text(TR.get('Path to directory', 'Path to directory'))
            dir_box.pack_start(dir_entry, False, False, 0)
            
            dir_browse = Gtk.Button(label=TR.get('Browse...', 'Browse...'))
            dir_browse.connect("clicked", self.on_browse_directory, dir_entry)
            dir_box.pack_start(dir_browse, False, False, 0)
            
            notebook.append_page(dir_box, Gtk.Label(label=TR.get('Directory', 'Directory')))
            
# === TAB 3: COMMAND ===
            cmd_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
            cmd_box.set_border_width(10)
            
            # Name
            cmd_box.pack_start(Gtk.Label(label=TR.get('Name:', 'Name:'), halign=Gtk.Align.START), False, False, 0)
            cmd_name_entry = Gtk.Entry()
            cmd_name_entry.set_placeholder_text(TR.get('Favorite name', 'Favorite name'))
            cmd_box.pack_start(cmd_name_entry, False, False, 0)
            
            # Command with browse button
            cmd_box.pack_start(Gtk.Label(label=TR.get('Command:', 'Command:'), halign=Gtk.Align.START), False, False, 0)
            
            # Horizontal box for command + browse button
            cmd_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
            
            cmd_exec_entry = Gtk.Entry()
            cmd_exec_entry.set_placeholder_text(TR.get('Command to execute', 'Command to execute'))
            cmd_hbox.pack_start(cmd_exec_entry, True, True, 0)
            
            # Browse button to select executable
            cmd_browse_button = Gtk.Button(label="📂")
            cmd_browse_button.set_tooltip_text(TR.get('Browse command', 'Browse command'))
            cmd_browse_button.connect("clicked", self.on_browse_file, cmd_exec_entry, TR.get('Select command', 'Select command'))
            cmd_hbox.pack_start(cmd_browse_button, False, False, 0)
            
            cmd_box.pack_start(cmd_hbox, False, False, 0)
            
            # Icon with browse button
            cmd_box.pack_start(Gtk.Label(label=TR.get('Icon (optional):', 'Icon (optional):'), halign=Gtk.Align.START), False, False, 0)
            
            # Horizontal box for entry + button
            icon_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
            
            cmd_icon_entry = Gtk.Entry()
            cmd_icon_entry.set_placeholder_text(TR.get('Icon name or path', 'Icon name or path'))
            icon_hbox.pack_start(cmd_icon_entry, True, True, 0)
            
            # Icon browse button
            icon_browse_button = Gtk.Button(label="📂")
            icon_browse_button.set_tooltip_text(TR.get('Browse icon', 'Browse icon'))
            icon_browse_button.connect("clicked", self.on_browse_icon_clicked, cmd_icon_entry)
            icon_hbox.pack_start(icon_browse_button, False, False, 0)
            
            cmd_box.pack_start(icon_hbox, False, False, 0)
            
            notebook.append_page(cmd_box, Gtk.Label(label=TR.get('Command', 'Command')))
            
            dialog.show_all()
            response = dialog.run()
            
            if response == Gtk.ResponseType.OK:
                current_page = notebook.get_current_page()
                fav = None
                
                if current_page == 0:  # Application (.desktop)
                    selected = app_listbox.get_selected_row()
                    if selected:
                        # Try to read the real icon from .desktop if possible
                        icon_name = "application-x-desktop"
                        try:
                            with open(selected.desktop_path, 'r') as f:
                                for line in f:
                                    if line.startswith("Icon="):
                                        icon_name = line.split("=")[1].strip()
                                        break
                        except: pass
                        
                        fav = {
                            'name': selected.display_name,
                            'exec': f"gtk-launch {os.path.basename(selected.desktop_path)}",
                            'icon': icon_name
                        }
                
                elif current_page == 1:  # Directory
                    path = dir_entry.get_text().strip()
                    if path:
                        fav = {
                            'name': os.path.basename(path) or path,
                            'exec': f"pcmanfm '{path}'", # Or Puppy's file manager (rox, pcmanfm)
                            'icon': 'folder'
                        }
                
                elif current_page == 2:  # Custom command
                    name = cmd_name_entry.get_text().strip()
                    exec_cmd = cmd_exec_entry.get_text().strip()
                    icon = cmd_icon_entry.get_text().strip()
                    if name and exec_cmd:
                        fav = {
                            'name': name,
                            'exec': exec_cmd,
                            'icon': icon if icon else 'application-x-executable'
                        }
                
                # Save if a valid favorite object was created
                if fav:
                    if 'favorites' not in self.config:
                        self.config['favorites'] = []
                    self.config['favorites'].append(fav)
                    self.config_manager.save_config(self.config)
                    self.load_favorites_list() # Refresh the list in the configurator
            
            dialog.destroy()
            
    def on_edit_favorite_clicked(self, button, fav_original):
        """Show dialog to edit an existing favorite"""
        dialog = Gtk.Dialog(
            title=TR.get('Edit Favorite', 'Edit Favorite'),
            parent=self,
            flags=0
        )
        dialog.add_buttons(
            TR['Cancel'], Gtk.ResponseType.CANCEL,
            TR.get('Save', 'Save'), Gtk.ResponseType.OK
        )
        dialog.set_default_size(500, 300)
        
        content = dialog.get_content_area()
        content.set_spacing(10)
        content.set_border_width(10)
        
        # Name
        content.pack_start(Gtk.Label(label=TR.get('Name:', 'Name:'), halign=Gtk.Align.START), False, False, 0)
        name_entry = Gtk.Entry()
        name_entry.set_text(fav_original.get('name', ''))
        content.pack_start(name_entry, False, False, 0)
        
        # Command with browse button
        content.pack_start(Gtk.Label(label=TR.get('Command:', 'Command:'), halign=Gtk.Align.START), False, False, 0)
        
        cmd_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        exec_entry = Gtk.Entry()
        exec_entry.set_text(fav_original.get('exec', ''))
        cmd_hbox.pack_start(exec_entry, True, True, 0)
        
        # Browse button to select executable file
        cmd_browse_button = Gtk.Button(label="📂")
        cmd_browse_button.set_tooltip_text(TR.get('Browse command', 'Browse command'))
        cmd_browse_button.connect("clicked", self.on_browse_file, exec_entry, TR.get('Select command', 'Select command'))
        cmd_hbox.pack_start(cmd_browse_button, False, False, 0)
        
        content.pack_start(cmd_hbox, False, False, 0)
        
        # Icon with browse buttons
        content.pack_start(Gtk.Label(label=TR.get('Icon (optional):', 'Icon (optional):'), halign=Gtk.Align.START), False, False, 0)
        
        icon_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        
        icon_entry = Gtk.Entry()
        icon_entry.set_text(fav_original.get('icon', ''))
        icon_hbox.pack_start(icon_entry, True, True, 0)
        
        # Icon browse button
        icon_browse_button = Gtk.Button(label="📂")
        icon_browse_button.set_tooltip_text(TR.get('Browse icon', 'Browse icon'))
        icon_browse_button.connect("clicked", self.on_browse_icon_clicked, icon_entry)
        icon_hbox.pack_start(icon_browse_button, False, False, 0)
        
        content.pack_start(icon_hbox, False, False, 0)
        
        dialog.show_all()
        response = dialog.run()
        
        if response == Gtk.ResponseType.OK:
            name = name_entry.get_text().strip()
            exec_cmd = exec_entry.get_text().strip()
            icon = icon_entry.get_text().strip()
            
            if name and exec_cmd:
                # Remove old favorite
                if 'favorites' in self.config and fav_original in self.config['favorites']:
                    self.config['favorites'].remove(fav_original)
                
                # Add updated favorite
                fav_updated = {
                    'name': name,
                    'exec': exec_cmd,
                    'icon': icon if icon else 'application-x-executable'
                }
                
                if 'favorites' not in self.config:
                    self.config['favorites'] = []
                
                self.config['favorites'].append(fav_updated)
                self.config_manager.save_config(self.config)
                self.load_favorites_list()
                print(f"Favorite updated: {fav_updated}")
        
        dialog.destroy()            
        
    def get_desktop_files(self):
        """Get list of .desktop files from the system"""
        desktop_files = []
        search_paths = [
            '/usr/share/applications',
            '/usr/local/share/applications',
            os.path.expanduser('~/.local/share/applications')
        ]
        
        for path in search_paths:
            if os.path.exists(path):
                for file in os.listdir(path):
                    if file.endswith('.desktop'):
                        desktop_files.append(os.path.join(path, file))
        
        return desktop_files
    
    def on_browse_directory(self, button, entry):
            """Open directory selector with file manager button"""
            dialog = Gtk.FileChooserDialog(
                title=TR.get('Select Directory', 'Select Directory'),
                parent=self,
                action=Gtk.FileChooserAction.SELECT_FOLDER
            )
            dialog.add_buttons(
                TR['Cancel'], Gtk.ResponseType.CANCEL,
                TR['Select'], Gtk.ResponseType.OK
            )
            
            # NEW: Button to open file manager
            file_manager_button = Gtk.Button(label="📂 " + TR.get('Open File Manager', 'Open File Manager'))
            file_manager_button.connect("clicked", self.on_open_file_manager_clicked)
            dialog.get_action_area().pack_start(file_manager_button, False, False, 0)
            dialog.get_action_area().reorder_child(file_manager_button, 0)
            
            response = dialog.run()
            if response == Gtk.ResponseType.OK:
                entry.set_text(dialog.get_filename())
            
            dialog.destroy()
            
    def on_browse_icon_clicked(self, button, entry):
            """Open dialog to select an icon file"""
            dialog = Gtk.FileChooserDialog(
                title=TR.get('Select Icon', 'Select Icon'),
                parent=self,
                action=Gtk.FileChooserAction.OPEN
            )
            dialog.add_buttons(
                TR['Cancel'], Gtk.ResponseType.CANCEL,
                TR['Select'], Gtk.ResponseType.OK
            )
            
            # Filter for image files
            filter_images = Gtk.FileFilter()
            filter_images.set_name(TR.get('Image files', 'Image files'))
            filter_images.add_mime_type('image/png')
            filter_images.add_mime_type('image/svg+xml')
            filter_images.add_mime_type('image/x-icon')
            filter_images.add_pattern('*.png')
            filter_images.add_pattern('*.svg')
            filter_images.add_pattern('*.ico')
            filter_images.add_pattern('*.xpm')
            dialog.add_filter(filter_images)
            
            # Filter for all files
            filter_all = Gtk.FileFilter()
            filter_all.set_name(TR.get('All files', 'All files'))
            filter_all.add_pattern('*')
            dialog.add_filter(filter_all)
            
            # Set initial folder to /usr/share/pixmaps or /usr/share/icons
            if os.path.exists('/usr/share/pixmaps'):
                dialog.set_current_folder('/usr/share/pixmaps')
            elif os.path.exists('/usr/share/icons'):
                dialog.set_current_folder('/usr/share/icons')
            
            # File manager button
            file_manager_button = Gtk.Button(label="📂 " + TR.get('Open File Manager', 'Open File Manager'))
            file_manager_button.connect("clicked", self.on_open_file_manager_clicked)
            dialog.get_action_area().pack_start(file_manager_button, False, False, 0)
            dialog.get_action_area().reorder_child(file_manager_button, 0)
            
            response = dialog.run()
            if response == Gtk.ResponseType.OK:
                selected_file = dialog.get_filename()
                entry.set_text(selected_file)
            
            dialog.destroy()            
            
    def on_open_file_manager_clicked(self, button):
            """Open the system file manager"""
            import subprocess
            # Detect available file manager
            file_managers = ['rox', 'pcmanfm', 'thunar', 'nautilus', 'dolphin', 'nemo']
            
            for fm in file_managers:
                try:
                    subprocess.Popen([fm], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    print(f"✅ Opening {fm}")
                    return
                except FileNotFoundError:
                    continue
            
            # If none work, try with xdg-open
            try:
                subprocess.Popen(['xdg-open', os.path.expanduser('~')], 
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception as e:
                print(f"❌ Could not open file manager: {e}")            
    
    def add_favorite(self, fav):
        """Add a favorite to the configuration"""
        if 'favorites' not in self.config:
            self.config['favorites'] = []
        
        self.config['favorites'].append(fav)
        self.config_manager.save_config(self.config)
        self.load_favorites_list()
        print(f"Favorite added: {fav}")
    
    def on_delete_favorite_clicked(self, button, fav):
        """Delete a favorite"""
        if 'favorites' in self.config and fav in self.config['favorites']:
            self.config['favorites'].remove(fav)
            self.config_manager.save_config(self.config)
            self.load_favorites_list()
            print(f"Favorite removed: {fav}")                             
        
    def on_browse_file(self, button, entry, dialog_title):
            """Open dialog to select a file with file manager"""
            dialog = Gtk.FileChooserDialog(
                title=dialog_title,
                parent=self,
                action=Gtk.FileChooserAction.OPEN
            )
            dialog.add_buttons(
                TR['Cancel'], Gtk.ResponseType.CANCEL,
                TR['Select'], Gtk.ResponseType.OK
            )
            
            # NEW: Button to open file manager
            file_manager_button = Gtk.Button(label="📂 " + TR.get('Open File Manager', 'Open File Manager'))
            file_manager_button.connect("clicked", self.on_open_file_manager_clicked)
            dialog.get_action_area().pack_start(file_manager_button, False, False, 0)
            dialog.get_action_area().reorder_child(file_manager_button, 0)
            
            response = dialog.run()
            if response == Gtk.ResponseType.OK:
                selected_file = dialog.get_filename()
                entry.set_text(selected_file)
            
            dialog.destroy()
        

    def update_tray_widgets_sensitivity(self):
        """Actualizar la visibilidad de los widgets según el tipo de tray seleccionado"""
        tray_type = self.config.get('tray', {}).get('type', 'jwm')
        
        # Mostrar solo la configuración correspondiente al tipo seleccionado
        self.jwm_label.set_visible(tray_type == 'jwm')
        self.entry_jwmrc_tray.set_visible(tray_type == 'jwm')
        
        self.tint2_label.set_visible(tray_type == 'tint2')
        self.entry_tint2rc.set_visible(tray_type == 'tint2')
        
        self.xfce_label.set_visible(tray_type == 'xfce')
        self.entry_xfce_panel.set_visible(tray_type == 'xfce')    
        
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
        value = int(spin_button.get_value())  # ← Definir la variable
        self.config[category][key] = value
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
