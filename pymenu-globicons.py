#!/usr/bin/env python3
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GdkPixbuf, Gio, GLib
import xml.etree.ElementTree as ET
import os
import cairo
import subprocess
import sys
import shlex
import json
import urllib.parse
import locale
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

# === 🌍 Sistema de Traducción ===
try:
    sys.path.insert(0, '/usr/local/bin')
    from pymenupuplang import TranslationManager
except ModuleNotFoundError:
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

# Generar CATEGORY_MAP automáticamente desde archivos .lang
CATEGORY_MAP = TR.get_category_map()

# Import the pango module using GObject Introspection
gi.require_version('Pango', '1.0')
from gi.repository import Pango

CONFIG_FILE = os.path.expanduser("~/.config/pymenu.json")


def open_directory(path):
    """
    Intenta expandir la ruta de acceso rápido (~) y abrirla. 
    Si no existe, la crea antes de intentar abrir.
    """
    # 1. Expande el caracter '~' a la ruta completa del usuario.
    expanded_path = os.path.expanduser(path)
    
    # 2. Verifica si la carpeta existe.
    if not os.path.exists(expanded_path):
        try:
            # Si no existe, la crea con el nombre traducido (ej. 'Descargas')
            os.makedirs(expanded_path, exist_ok=True)
            print(f"Carpeta creada: {expanded_path}")
        except Exception as e:
            print(f"Error al crear la carpeta {expanded_path}: {e}")
            return 
    
    # 3. Abre la carpeta.
    try:
        subprocess.Popen(["xdg-open", expanded_path],
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"Error al intentar abrir el directorio {expanded_path}: {e}")
                

class ConfigManager:
    """Manages reading and writing the application's JSON configuration."""
    def __init__(self, config_file=CONFIG_FILE):
        self.config_file = config_file
        self.config = self.load_config()

    def get_default_config(self):
        """Return the default configuration matching the current script's aesthetics."""
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
                "hide_hostname": False
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
        """Load configuration from the JSON file or create a default one."""
        if not os.path.exists(self.config_file):
            print(f"Config file not found. Creating default config at {self.config_file}")
            self.save_config(self.get_default_config())
            return self.get_default_config()
        
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                # Merge with default config to ensure all keys exist
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
            print(f"Error loading config file: {e}. Using default settings.")
            return self.get_default_config()
    
    def save_config(self, config_data):
        """Save configuration to the JSON file."""
        config_dir = os.path.dirname(self.config_file)
        if not os.path.exists(config_dir):
            os.makedirs(config_dir, exist_ok=True)
            
        with open(self.config_file, 'w') as f:
            json.dump(config_data, f, indent=4)
            
def detect_window_manager():
    """
    Detecta el window manager desde /etc/windowmanager.
    Retorna 'openbox' si encuentra openbox-session, 'jwm' en cualquier otro caso.
    """
    try:
        with open('/etc/windowmanager', 'r') as f:
            wm_content = f.read().strip().lower()
            if 'openbox-session' in wm_content or 'openbox' in wm_content:
                return 'openbox'
    except FileNotFoundError:
        print("Archivo /etc/windowmanager no encontrado, asumiendo JWM")
    except Exception as e:
        print(f"Error leyendo /etc/windowmanager: {e}")
    
    return 'jwm'

def apply_circular_mask(pixbuf):
    """Aplica una máscara circular a un GdkPixbuf, mostrando la imagen dentro del círculo."""
    try:
        width = pixbuf.get_width()
        height = pixbuf.get_height()
        
        # Determinar el tamaño del cuadrado más pequeño
        size = min(width, height)
        
        # 1. Asegurar que el pixbuf tiene canal alfa
        if not pixbuf.get_has_alpha():
            pixbuf = pixbuf.add_alpha(True, 0, 0, 0)
        
        # 2. Escalar a un cuadrado perfecto si no lo es
        if width != height or width != size:
            pixbuf = pixbuf.scale_simple(size, size, GdkPixbuf.InterpType.BILINEAR)
            width = height = size
        
        # 3. Crear una superficie temporal para la máscara
        # Esta será completamente negra (transparente)
        mask_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
        mask_cr = cairo.Context(mask_surface)
        
        # Llenar de negro transparente
        mask_cr.set_source_rgba(0, 0, 0, 0)
        mask_cr.paint()
        
        # Dibujar un círculo blanco opaco en la máscara
        # donde queremos que se vea la imagen
        center_x = size / 2.0
        center_y = size / 2.0
        radius = size / 2.0
        
        mask_cr.arc(center_x, center_y, radius, 0, 2 * 3.141592653589793)
        mask_cr.set_source_rgba(1, 1, 1, 1)  # Blanco opaco
        mask_cr.fill()
        
        # 4. Convertir el pixbuf a una superficie Cairo
        original_surface = Gdk.cairo_surface_create_from_pixbuf(pixbuf, 0, None)
        
        # 5. Crear la superficie final
        final_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
        final_cr = cairo.Context(final_surface)
        
        # Dibujar la imagen original
        final_cr.set_source_surface(original_surface, 0, 0)
        final_cr.paint()
        
        # Aplicar la máscara usando el operador IN
        # Esto mantiene solo la parte de la imagen dentro del círculo
        final_cr.set_source_surface(mask_surface, 0, 0)
        final_cr.set_operator(cairo.OPERATOR_DEST_IN)
        final_cr.paint()
        
        # 6. Convertir la superficie final a GdkPixbuf
        new_pixbuf = Gdk.pixbuf_get_from_surface(final_surface, 0, 0, size, size)
        
        if new_pixbuf:
            return new_pixbuf
        else:
            print("⚠️ Advertencia: No se pudo crear pixbuf circular, devolviendo original")
            return pixbuf
        
    except Exception as e:
        print(f"❌ Error aplicando máscara circular: {e}")
        import traceback
        traceback.print_exc()
        return pixbuf  

