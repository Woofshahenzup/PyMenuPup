#!/usr/bin/env python3
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GdkPixbuf, Gio, GLib
import xml.etree.ElementTree as ET
import os
import subprocess
import sys
import shlex
import json
import urllib.parse
import locale
import warnings
import cairo

# Import the pango module using GObject Introspection
gi.require_version('Pango', '1.0')
from gi.repository import Pango

warnings.filterwarnings("ignore", category=DeprecationWarning)

# === 🌍 Diccionario de Traducción (Versión Completa) ===
LANG = {
    'en': {
        'Search applications...': 'Search applications...',
        'Shutdown': 'Shutdown',
        'Search in the web': 'Search in the web',
        'Pymenu config': 'Pymenu config',
        'Select avatar': 'Select avatar',
        'Terminal': 'Terminal',
        'Terminal emulator': 'Terminal emulator',
        'File Manager': 'File Manager',
        'File manager': 'File manager',
        'Firefox': 'Firefox',
        'Web browser': 'Web browser',
        'DownloadsDir': 'Downloads',
        'MusicDir': 'Music',
        'VideosDir': 'Videos',
        'PicturesDir': 'Pictures',
        'DocumentsDir': 'Documents',
        'Open directory:': 'Open directory:',
        'Social Networks': 'Social Networks',
        'Hide social networks:': 'Hide social networks:',
        'Desktop': 'Desktop',
        'System': 'System',
        'Setup': 'Setup',
        'Utility': 'Utility',
        'Filesystem': 'Filesystem',
        'Graphic': 'Graphic',
        'Document': 'Document',
        'Business': 'Business',
        'Personal': 'Personal',
        'Network': 'Network',
        'Internet': 'Internet',
        'Multimedia': 'Multimedia',
        'Fun': 'Fun',
        'Help': 'Help',
        'Rectify': 'Rectify',
        'Leave': 'Leave',
        'Run': 'Run',
        'Create desktop shortcut': 'Create desktop shortcut'
    },
    'es': {
        'Search applications...': 'Buscar aplicaciones...',
        'Shutdown': 'Apagar',
        'Search in the web': 'Buscar en la web',
        'Pymenu config': 'Configurar Pymenu',
        'Select avatar': 'Seleccione avatar',
        'Terminal': 'Terminal',
        'Terminal emulator': 'Emulador de terminal',
        'File Manager': 'Gestor de Archivos',
        'File manager': 'Gestor de archivos',
        'Firefox': 'Firefox',
        'Web browser': 'Navegador web',
        'DownloadsDir': 'Descargas',
        'MusicDir': 'Música',
        'VideosDir': 'Videos',
        'DocumentsDir': 'Documentos',
        'PicturesDir': 'Imágenes',
        'Open directory:': 'Abrir directorio:',
        'Social Networks': 'Redes Sociales', 
        'Hide social networks:': 'Ocultar redes sociales:',
        'Desktop': 'Escritorio',
        'System': 'Sistema',
        'Setup': 'Configuración',
        'Utility': 'Utilidades',
        'Filesystem': 'Archivos',
        'Graphic': 'Gráficos',
        'Document': 'Documentos',
        'Business': 'Oficina',
        'Personal': 'Personal',
        'Network': 'Red',
        'Internet': 'Internet',
        'Multimedia': 'Multimedia',
        'Fun': 'Juegos',
        'Help': 'Ayuda',
        'Rectify': 'Rectificar',
        'Leave': 'Salir',
        'Run': 'Ejecutar',
        'Create desktop shortcut': 'Crear acceso en escritorio'
    }
}

def get_translation_texts():
    try:
        sys_locale = locale.getlocale()
        lang_code = sys_locale[0].split('_')[0] if sys_locale[0] else 'en'
        return LANG.get(lang_code, LANG['en'])
    except Exception:
        return LANG['en']

TR = get_translation_texts()

PROFILE_PIC = "/root/.face"
PROFILE_MANAGER = "/usr/local/bin/ProfileManager.py"
SHUTDOWN_CMD = "/usr/local/bin/apagado-avatar.py"
CONFIG_FILE = "/root/.config/pymenu.json"

# === Funciones Auxiliares ===

def open_directory(path):
    expanded_path = os.path.expanduser(path)
    if not os.path.exists(expanded_path):
        try:
            os.makedirs(expanded_path, exist_ok=True)
        except Exception as e:
            print(f"Error al crear carpeta {expanded_path}: {e}")
            return 
    try:
        subprocess.Popen(["xdg-open", expanded_path],
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"Error al abrir directorio {expanded_path}: {e}")

def apply_circular_mask(pixbuf):
    try:
        width = pixbuf.get_width()
        height = pixbuf.get_height()
        size = min(width, height)
        
        if not pixbuf.get_has_alpha():
            pixbuf = pixbuf.add_alpha(True, 0, 0, 0)
        
        if width != height or width != size:
            pixbuf = pixbuf.scale_simple(size, size, GdkPixbuf.InterpType.BILINEAR)
            width = height = size
        
        mask_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
        mask_cr = cairo.Context(mask_surface)
        mask_cr.set_source_rgba(0, 0, 0, 0)
        mask_cr.paint()
        
        center_x = size / 2.0
        center_y = size / 2.0
        radius = size / 2.0
        
        mask_cr.arc(center_x, center_y, radius, 0, 2 * 3.141592653589793)
        mask_cr.set_source_rgba(1, 1, 1, 1)
        mask_cr.fill()
        
        original_surface = Gdk.cairo_surface_create_from_pixbuf(pixbuf, 0, None)
        final_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
        final_cr = cairo.Context(final_surface)
        
        final_cr.set_source_surface(original_surface, 0, 0)
        final_cr.paint()
        
        final_cr.set_source_surface(mask_surface, 0, 0)
        final_cr.set_operator(cairo.OPERATOR_DEST_IN)
        final_cr.paint()
        
        new_pixbuf = Gdk.pixbuf_get_from_surface(final_surface, 0, 0, size, size)
        return new_pixbuf if new_pixbuf else pixbuf
    except Exception as e:
        print(f"Error applying circular mask: {e}")
        return pixbuf

# === Config Manager ===