class JWMMenuParser:
    def __init__(self, jwm_file="/usr/share/jwm/jwm/jwmrc"):
        self.jwm_file = jwm_file
        self.applications = {}
        self.icon_paths = []
        self.tray_config = None
        
    def parse_tray_config(self):
        """Parse tint2 or JWM config based on user preference to get tray position and size"""
        tray_info = {
            'height': 30,
            'width': 1300,
            'valign': 'bottom',
            'halign': 'center',
            'layer': 'above',
            'autohide': 'off',
            'source': 'default'
        }
    
        # Leer preferencia de configuración desde el ConfigManager
        config_manager = ConfigManager()
        config = config_manager.config
        
        # NUEVA FUNCIONALIDAD: Detectar automáticamente el window manager
        detected_wm = detect_window_manager()
        
        # Si es Openbox, forzar uso de tint2
        if detected_wm == 'openbox':
            use_tint2 = True
            print(f"🔍 Window Manager detectado: Openbox → Usando configuración de Tint2 automáticamente")
        else:
            # Si es JWM, usar la preferencia del usuario del JSON
            use_tint2 = config.get('tray', {}).get('use_tint2', False)
            print(f"🔍 Window Manager detectado: JWM → Usando configuración del usuario (use_tint2={use_tint2})")
        
        if use_tint2:
            # Intentar leer tint2rc desde la ruta configurada
            tint2_config = config.get('paths', {}).get('tint2rc', os.path.expanduser("/usr/share/tint2/tint2/tint2rc"))
            tint2_config = os.path.expanduser(tint2_config)
            
            if os.path.exists(tint2_config):
                try:
                    with open(tint2_config, 'r') as f:
                        for line in f:
                            line = line.strip()
                            
                            # Extraer panel_size = 80% 30
                            if line.startswith('panel_size'):
                                parts = line.split('=')
                                if len(parts) == 2:
                                    size_parts = parts[1].strip().split()
                                    if len(size_parts) >= 2:
                                        try:
                                            tray_info['height'] = int(size_parts[1])
                                        except ValueError:
                                            pass
                            
                            # Extraer panel_position = bottom center horizontal
                            elif line.startswith('panel_position'):
                                parts = line.split('=')
                                if len(parts) == 2:
                                    pos_parts = parts[1].strip().split()
                                    if len(pos_parts) >= 2:
                                        # Primer valor: top/bottom
                                        valign = pos_parts[0].lower()
                                        if valign in ['top', 'bottom']:
                                            tray_info['valign'] = valign
                                        
                                        # Segundo valor: left/center/right
                                        halign = pos_parts[1].lower()
                                        if halign in ['left', 'center', 'right']:
                                            tray_info['halign'] = halign
                    
                    tray_info['source'] = 'tint2'
                    print(f"✅ Configuración de tray detectada desde tint2rc: {tray_info}")
                    self.tray_config = tray_info
                    return tray_info
                    
                except Exception as e:
                    print(f"❌ Error parsing tint2 config: {e}")
            else:
                print(f"⚠️ Tint2 config no encontrado en: {tint2_config}")
        
        # Si no usa Tint2 o falló, intentar con JWM
        try:
            jwm_tray_file = config.get('paths', {}).get('jwmrc_tray', os.path.expanduser("/usr/share/jwm/jwm/jwmrc-tray"))
            jwm_tray_file = os.path.expanduser(jwm_tray_file)
            
            if os.path.exists(jwm_tray_file):
                target_file = jwm_tray_file
            else:
                target_file = self.jwm_file
    
            if not os.path.exists(target_file):
                print(f"JWM file not found: {target_file}")
                self.tray_config = tray_info
                return tray_info
    
            tree = ET.parse(target_file)
            root = tree.getroot()
    
            tray_element = root.find('.//Tray')
            if tray_element is not None:
                tray_info['height'] = int(tray_element.get('height', '30'))
                tray_info['width'] = int(tray_element.get('width', '1300'))
                tray_info['valign'] = tray_element.get('valign', 'bottom').lower()
                tray_info['halign'] = tray_element.get('halign', 'center').lower()
                tray_info['layer'] = tray_element.get('layer', 'above').lower()
                tray_info['autohide'] = tray_element.get('autohide', 'off').lower()
                tray_info['source'] = 'jwm'
    
                print(f"✅ Configuración de tray detectada desde {target_file}: {tray_info}")
    
        except Exception as e:
            print(f"❌ Error parsing JWM tray config: {e}")
    
        self.tray_config = tray_info
        return tray_info
        
    def parse_jwm_menu(self):
        """Parse JWM menu file and extract applications"""
        try:
            if not os.path.exists(self.jwm_file):
                print(f"JWM file not found: {self.jwm_file}")
                return self.get_fallback_applications()
            
            tree = ET.parse(self.jwm_file)
            root = tree.getroot()
            
            self.icon_paths = self.extract_icon_paths(root)
            
            applications = {}
            for menu in root.findall('.//Menu'):
                label = menu.get('label', 'Unknown')
                if label:
                    # NUEVA LÍNEA: Normalizar nombre de categoría
                    normalized_label = CATEGORY_MAP.get(label, label)
                    apps = self.extract_programs_from_menu(menu)
                    if apps:
                        if normalized_label not in applications:
                            applications[normalized_label] = []
                        applications[normalized_label].extend(apps)
            
            root_programs = []
            # Buscar elementos Program directos bajo root
            for program in root.findall('./Program'):
                label = program.get('label', '')
                icon = program.get('icon', '')
                tooltip = program.get('tooltip', '')
                command = program.text.strip() if program.text else ''
                
                if label and command:
                    app_info = {
                        'Name': label,
                        'Exec': command,
                        'Icon': icon,
                        'Comment': tooltip or label,
                        'Terminal': 'terminal' in command.lower() or 'urxvt' in command.lower(),
                        'Categories': []
                    }
                    
                    
                    
                    if label.lower() in ['help', 'ayuda']:
                        if 'Help' not in applications:
                            applications['Help'] = []
                        applications['Help'].append(app_info)
                        
                    elif label.lower() in ['leave', 'salir', 'exit', 'logout']:
                        if 'Leave' not in applications:
                            applications['Leave'] = []
                        applications['Leave'].append(app_info)
                        
                    else:
                        root_programs.append(app_info)
            
            # También buscar elementos Program dentro de RootMenu
            for root_menu in root.findall('.//RootMenu'):
                
                for program in root_menu.findall('./Program'):
                    label = program.get('label', '')
                    icon = program.get('icon', '')
                    tooltip = program.get('tooltip', '')
                    command = program.text.strip() if program.text else ''
                    
                    if label and command:
                        app_info = {
                            'Name': label,
                            'Exec': command,
                            'Icon': icon,
                            'Comment': tooltip or label,
                            'Terminal': 'terminal' in command.lower() or 'urxvt' in command.lower(),
                            'Categories': []
                        }
                        
                       
                        
                        if label.lower() in ['help', 'ayuda']:
                            if 'Help' not in applications:
                                applications['Help'] = []
                            applications['Help'].append(app_info)
                            
                        elif label.lower() in ['leave', 'salir', 'exit', 'logout']:
                            if 'Leave' not in applications:
                                applications['Leave'] = []
                            applications['Leave'].append(app_info)
                            
                        else:
                            root_programs.append(app_info)
            
            if root_programs:
                applications['System'] = applications.get('System', []) + root_programs
                           
            
            return applications if applications else self.get_fallback_applications()
            
        except Exception as e:
            print(f"Error parsing JWM menu: {e}")
            return self.get_fallback_applications()
    
    def extract_icon_paths(self, root):
        """Extract icon paths from JWM config"""
        paths = []
        for iconpath in root.findall('.//IconPath'):
            if iconpath.text:
                paths.append(iconpath.text.strip())
        
        # MODIFICACIÓN: Siempre agregar rutas predeterminadas como fallback
        default_paths = [
            "/usr/local/lib/X11/pixmaps",            
            "/usr/share/pixmaps",
            "/usr/share/icons/hicolor/48x48/apps",
            "/usr/share/icons/hicolor/32x32/apps",
            "/usr/share/icons/hicolor/64x64/apps",
            "/usr/share/pixmaps/puppy"
        ]
        
        # Agregar rutas que no estén ya incluidas
        for path in default_paths:
            if path not in paths:
                paths.append(path)
        
        return paths
    
    def extract_programs_from_menu(self, menu_element):
        """Extract program entries from a menu element"""
        programs = []
        for program in menu_element.findall('./Program'):
            label = program.get('label', '')
            icon = program.get('icon', '')
            tooltip = program.get('tooltip', '')
            command = program.text.strip() if program.text else ''
            
            if label and command:
                app_info = {
                    'Name': label,
                    'Exec': command,
                    'Icon': icon,
                    'Comment': tooltip or label,
                    'Terminal': 'terminal' in command.lower() or 'urxvt' in command.lower(),
                    'Categories': []
                }
                programs.append(app_info)
        
        return programs

    def get_fallback_applications(self):
        """Fallback applications if JWM parsing fails"""
        return {
            'System': [
                {'Name': 'Terminal', 'Exec': 'lxterminal', 'Icon': 'terminal', 'Comment': 'Terminal emulator', 'Terminal': False, 'Categories': []},
                {'Name': 'File Manager', 'Exec': 'rox', 'Icon': 'folder', 'Comment': 'File manager', 'Terminal': False, 'Categories': []},
            ],
            'Internet': [
                {'Name': 'Firefox', 'Exec': 'firefox', 'Icon': 'firefox', 'Comment': 'Web browser', 'Terminal': False, 'Categories': []},
            ]
        } 

        
class ArcMenuLauncher(Gtk.Window):
    def __init__(self, icon_size=None, jwm_file=None, x=None, y=None):
        super().__init__(title="Pymenu")
        
        self.config_manager = ConfigManager()
        self.config = self.config_manager.config
        self.is_resizing = False 
        # Use icon_size from config, or fallback to default
        self.icon_size = self.config['window'].get('icon_size', 32)
        
        self.parser = JWMMenuParser(jwm_file or "/root/.jwmrc")
        
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
        
        self.pos_x = x
        self.pos_y = y
        self.context_menu_active = False
    
        screen = Gdk.Screen.get_default()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.set_visual(visual)
            self.set_app_paintable(True)
        
        self.apply_css()
        self.setup_window()
        self.create_interface()
        
        jwm_file_path = jwm_file or "/root/.jwmrc"
        self.jwm_file = Gio.File.new_for_path(jwm_file_path)
        self.file_monitor = self.jwm_file.monitor_file(Gio.FileMonitorFlags.NONE, None)
        self.file_monitor.connect("changed", self.on_jwm_file_changed)
        print(f"Now monitoring JWM file for changes: {jwm_file_path}")

    def apply_css(self):
        """Loads and applies CSS from the configuration."""
        # Verificar si debe usar tema GTK
        use_gtk_theme = self.config['colors'].get('use_gtk_theme', False)
        
        if use_gtk_theme:
            # Si usa tema GTK, usar un fondo sólido compatible
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
                /* Esto hace que el botón sea circular */
                border-radius: 50%;
                padding: 0; 
                border: none;
                min-width: 64px; 
                min-height: 64px;
            }}
            
            button.profile-circular-style:hover {{
                /* Esto define el efecto HOVER circular */
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
        """Reload the menu when the JWM file is modified"""
        if event_type == Gio.FileMonitorEvent.CHANGES_DONE_HINT:
            print("JWM file changed, reloading menu...")
            self.applications = self.parser.parse_jwm_menu()
            for child in self.get_children():
                self.remove(child)
            self.create_interface()
            self.show_all()
            self.present()

    def get_hostname(self):
        """Get the system hostname from /etc/hostname"""
        try:
            with open("/etc/hostname", "r") as f:
                hostname = f.read().strip()
                if hostname:
                    return hostname
        except Exception as e:
            print(f"Error reading hostname: {e}")
        return "Unknown Host"

    def get_os_info(self):
        """Get OS name and kernel version"""
        try:
            os_name = "Unknown OS"
            for path in ['/etc/os-release', '/usr/lib/os-release']:
                if os.path.exists(path):
                    with open(path, 'r') as f:
                        for line in f:
                            if line.startswith('PRETTY_NAME='):
                                os_name = line.split('=', 1)[1].strip().strip('"')
                                break
                    break
            else:
                result = subprocess.run(['uname', '-sr'], capture_output=True, text=True)
                if result.returncode == 0:
                    os_name = result.stdout.strip()
            
            result = subprocess.run(['uname', '-r'], capture_output=True, text=True)
            kernel = result.stdout.strip() if result.returncode == 0 else "Unknown"
            
            return os_name, kernel
            
        except Exception as e:
            print(f"Error getting OS info: {e}")
            return "Unknown OS", "Unknown"
                
    def on_size_changed(self, widget, event):
            """Salva el nuevo tamaño de la ventana al archivo de configuración."""
            width, height = self.get_size()
            
            # Activa la bandera de redimensionamiento
            self.is_resizing = True
            
            # Desactiva la bandera después de un breve retraso
            GLib.timeout_add(150, self.reset_resizing_flag)
            
            # Verifica si el tamaño ha cambiado para evitar escrituras innecesarias
            if width != self.config['window']['width'] or height != self.config['window']['height']:
                print(f"Tamaño de ventana cambiado a {width}x{height}. Guardando...")
                self.config['window']['width'] = width
                self.config['window']['height'] = height
                self.config_manager.save_config(self.config)
                
    def reset_resizing_flag(self):
        """Reinicia la bandera de redimensionamiento."""
        self.is_resizing = False
        return False # No repetir el temporizador           
                
    def calculate_menu_position(self):
        """Calculate menu position based on config and screen size"""
        display = Gdk.Display.get_default()
        monitor = display.get_primary_monitor()
        geometry = monitor.get_geometry()
    
        screen_width = geometry.width
        screen_height = geometry.height
    
        menu_width = int(self.config['window'].get('width', 300))
        menu_height = int(self.config['window'].get('height', 200))
    
        # ---------- HORIZONTAL ----------
        menu_halign = self.config['window'].get('halign', 'center')
        if menu_halign == 'left':
            x = 10
        elif menu_halign == 'right':
            x = screen_width - menu_width - 10
        else:  # default = center
            x = (screen_width - menu_width) // 2
    
        # ---------- VERTICAL ----------
        tray_height = int(self.tray_config.get('height', 0))
        tray_valign = self.tray_config.get('valign', 'center')
    
        if tray_valign == 'top':
            y = tray_height
        elif tray_valign == 'bottom':
            y = screen_height - tray_height - menu_height
        else:
            y = (screen_height - menu_height) // 2
    
        # Clamp para evitar que quede fuera de pantalla
        x = max(0, min(x, screen_width - menu_width))
        y = max(0, min(y, screen_height - menu_height))
    
        return int(x), int(y)

    def setup_window(self):
        """Configure main window"""
        win_size = self.config['window']
        self.set_default_size(win_size['width'], win_size['height'])
        
        if self.pos_x is not None and self.pos_y is not None:
            self.move(int(self.pos_x), int(self.pos_y))
        else:
            x, y = self.calculate_menu_position()
            self.move(x, y)
   #         print(f"Positioning menu at ({x}, {y}) based on tray config: {self.tray_config}")
    
        self.set_resizable(True)
        self.set_decorated(self.config['window'].get('decorated_window', False))
        self.set_app_paintable(True)
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.connect("key-press-event", self.on_key_press)
        self.connect("focus-out-event", self.on_focus_out)
        self.connect("button-press-event", self.on_button_press)
        self.connect("configure-event", self.on_size_changed)
        self.show_all()
        self.present()
        self.grab_focus()
        self.set_keep_above(True)
        GLib.timeout_add(500, lambda: self.set_keep_above(False))
    
        try:
            self.set_icon_name("applications-system")
        except:
            pass      
            
    def on_button_press(self, widget, event):
        """Allows window to be dragged if ALT key is pressed and closes on right-click"""
        # Close the window on right-click (button 3)
        if event.button == 2:
            Gtk.main_quit()
            return True
        
        # Allows window to be dragged if ALT key is pressed
        if event.button == 1 and (event.state & Gdk.ModifierType.MOD1_MASK):
            self.begin_move_drag(event.button, int(event.x_root), int(event.y_root), event.time)
            return True
            
        return False
 
    def on_key_press(self, widget, event):
        """Close window with Escape key"""
        if event.keyval == Gdk.KEY_Escape:
            Gtk.main_quit()
            return True
        return False
    
    def on_focus_out(self, widget, event):
            """Cierra la ventana cuando pierde el foco, a menos que se esté redimensionando."""
            if not self.is_resizing and not self.context_menu_active:
                Gtk.main_quit()
            return False
                    
    def create_interface(self):
        """Create the main interface"""
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        main_box.get_style_context().add_class('menu-window')
        self.add(main_box)
        top_spacer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        top_spacer.set_size_request(-1, 2)  # 20 píxeles de altura
        main_box.pack_start(top_spacer, False, False, 0)
    
        if not self.config['window'].get('hide_header', False):
            header_box = self.create_header()
            main_box.pack_start(header_box, False, False, 0)
            
 #           main_box.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 0)
  
        content_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        # NUEVA SECCIÓN: Botones de acceso rápido (independiente del header)
        # Quick access — solo mostrar si no está oculto en la config
        if not self.config['window'].get('hide_quick_access', False):
            quick_access_container = self.create_quick_access_container()
            main_box.pack_start(quick_access_container, False, False, 0)
            main_box.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 0)

        
        main_box.pack_start(content_box, True, True, 0)
    
        # Columna 1: Redes sociales (solo si no están ocultas en la config)
        if not self.config['window'].get('hide_social_networks', False):
            social_sidebar = self.create_social_networks_sidebar()
            content_box.pack_start(social_sidebar, False, False, 0)
            content_box.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 0)
        
        # Columna 2: Categorías
        content_box.pack_start(self.create_categories_sidebar(), False, False, 0)
        content_box.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 0)
        
        # Columna 3: Aplicaciones
        content_box.pack_start(self.create_applications_area(), True, True, 0)
        
        # === NUEVA LÓGICA: Verificar posición de la barra de búsqueda ===
        search_position = self.config['window'].get('search_bar_position', 'bottom')
        
        # Crear la barra de búsqueda y botones
        search_and_buttons_box = self.create_search_and_buttons_box()
        
        if search_position == 'top':
            # Si está arriba, insertarla después del header
            # Contar cuántos elementos hay antes de content_box
            main_box_children = main_box.get_children()
            insert_position = 0
            
            # Encontrar la posición correcta (después del header/quick_access/separadores)
            for i, child in enumerate(main_box_children):
                if child == content_box:
                    insert_position = i
                    break
            
            # Insertar separador y barra de búsqueda
#            main_box.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 0)
            main_box.pack_start(search_and_buttons_box, False, False, 0)
            main_box.reorder_child(main_box.get_children()[-1], insert_position)
            
            main_box.pack_start(search_and_buttons_box, False, False, 0)
            main_box.reorder_child(main_box.get_children()[-1], insert_position + 1)
        else:
            # Si está abajo (comportamiento original)