class ConfigManager:
    def __init__(self, config_file=CONFIG_FILE):
        self.config_file = config_file
        self.config = self.load_config()

    def get_default_config(self):
        return {
            "window": {
                "width": 630,
                "height": 650,
                "decorated_window": False,
                "hide_header": False, 
                "hide_quick_access": True,
                "hide_social_networks": True,
                "hide_category_text": False,
                "halign": "center",
                "icon_size": 32,
                "category_icon_size": 16,
                "profile_pic_size": 128,
                "profile_pic_shape": "square" 
            },
            "font": {
                "family": "Terminess Nerd Font Propo",
                "size_categories": 15000,
                "size_names": 14000,
                "size_header": 16000
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
                "categories_background": "rgba(0,0,0,0.6)",
            },
            "paths": {
                "profile_pic": "/root/.face",
                "profile_manager": "/usr/local/bin/ProfileManager.py",
                "shutdown_cmd": "/usr/local/bin/apagado-avatar.py",
                "jwmrc_tray": "/root/.jwmrc-tray",          
                "tint2rc": "/root/.config/tint2/tint2rc"    
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
        except Exception as e:
            print(f"Error loading config: {e}. Using defaults.")
            return self.get_default_config()
    
    def save_config(self, config_data):
        config_dir = os.path.dirname(self.config_file)
        if not os.path.exists(config_dir):
            os.makedirs(config_dir, exist_ok=True)
        with open(self.config_file, 'w') as f:
            json.dump(config_data, f, indent=4)

# === Openbox Menu Parser (Wayland/LabWC compatible) ===

class OpenboxMenuParser:
    def __init__(self, menu_file="/root/.config/labwc/menu.xml"):
        self.menu_file = menu_file
        self.applications = {}
        # Rutas extendidas para iconos (Estilo globicons)
        self.icon_paths = [
            "/usr/local/lib/X11/pixmaps",
            "/usr/share/pixmaps",
            "/usr/share/icons/hicolor/48x48/apps",
            "/usr/share/icons/hicolor/32x32/apps",
            "/usr/share/icons/hicolor/64x64/apps",
            "/usr/share/icons/hicolor/128x128/apps",
            "/usr/share/pixmaps/puppy",
            "/usr/local/share/pixmaps"
        ]
        self.tray_config = {
            'height': 30,
            'width': 1300,
            'valign': 'bottom',
            'halign': 'center',
            'layer': 'above',
            'autohide': 'off'
        }
        
    def parse_tray_config(self):
        return self.tray_config
            
    def parse_jwm_menu(self):
        try:
            if not os.path.exists(self.menu_file):
                print(f"Menu file not found: {self.menu_file}")
                return self.get_fallback_applications()
    
            tree = ET.parse(self.menu_file)
            root = tree.getroot()
            applications = {}
    
            for menu in root.findall('.//menu'):
                label = menu.get('label')
                menu_id = menu.get('id')
                if not label and menu_id: continue
                apps = self.extract_items_from_menu(menu)
                if apps:
                    applications[label] = apps
    
            root_menu = root.find('.//menu[@id="root-menu"]')
            if root_menu is not None:
                for item in root_menu.findall('./item'):
                    label = item.get('label', '')
                    command = item.findtext('./action/command', '').strip()
                    icon = item.get('icon', '')
                    if not label or not command: continue
                    app_info = {
                        'Name': label,
                        'Exec': command,
                        'Icon': icon,
                        'Comment': label,
                        'Terminal': 'terminal' in command.lower(),
                        'Categories': []
                    }
                    if 'Help' in label:
                        applications['Help'] = applications.get('Help', []) + [app_info]
                    elif 'Leave' in label:
                        applications['Leave'] = applications.get('Leave', []) + [app_info]
    
            return applications if applications else self.get_fallback_applications()
        except Exception as e:
            print(f"Error parsing menu: {e}")
            return self.get_fallback_applications()

    def extract_items_from_menu(self, menu_element):
        programs = []
        for item in menu_element.findall('./item'):
            label = item.get('label')
            icon = item.get('icon', '')
            command = item.findtext('./action/command', '').strip()
            if label and command:
                app_info = {
                    'Name': label,
                    'Exec': command,
                    'Icon': icon,
                    'Comment': label,
                    'Terminal': 'terminal' in command.lower() or 'urxvt' in command.lower(),
                    'Categories': []
                }
                programs.append(app_info)
        return programs

    def get_fallback_applications(self):
        return {
            'System': [
                {'Name': 'Terminal', 'Exec': 'lxterminal', 'Icon': 'terminal', 'Comment': 'Terminal', 'Terminal': False},
                {'Name': 'File Manager', 'Exec': 'spacefm', 'Icon': 'folder', 'Comment': 'Files', 'Terminal': False},
            ],
            'Internet': [
                {'Name': 'Firefox', 'Exec': 'firefox', 'Icon': 'firefox', 'Comment': 'Browser', 'Terminal': False},
            ]
        }

# === Aplicación Principal ===

class ArcMenuLauncher(Gtk.Window):
    def __init__(self, icon_size=None, jwm_file=None, x=None, y=None):
        super().__init__(title="PyMenuPup")
        self.set_wmclass("pymenu", "PyMenuPup")
        self.config_manager = ConfigManager()
        self.config = self.config_manager.config
        self.icon_size = self.config['window'].get('icon_size', 32)
        
        self.parser = OpenboxMenuParser(jwm_file or "/root/.config/labwc/menu.xml")
        self.tray_config = self.parser.parse_tray_config()
        self.applications = self.parser.parse_jwm_menu()
        
        self.apps_flowbox = None
        self.categories_listbox = None
        self.search_entry = None
        self.profile_image = None
        self.icon_cache = {}
        
        self.current_category = "All"
        self.hover_timeout = None
        self.restore_timeout = None
        self.mouse_in_menu = False
        self.selected_category = None
        self.hovered_category = None
        self.selected_category_row = None
        self.context_menu_active = False
        
        self.pos_x = x
        self.pos_y = y
    
        screen = Gdk.Screen.get_default()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.set_visual(visual)
            self.set_app_paintable(True)
        
        self.apply_css()
        self.setup_window()
        self.create_interface()
        
        # Monitor de archivo de menú
        try:
            menu_path = self.parser.menu_file
            if menu_path and os.path.exists(menu_path):
                self.menu_file = Gio.File.new_for_path(menu_path)
                self.file_monitor = self.menu_file.monitor_file(Gio.FileMonitorFlags.NONE, None)
                self.file_monitor.connect("changed", self.on_jwm_file_changed)
        except Exception as e:
            print(f"Error monitoring menu: {e}")

        # Monitor del config file
        try:
            if os.path.exists(CONFIG_FILE):
                self.config_file_obj = Gio.File.new_for_path(CONFIG_FILE)
                self.config_monitor = self.config_file_obj.monitor_file(Gio.FileMonitorFlags.NONE, None)
                self.config_monitor.connect("changed", self.on_config_file_changed)
                print(f"Monitoring config file: {CONFIG_FILE}")
        except Exception as e:
            print(f"Error monitoring config: {e}")
            
            
        # 2. Inicializar aplicaciones y seleccionar la categoría "All"
        self.filter_applications("All") 
        if self.categories_listbox and self.categories_listbox.get_row_at_index(0):
            self.categories_listbox.select_row(self.categories_listbox.get_row_at_index(0))
            
    def filter_applications(self, category):
        """Filtra y muestra las aplicaciones en el flowbox según la categoría seleccionada."""
        if self.apps_flowbox:
            # 1. Limpiar el flowbox
            for child in self.apps_flowbox.get_children():
                self.apps_flowbox.remove(child)

            # 2. Determinar qué aplicaciones mostrar
            if category == "All":
                apps_to_show = self.applications.get("All", [])
            else:
                apps_to_show = self.applications.get(category, [])

            # 3. Mostrar las aplicaciones (sustituir 'pass' por su lógica real)
            for app_info in apps_to_show:
                if 'Name' in app_info and 'Exec' in app_info:
                    pass 

        print(f"DEBUG: Aplicaciones filtradas para la categoría: {category}") 

# El resto de la clase (def apply_css, def setup_window, etc.) debe seguir aquí.      



    def apply_css(self):
            """Loads and applies CSS from the configuration."""
            # Verificar si debe usar tema GTK
            use_gtk_theme = self.config['colors'].get('use_gtk_theme', False)
            
            if use_gtk_theme:
                # Si usa tema GTK, usar colores del tema del sistema
                css = """
                GtkWindow, GtkEventBox {
                    background-color: @theme_bg_color;
                    border-radius: 0px;
                    box-shadow: none;
                    border: none;
                }
                .menu-window {
                    background-color: @theme_bg_color;
                    border-radius: 14px;
                    box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.3);
                    border: 1px solid @theme_unfocused_fg_color;
                    padding: 5px 10px 10px 10px;
                }
                """
                print("Using GTK theme colors")
            else:
                # CSS personalizado original
                colors = self.config['colors']
                
                css = f"""
                GtkWindow, GtkEventBox {{
                    background-color: {colors['background']};
                    border-radius: 0px;
                    box-shadow: none;
                    border: none;
                }}
                .tooltip, tooltip, GtkTooltip {{
                    background-color: {colors['background']};
                    color: {colors['text_normal']};
                    border-radius: 8px;
                    padding: 10px 10px;
                    border: 1px solid {colors['border']};
                    box-shadow: 0px 2px 5px rgba(0, 0, 0, 0.2);
                }}   
                .menu-window {{
                    background-color: {colors['background']};
                    border-radius: 14px;
                    box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.3);
                    border: 1px solid {colors['border']};
                    padding: 5px 10px 10px 10px;
                }}
            
                listbox {{
                    padding: 2px;
                }}
                
                listbox row {{
                    background-color: {self.config['colors'].get('categories_background', 'rgba(0,0,0,0.4)')};
                    color: {self.config['colors']['text_normal']};
                    border-radius: 6px;
                    padding: 2px;
                    margin: 1px;
                    min-height: 26px;
                }}
            
                listbox row:selected {{
                    background-color: {colors['selected_background']};
                    color: {colors['selected_text']};
                }}
            
                listbox row:hover {{
                    background-color: {colors['hover_background']};
                }}
            
                button {{
                    border-radius: 8px;
                    padding: 2px 2px;
                    background-color: {colors['button_normal_background']};
                    color: {colors['button_text']};
                    border: none;
                }}
                .action-button {{
                    border-radius: 6px;
                    background-color: {colors['button_normal_background']};
                    color: {colors['text_normal']};
                    border: 1px solid {colors['button_normal_background']};
                }}
                .action-button:hover {{
                    background-color: {colors['hover_background']};
                }}
                
                listbox row.selected-category {{
                    background-color: {colors['selected_background']};
                    color: {colors['selected_text']};
                }}
            
                button:hover {{
                    background-color: {colors['hover_background']};
                }}       
                .search-box:focus {{
                background-color: {colors['button_normal_background']};
                color: {colors['text_normal']};
                border: 1px solid {colors['border']} ;
                border-radius: 8px;
                }}
                .app-box {{
                    min-width: {self.icon_size + 0}px;
                }}
                .category-list {{
                     background-color: {colors['categories_background']};
                     padding: 1px;
                     border-radius: 12px;
                }}
                menuitem {{
                    background-color: {colors['background']};
                    color: {colors['text_normal']};
                    border-radius: 8px;
                    padding: 10px 10px;
                    border: 1px solid {colors['border']};
                    box-shadow: 0px 2px 5px rgba(0, 0, 0, 0.2);
                }}
                
                menuitem:hover {{
                    background-color: {colors['hover_background']};
                    color: {colors['text_normal']};
                }}
                
                menuitem:selected {{
                    background-color: {colors['hover_background']};
                    color: {colors['text_normal']};
                }}
                .quick-access-button {{
                    padding: 5px;
                    margin: 2px;
                }}
                .quick-access-button:hover {{
                    background-color: {colors['hover_background']};
                }}
                #quick-access-icon {{
                    font-size: 18pt;
                }}
                .social-button {{
                    padding: 5px;
                    margin: 2px;
                    border-radius: 8px;
                    background-color: {colors['button_normal_background']};
                }}
                .social-button:hover {{
                    background-color: {colors['hover_background']};
                }}
                #social-icon {{
                    font-size: 16pt;
                    color: {colors['text_normal']};
                }}
                button.profile-circular-style {{
                    border-radius: 50%;
                    padding: 0; 
                    border: none;
                    min-width: 64px; 
                    min-height: 64px;
                }}
                
                button.profile-circular-style:hover {{
                    background-color: rgba(255, 255, 255, 0.1);
                    box-shadow: none;
                }}            
                """
                print("Using custom colors")
            
            style_provider = Gtk.CssProvider()
            style_provider.load_from_data(css.encode('utf-8'))
            Gtk.StyleContext.add_provider_for_screen(
                Gdk.Screen.get_default(),
                style_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )

    def on_jwm_file_changed(self, monitor, file, other_file, event_type):
        if event_type == Gio.FileMonitorEvent.CHANGES_DONE_HINT:
            self.applications = self.parser.parse_jwm_menu()
            for child in self.get_children():
                self.remove(child)
            self.create_interface()
            self.show_all()
            self.present()
            
    def on_config_file_changed(self, monitor, file, other_file, event_type):
            """Reload configuration and interface when config file changes"""
            if event_type == Gio.FileMonitorEvent.CHANGES_DONE_HINT:
                print("Config file changed, reloading...")
                old_use_gtk = self.config['colors'].get('use_gtk_theme', False)
                self.config = self.config_manager.load_config()
                new_use_gtk = self.config['colors'].get('use_gtk_theme', False)
                
                # Si cambió la opción de tema GTK, recargar interfaz completa
                if old_use_gtk != new_use_gtk:
                    print(f"GTK theme option changed from {old_use_gtk} to {new_use_gtk}")
                    GLib.idle_add(self.recreate_interface)
    
    def recreate_interface(self):
        """Recreate interface to apply new styles"""
        for child in self.get_children():
            self.remove(child)
        
        # Reaplicar CSS según configuración actualizada
        self.apply_css()
        
        self.create_interface()
        self.show_all()
        return False            

    def get_hostname(self):
        try:
            with open("/etc/hostname", "r") as f:
                return f.read().strip()
        except: return "Unknown"

    def get_os_info(self):
        os_name = "Unknown OS"
        try:
            if os.path.exists('/etc/os-release'):
                with open('/etc/os-release', 'r') as f:
                    for line in f:
                        if line.startswith('PRETTY_NAME='):
                            os_name = line.split('=', 1)[1].strip().strip('"')
                            break
            result = subprocess.run(['uname', '-r'], capture_output=True, text=True)
            kernel = result.stdout.strip() if result.returncode == 0 else "Unknown"
            return os_name, kernel
        except: return "Unknown OS", "Unknown"
                
    def calculate_menu_position(self):
        display = Gdk.Display.get_default()
        monitor = None
        if display:
            try: monitor = display.get_primary_monitor()
            except: pass
        if not monitor:
            # Fallback centrado
            sw = self.config['window'].get('width', 800)
            sh = self.config['window'].get('height', 600)
            return int((sw - 700)//2), int((sh - 650)//2)
    
        geometry = monitor.get_geometry()
        screen_width = geometry.width
        screen_height = geometry.height
        menu_width = self.config['window']['width']
        menu_height = self.config['window']['height']
    
        menu_halign = self.config['window'].get('halign', None)
        if menu_halign == 'left': x = 10
        elif menu_halign == 'right': x = screen_width - menu_width - 10
        else: x = (screen_width - menu_width) // 2
    
        tray_height = self.tray_config.get('height', 0)
        tray_valign = self.tray_config.get('valign', 'bottom')
    
        if tray_valign == 'top': y = tray_height
        elif tray_valign in ['bottom', 'buttom']: y = screen_height - tray_height - menu_height
        else: y = (screen_height - menu_height) // 2
    
        return int(max(0, min(x, screen_width - menu_width))), int(max(0, min(y, screen_height - menu_height)))

    def setup_window(self):
        win_size = self.config['window']
        self.set_default_size(win_size['width'], win_size['height'])
        
        if self.pos_x is not None and self.pos_y is not None:
            self.move(int(self.pos_x), int(self.pos_y))
        else:
            x, y = self.calculate_menu_position()
            self.move(x, y)
    
        self.set_resizable(False)
        self.set_decorated(False)
        self.set_app_paintable(True)
        self.set_type_hint(Gdk.WindowTypeHint.UTILITY)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.connect("key-press-event", self.on_key_press)
        self.connect("focus-out-event", self.on_focus_out)
        self.connect("button-press-event", self.on_button_press)

    def on_button_press(self, widget, event):
        if event.button == 2: # Middle click
            Gtk.main_quit()
            return True
        if event.button == 1 and (event.state & Gdk.ModifierType.MOD1_MASK):
            self.begin_move_drag(event.button, int(event.x_root), int(event.y_root), event.time)
            return True
        return False
 
    def on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            Gtk.main_quit()
            return True
        return False
    
    def on_focus_out(self, widget, event):
        if not self.context_menu_active:
            Gtk.main_quit()
        return False
                    
    def create_interface(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        main_box.get_style_context().add_class('menu-window')
        self.add(main_box)
        
        # 1. Header
        if not self.config['window'].get('hide_header', False):
            header_box = self.create_header()
            main_box.pack_start(header_box, False, False, 0)
            
        # 2. Acceso Rápido (Quick Access)
        if not self.config['window'].get('hide_quick_access', False):
            qa_container = self.create_quick_access_container()
            main_box.pack_start(qa_container, False, False, 0)
            main_box.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 0)
    
        # 3. Contenido Principal
        content_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        main_box.pack_start(content_box, True, True, 0)
        
        # A. Redes Sociales
        if not self.config['window'].get('hide_social_networks', False):
            social_sidebar = self.create_social_networks_sidebar()
            content_box.pack_start(social_sidebar, False, False, 0)
            content_box.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 0)
    
        # B. Categorías
        content_box.pack_start(self.create_categories_sidebar(), False, False, 0)
        content_box.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 0)
        
        # C. Aplicaciones
        content_box.pack_start(self.create_applications_area(), True, True, 0)
    
        main_box.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 0)
    
        # 4. Barra Inferior
        bottom_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        bottom_box.set_margin_top(6)
        bottom_box.set_margin_bottom(6)
        bottom_box.set_margin_start(10)
        bottom_box.set_margin_end(10)
    
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text(TR['Search applications...'])
        self.search_entry.connect("search-changed", self.on_search_changed)
        self.search_entry.set_size_request(200, 30)
        bottom_box.pack_start(self.search_entry, True, True, 0)
        
        # Botones inferiores
        self.add_action_button(bottom_box, "shutdown48", "󰤁", TR['Shutdown'], self.on_shutdown_clicked)
        self.add_action_button(bottom_box, "www48", "󰜏", TR['Search in the web'], self.on_browser_search_clicked)
        self.add_action_button(bottom_box, "configuration48", "", TR['Pymenu config'], self.on_config_clicked)
        
        main_box.pack_end(bottom_box, False, False, 0)
        self.show_all()
        GLib.timeout_add(100, lambda: self.search_entry.grab_focus())

    def add_action_button(self, box, icon_name, nerd_icon, tooltip, callback):
        btn = Gtk.Button()
        icon_path = self.find_icon_path(icon_name)
        if icon_path:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(icon_path, 20, 20)
            img = Gtk.Image.new_from_pixbuf(pixbuf)
        else:
            lbl = Gtk.Label()
            lbl.set_markup(f'<span font="Terminess Nerd Font Propo 16">{nerd_icon}</span>')
            img = lbl
        btn.add(img)
        btn.set_tooltip_text(tooltip)
        btn.connect("clicked", callback)
        box.pack_end(btn, False, False, 0)

    # === Header Logic ===
    def create_header(self):
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        header_box.set_margin_top(5); header_box.set_margin_bottom(5)
        header_box.set_margin_start(10); header_box.set_margin_end(10)
        
        # Perfil
        profile_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        profile_box.set_valign(Gtk.Align.CENTER)
        profile_btn = Gtk.Button()
        profile_btn.set_relief(Gtk.ReliefStyle.NONE)
        profile_btn.get_style_context().add_class('profile-button')
        
        if self.config['window'].get('profile_pic_shape', 'square') == 'circular':
            profile_btn.get_style_context().add_class('profile-circular-style')

        self.profile_image = Gtk.Image()
        profile_btn.add(self.profile_image)
        
        def load_profile():
            path = self.config['paths']['profile_pic']
            size = self.config['window'].get('profile_pic_size', 96)
            shape = self.config['window'].get('profile_pic_shape', 'square')
            try:
                pix = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, size, size, True)
                if shape == 'circular': pix = apply_circular_mask(pix)
                self.profile_image.set_from_pixbuf(pix)
            except:
                self.profile_image.set_from_icon_name("avatar-default", Gtk.IconSize.DIALOG)
        
        load_profile()
        profile_btn.connect("clicked", self.on_profile_clicked)
        profile_box.pack_start(profile_btn, False, False, 0)
        
        # Info Sistema
        sys_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        sys_box.set_valign(Gtk.Align.CENTER)
        os_name, kernel = self.get_os_info()
        host = self.get_hostname()
        
        font_desc = Pango.FontDescription(self.config['font']['family'])
        
        def mk_lbl(txt, color_key):
            l = Gtk.Label()
            c = self.config['colors'].get(color_key, '#cccccc')
            l.set_markup(f'<span color="{c}">{txt}</span>')
            l.override_font(font_desc)
            l.set_halign(Gtk.Align.START)
            l.set_ellipsize(Pango.EllipsizeMode.END)
            return l

        sys_box.pack_start(mk_lbl(f"<b>{os_name}</b>", 'text_header_os'), False, False, 0)
        sys_box.pack_start(mk_lbl(f" {kernel}", 'text_header_kernel'), False, False, 0)
        sys_box.pack_start(mk_lbl(f" {host}", 'text_header_hostname'), False, False, 0)
        
        # Layout
        layout = self.config['window'].get('header_layout', 'left')
        if layout == 'right':
            header_box.pack_start(sys_box, True, True, 0)
            header_box.pack_start(profile_box, False, False, 0)
        elif layout == 'center':
            sp1, sp2 = Gtk.Box(), Gtk.Box()
            header_box.pack_start(sp1, True, True, 0)
            header_box.pack_start(profile_box, False, False, 0)
            header_box.pack_start(sp2, True, True, 0)
            sys_box.set_halign(Gtk.Align.START)
            sp1.pack_start(sys_box, False, False, 0)
        else: # Left
            header_box.pack_start(profile_box, False, False, 0)
            header_box.pack_start(sys_box, True, True, 0)

        # Monitor de cambios en avatar
        try:
            f = Gio.File.new_for_path(self.config['paths']['profile_pic'])
            m = f.monitor_file(Gio.FileMonitorFlags.NONE, None)
            m.connect("changed", lambda *a: GLib.idle_add(load_profile))
        except: pass
        
        return header_box

    # === Quick Access & Social ===
    
    def create_quick_access_container(self):
        container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        container.set_margin_top(5); container.set_margin_bottom(5)
        container.set_margin_start(10); container.set_margin_end(10)
        
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
        box.set_halign(Gtk.Align.END)
        
        items = [('󰉍', 'DownloadsDir'), ('󰲂', 'DocumentsDir'), ('󰎆', 'MusicDir'), ('', 'VideosDir'), ('󰋩', 'PicturesDir')]
        
        for icon, key in items:
            btn = Gtk.Button()
            btn.set_relief(Gtk.ReliefStyle.NONE)
            btn.get_style_context().add_class('quick-access-button')
            path = f"~/{TR[key]}"
            lbl = Gtk.Label(label=icon)
            lbl.set_name("quick-access-icon")
            
            font = Pango.FontDescription("Terminess Nerd Font Propo 12")
            lbl.override_font(font)
            
            btn.add(lbl)
            btn.set_tooltip_text(TR[key])
            btn.connect("clicked", lambda b, p=path: open_directory(p))
            box.pack_start(btn, False, False, 0)
            
        container.pack_end(box, False, False, 0)
        return container

    def create_social_networks_sidebar(self):
        socials = [
            ('', 'YouTube', 'https://youtube.com', 'red'),
            ('', 'Facebook', 'https://facebook.com', '#3b5998'), 
            ('', 'Telegram', 'https://telegram.org', '#0088cc'),
            ('', 'Discord', 'https://discord.com', '#5865F2'),
            ('', 'Puppy Forum', 'https://forum.puppylinux.com', '#ffffff'),
            ('󰊢', 'Github', 'https://github.com', 'yellow'),
            ('', 'X', 'https://x.com', '#0788CA'),
            ('', 'Reddit', 'https://reddit.com', 'red'),
            ('', 'Whatsapp', 'https://web.whatsapp.com/', 'green'),
        ]
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        box.set_halign(Gtk.Align.CENTER)
        box.set_margin_top(5); box.set_margin_bottom(5)
        
        for icon, name, url, color in socials:
            btn = Gtk.Button()
            btn.set_relief(Gtk.ReliefStyle.NONE)
            btn.get_style_context().add_class('social-button')
            btn.set_size_request(40, 40)
            
            lbl = Gtk.Label()
            lbl.set_name("social-icon")
            lbl.set_markup(f'<span foreground="{color}">{icon}</span>')
            font = Pango.FontDescription("Terminess Nerd Font Propo 12")
            lbl.override_font(font)
            
            btn.add(lbl)
            btn.set_tooltip_text(name)
            btn.connect("clicked", lambda b, u=url: self.open_url(u))
            box.pack_start(btn, False, False, 0)
            
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.add(box)
        return scrolled

    def open_url(self, url):
        try:
            subprocess.Popen(["xdg-open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            Gtk.main_quit()
        except Exception as e:
            print(f"Error opening URL: {e}")

    # === Categories & Apps ===

    def create_categories_sidebar(self):
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_size_request(175, -1)
        
        self.categories_listbox = Gtk.ListBox()
        self.categories_listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.categories_listbox.connect("row-activated", self.on_category_clicked)
    
        # ICONOS ACTUALIZADOS PARA USAR GLOBICONS DE PUPPY
        category_icons = {
            'Desktop': 'pc48',
            'System': 'x48',
            'Setup': 'configuration48',
            'Utility': 'utility48',
            'Filesystem': 'home48',
            'Graphic': 'paint48',
            'Document': 'word48',
            'Business': 'spread48',
            'Personal': 'date48',
            'Network': 'connect48',
            'Internet': 'www48',
            'Multimedia': 'multimedia48',
            'Fun': 'games48',
            'Help': 'help48',
            'Rectify': 'save48',
            'Shutdown': 'shutdown48',
            'Leave': 'shutdown48'
        }
    
        preferred = ['Desktop', 'System', 'Setup', 'Utility', 'Filesystem', 
                     'Graphic', 'Document', 'Business', 'Personal', 
                     'Network', 'Internet', 'Multimedia', 'Fun', 'Help', 'Leave']
        
        excluded = self.config.get('categories', {}).get('excluded', [])
        added = set()
    
        for c in preferred:
            if c in self.applications and self.applications[c] and c not in excluded:
                self.add_category_row(c, category_icons.get(c, 'applications-other'))
                added.add(c)
        
        for c in sorted(self.applications.keys()):
            if c not in added and self.applications[c] and c not in excluded:
                self.add_category_row(c, category_icons.get(c, 'applications-other'))
    
        scrolled.add(self.categories_listbox)
        
        # Select first
        first = self.categories_listbox.get_row_at_index(0)
        if first:
            self.categories_listbox.select_row(first)
            cat = getattr(first, "category_name", None)
            self.selected_category = cat
            self.current_category = cat
            first.get_style_context().add_class("selected-category")
            self.selected_category_row = first
            self.show_category_applications(cat)
        
        return scrolled
    
    def add_category_row(self, category, icon_name):
        row = Gtk.ListBoxRow()
        row.category_name = category
        event_box = Gtk.EventBox()
        event_box.set_above_child(True)
        
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        box.set_property("margin", 2)

        icon_path = self.find_icon_path(icon_name)
        size = self.config['window'].get('category_icon_size', 24)
        
        if icon_path:
            try:
                pb = GdkPixbuf.Pixbuf.new_from_file_at_size(icon_path, size, size)
                icon = Gtk.Image.new_from_pixbuf(pb)
            except: icon = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.MENU)
        else:
            icon = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.MENU)
            
        if self.config['window'].get('hide_category_text', False):
            # Centered icon only
            cbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            cbox.pack_start(Gtk.Box(), True, True, 0)
            cbox.pack_start(icon, False, False, 0)
            cbox.pack_start(Gtk.Box(), True, True, 0)
            box.pack_start(cbox, True, True, 0)
            row.set_tooltip_text(TR.get(category, category))
        else:
            box.pack_start(icon, False, False, 0)
            label = Gtk.Label()
            font = Pango.FontDescription(self.config['font']['family'])
            font.set_size(self.config['font']['size_categories'])
            label.override_font(font)
            translated = TR.get(category, category)
            label.set_markup(f"<span foreground='{self.config['colors']['text_normal']}'>{translated}</span>")
            label.set_halign(Gtk.Align.START)
            box.pack_start(label, True, True, 5)

        event_box.add(box)
        row.add(event_box)
        
        event_box.add_events(Gdk.EventMask.ENTER_NOTIFY_MASK | Gdk.EventMask.LEAVE_NOTIFY_MASK)
        event_box.connect("enter-notify-event", lambda w, e: self.on_category_hover_enter(row, e))
        event_box.connect("leave-notify-event", lambda w, e: self.on_category_hover_leave(row, e))
        
        self.categories_listbox.add(row)

    def on_category_hover_enter(self, row, event):
        cat = getattr(row, "category_name", None)
        if not cat or cat == self.current_category: return False
        if self.hover_timeout: GLib.source_remove(self.hover_timeout)
        if self.restore_timeout: GLib.source_remove(self.restore_timeout); self.restore_timeout = None
        
        self.hover_timeout = GLib.timeout_add(150, self._activate_hover_preview, cat)
        self.hovered_category = cat
        return False

    def on_category_hover_leave(self, row, event):
        if self.hover_timeout: GLib.source_remove(self.hover_timeout); self.hover_timeout = None
        self.hovered_category = None
        return False

    def _activate_hover_preview(self, category):
        self.hover_timeout = None
        self.current_category = category
        self.show_category_applications(category)
        return False
    
    def restore_to_selected_category(self):
        self.restore_timeout = None
        if not self.mouse_in_menu:
            self.current_category = self.selected_category
            self.show_category_applications(self.selected_category)
        return False

    def on_category_clicked(self, listbox, row):
        if not row: return
        cat = getattr(row, "category_name", None)
        if cat:
            if self.hover_timeout: GLib.source_remove(self.hover_timeout); self.hover_timeout = None
            if self.selected_category_row: self.selected_category_row.get_style_context().remove_class("selected-category")
            row.get_style_context().add_class("selected-category")
            self.selected_category_row = row
            self.selected_category = cat
            self.current_category = cat
            self.show_category_applications(cat)

    def create_applications_area(self):
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        
        self.apps_flowbox = Gtk.FlowBox()
        self.apps_flowbox.set_valign(Gtk.Align.START)
        self.apps_flowbox.set_max_children_per_line(30)
        self.apps_flowbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.apps_flowbox.set_margin_start(10); self.apps_flowbox.set_margin_end(10)
        self.apps_flowbox.set_margin_top(10); self.apps_flowbox.set_margin_bottom(10)
        
        eventbox = Gtk.EventBox()
        eventbox.add(self.apps_flowbox)
        eventbox.add_events(Gdk.EventMask.ENTER_NOTIFY_MASK | Gdk.EventMask.LEAVE_NOTIFY_MASK)
        eventbox.connect("enter-notify-event", lambda w,e: setattr(self, 'mouse_in_menu', True))
        eventbox.connect("leave-notify-event", self.on_menu_leave)
        
        self.apps_flowbox.connect("key-press-event", self.on_apps_key_press)
        scrolled.add(eventbox)
        return scrolled
    
    def on_menu_leave(self, widget, event):
        self.mouse_in_menu = False
        if not self.restore_timeout:
            self.restore_timeout = GLib.timeout_add(150, self.restore_to_selected_category)
        return False

    def on_app_enter(self, widget, event):
        """Fix for flickering: When entering a button, we are still in the menu"""
        self.mouse_in_menu = True
        if self.restore_timeout:
            GLib.source_remove(self.restore_timeout)
            self.restore_timeout = None
        return False

    def create_app_button(self, app_info):
        btn = Gtk.Button()
        btn.set_can_focus(True)
        btn.set_relief(Gtk.ReliefStyle.NONE)
        btn.connect("clicked", self.on_app_clicked, app_info)
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        box.set_margin_top(5); box.set_margin_bottom(5)
        box.set_margin_start(5); box.set_margin_end(5)
        
        icon = self.load_app_icon(app_info.get('Icon', 'application-x-executable'))
        box.pack_start(icon, False, False, 0)
        
        lbl = Gtk.Label(label=app_info['Name'])
        font = Pango.FontDescription(self.config['font']['family'])
        font.set_size(self.config['font']['size_names'])
        lbl.override_font(font)
        lbl.set_line_wrap(True)
        lbl.set_max_width_chars(12)
        lbl.set_lines(2)
        lbl.set_ellipsize(Pango.EllipsizeMode.END)
        lbl.set_justify(Gtk.Justification.CENTER)
        
        box.pack_start(lbl, False, False, 0)
        btn.add(box)
        btn.set_tooltip_text(app_info.get('Comment', app_info['Name']))
        btn.app_info = app_info
        
        # === FIX: Prevent flickering by telling parent we are still in menu ===
        btn.connect("enter-notify-event", self.on_app_enter)
        btn.connect("leave-notify-event", self.on_menu_leave)
        
        # Context Menu
        btn.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        btn.connect("button-press-event", lambda w, e: self.on_app_right_click(w, e, app_info))
        
        return btn

    def on_app_right_click(self, button, event, app_info):
        if event.button == 3:
            self.context_menu_active = True
            menu = Gtk.Menu()
            
            i_run = Gtk.MenuItem(label=TR['Run'])
            i_run.connect("activate", lambda w: self.on_app_clicked(button, app_info))
            menu.append(i_run)
            
            menu.append(Gtk.SeparatorMenuItem())
            
            i_link = Gtk.MenuItem(label=TR['Create desktop shortcut'])
            i_link.connect("activate", lambda w: self.create_desktop_shortcut(app_info))
            menu.append(i_link)
            
            menu.connect("deactivate", lambda m: setattr(self, 'context_menu_active', False))
            menu.show_all()
            menu.popup_at_pointer(event)
            return True
        return False

    def load_app_icon(self, icon_name):
        if not icon_name: icon_name = "application-x-executable"
        cache_key = f"{icon_name}_{self.icon_size}"
        if cache_key in self.icon_cache: return self.icon_cache[cache_key]

        # 1. Try Path directly
        path = self.find_icon_path(icon_name)
        if path:
            try:
                pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, self.icon_size, self.icon_size, True)
                img = Gtk.Image.new_from_pixbuf(pb)
                self.icon_cache[cache_key] = img
                return img
            except: pass
            
        # 2. Try Theme
        try:
            theme = Gtk.IconTheme.get_default()
            info = theme.lookup_icon(icon_name, self.icon_size, Gtk.IconLookupFlags.FORCE_SIZE)
            if info:
                img = Gtk.Image.new_from_pixbuf(info.load_icon())
                self.icon_cache[cache_key] = img
                return img
        except: pass
        
        # 3. Fallback
        img = Gtk.Image.new_from_icon_name("application-x-executable", Gtk.IconSize.BUTTON)
        self.icon_cache[cache_key] = img
        return img

    def find_icon_path(self, icon_name):
        if os.path.isabs(icon_name) and os.path.exists(icon_name): return icon_name
        
        exts = ['.png', '.svg', '.xpm', '.ico', '.jpg', '', '.jpeg']
        for path in self.parser.icon_paths:
            if not os.path.exists(path): continue
            
            # Exact match + ext
            for e in exts:
                full = os.path.join(path, icon_name + e)
                if os.path.exists(full): return full
                
            # Partial match (glob-like)
            try:
                for f in os.listdir(path):
                    if f.startswith(icon_name) and any(f.endswith(e) for e in exts if e):
                        return os.path.join(path, f)
            except: pass
        return None

    def show_category_applications(self, category):
        if not self.apps_flowbox: return
        self.current_category = category
        for c in self.apps_flowbox.get_children(): c.destroy()
        
        if category in self.applications:
            GLib.idle_add(self.load_applications_batch, [(category, self.applications[category])], 0)
        self.apps_flowbox.show_all()

    def load_applications_batch(self, data, start_idx, batch=15):
        cnt = 0
        for cat, apps in data:
            for i, app in enumerate(apps[start_idx:], start_idx):
                if cnt >= batch:
                    GLib.idle_add(self.load_applications_batch, [(cat, apps)], i)
                    return False
                self.apps_flowbox.add(self.create_app_button(app))
                cnt += 1
        self.apps_flowbox.show_all()
        return False

    def on_search_changed(self, entry):
        txt = entry.get_text().lower()
        for c in self.apps_flowbox.get_children(): c.destroy()
        
        if not txt:
            if self.current_category: self.show_category_applications(self.current_category)
            return
            
        for cat, apps in self.applications.items():
            for app in apps:
                if txt in app['Name'].lower() or txt in app.get('Comment','').lower():
                    self.apps_flowbox.add(self.create_app_button(app))
        self.apps_flowbox.show_all()

    def on_apps_key_press(self, widget, event):
        key = event.keyval
        children = self.apps_flowbox.get_children()
        if not children: return False
        
        sel = self.apps_flowbox.get_selected_children()
        curr = children.index(sel[0]) if sel else -1
        cols = 1
        if len(children) > 1 and children[1].get_allocation().y == children[0].get_allocation().y:
            cols = len([c for c in children if c.get_allocation().y == children[0].get_allocation().y])
            
        new_idx = curr
        if key == Gdk.KEY_Down: new_idx = min(len(children)-1, curr + cols)
        elif key == Gdk.KEY_Up: new_idx = max(0, curr - cols)
        elif key == Gdk.KEY_Right: new_idx = min(len(children)-1, curr + 1)
        elif key == Gdk.KEY_Left: new_idx = max(0, curr - 1)
        elif key == Gdk.KEY_Return and sel:
            self.on_app_clicked(sel[0].get_child(), sel[0].get_child().app_info)
            return True
            
        if new_idx != curr and 0 <= new_idx < len(children):
            self.apps_flowbox.select_child(children[new_idx])
            children[new_idx].grab_focus()
            return True
        return False

    def on_app_clicked(self, btn, app_info):
        try:
            GLib.timeout_add(50, Gtk.main_quit)
            cmd = app_info['Exec']
            parts = shlex.split(cmd)
            clean = [p for p in parts if not any(p.startswith(x) for x in ['%f','%F','%u','%U','%i','%c'])]
            
            if not clean: return
            
            if app_info.get('Terminal', False):
                subprocess.Popen(['lxterminal', '-e'] + clean, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                subprocess.Popen(clean, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"Launching: {clean}")
        except Exception as e:
            print(f"Error launching: {e}")

    def create_desktop_shortcut(self, app_info):
        try:
            desk_dir = os.path.expanduser('~/Desktop')
            if not os.path.isdir(desk_dir): desk_dir = os.path.expanduser('~/Escritorio')
            os.makedirs(desk_dir, exist_ok=True)
            
            name = app_info.get('Name','app').replace('/','-').replace(' ','_')
            fname = os.path.join(desk_dir, f"{name}.desktop")
            
            parts = shlex.split(app_info['Exec'])
            clean_cmd = ' '.join([p for p in parts if not any(p.startswith(x) for x in ['%f','%F','%u','%U'])])
            
            icon = self.find_icon_path(app_info.get('Icon','')) or app_info.get('Icon','')
            
            content = f"""[Desktop Entry]
Type=Application
Version=1.0
Name={app_info.get('Name')}
Comment={app_info.get('Comment','')}
Exec={clean_cmd}
Icon={icon}
Terminal={'true' if app_info.get('Terminal') else 'false'}
Categories=Application;
"""
            with open(fname, 'w') as f: f.write(content)
            os.chmod(fname, 0o755)
            print(f"Shortcut created: {fname}")
        except Exception as e:
            print(f"Error creating shortcut: {e}")

    def on_browser_search_clicked(self, btn):
        txt = self.search_entry.get_text().strip()
        if not txt: return
        url = f"https://www.google.com/search?q={urllib.parse.quote_plus(txt)}"
        self.open_url(url)

    def on_profile_clicked(self, btn):
        GLib.timeout_add(50, Gtk.main_quit)
        pm = self.config['paths']['profile_manager']
        try: subprocess.Popen([pm], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except: subprocess.Popen(["python3", pm], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def on_config_clicked(self, btn):
        GLib.timeout_add(50, Gtk.main_quit)
        subprocess.Popen(["python3", "/usr/local/bin/pymenu-config.py"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def on_shutdown_clicked(self, btn):
        GLib.timeout_add(50, Gtk.main_quit)
        cmd = self.config['paths']['shutdown_cmd']
        try: subprocess.Popen([cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except: subprocess.Popen(["python3", cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def main():
    icon_size = None
    jwm_file = None
    x, y = None, None
    
    if len(sys.argv) >= 3:
        try:
            x, y = int(sys.argv[1]), int(sys.argv[2])
        except:
            jwm_file = sys.argv[1]
            try: icon_size = int(sys.argv[2])
            except: pass
    elif len(sys.argv) == 2:
        try: x = int(sys.argv[1])
        except: jwm_file = sys.argv[1]
    
    app = ArcMenuLauncher(icon_size, jwm_file, x, y)
    app.connect("destroy", Gtk.main_quit)
    app.show_all()
    Gtk.main()

if __name__ == "__main__":
    main()