#           main_box.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 0)
            main_box.pack_end(search_and_buttons_box, False, False, 0)
        
        self.show_all()
        GLib.timeout_add(100, self.delayed_focus_grab)
        
    def create_search_and_buttons_box(self):
        """Crea la caja con barra de búsqueda y botones de acción"""
        bottom_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        bottom_box.set_margin_top(4)
        bottom_box.set_margin_bottom(4)
        bottom_box.set_margin_start(4)
        bottom_box.set_margin_end(4)
    
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.get_style_context().add_class('search-box')
        
        self.search_entry.set_placeholder_text(TR['Search applications...'])
        self.search_entry.connect("search-changed", self.on_search_changed)
        self.search_entry.set_size_request(200, 10)
        self.search_entry.set_can_focus(True)
        self.search_entry.set_tooltip_text(TR['Search applications...'])
        bottom_box.pack_start(self.search_entry, True, True, 0)
        
        # ---- Botón de apagado ----
        shutdown_button = Gtk.Button()
        shutdown_button.get_style_context().add_class('action-button') 
        shutdown_button.set_size_request(30, 5)
        icon_path = self.find_icon_path("shutdown48")
        if icon_path:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(icon_path, 20, 20)
            shutdown_icon = Gtk.Image.new_from_pixbuf(pixbuf)
        else:
            shutdown_icon = Gtk.Image.new_from_icon_name("system-shutdown", Gtk.IconSize.SMALL_TOOLBAR)        
        shutdown_button.add(shutdown_icon)
        shutdown_button.set_tooltip_text(TR['Shutdown'])
        shutdown_button.connect("clicked", self.on_shutdown_clicked)
        bottom_box.pack_end(shutdown_button, False, False, 0)
        
        # ---- Botón de navegador ----
        browser_button = Gtk.Button()
        browser_button.get_style_context().add_class('action-button') 
        browser_button.set_size_request(30, 5)
        icon_path = self.find_icon_path("www48")
        if icon_path:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(icon_path, 20, 20)
            browser_icon = Gtk.Image.new_from_pixbuf(pixbuf)
        else:
            browser_icon = Gtk.Image.new_from_icon_name("applications-internet", Gtk.IconSize.SMALL_TOOLBAR)       
        browser_button.add(browser_icon)
        browser_button.set_tooltip_text(TR['Search in the web'])
        browser_button.connect("clicked", self.on_browser_search_clicked)
        bottom_box.pack_end(browser_button, False, False, 0)
        
        # ---- Botón de configuración ----
        config_button = Gtk.Button()
        config_button.get_style_context().add_class('action-button')
        config_button.set_size_request(30, 5)
        icon_path = self.find_icon_path("configuration48")
        if icon_path:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(icon_path, 20, 20)
            config_icon = Gtk.Image.new_from_pixbuf(pixbuf)
        else:
            config_icon = Gtk.Image.new_from_icon_name("preferences-system", Gtk.IconSize.SMALL_TOOLBAR)
        
        config_button.add(config_icon)
        config_button.set_tooltip_text(TR['Pymenu config'])
        config_button.connect("clicked", self.on_config_clicked)
        bottom_box.pack_end(config_button, False, False, 0)
        
        return bottom_box        
        
    def delayed_focus_grab(self):
        """Grab focus on search entry after a small delay to preserve placeholder visibility"""
        if self.search_entry:
            self.search_entry.grab_focus()
        return False  # Don't repeat the timeout        

        
    def create_header(self):
        """Create the top header with profile picture, OS, kernel, and hostname"""
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=50)
        header_box.set_margin_top(1)
        header_box.set_margin_bottom(1)
        header_box.set_margin_start(5)
        header_box.set_margin_end(5)
        hide_profile = self.config['window'].get('hide_profile_pic', False)
    
        # === CREAR EL PERFIL ===
        profile_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        profile_box.set_valign(Gtk.Align.CENTER)
        
        profile_button = Gtk.Button()
        profile_button.set_relief(Gtk.ReliefStyle.NONE)
        profile_button.get_style_context().add_class('profile-button') 
        
        if self.config['window'].get('profile_pic_shape', 'square') == 'circular':
            profile_button.get_style_context().add_class('profile-circular-style')
        
        self.profile_image = Gtk.Image()
        profile_button.add(self.profile_image)
        self.profile_image.set_halign(Gtk.Align.CENTER)
        self.profile_image.set_valign(Gtk.Align.CENTER)
        
        def load_profile_image():
            profile_pic_path = self.config['paths']['profile_pic']
            profile_pic_size = self.config['window'].get('profile_pic_size', 128)
            profile_pic_shape = self.config['window'].get('profile_pic_shape', 'square')
            
            pixbuf = None

            # 1. Intentar cargar el .face del usuario
            if profile_pic_path and os.path.exists(profile_pic_path):
                try:
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                        profile_pic_path, profile_pic_size, profile_pic_size, True
                    )
                except Exception as e:
                    print(f"Error cargando .face: {e}")

            # 2. Si no hay .face, buscar el genérico en el sistema (esencia preservada)
            if pixbuf is None:
                # Lista de nombres comunes en /usr/share/icons
                icon_names = ["user-info", "avatar-default", "user-available", "system-users"]
                theme = Gtk.IconTheme.get_default()
                
                for name in icon_names:
                    if theme.has_icon(name):
                        try:
                            # Cargamos el icono del sistema como Pixbuf para poder manipularlo
                            pixbuf = theme.load_icon(name, profile_pic_size, Gtk.IconLookupFlags.FORCE_SIZE)
                            break
                        except:
                            continue

            # 3. Aplicar forma y mostrar
            if pixbuf:
                if profile_pic_shape == 'circular':
                    pixbuf = apply_circular_mask(pixbuf)
                self.profile_image.set_from_pixbuf(pixbuf)
            else:
                # Caso extremo: si ni el genérico existe, poner uno de stock simple
                self.profile_image.set_from_icon_name("image-missing", Gtk.IconSize.DIALOG)
        
        load_profile_image()
    
        def on_profile_clicked(button):
            profile_manager_path = self.config['paths'].get('profile_manager', "")
            if profile_manager_path: # Solo intenta ejecutar si NO está vacío
                try:
                    GLib.timeout_add(100, lambda: Gtk.main_quit())
                    # Verificamos si es un script ejecutable o requiere python3
                    if os.access(profile_manager_path, os.X_OK):
                        subprocess.Popen([profile_manager_path])
                    else:
                        subprocess.Popen(["python3", profile_manager_path])
                except Exception as e:
                    print(f"Error: {e}")
            else:
                print("Profile Manager no configurado por el usuario.")
        
        profile_button.set_tooltip_text(TR["Select avatar"])
        profile_button.connect("clicked", on_profile_clicked)
        profile_box.pack_start(profile_button, False, False, 0)
        
        # === CREAR LA INFO DEL SISTEMA ===
        system_info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        system_info_box.set_valign(Gtk.Align.CENTER)
        
        os_name, kernel = self.get_os_info()
        hostname = self.get_hostname()
        
        header_font_string = self.config['font']['family']
        header_font_description = Pango.FontDescription.from_string(header_font_string)
        header_font_description.set_size(self.config['font']['size_header'])
        
        use_gtk_theme = self.config['colors'].get('use_gtk_theme', False)
            # ← NUEVA LÍNEA: Obtener alineación del texto
        text_align = self.config['window'].get('header_text_align', 'left')
        
                # Convertir a constante de GTK
        if text_align == 'center':
            gtk_align = Gtk.Align.CENTER
        elif text_align == 'right':
            gtk_align = Gtk.Align.END
        else:  # left
            gtk_align = Gtk.Align.START
        
        # OS Label - solo mostrar si no está oculto
        if not self.config['window'].get('hide_os_name', False):
            os_label = Gtk.Label()
            if use_gtk_theme:
                os_label.set_markup(f'<b>{os_name}</b>')
            else:
                os_label.set_markup(f'<span color="{self.config["colors"]["text_header_os"]}"><b>{os_name}</b></span>')
            os_label.override_font(header_font_description)
            os_label.set_halign(gtk_align)  # ← APLICAR ALINEACIÓN
            os_label.set_ellipsize(3)
            os_label.set_max_width_chars(30)
            system_info_box.pack_start(os_label, False, False, 0)
        
        # Kernel Label - solo mostrar si no está oculto
        if not self.config['window'].get('hide_kernel', False):
            kernel_label = Gtk.Label()
            if use_gtk_theme:
                kernel_label.set_markup(f' {kernel}')
            else:
                kernel_label.set_markup(f'<span color="{self.config["colors"]["text_header_kernel"]}"> {kernel}</span>')
            kernel_label.override_font(header_font_description)
            kernel_label.set_halign(gtk_align)  # ← APLICAR ALINEACIÓN
            kernel_label.set_ellipsize(3)
            kernel_label.set_max_width_chars(30)
            system_info_box.pack_start(kernel_label, False, False, 0)
        
        # Hostname Label - solo mostrar si no está oculto
        if not self.config['window'].get('hide_hostname', False):
            hostname_label = Gtk.Label()
            if use_gtk_theme:
                hostname_label.set_markup(f' {hostname}')
            else:
                hostname_label.set_markup(f'<span color="{self.config["colors"]["text_header_hostname"]}"> {hostname}</span>')
            hostname_label.override_font(header_font_description)
            hostname_label.set_halign(gtk_align)  # ← APLICAR ALINEACIÓN
            hostname_label.set_ellipsize(3)
            hostname_label.set_max_width_chars(30)
            system_info_box.pack_start(hostname_label, False, False, 0)
        
    # === APLICAR EL LAYOUT SEGÚN CONFIGURACIÓN ===
        header_layout = self.config['window'].get('header_layout', 'left')
        
        if hide_profile:
            # Si el perfil está oculto, solo mostrar info del sistema
            header_box.pack_start(system_info_box, True, True, 0)
        elif header_layout == 'right':
            # Avatar a la derecha, info a la izquierda
            header_box.pack_start(system_info_box, True, True, 0)
            header_box.pack_start(profile_box, False, False, 0)
        elif header_layout == 'center':
            # Avatar centrado con info del sistema a ambos lados
            left_spacer = Gtk.Box()
            right_spacer = Gtk.Box()
            
            header_box.pack_start(left_spacer, True, True, 0)
            header_box.pack_start(profile_box, False, False, 0)
            header_box.pack_start(right_spacer, True, True, 0)
            
            system_info_box.set_halign(Gtk.Align.START)
            left_spacer.pack_start(system_info_box, False, False, 0)
        else:
            # Avatar a la izquierda, info a la derecha (layout original)
            header_box.pack_start(profile_box, False, False, 0)
            header_box.pack_start(system_info_box, True, True, 0)
        
    # Monitor de cambios en el archivo de perfil (solo si no está oculto)
            if not hide_profile:
                profile_pic_path = self.config['paths']['profile_pic']
                if profile_pic_path and os.path.exists(profile_pic_path):
                    profile_file = Gio.File.new_for_path(profile_pic_path)
                    monitor = profile_file.monitor_file(Gio.FileMonitorFlags.NONE, None)
                    
                    def on_file_changed(monitor, file, other_file, event_type):
                        if event_type in (Gio.FileMonitorEvent.CHANGED, Gio.FileMonitorEvent.CREATED):
                            GLib.idle_add(load_profile_image)
                    
                    monitor.connect("changed", on_file_changed)
        
        return header_box
            
    def create_quick_access_buttons(self):
        """Crear botones de acceso rápido con nerd fonts y rutas localizadas"""
        
        quick_access_items = [
            ('󰉍', 'DownloadsDir'),
            ('󰲂', 'DocumentsDir'),
            ('󰎆', 'MusicDir'),
            ('', 'VideosDir'),
            ('󰋩', 'PicturesDir'),
        ]
        
        quick_access_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
        quick_access_box.set_halign(Gtk.Align.END)
        
        from gi.repository import Pango
        
        for icon, dir_key in quick_access_items:
            button = Gtk.Button()
            button.set_relief(Gtk.ReliefStyle.NONE)
            button.get_style_context().add_class('quick-access-button')
        
            translated_dir_name = TR[dir_key] 
            path = f"~/{translated_dir_name}" 
        
            icon_label = Gtk.Label(label=icon) 
            font = Pango.FontDescription()
            font.set_family("Terminess Nerd Font Propo")
            font.set_size(12 * Pango.SCALE)
            icon_label.override_font(font)
            icon_label.set_name("quick-access-icon")
            icon_label.set_halign(Gtk.Align.CENTER)
            
            button.add(icon_label)
            button.connect("clicked", lambda b, p=path: open_directory(p)) 
            button.set_tooltip_text(translated_dir_name)
            
            # 👉 Usar pack_start para mantener el orden correcto
            quick_access_box.pack_start(button, False, False, 0)
            
        return quick_access_box

    def create_quick_access_container(self):
        container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        container.set_margin_top(5)
        container.set_margin_bottom(5)
        container.set_margin_start(10)
        container.set_margin_end(10)
        
        quick_access_box = self.create_quick_access_buttons()
        # 👉 aquí sí usamos pack_end para mandarlo a la derecha
        container.pack_end(quick_access_box, False, False, 0)
        
        return container
        
        
    def create_social_networks_sidebar(self):
        """Crear botones de redes sociales verticales para la barra lateral con scroll automático"""
        
        social_networks = [
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
        
        social_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        social_box.set_halign(Gtk.Align.CENTER)
        social_box.set_margin_top(1)
        social_box.set_margin_bottom(5)
        social_box.set_margin_start(5)
        social_box.set_margin_end(5)
        
        from gi.repository import Pango
        
        for icon, name, url, color in social_networks:
            button = Gtk.Button()
            button.set_relief(Gtk.ReliefStyle.NONE)
            button.get_style_context().add_class('social-button')
            button.set_size_request(40, 40)
    
            icon_label = Gtk.Label()
            font = Pango.FontDescription()
            font.set_family("Terminess Nerd Font Propo")
            font.set_size(12 * Pango.SCALE)
            icon_label.override_font(font)
            icon_label.set_name("social-icon")
            icon_label.set_halign(Gtk.Align.CENTER)
            icon_label.set_markup(f'<span foreground="{color}">{icon}</span>')
    
            button.add(icon_label)
            button.connect("clicked", lambda b, u=url: self.open_url(u)) 
            button.set_tooltip_text(name)
    
            social_box.pack_start(button, False, False, 0)
    
        # Scroll automático solo cuando la lista sobrepasa la altura
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.add(social_box)
    
        # Contenedor con separador a la derecha
        container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        container.pack_start(scrolled, True, True, 0)
        container.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 0)
    
        return container
    
    def open_url(self, url):
        """Abrir URL en el navegador predeterminado"""
        try:
            import subprocess
            subprocess.Popen(["xdg-open", url], 
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
            # Cerrar el menú después de abrir la URL
            Gtk.main_quit()
        except Exception as e:
            print(f"Error al abrir URL {url}: {e}")        
                    
    def create_categories_sidebar(self):
        """Create categories sidebar with improved hover functionality"""
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        # La línea de abajo no es necesaria para la lista, pero si la quieres
        # para el contenedor ScrolledWindow, déjala aquí.
        scrolled.set_size_request(15, -1)
        
        # Aquí creas el ListBox una sola vez.
        self.categories_listbox = Gtk.ListBox()
        
        # Aquí aplicas todas las configuraciones a ese ListBox.
        self.categories_listbox.set_size_request(12, -1) # Puedes ajustar este valor ancho de columna
        self.categories_listbox.get_style_context().add_class('category-list')
        self.categories_listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.categories_listbox.connect("row-activated", self.on_category_clicked)
    
        category_icons = {
            'Desktop': 'pc48',            
            'System':  'x48',     # Usando el ícono de configuración
            'Setup':  'configuration48',
            'Utility':  'utility48',          # La terminal puede ir en utilidades 
            'Filesystem': 'home48',          # Para el gestor de archivos
            'Graphic': 'paint48',            # Para programas gráficos
            'Document': 'word48',            # Para editores de texto
            'Business': 'spread48',          # Para hojas de cálculo
            'Personal': 'date48',            # Para calendarios
            'Network': 'connect48',          # Para conexiones de red
            'Internet': 'www48',             # Para navegadores
            'Multimedia': 'multimedia48',    # Para reproductores
            'Fun': 'games48',                # Suponiendo que tengas un 'games48.png'
            'Help': 'help48',
            'Shutdown': 'shutdown48',           # Suponiendo que tengas un 'shutdown48.png'
             'Rectify': 'save48',
             'Leave': 'shutdown48',
        }
    
        preferred_order = ['Desktop', 'System', 'Setup', 'Utility', 'Filesystem', 
                           'Graphic', 'Document', 'Business', 'Personal', 
                           'Network', 'Internet', 'Multimedia', 'Fun', 'Help', 'Leave']
        
        # Obtener categorías excluidas desde la configuración
        excluded_categories = self.config.get('categories', {}).get('excluded', [])
        
        added_categories = set()
        for category in preferred_order:
            if category in self.applications and self.applications[category] and category not in excluded_categories:
                self.add_category_row(category, category_icons.get(category, 'applications-other'))
                added_categories.add(category)
        
        for category in sorted(self.applications.keys()):
            if category not in added_categories and self.applications[category] and category not in excluded_categories:
                self.add_category_row(category, category_icons.get(category, 'applications-other'))
    
        scrolled.add(self.categories_listbox)
    
        first_row = self.categories_listbox.get_row_at_index(0)
        if first_row:
            self.categories_listbox.select_row(first_row)
            category = self.get_row_category(first_row)
            self.selected_category = category
            self.current_category = category
            first_row.get_style_context().add_class("selected-category")
            self.selected_category_row = first_row
            self.show_category_applications(category)
    
        return scrolled
    
    def add_category_row(self, category, icon_name):
        """Add a category row with hover events"""
        row = Gtk.ListBoxRow()
        event_box = Gtk.EventBox()
        event_box.set_above_child(True)
        
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=1)
        box.set_property("margin-left", 2)
        box.set_property("margin-right", 1)
        box.set_property("margin-top", 2)
        box.set_property("margin-bottom", 2)
        
        icon_path = self.find_icon_path(icon_name)
        if icon_path:
            category_icon_size = self.config['window'].get('category_icon_size', 24)
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(icon_path, category_icon_size, category_icon_size)
            icon = Gtk.Image.new_from_pixbuf(pixbuf)
        else:
            icon = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.MENU)
        
        # --- LÓGICA DE VISIBILIDAD DE ICONO Y TEXTO ---
        if self.config['window'].get('hide_category_text', False):
            # Crear un contenedor específico para centrar el icono
            center_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            center_box.set_homogeneous(False)
            
            # Tres secciones: vacía - icono - vacía
            left_spacer = Gtk.Box()
            right_spacer = Gtk.Box()
            
            center_box.pack_start(left_spacer, True, True, 0)
            center_box.pack_start(icon, False, False, 0)
            center_box.pack_start(right_spacer, True, True, 0)
            
            box.pack_start(center_box, True, True, 0)
            row.set_tooltip_text(TR.get(category, category))
        else:
            # Si el texto es visible, usar el diseño normal sin center_box
            box.pack_start(icon, False, False, 0)
            
            label = Gtk.Label()
            font_description = Pango.FontDescription.from_string(self.config['font'].get('family_categories', self.config['font']['family']))
            font_description.set_size(self.config['font']['size_categories'])
            label.override_font(font_description)
            translated_category = TR.get(category, category)
            use_gtk_theme = self.config['colors'].get('use_gtk_theme', False)
            if use_gtk_theme:
                label.set_markup(f"{translated_category}")
            else:
                label.set_markup(f"<span foreground='{self.config['colors']['text_normal']}'>{translated_category}</span>")
            label.set_halign(Gtk.Align.START)
            box.pack_start(label, True, True, 5)
        
        event_box.add(box)
        row.add(event_box)
        row.category_name = category
        
        event_box.add_events(Gdk.EventMask.ENTER_NOTIFY_MASK | Gdk.EventMask.LEAVE_NOTIFY_MASK)
        event_box.connect("enter-notify-event", lambda w, e: self.on_category_hover_enter(row, e))
        event_box.connect("leave-notify-event", lambda w, e: self.on_category_hover_leave(row, e))
        
        self.categories_listbox.add(row)
        row.show_all()
    
    def get_row_category(self, row):
        """Get category name from row"""
        return getattr(row, "category_name", None)
    
    def on_menu_enter(self, widget, event):
        """Handle mouse entering the whole menu"""
        self.mouse_in_menu = True
        if self.restore_timeout:
            GLib.source_remove(self.restore_timeout)
            self.restore_timeout = None
        return False
    
    def on_menu_leave(self, widget, event):
        """Handle mouse leaving the whole menu"""
        self.mouse_in_menu = False
        if not self.restore_timeout:
            self.restore_timeout = GLib.timeout_add(150, self.restore_to_selected_category)
        return False

    def on_category_hover_enter(self, row, event):
        """Handle mouse entering a category row"""
        category = self.get_row_category(row)
        if not category or category == self.current_category:
            return False
            
        if self.hover_timeout:
            GLib.source_remove(self.hover_timeout)
        if self.restore_timeout:
            GLib.source_remove(self.restore_timeout)
            self.restore_timeout = None
        
        self.hover_timeout = GLib.timeout_add(150, self._activate_hover_preview, category)
        self.hovered_category = category
        
        return False
        
    def on_category_hover_leave(self, row, event):
        """Handle mouse leaving a category row"""
        if self.hover_timeout:
            GLib.source_remove(self.hover_timeout)
            self.hover_timeout = None
            
        self.hovered_category = None
        return False

    def on_category_clicked(self, listbox, row):
        """Handle category selection by click or Enter key."""
        if not row:
            return
        
        category = self.get_row_category(row)
        if category:
            if self.hover_timeout:
                GLib.source_remove(self.hover_timeout)
                self.hover_timeout = None
        
            if self.selected_category_row:
                self.selected_category_row.get_style_context().remove_class("selected-category")
        
            row.get_style_context().add_class("selected-category")
        
            self.selected_category_row = row
            self.selected_category = category
            self.current_category = category
            
            self.show_category_applications(category)
        
    def restore_to_selected_category(self):
        """Revert to the permanently selected category"""
        self.restore_timeout = None
        if not self.mouse_in_menu:
            self.current_category = self.selected_category
            self.show_category_applications(self.selected_category)
        return False
        
    def _activate_hover_preview(self, category):
        """Activate the category preview on hover"""
        self.hover_timeout = None
        self.current_category = category
        self.show_category_applications(category)
        return False
    
    def _restore_selected_category(self):
        """Restore the selected category if no active hover"""
        if (not self.hover_timeout and 
            self.selected_category and 
            self.selected_category != self.current_category):
            
            self.hovered_category = None
            self.current_category = self.selected_category
            self.show_category_applications(self.selected_category)
        
        self.restore_timeout = None
        return False

    def create_applications_area(self):
        """Create applications display area"""
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        
        self.apps_flowbox = Gtk.FlowBox()
        self.apps_flowbox.set_valign(Gtk.Align.START)
        self.apps_flowbox.set_max_children_per_line(30)
        self.apps_flowbox.set_selection_mode(Gtk.SelectionMode.SINGLE)  # Cambiado a SINGLE
        self.apps_flowbox.set_property("margin-left", 5)
        self.apps_flowbox.set_property("margin-right", 5)
        self.apps_flowbox.set_property("margin-top", 10)
        self.apps_flowbox.set_property("margin-bottom", 10)
        
        apps_eventbox = Gtk.EventBox()
        apps_eventbox.add(self.apps_flowbox)
        apps_eventbox.add_events(Gdk.EventMask.ENTER_NOTIFY_MASK)
        apps_eventbox.connect("enter-notify-event", self.on_apps_area_enter)
        
        # Conecta el manejador de teclas a la ventana del FlowBox
        self.apps_flowbox.connect("key-press-event", self.on_apps_key_press)
        
        scrolled.add(apps_eventbox)
        
        first_category = None
        preferred_order = ['Desktop', 'System', 'Setup', 'Utility', 'Filesystem', 
                          'Graphic', 'Document', 'Business', 'Personal', 
                          'Network', 'Internet', 'Multimedia', 'Fun', 'Help', 'Leave']
        
        for cat in preferred_order:
            if cat in self.applications and self.applications[cat]:
                first_category = cat
                break
        
        if first_category:
            self.current_category = first_category
            GLib.idle_add(self.show_category_applications, first_category)
        
        return scrolled
    
    def on_apps_area_enter(self, widget, event):
        """Handle mouse entering the applications area"""
        print("Mouse entered applications area")
        return False
    
    def create_statusbar(self):
        """Create status bar (kept for compatibility but not shown)"""
        statusbar = Gtk.Statusbar()
        context_id = statusbar.get_context_id("main")
        total_apps = sum(len(apps) for apps in self.applications.values())
        statusbar.push(context_id, f"Total applications: {total_apps}")
        return statusbar
    
    def create_app_button(self, app_info):
        """Create a button for an application"""
        button = Gtk.Button()
        button.set_can_focus(True)
        button.set_relief(Gtk.ReliefStyle.NONE)
        button.connect("clicked", self.on_app_clicked, app_info)
        
        # Contenedor vertical para ícono y nombre
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        box.set_hexpand(False)
        box.set_property("margin-top", 4)
        box.set_property("margin-bottom", 4)
        
        # Ícono de la aplicación
        icon = self.load_app_icon(app_info.get('Icon', 'application-x-executable'))
        box.pack_start(icon, False, False, 0)
        
        # Verificar si se debe ocultar el nombre de la app
        if not self.config['window'].get('hide_app_names', False):
            # Nombre de la aplicación
            name_label = Gtk.Label(label=app_info['Name'])
            
            # Estilo de fuente
            font_description = Pango.FontDescription.from_string(self.config['font']['family'])
            font_description.set_size(self.config['font']['size_names'])
            name_label.override_font(font_description)
            
            # Solución definitiva para el salto de línea
            name_label.set_line_wrap(True)
            name_label.set_max_width_chars(10)  # Fija el ancho máximo en caracteres
            name_label.set_lines(2)
            name_label.set_ellipsize(Pango.EllipsizeMode.END)
            name_label.set_justify(Gtk.Justification.CENTER)
            name_label.set_halign(Gtk.Align.CENTER)
            
            box.pack_start(name_label, False, False, 0)
        
        button.add(box)
        button.set_tooltip_text(app_info.get('Comment', app_info['Name']))
        
        # Añade la información de la aplicación al botón para un acceso más fácil
        button.app_info = app_info
        # Habilitar eventos de mouse
        button.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        
        def on_right_click(widget, event):
            if event.button == 3:  # Clic derecho
                self.context_menu_active = True
                
                menu = Gtk.Menu()
                
                # Opción ejecutar
                item_run = Gtk.MenuItem(label=TR['Run'])
                item_run.connect("activate", lambda w: self.on_app_clicked(button, app_info))
                menu.append(item_run)
                
                # Separador
                separator = Gtk.SeparatorMenuItem()
                menu.append(separator)
                
                # Opción crear acceso directo
                item_shortcut = Gtk.MenuItem(label=TR['Create desktop shortcut'])
                item_shortcut.connect("activate", lambda w: self.create_desktop_shortcut(app_info))
                menu.append(item_shortcut)
                
                # Manejar cuando el menú se cierra
                def on_menu_deactivate(menu):
                    self.context_menu_active = False
                
                menu.connect("deactivate", on_menu_deactivate)
                menu.connect("cancel", on_menu_deactivate)
                
                # Mostrar menú
                menu.show_all()
                menu.popup_at_pointer(event)
                return True
            return False
        
        button.connect("button-press-event", on_right_click)       
        
        return button

    
    def load_app_icon(self, icon_name):
        """
        Carga el ícono de la aplicación con caché y un sistema robusto de fallbacks.
        Almacena el pixbuf en caché para evitar que los íconos se "pierdan".
        """
        if not icon_name:
            icon_name = "application-x-executable"
    
        cache_key = f"{icon_name}_{self.icon_size}"
        pixbuf = self.icon_cache.get(cache_key)
    
        # 1. Si el pixbuf está en la caché, úsalo para crear un nuevo widget de imagen.
        if pixbuf:
            return Gtk.Image.new_from_pixbuf(pixbuf)
    
        # 2. Intentar cargar desde el tema de íconos.
        try:
            pixbuf = Gtk.IconTheme.get_default().load_icon(
                icon_name, self.icon_size, Gtk.IconLookupFlags.FORCE_SIZE
            )
        except Exception:
            pixbuf = None
    
        # 3. Si falla, intentar cargar desde una ruta de archivo.
        if pixbuf is None:
            icon_path = self.find_icon_path(icon_name)
            if icon_path and os.path.exists(icon_path):
                try:
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                        icon_path, self.icon_size, self.icon_size, True
                    )
                except Exception as e:
                    print(f"Failed to load image from path {icon_path}: {e}")
                    pixbuf = None
    
        # 4. Fallback final si todo lo demás falla.
        if pixbuf is None:
            try:
                pixbuf = Gtk.IconTheme.get_default().load_icon(
                    "application-x-executable", self.icon_size, Gtk.IconLookupFlags.FORCE_SIZE
                )
            except Exception:
                return Gtk.Image()
    
        # 5. Guardar el pixbuf en caché y devolver un nuevo widget de imagen.
        self.icon_cache[cache_key] = pixbuf
        return Gtk.Image.new_from_pixbuf(pixbuf)
    
    
    def find_icon_path(self, icon_name):
        """Encuentra el ícono en las rutas definidas, manejando extensiones comunes."""
        if os.path.isabs(icon_name) and os.path.exists(icon_name):
            return icon_name
    
        # Lista extendida de extensiones comunes para íconos
        extensions = [
            '.png', '.svg', '.xpm', '.ico',
            '.jpg', '.jpeg', '.gif', '.tiff', '.bmp'
        ]
    
        for path in self.parser.icon_paths:
            if not os.path.exists(path):
                continue
    
            # Buscar el ícono con y sin extensiones
            base_name, ext = os.path.splitext(icon_name)
            if ext:  # Si el nombre del ícono ya tiene una extensión
                full_path = os.path.join(path, icon_name)
                if os.path.exists(full_path):
                    return full_path
            else:  # Si el nombre no tiene extensión, probar las comunes
                for extension in extensions:
                    full_path = os.path.join(path, f"{base_name}{extension}")
                    if os.path.exists(full_path):
                        return full_path
    
        return None
    
    def is_valid_image_file(self, file_path):
        """Check if file is a valid image that GdkPixbuf can load"""
        if not os.path.isfile(file_path):
            return False
    
        _, ext = os.path.splitext(file_path.lower())
        valid_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.xpm', '.ico', '.tiff', '.tif'}
    
        if ext in valid_extensions:
            return True
    
        try:
            with open(file_path, 'rb') as f:
                header = f.read(16)
            if header.startswith(b'\x89PNG') or header.startswith(b'\xFF\xD8\xFF') or header.startswith(b'GIF87a') or header.startswith(b'GIF89a') or b'<svg' in header.lower() or header.startswith(b'<?xml') or b'XPM' in header or header.startswith(b'BM'):
                return True
        except (OSError, IOError):
            pass
    
        return False
    
    def show_all_applications(self):
        """Show all applications with lazy loading"""
        if not self.apps_flowbox:
            return
        
        self.current_category = "All"
        
        for child in self.apps_flowbox.get_children():
            child.destroy()
        
        GLib.idle_add(self.load_applications_batch, list(self.applications.items()), 0)
    
    def show_category_applications(self, category):
        """Show applications from specific category with lazy loading"""
        if not self.apps_flowbox:
            return
        
        self.current_category = category
        
        for child in self.apps_flowbox.get_children():
            child.destroy()
        
        if category in self.applications:
            apps_data = [(category, self.applications[category])]
            GLib.idle_add(self.load_applications_batch, apps_data, 0)
        
        self.apps_flowbox.show_all()
    
    def load_applications_batch(self, apps_data, start_index, batch_size=10):
        """Load applications in batches to avoid UI freezing"""
        count = 0
        
        for category, apps in apps_data:
            for i, app in enumerate(apps[start_index:], start_index):
                if count >= batch_size:
                    GLib.idle_add(self.load_applications_batch, [(category, apps)], i)
                    return False
                
                button = self.create_app_button(app)
                self.apps_flowbox.add(button)
                count += 1
        
        self.apps_flowbox.show_all()
        return False
    
    def on_search_changed(self, search_entry):
        """Handle search text change"""
        if not self.apps_flowbox:
            return
            
        search_text = search_entry.get_text().lower()
        
        for child in self.apps_flowbox.get_children():
            child.destroy()
        
        if not search_text:
            if hasattr(self, 'current_category') and self.current_category:
                self.show_category_applications(self.current_category)
            else:
                preferred_order = ['Desktop', 'System', 'Setup', 'Utility', 'Filesystem', 
                                  'Graphic', 'Document', 'Business', 'Personal', 
                                  'Network', 'Internet', 'Multimedia', 'Fun', 'Help', 'Leave']
                for cat in preferred_order:
                    if cat in self.applications and self.applications[cat]:
                        self.show_category_applications(cat)
                        break
            return
        
        for category, apps in self.applications.items():
            for app in apps:
                if (search_text in app['Name'].lower() or 
                    search_text in app.get('Comment', '').lower()):
                    button = self.create_app_button(app)
                    self.apps_flowbox.add(button)
        
        self.apps_flowbox.show_all()

    def on_apps_key_press(self, widget, event):
        """Handles key presses (arrows, Enter) on the apps flowbox."""
        keyval = event.keyval
        
        if keyval in [Gdk.KEY_Down, Gdk.KEY_Up, Gdk.KEY_Right, Gdk.KEY_Left]:
            self.navigate_apps(keyval)
            return True
        elif keyval == Gdk.KEY_Return:
            self.launch_selected_app()
            return True
        return False

    def navigate_apps(self, keyval):
        """Navigate through applications with arrow keys."""
        children = self.apps_flowbox.get_children()
        if not children:
            return

        selected_children = self.apps_flowbox.get_selected_children()
        if not selected_children:
            current_index = -1
        else:
            current_index = children.index(selected_children[0])

        new_index = -1
        
        # Determine the number of columns on the first row.
        # This is a more robust way to get the column count.
        cols = 1
        if len(children) > 1:
            y_pos_first_child = children[0].get_allocation().y
            for i in range(1, len(children)):
                if children[i].get_allocation().y == y_pos_first_child:
                    cols += 1
                else:
                    break

        if keyval == Gdk.KEY_Down:
            if current_index >= 0:
                new_index = current_index + cols
        elif keyval == Gdk.KEY_Up:
            if current_index >= 0:
                new_index = current_index - cols
        elif keyval == Gdk.KEY_Right:
            if current_index >= 0:
                new_index = current_index + 1
            else:
                new_index = 0
        elif keyval == Gdk.KEY_Left:
            if current_index > 0:
                new_index = current_index - 1
            else: # Go to the end if at the start
                new_index = len(children) - 1

        if 0 <= new_index < len(children):
            self.apps_flowbox.unselect_all()
            self.apps_flowbox.select_child(children[new_index])
            children[new_index].grab_focus()

    def launch_selected_app(self):
        """Lanza la aplicación seleccionada con el teclado."""
        selected = self.apps_flowbox.get_selected_children()
        if selected:
            child = selected[0]
            button = child.get_child()  # el Gtk.Button
            if button and hasattr(button, 'app_info'):
                self.on_app_clicked(button, button.app_info)


    def on_browser_search_clicked(self, button):
        """Launches a browser search with the text from the search box"""
        search_query = self.search_entry.get_text().strip()
        
        if not search_query:
            print("Search box is empty. Doing nothing.")
            return
    
        # Encode the search query to be URL-safe
        encoded_query = urllib.parse.quote_plus(search_query)
        
        # Obtener motor de búsqueda desde la configuración
        search_engine = self.config.get('search_engine', {}).get('engine', 'google')
        
        # Diccionario de URLs de búsqueda
        search_urls = {
            'google': f"https://www.google.com/search?q={encoded_query}",
            'duckduckgo': f"https://duckduckgo.com/?q={encoded_query}",
            'brave': f"https://search.brave.com/search?q={encoded_query}",
            'searxng': f"https://searx.be/search?q={encoded_query}",
            'librex': f"https://librex.terryiscool160.xyz/search.php?q={encoded_query}"
        }
        
        # Obtener URL del motor seleccionado, con Google como fallback
        search_url = search_urls.get(search_engine, search_urls['google'])
        
        try:
            print(f"Launching browser search for: '{search_query}' using {search_engine}")
            subprocess.Popen(["xdg-open", search_url], 
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
            Gtk.main_quit()
        except FileNotFoundError:
            print("Error: 'xdg-open' not found. Please make sure you have a default browser configured.")
        except Exception as e:
            print(f"Failed to launch browser: {e}")

    def on_app_clicked(self, button, app_info):
        """Handle application launch"""
        try:
            GLib.timeout_add(50, lambda: Gtk.main_quit())
            
            command = app_info['Exec']
            try:
                cmd_parts = shlex.split(command)
            except ValueError:
                cmd_parts = command.split()

            cleaned_parts = [part for part in cmd_parts if not any(part.startswith(code) for code in ['%f', '%F', '%u', '%U', '%i', '%c'])]

            if not cleaned_parts:
                print(f"No executable command found for {app_info['Name']}")
                return

            if app_info.get('Terminal', False):
                subprocess.Popen(['lxterminal', '-e'] + cleaned_parts,
                                 stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)
            else:
                subprocess.Popen(cleaned_parts,
                                 stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)

            print(f"Launching: {app_info['Name']} ({' '.join(cleaned_parts)})")

        except Exception as e:
            print(f"Error launching {app_info.get('Name', 'Unknown')}: {e}")
            
    # Función que faltaba
    def on_config_clicked(self, button):
        """Lanza el script de configuración."""
        try:
            # Cerrar la ventana del menú inmediatamente
            GLib.timeout_add(100, lambda: Gtk.main_quit())
            
            # Lanzar el script de configuración
            config_script = "/usr/local/bin/pymenu-config.py"
            subprocess.Popen(["python3", config_script],
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
            print(f"Lanzando el configurador: {config_script}")
        except Exception as e:
            print(f"Error al lanzar el configurador: {e}")

    def on_shutdown_clicked(self, button):
            """Run shutdown command or path"""
            try:
                # Obtenemos el texto del JSON
                cmd = self.config['paths'].get('shutdown_cmd', "").strip()
                
                if not cmd:
                    print("No hay comando de apagado configurado.")
                    Gtk.main_quit()
                    return
    
                # Cerramos el menú
                GLib.timeout_add(100, lambda: Gtk.main_quit())
                subprocess.Popen(cmd, 
                                 shell=True,
                                 stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)
                                 
                print(f"Ejecutando: {cmd}")
                
            except Exception as e:
                print(f"Error al ejecutar el comando de apagado: {e}")
            
    def create_desktop_shortcut(self, app_info):
        """Crear un acceso directo .desktop usando spacefm"""
        try:
            # Determinar carpeta del escritorio
            desktop_dir = os.path.expanduser('~/Desktop')
            if not os.path.isdir(desktop_dir):
                desktop_dir = os.path.expanduser('~/Escritorio')
            
            # Crear directorio si no existe
            os.makedirs(desktop_dir, exist_ok=True)
            
            # Nombre del archivo .desktop
            app_name = app_info.get('Name', 'app').replace('/', '-').replace(' ', '_')
            desktop_file = os.path.join(desktop_dir, f"{app_name}.desktop")
            
            # Limpiar y validar comando
            exec_cmd = app_info.get('Exec', '')
            try:
                parts = shlex.split(exec_cmd)
            except:
                parts = exec_cmd.split()
            
            cleaned_parts = [p for p in parts if not any(p.startswith(x) for x in ['%f','%F','%u','%U','%i','%c'])]
            
            if not cleaned_parts:
                raise Exception("No se encontró comando ejecutable")
            
            # Verificar si el comando principal existe y es ejecutable
            main_command = cleaned_parts[0]
            if not os.path.isabs(main_command):
                # Si no es ruta absoluta, buscar en PATH
                command_path = subprocess.run(['which', main_command], 
                                            capture_output=True, text=True)
                if command_path.returncode == 0:
                    main_command = command_path.stdout.strip()
                    cleaned_parts[0] = main_command
                else:
                    raise Exception(f"Comando '{main_command}' no encontrado en el sistema")
            else:
                # Si es ruta absoluta, verificar que existe y es ejecutable
                if not os.path.exists(main_command):
                    raise Exception(f"El archivo '{main_command}' no existe")
                if not os.access(main_command, os.X_OK):
                    raise Exception(f"El archivo '{main_command}' no tiene permisos de ejecución")
            
            clean_exec = ' '.join(cleaned_parts)
            
            # Buscar ruta del ícono
            icon_value = app_info.get('Icon', '')
            icon_path = self.find_icon_path(icon_value) if icon_value else ''
            final_icon = icon_path if icon_path else icon_value
            
            # Contenido del archivo .desktop
            desktop_lines = [
                "[Desktop Entry]",
                "Type=Application",
                "Version=1.0",
                f"Name={app_info.get('Name', 'Aplicación')}",
                f"Comment={app_info.get('Comment', '')}",
                f"Exec={clean_exec}",
                f"Icon={final_icon}",
                f"Terminal={'true' if app_info.get('Terminal', False) else 'false'}",
                "Categories=Application;",
                "StartupNotify=true"
            ]
            
            desktop_content = '\n'.join(desktop_lines) + '\n'
            
            # Escribir archivo
            with open(desktop_file, 'w', encoding='utf-8') as f:
                f.write(desktop_content)
            
            # Dar permisos de ejecución
            os.chmod(desktop_file, 0o755)
            
            print(f"Acceso directo creado: {desktop_file}")
            print(f"Comando validado: {clean_exec}")
            
            # Opcional: mostrar notificación
            try:
                subprocess.run(['notify-send', 'Pymenu', f'Acceso creado para {app_info.get("Name")}'], 
                              check=False)
            except:
                pass
                
        except Exception as e:
            print(f"Error creando acceso directo: {e}")
            try:
                subprocess.run(['notify-send', 'Pymenu', f'Error: {str(e)}'], check=False)
            except:
                pass        
            
def main():
    icon_size = None
    jwm_file = None
    x = None
    y = None
    
    if len(sys.argv) >= 3:
        try:
            x = int(sys.argv[1])
            y = int(sys.argv[2])
        except ValueError:
            jwm_file = sys.argv[1]
            try:
                icon_size = int(sys.argv[2])
                if icon_size not in [16, 24, 32, 40, 48]:
                    icon_size = None
            except ValueError:
                icon_size = None
    elif len(sys.argv) == 2:
        try:
            x = int(sys.argv[1])
            x = None
        except ValueError:
            jwm_file = sys.argv[1]
    
    app = ArcMenuLauncher(icon_size, jwm_file, x, y)
    app.connect("destroy", Gtk.main_quit)
    app.show_all()
    
    Gtk.main()

if __name__ == "__main__":
    main()
