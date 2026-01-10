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
    print("Warning: pymenupuplang not found, using English")

# Generar CATEGORY_MAP automáticamente desde archivos .lang
CATEGORY_MAP = TR.get_category_map()

# Import the pango module using GObject Introspection
gi.require_version('Pango', '1.0')
from gi.repository import Pango

CONFIG_FILE = "/root/.config/pymenu.json"


def open_directory(path):
    """
    Intenta expandir la ruta y abrirla con el administrador predeterminado del sistema.
    """
    expanded_path = os.path.expanduser(path)
    
    if not os.path.exists(expanded_path):
        try:
            os.makedirs(expanded_path, exist_ok=True)
            print(f"{TR['Folder created:']} {expanded_path}")
        except Exception as e:
            print(f"Error al crear la carpeta {expanded_path}: {e}")
            return 
    
    try:
        # Esto le pide al sistema que abra la ruta con la APP PREDETERMINADA
        # (Sea Thunar, PCManFM, Nautilus, etc.)
        gio_file = Gio.File.new_for_path(expanded_path)
        Gio.AppInfo.launch_default_for_uri(gio_file.get_uri(), None)
    except Exception as e:
        # Si falla Gio, intentamos con xdg-open como respaldo
        try:
            subprocess.Popen(["xdg-open", expanded_path],
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
        except Exception as ex:
            print(f"Error al abrir el directorio: {ex}")
                

class ConfigManager:
    """Manages reading and writing the application's JSON configuration."""
    def __init__(self, config_file=CONFIG_FILE):
        self.config_file = config_file
        self.config = self.load_config()

    def get_default_config(self):
        """Devuelve una configuración predeterminada."""
        return {
            "window": {
                "width": 715,
                "height": 491,
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
                "size_header": 13000
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
                "use_tint2": False,
                "use_xfce": False
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
            elif 'xfce' in wm_content or 'xfce4' in wm_content:
                return 'xfce'
            elif 'lxde' in wm_content or 'lxpanel' in wm_content:
                return 'lxde'
    except FileNotFoundError:
        print(f"{TR['File /etc/windowmanager not found, assuming JWM']}")
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
        """Parse tint2, XFCE, LXDE or JWM config based on user preference to get tray position and size"""
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
            use_xfce = False
            use_lxde = False
            print(f"🔍 {TR['Window Manager detected:']} Openbox → {TR['Automatically using Tint2 config']}")
        elif detected_wm == 'xfce':
            use_tint2 = False
            use_xfce = True
            use_lxde = False
            print(f"🔍 {TR['Window Manager detected:']} XFCE → {TR['Automatically using XFCE config']}")
            # Guardar ruta del config para monitorear después
            self.xfce_config_file = os.path.expanduser("~/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-panel.xml")
        elif detected_wm == 'lxde':
            use_tint2 = False
            use_xfce = False
            use_lxde = True
            print(f"🔍 {TR['Window Manager detected:']} LXDE → {TR['Automatically using LXDE config']}")
        else:
            # Si es JWM, usar la preferencia del usuario del JSON
            use_tint2 = config.get('tray', {}).get('use_tint2', False)
            use_xfce = config.get('tray', {}).get('use_xfce', False)
            use_lxde = config.get('tray', {}).get('use_lxde', False)
            print(f"🔍 Window Manager detectado: JWM → Usando configuración del usuario (use_tint2={use_tint2}, use_xfce={use_xfce}, use_lxde={use_lxde})")
        
        # PRIMERO: Intentar con XFCE si está configurado o detectado
        if use_xfce or detected_wm == 'xfce':
            xfce_config = self.parse_xfce_panel_config()
            if xfce_config:
                tray_info.update(xfce_config)
                tray_info['source'] = 'xfce'
                print(f"✅ Configuración de panel detectada desde XFCE: {tray_info}")
                self.tray_config = tray_info
                return tray_info
        
        # SEGUNDO: Intentar con LXDE si está configurado o detectado
        if use_lxde or detected_wm == 'lxde':
            lxde_config = self.parse_lxde_panel_config()
            if lxde_config:
                tray_info.update(lxde_config)
                tray_info['source'] = 'lxde'
                print(f"✅ Configuración de panel detectada desde LXDE: {tray_info}")
                self.tray_config = tray_info
                return tray_info
        
        # TERCERO: Intentar con Tint2 si está configurado
        if use_tint2 or detected_wm == 'openbox':
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
        
        # TERCERO: Si no usa XFCE o Tint2, o fallaron, intentar con JWM
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
            
    def parse_xfce_panel_config(self):
        """Parse XFCE panel configuration - supports multiple panels"""
        xfce_config = None
        
        xfce_config_paths = [
            os.path.expanduser("~/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-panel.xml"),
            "/etc/xdg/xfce4/panel/default.xml",
            "/usr/share/xfce4/panel/default.xml"
        ]
        
        for config_file in xfce_config_paths:
            if os.path.exists(config_file):
                try:
                    tree = ET.parse(config_file)
                    root = tree.getroot()
                    
                    # Buscar TODOS los paneles manualmente (panel-1, panel-2, etc.)
                    # No podemos usar starts-with() en ElementTree
                    all_properties = root.findall(".//property")
                    panels = [p for p in all_properties if p.get('name', '').startswith('panel-')]
                    
                    print(f"🔍 DEBUG: Encontrados {len(panels)} paneles en {config_file}")
                    
                    for panel in panels:
                        panel_name = panel.get('name')
                        temp_config = {}
                        
                        # Tamaño
                        size_elem = panel.find(".//property[@name='size']")
                        if size_elem is not None:
                            temp_config['height'] = int(size_elem.get('value', '30'))
                        
                        # Longitud
                        length_elem = panel.find(".//property[@name='length']")
                        if length_elem is not None:
                            try:
                                length_percent = float(length_elem.get('value', '100'))
                                temp_config['width'] = int(1920 * (length_percent / 100))
                            except ValueError:
                                temp_config['width'] = 1300
                        
                        # Posición
                        position_elem = panel.find(".//property[@name='position']")
                        if position_elem is not None:
                            position = position_elem.get('value', 'p=6;')
                            
                            print(f"🔍 DEBUG: {panel_name} position = '{position}'")
                            
                            # WORKAROUND: Usar coordenada Y como fallback
                            y_coord = None
                            if 'y=' in position:
                                try:
                                    y_str = position.split('y=')[1].split(';')[0]
                                    y_coord = int(y_str)
                                    print(f"   → Y coordinate: {y_coord}")
                                except:
                                    pass
                            
                            if 'p=' in position:
                                p_value = position.split('p=')[1].split(';')[0]
                                try:
                                    p_int = int(p_value)
                                    
                                    # Top positions: 12, 2, 4
                                    if p_int in [12, 2, 4]:
                                        temp_config['valign'] = 'top'
                                    # Bottom positions: 6, 8, 10
                                    elif p_int in [6, 8, 10]:
                                        temp_config['valign'] = 'bottom'
                                    else:
                                        temp_config['valign'] = 'bottom'
                                    
                                    # Horizontal alignment
                                    if p_int in [8, 12]:  # Left
                                        temp_config['halign'] = 'left'
                                    elif p_int in [10, 4]:  # Right
                                        temp_config['halign'] = 'right'
                                    else:  # Center
                                        temp_config['halign'] = 'center'
                                    
                                    # WORKAROUND: Si Y es bajo (<100), forzar TOP
                                    if y_coord is not None and y_coord < 100:
                                        temp_config['valign'] = 'top'
                                        print(f"   ⚠️  XML dice bottom pero Y={y_coord} indica TOP - corrigiendo")
                                    
                                    print(f"   → Detectado: {temp_config.get('valign')} {temp_config.get('halign')}, altura {temp_config.get('height')}px")
                                    
                                except ValueError:
                                    temp_config['valign'] = 'bottom'
                                    temp_config['halign'] = 'center'
                        
                        # ESTRATEGIA: Usar el panel TOP si existe, sino usar el primero que encuentre
                        if temp_config.get('valign') == 'top':
                            xfce_config = temp_config
                            print(f"✅ Usando {panel_name} (TOP) para posicionar el menú")
                            break  # Priorizar panel superior
                        elif xfce_config is None:
                            xfce_config = temp_config
                    
                    if xfce_config:
                        return xfce_config
                        
                except Exception as e:
                    print(f"❌ Error parsing XFCE config {config_file}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
        
        return None         
    
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
        
    def parse_lxde_panel_config(self):
        """Parse LXDE panel configuration to get position and size"""
        lxde_config = {}
        
        # Rutas comunes de configuración de LXDE
        lxde_config_paths = [
            os.path.expanduser("~/.config/lxpanel/LXDE/panels/panel"),
            "/etc/xdg/lxpanel/LXDE/panels/panel",
            "/usr/share/lxpanel/profile/LXDE/panels/panel"
        ]
        
        for config_file in lxde_config_paths:
            if os.path.exists(config_file):
                try:
                    with open(config_file, 'r') as f:
                        lines = f.readlines()
                        
                        for line in lines:
                            line = line.strip()
                            
                            # Buscar configuración Global
                            if line.startswith('edge='):
                                edge = line.split('=')[1].strip()
                                lxde_config['valign'] = edge  # top/bottom
                            
                            elif line.startswith('allign='):
                                align = line.split('=')[1].strip()
                                lxde_config['halign'] = align  # left/center/right
                            
                            elif line.startswith('margin='):
                                try:
                                    margin = int(line.split('=')[1].strip())
                                    lxde_config['margin'] = margin
                                except ValueError:
                                    pass
                            
                            elif line.startswith('width='):
                                try:
                                    width = int(line.split('=')[1].strip())
                                    lxde_config['width'] = width
                                except ValueError:
                                    pass
                            
                            elif line.startswith('height='):
                                try:
                                    height = int(line.split('=')[1].strip())
                                    lxde_config['height'] = height
                                except ValueError:
                                    pass
                    
                    # Establecer valores por defecto si no se encontraron
                    if 'height' not in lxde_config:
                        lxde_config['height'] = 30
                    if 'width' not in lxde_config:
                        lxde_config['width'] = 1300
                    if 'valign' not in lxde_config:
                        lxde_config['valign'] = 'bottom'
                    if 'halign' not in lxde_config:
                        lxde_config['halign'] = 'center'
                    
                    return lxde_config
                        
                except Exception as e:
                    print(f"❌ Error parsing LXDE config {config_file}: {e}")
                    continue
        
        return None        
    
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
        super().__init__(title="PyMenuPup")
        
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
        self.showing_favorites = False
        self.favorites_cleanup_timeout = None 
        
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
        print(f"{TR['Now monitoring JWM file for changes:']} {jwm_file_path}")
        if hasattr(self.parser, 'xfce_config_file') and os.path.exists(self.parser.xfce_config_file):
            try:
                xfce_file = Gio.File.new_for_path(self.parser.xfce_config_file)
                self.xfce_monitor = xfce_file.monitor_file(Gio.FileMonitorFlags.NONE, None)
                self.xfce_monitor.connect("changed", self.on_xfce_panel_changed)
                print(f"👀 Monitoreando cambios XFCE panel: {self.parser.xfce_config_file}")
            except Exception as e:
                print(f"⚠️  Error monitoreando XFCE: {e}")
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
            print(TR['Using GTK theme colors'])
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

            
    def on_xfce_panel_changed(self, monitor, file, other_file, event_type):
        """Reposicionar menú cuando cambia la configuración del panel XFCE"""
        if event_type == Gio.FileMonitorEvent.CHANGES_DONE_HINT:
            print("🔄 Panel XFCE cambió, reposicionando menú...")
            self.tray_config = self.parser.parse_tray_config()
            x, y = self.calculate_menu_position()
            self.move(x, y)
            print(f"📍 Nueva posición: ({x}, {y})")       

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
            
    def load_favorites(self):
            """Carga los favoritos desde el archivo de configuración"""
            favorites_list = []
            # El CONFIG_FILE ya está definido al inicio de tu script
            if os.path.exists(CONFIG_FILE):
                try:
                    with open(CONFIG_FILE, 'r') as f:
                        config = json.load(f)
                        # Extraer la sección 'favorites' del JSON
                        favs = config.get('favorites', [])
                        for fav in favs:
                            favorites_list.append({
                                "Name": fav.get('name', 'Fav'),
                                "Exec": fav.get('exec', ''),
                                "Icon": fav.get('icon', 'star'),
                                "IsFavorite": True 
                            })
                except Exception as e:
                    print(f"Error cargando favoritos: {e}")
            return favorites_list            
                    
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
        
        main_box.pack_start(content_box, True, True, 0)
    
        # Columna 1: Places (Lugares) - nueva columna
        if not self.config['window'].get('hide_places', False):
            places_sidebar = self.create_places_sidebar()
            content_box.pack_start(places_sidebar, False, False, 0)
            content_box.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 0)
        
        # Columna 2: Redes sociales (solo si no están ocultas en la config)
        if not self.config['window'].get('hide_social_networks', False):
            social_sidebar = self.create_social_networks_sidebar()
            content_box.pack_start(social_sidebar, False, False, 0)
            content_box.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 0)
        
        # Columna 3: Categorías
        content_box.pack_start(self.create_categories_sidebar(), False, False, 0)
        content_box.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 0)
        
# Columna 4: Aplicaciones
        apps_area = self.create_applications_area()
        content_box.pack_start(apps_area, True, True, 0)
        
        # === NUEVA LÓGICA: Verificar CONTENEDOR de la barra de búsqueda ===
        search_container = self.config['window'].get('search_bar_container', 'window')
        
        if search_container == 'apps_column':
            # La barra ya está integrada en create_applications_area()
            pass
        else:
            # Comportamiento original: barra en la ventana principal
            search_position = self.config['window'].get('search_bar_position', 'bottom')
            search_and_buttons_box = self.create_search_and_buttons_box()
            
            if search_position == 'top':
                main_box_children = main_box.get_children()
                insert_position = 0
                
                for i, child in enumerate(main_box_children):
                    if child == content_box:
                        insert_position = i
                        break
                
                main_box.pack_start(search_and_buttons_box, False, False, 0)
                main_box.reorder_child(main_box.get_children()[-1], insert_position)
            else:
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
        # Si el perfil está en Places, solo mostrar info del sistema
        if self.config['window'].get('profile_in_places', False):
            return self.create_system_info_only()
        
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=50)
        header_box.set_margin_top(1)
        header_box.set_margin_bottom(1)
        header_box.set_margin_start(5)
        header_box.set_margin_end(5)
        hide_profile = self.config['window'].get('hide_profile_pic', False)
    
    # ... resto del código original continúa igual
    
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
        
        # Hostname Label - solo mostrar si no está oculto Y si no está en Places
        if not self.config['window'].get('hide_hostname', False) and not self.config['window'].get('profile_in_places', False):
            hostname_label = Gtk.Label()
            if use_gtk_theme:
                hostname_label.set_markup(f' {hostname}')
            else:
                hostname_label.set_markup(f'<span color="{self.config["colors"]["text_header_hostname"]}"> {hostname}</span>')
            hostname_label.override_font(header_font_description)
            hostname_label.set_halign(gtk_align)
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
        
    def create_system_info_only(self):
        """Crear solo la información del sistema sin el perfil"""
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        header_box.set_margin_top(1)
        header_box.set_margin_bottom(1)
        header_box.set_margin_start(5)
        header_box.set_margin_end(5)
        
        system_info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        system_info_box.set_valign(Gtk.Align.CENTER)
        
        os_name, kernel = self.get_os_info()
        hostname = self.get_hostname()
        
        # Verificar si el perfil está en Places
        profile_in_places = self.config['window'].get('profile_in_places', False)
        
        # ... (código existente para OS y Kernel) ...
        
        # SOLO mostrar hostname en el header si el perfil NO está en Places
        if not self.config['window'].get('hide_hostname', False) and not profile_in_places:
            hostname_label = Gtk.Label()
            if use_gtk_theme:
                hostname_label.set_markup(f' {hostname}')
            else:
                hostname_label.set_markup(f'<span color="{self.config["colors"]["text_header_hostname"]}"> {hostname}</span>')
            hostname_label.override_font(header_font_description)
            hostname_label.set_halign(gtk_align)
            hostname_label.set_ellipsize(3)
            hostname_label.set_max_width_chars(30)
            system_info_box.pack_start(hostname_label, False, False, 0)
        
        header_box.pack_start(system_info_box, True, True, 0)
        return header_box   
                   
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
        
    def create_places_sidebar(self):
        """Crear columna de lugares completa: Perfil -> Hostname -> System Places -> Favoritos"""
        places_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        places_box.set_halign(Gtk.Align.CENTER)
        places_box.set_margin_top(1)
        places_box.set_margin_bottom(5)
        places_box.set_margin_start(5)
        places_box.set_margin_end(5)
        
        # 1. SECCIÓN DE PERFIL Y HOSTNAME
        if self.config['window'].get('profile_in_places', False):
            profile_section = self.create_profile_section()
            places_box.pack_start(profile_section, False, False, 5)
            places_box.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 5)
        
        # 2. LUGARES DEL SISTEMA (Home, Downloads, etc.) - FILTRADOS POR CONFIGURACIÓN
        # Diccionario de carpetas disponibles con sus íconos y rutas
        all_system_places = {
            'Home': ('user-home', TR.get('Home', 'Home'), '~'),
            'Downloads': ('folder-download', TR.get('Downloads', 'Downloads'), f"~/{TR.get('DownloadsDir', 'Downloads')}"),
            'Documents': ('folder-documents', TR.get('Documents', 'Documents'), f"~/{TR.get('DocumentsDir', 'Documents')}"),
            'Music': ('folder-music', TR.get('Music', 'Music'), f"~/{TR.get('MusicDir', 'Music')}"),
            'Pictures': ('folder-pictures', TR.get('Pictures', 'Pictures'), f"~/{TR.get('PicturesDir', 'Pictures')}"),
            'Videos': ('folder-videos', TR.get('Videos', 'Videos'), f"~/{TR.get('VideosDir', 'Videos')}"),
            'Desktop': ('user-desktop', TR.get('Desktop', 'Desktop'), '~/Desktop'),
            'Templates': ('folder-templates', TR.get('Templates', 'Templates'), '~/Templates'),
            'Public': ('folder-publicshare', TR.get('Public', 'Public'), '~/Public'),
            'Recent': ('document-open-recent', TR.get('Recent', 'Recent'), '~/.local/share/recently-used.xbel')
        }
        
        # Obtener lista de carpetas visibles desde la configuración
        visible_folders = self.config.get('places', {}).get('visible_folders', ["Home", "Downloads", "Documents", "Music", "Pictures", "Videos"])
        
        # Fuente para los textos (FALTABA ESTA LÍNEA)
        font_desc = Pango.FontDescription.from_string(self.config['font'].get('family_categories', 'Sans'))
        font_desc.set_size(self.config['font'].get('size_categories', 12000))
        
        # Mostrar solo las carpetas visibles
        for folder_key in visible_folders:
            if folder_key in all_system_places:
                icon_name, label, path = all_system_places[folder_key]
                
                btn = Gtk.Button()
                btn.set_relief(Gtk.ReliefStyle.NONE)
                btn.get_style_context().add_class('social-button')
                btn.set_size_request(40, -1)
                
                hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
                hbox.set_halign(Gtk.Align.START)
                hbox.set_margin_start(5)
                
                # Icono de sistema (24px)
                icon_image = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.DND)
                icon_image.set_pixel_size(24)
                
                # Texto
                text_label = Gtk.Label(label=label)
                text_label.set_halign(Gtk.Align.START)
                text_label.override_font(font_desc)  # <-- AHORA font_desc ESTÁ DEFINIDA
                
                hbox.pack_start(icon_image, False, False, 0)
                hbox.pack_start(text_label, True, True, 0)
                
                btn.add(hbox)
                btn.connect("clicked", lambda b, p=path: open_directory(p))
                places_box.pack_start(btn, False, False, 0)
        
        # 3. SEPARADOR Y FAVORITOS
        places_box.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 5)
        
        # ===== AGREGAR FAVORITOS =====
        favorites = self.config.get('favorites', [])
        if favorites:
            # Crear un contenedor especial para toda la sección de favoritos
            favorites_section_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            
            # Título de favoritos
            # Buscar ícono personalizado para favoritos
            favorites_icon_path = None
            search_paths = [
                '/usr/local/lib/X11/pixmaps/',
                '/usr/share/pixmaps/',
                '/usr/share/pixmaps/puppy/'
            ]
            
            # Buscar archivos de íconos posibles
            favorites_icon_files = ['favorites48.png', 'favorites.png', 'bookmarks48.png', 
                                   'bookmarks.png', 'favorites.xpm', 'bookmarks.xpm']
            
            for search_path in search_paths:
                if os.path.exists(search_path):
                    for icon_file in favorites_icon_files:
                        test_path = os.path.join(search_path, icon_file)
                        if os.path.exists(test_path):
                            favorites_icon_path = test_path
                            break
                    if favorites_icon_path:
                        break
            
            # Crear caja horizontal para ícono + texto
            title_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
            title_hbox.set_halign(Gtk.Align.START)
            title_hbox.set_margin_start(5)
            
            # Agregar ícono si se encontró
            if favorites_icon_path:
                try:
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(favorites_icon_path, 24, 24)
                    icon_image = Gtk.Image.new_from_pixbuf(pixbuf)
                    title_hbox.pack_start(icon_image, False, False, 0)
                except Exception as e:
                    print(f"Error cargando ícono de favoritos: {e}")
                    # Fallback a emoji estrella
                    star_label = Gtk.Label(label="⭐")
                    title_hbox.pack_start(star_label, False, False, 0)
            else:
                # Si no hay ícono personalizado, usar emoji estrella
                star_label = Gtk.Label(label="⭐")
                title_hbox.pack_start(star_label, False, False, 0)
            
            # AGREGAR EL TEXTO "Favorites" después del ícono
            fav_text_label = Gtk.Label(label=TR.get('Favorites', 'Favorites'))
            fav_text_label.set_halign(Gtk.Align.START)
            fav_text_label.override_font(font_desc)  # Usar la misma fuente que antes
            title_hbox.pack_start(fav_text_label, False, False, 0)
            
            # En lugar de usar solo el label, usamos la caja horizontal
            # favorites_section_box.pack_start(fav_title_label, False, False, 2)
            favorites_section_box.pack_start(title_hbox, False, False, 2)
            
            # Contenedor para los botones de favoritos
            favorites_buttons_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            
            # Solo mostrar favoritos si NO están ocultos
            if not self.config['window'].get('hide_favorites', False):
                favorites = self.get_favorites()
                if favorites:
                    for fav in favorites:
                        # Crear estructura de datos consistente
                        fav_info = {
                            'Name': fav.get('name', 'App'),
                            'Exec': fav.get('exec', ''),
                            'Icon': fav.get('icon', 'star'),
                            'Comment': fav.get('name', 'App'),
                            'Terminal': False,
                            'Categories': []
                        }
                        
                        btn = Gtk.Button()
                        btn.set_relief(Gtk.ReliefStyle.NONE)
                        btn.get_style_context().add_class('social-button')
                        btn.set_size_request(40, -1)
                        
                        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
                        hbox.set_halign(Gtk.Align.START)
                        hbox.set_margin_start(5)
                        
                        icon_name = fav_info.get("Icon", "star")
                        
                        # Detectar si es una carpeta (para comandos como "pcmanfm '/ruta'")
                        exec_cmd = fav_info.get('Exec', '')
                        is_folder_fav = False
                        folder_path = None
                        
                        file_managers = ['pcmanfm', 'rox', 'thunar', 'nautilus', 'dolphin', 'caja', 'spacefm']
                        for fm in file_managers:
                            if exec_cmd.startswith(fm + ' '):
                                parts = exec_cmd.split(' ', 1)
                                if len(parts) > 1:
                                    potential_path = parts[1].strip().strip("'\"")
                                    folder_path = os.path.expanduser(potential_path)
                                    if os.path.isdir(folder_path):
                                        is_folder_fav = True
                                        break
                        
                        # También verificar si es una ruta directa
                        if not is_folder_fav:
                            test_path = exec_cmd.strip("'\"")
                            folder_path = os.path.expanduser(test_path)
                            if os.path.isdir(folder_path):
                                is_folder_fav = True
                        
                        if is_folder_fav:
                            # BUSCAR ÍCONOS DE CARPETA EN /usr/local/lib/X11/pixmaps/
                            folder_icon_path = None
                            search_paths = [
                                '/usr/local/lib/X11/pixmaps/',
                                '/usr/share/pixmaps/',
                                '/usr/share/icons/hicolor/48x48/places/',
                                '/usr/share/icons/Adwaita/48x48/places/'
                            ]
                            
                            # Lista de posibles nombres de archivos de íconos de carpeta
                            folder_icon_names = [
                                'folder.png', 'folder.svg', 'folder.xpm', 'folder48.png',
                                'folder-blue.png', 'folder-green.png', 'folder-red.png',
                                'folder-yellow.png', 'folder-documents.png', 'folder-downloads.png'
                            ]
                            
                            for search_path in search_paths:
                                if os.path.exists(search_path):
                                    for icon_file in folder_icon_names:
                                        test_path = os.path.join(search_path, icon_file)
                                        if os.path.exists(test_path):
                                            folder_icon_path = test_path
                                            break
                                    if folder_icon_path:
                                        break
                            
                            if folder_icon_path:
                                try:
                                    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(folder_icon_path, 24, 24)
                                    fav_icon = Gtk.Image.new_from_pixbuf(pixbuf)
                                except Exception as e:
                                    print(f"Error cargando ícono de carpeta {folder_icon_path}: {e}")
                                    fav_icon = Gtk.Image.new_from_icon_name("folder", Gtk.IconSize.DND)
                            else:
                                # Si no se encuentra ícono personalizado, usar el del tema
                                fav_icon = Gtk.Image.new_from_icon_name("folder", Gtk.IconSize.DND)
                        else:
                            # Para favoritos que no son carpetas (aplicaciones)
                            # Usar el sistema robusto de carga de íconos
                            try:
                                # Primero intentar con load_app_icon que tiene caché y fallbacks
                                icon_size = 24  # Tamaño para la columna de places
                                
                                # Verificar si es una ruta absoluta
                                if os.path.isabs(icon_name) and os.path.exists(icon_name):
                                    # Cargar desde archivo
                                    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                                        icon_name, icon_size, icon_size, True
                                    )
                                    fav_icon = Gtk.Image.new_from_pixbuf(pixbuf)
                                else:
                                    # Buscar ícono en las rutas del parser
                                    icon_path = self.find_icon_path(icon_name)
                                    if icon_path and os.path.exists(icon_path):
                                        # Cargar desde archivo encontrado
                                        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                                            icon_path, icon_size, icon_size, True
                                        )
                                        fav_icon = Gtk.Image.new_from_pixbuf(pixbuf)
                                    else:
                                        # Intentar desde tema de íconos
                                        try:
                                            theme = Gtk.IconTheme.get_default()
                                            pixbuf = theme.load_icon(
                                                icon_name, icon_size, Gtk.IconLookupFlags.FORCE_SIZE
                                            )
                                            fav_icon = Gtk.Image.new_from_pixbuf(pixbuf)
                                        except Exception as theme_error:
                                            print(f"No se encontró ícono {icon_name} en tema: {theme_error}")
                                            # Fallback a ícono genérico
                                            fav_icon = Gtk.Image.new_from_icon_name("application-x-executable", Gtk.IconSize.DND)
                            except Exception as e:
                                print(f"Error cargando ícono {icon_name}: {e}")
                                fav_icon = Gtk.Image.new_from_icon_name("application-x-executable", Gtk.IconSize.DND)
                        
                        fav_icon.set_pixel_size(24)
                        
                        fav_label = Gtk.Label(label=fav_info.get("Name", "App"))
                        fav_label.set_halign(Gtk.Align.START)
                        fav_label.override_font(font_desc)
                        
                        hbox.pack_start(fav_icon, False, False, 0)
                        hbox.pack_start(fav_label, True, True, 0)
                        btn.add(hbox)
                        
                        # Capturar comando y nombre directamente para evitar problemas de closure
                        btn.connect("clicked", lambda b, cmd=fav_info['Exec'], name=fav_info['Name'], 
                                   icon=fav_info['Icon'], comment=fav_info['Comment']: 
                                   self.on_app_clicked(b, {'Name': name, 'Exec': cmd, 'Icon': icon, 'Comment': comment}))
                        
                        favorites_buttons_box.pack_start(btn, False, False, 0)
            
            favorites_section_box.pack_start(favorites_buttons_box, False, False, 0)
            
            # Crear EventBox para toda la sección de favoritos
            favorites_event_box = Gtk.EventBox()
            favorites_event_box.add(favorites_section_box)
            favorites_event_box.add_events(Gdk.EventMask.ENTER_NOTIFY_MASK | Gdk.EventMask.LEAVE_NOTIFY_MASK)
            
            # Conectar eventos de hover a TODA la sección de favoritos
            favorites_event_box.connect("enter-notify-event", self.on_favorites_section_hover_enter)
            favorites_event_box.connect("leave-notify-event", self.on_favorites_section_hover_leave)
            
            places_box.pack_start(favorites_event_box, False, False, 0)
        
        # Scroll automático
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.add(places_box)
        
        return scrolled
    
    def on_favorites_section_hover_enter(self, widget, event):
        """Muestra los favoritos en la columna de aplicaciones al pasar el mouse sobre la sección"""
        
        # Cancelar cualquier timeout de categorías
        if self.hover_timeout:
            GLib.source_remove(self.hover_timeout)
            self.hover_timeout = None
        
        # Guardar la categoría actual antes de cambiar
        self.previous_category = self.current_category  # ← CAMBIAR ESTA LÍNEA (no "Favorites")
        self.showing_favorites = True
        self.just_left_favorites = False
        
        # Obtener favoritos
        favorites = self.get_favorites()
        if not favorites:
            return False
        
        # Limpiar la columna de aplicaciones
        if self.apps_flowbox:
            for child in self.apps_flowbox.get_children():
                child.destroy()
        
        # Convertir favoritos al formato de aplicación
        fav_apps = []
        for fav in favorites:
            fav_app = {
                'Name': fav.get('name', 'App'),
                'Exec': fav.get('exec', ''),
                'Icon': fav.get('icon', 'star'),
                'Comment': fav.get('name', 'App'),
                'Terminal': False,
                'Categories': ['Favorites']
            }
            fav_apps.append(fav_app)
        
        # Mostrar favoritos en la columna de aplicaciones
        for app_info in fav_apps:
            button = self.create_app_button(app_info)
            self.apps_flowbox.add(button)
        
        self.apps_flowbox.show_all()
        return False
    
    def on_favorites_section_hover_leave(self, widget, event):
        """Manejar salida de la sección de favoritos"""
        
        # Cancelar timeout existente si hay
        if hasattr(self, 'favorites_cleanup_timeout') and self.favorites_cleanup_timeout is not None:
            GLib.source_remove(self.favorites_cleanup_timeout)
            self.favorites_cleanup_timeout = None
        
        return False

                        
    def safe_execute(self, command):
            """Busca el comando real dentro del .desktop y lo ejecuta"""
            try:
                import re
                clean_cmd = re.sub(r'\s+%\w', '', command).replace('gtk-launch ', '').strip()
    
                if clean_cmd.endswith(".desktop"):
                    paths = ["/usr/share/applications/", "/usr/local/share/applications/", "/root/.local/share/applications/"]
                    for p in paths:
                        full_path = os.path.join(p, clean_cmd)
                        if os.path.exists(full_path):
                            with open(full_path, 'r') as f:
                                for line in f:
                                    if line.startswith("Exec="):
                                        clean_cmd = line.replace("Exec=", "").split('%')[0].strip()
                                        clean_cmd = clean_cmd.replace('"', '').replace("'", "")
                                        break
                            break
    
                subprocess.Popen(clean_cmd, shell=True, start_new_session=True,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self.hide() # En tu clase 'self' es la ventana
            except Exception as e:
                print(f"Error: {e}")
            
    def create_profile_section(self):
        """Crear sección de perfil compacta para la columna de Places"""
        profile_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        profile_box.set_halign(Gtk.Align.CENTER)
        
        # Botón de perfil
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
            profile_pic_size = self.config['window'].get('profile_pic_size', 64)
            profile_pic_shape = self.config['window'].get('profile_pic_shape', 'square')
            
            pixbuf = None
    
            if profile_pic_path and os.path.exists(profile_pic_path):
                try:
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                        profile_pic_path, profile_pic_size, profile_pic_size, True
                    )
                except Exception as e:
                    print(f"Error cargando .face: {e}")
    
            if pixbuf is None:
                icon_names = ["user-info", "avatar-default", "user-available", "system-users"]
                theme = Gtk.IconTheme.get_default()
                
                for name in icon_names:
                    if theme.has_icon(name):
                        try:
                            pixbuf = theme.load_icon(name, profile_pic_size, Gtk.IconLookupFlags.FORCE_SIZE)
                            break
                        except:
                            continue
    
            if pixbuf:
                if profile_pic_shape == 'circular':
                    pixbuf = apply_circular_mask(pixbuf)
                self.profile_image.set_from_pixbuf(pixbuf)
            else:
                self.profile_image.set_from_icon_name("image-missing", Gtk.IconSize.DIALOG)
        
        load_profile_image()
    
        def on_profile_clicked(button):
            profile_manager_path = self.config['paths'].get('profile_manager', "")
            if profile_manager_path:
                try:
                    GLib.timeout_add(100, lambda: Gtk.main_quit())
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
        
        # Nombre de usuario (hostname) - SOLO si no está oculto en la configuración
        if not self.config['window'].get('hide_hostname', False):
            hostname = self.get_hostname()
            username_label = Gtk.Label(label=hostname)
            username_label.set_halign(Gtk.Align.CENTER)
            
            font_description = Pango.FontDescription.from_string(self.config['font']['family'])
            font_description.set_size(self.config['font']['size_header'])
            username_label.override_font(font_description)
            
            use_gtk_theme = self.config['colors'].get('use_gtk_theme', False)
            if not use_gtk_theme:
                username_label.set_markup(f'<span color="{self.config["colors"]["text_header_os"]}"><b>{hostname}</b></span>')
            else:
                username_label.set_markup(f'<b>{hostname}</b>')
            
            profile_box.pack_start(username_label, False, False, 0)
        
        # Monitor de cambios en el archivo de perfil
        profile_pic_path = self.config['paths']['profile_pic']
        if profile_pic_path and os.path.exists(profile_pic_path):
            profile_file = Gio.File.new_for_path(profile_pic_path)
            monitor = profile_file.monitor_file(Gio.FileMonitorFlags.NONE, None)
            
            def on_file_changed(monitor, file, other_file, event_type):
                if event_type in (Gio.FileMonitorEvent.CHANGED, Gio.FileMonitorEvent.CREATED):
                    GLib.idle_add(load_profile_image)
            
            monitor.connect("changed", on_file_changed)
        
        return profile_box      
    
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
        if not category:
            return False
        
        # Si ya estamos en esta categoría Y NO mostrando favoritos, no hacer nada
        if category == self.current_category and not self.showing_favorites:
            return False
        
        # PASO 1: Cancelar timeout de favoritos si existe
        if hasattr(self, 'favorites_cleanup_timeout') and self.favorites_cleanup_timeout is not None:
            GLib.source_remove(self.favorites_cleanup_timeout)
            self.favorites_cleanup_timeout = None
        
        # PASO 2: Cancelar hover timeout anterior si existe
        if self.hover_timeout:
            GLib.source_remove(self.hover_timeout)
            self.hover_timeout = None
        
        if self.restore_timeout:
            GLib.source_remove(self.restore_timeout)
            self.restore_timeout = None
        
        # PASO 3: NUEVO - Programar activación con delay de 300ms
        # Esto da tiempo para que el mouse "pase de largo" sin activar la categoría
        def activate_category():
            self.hover_timeout = None
            self.showing_favorites = False
            self.hovered_category = category
            self.current_category = category
            self.show_category_applications(category)
            return False
        
        # Solo activar después de 300ms de estar sobre la categoría
        self.hover_timeout = GLib.timeout_add(250, activate_category)
        
        return False
        
    def _cleanup_favorites_state(self):
        """Función de limpieza para el estado de favoritos"""
        self.showing_favorites = False
        self.favorites_cleanup_timeout = None
        self.just_left_favorites = False
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
            """Create applications display area with optional integrated search bar"""
            # Contenedor principal vertical para apps + búsqueda opcional
            main_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            
            # Verificar si la búsqueda debe estar en esta columna
            search_container = self.config['window'].get('search_bar_container', 'window')
            search_position = self.config['window'].get('search_bar_position', 'bottom')
            
            # Si la búsqueda va arriba Y en esta columna, agregarla primero
            if search_container == 'apps_column' and search_position == 'top':
                search_and_buttons_box = self.create_search_and_buttons_box()
                main_container.pack_start(search_and_buttons_box, False, False, 0)
                main_container.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 0)
            
            # Área de aplicaciones con scroll
            scrolled = Gtk.ScrolledWindow()
            scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            
            self.apps_flowbox = Gtk.FlowBox()
            self.apps_flowbox.set_valign(Gtk.Align.START)
            self.apps_flowbox.set_max_children_per_line(30)
            self.apps_flowbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
            self.apps_flowbox.set_property("margin-left", 5)
            self.apps_flowbox.set_property("margin-right", 5)
            self.apps_flowbox.set_property("margin-top", 10)
            self.apps_flowbox.set_property("margin-bottom", 10)
            
            apps_eventbox = Gtk.EventBox()
            apps_eventbox.add(self.apps_flowbox)
            apps_eventbox.add_events(Gdk.EventMask.ENTER_NOTIFY_MASK)
            apps_eventbox.connect("enter-notify-event", self.on_apps_area_enter)
            
            self.apps_flowbox.connect("key-press-event", self.on_apps_key_press)
            
            scrolled.add(apps_eventbox)
            main_container.pack_start(scrolled, True, True, 0)
            
            # Si la búsqueda va abajo Y en esta columna, agregarla al final
            if search_container == 'apps_column' and search_position == 'bottom':
                main_container.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 0)
                search_and_buttons_box = self.create_search_and_buttons_box()
                main_container.pack_start(search_and_buttons_box, False, False, 0)
            
            # Cargar primera categoría
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
            
            return main_container
    
    def on_apps_area_enter(self, widget, event):
        """Handle mouse entering the applications area"""
        # Si estamos mostrando favoritos, NO hacer nada
        # Esto permite que puedas hacer clic en los favoritos
        if self.showing_favorites:
            return False
        
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
        
    def load_favorites_data(self):
        """Lee los favoritos del archivo JSON"""
        favs_list = []
        print(f"DEBUG: Buscando archivo de config: {CONFIG_FILE}")
        
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    print(f"DEBUG: Config cargada, favoritos: {config.get('favorites', [])}")
                    
                    for fav in config.get('favorites', []):
                        fav_item = {
                            "Name": fav.get('name', 'Fav'),
                            "Exec": fav.get('exec', ''),
                            "Icon": fav.get('icon', 'star'),
                            "Comment": fav.get('name', 'Fav'),
                            "Terminal": False,
                            "Categories": []
                        }
                        print(f"DEBUG: Favorito cargado: {fav_item['Name']} - {fav_item['Exec']}")
                        favs_list.append(fav_item)
            except Exception as e:
                print(f"Error en favoritos: {e}")
        else:
            print(f"ERROR: Archivo de configuración no existe: {CONFIG_FILE}")
            
        return favs_list
    
    def get_favorites(self):
            """Lee los favoritos reales del archivo JSON"""
            if os.path.exists(CONFIG_FILE):
                try:
                    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                        # Retornamos la lista de favoritos tal cual está en el JSON
                        return config.get('favorites', [])
                except Exception as e:
                    print(f"Error cargando favoritos: {e}")
            return []              
    
    def show_all_applications(self):
            """Muestra favoritos con sus nombres reales y luego el resto de apps"""
            if not self.apps_flowbox:
                return
            
            self.current_category = "All"
            
            # Limpiar iconos actuales
            for child in self.apps_flowbox.get_children():
                child.destroy()
            
            # --- CARGAR FAVORITOS ---
            favorites = self.get_favorites()
            for fav in favorites:
                # IMPORTANTE: Mapear exactamente las llaves del JSON a lo que el menú usa
                fav_info = {
                    "Name": fav.get('name', 'Sin nombre'), # Toma el nombre del configurador
                    "Exec": fav.get('exec', ''),           # Toma el comando
                    "Icon": fav.get('icon', 'exec'),       # Toma el icono
                    "is_favorite": True
                }
                
                # Llamamos a tu función de crear item con el nombre real
                item = self.create_app_item(fav_info["Name"], fav_info)
                if item:
                    self.apps_flowbox.add(item)
            
            # --- CARGAR EL RESTO DE APPS ---
            GLib.idle_add(self.load_applications_batch, list(self.applications.items()), 0)
            
            self.apps_flowbox.show_all()
    
    def show_category_applications(self, category):
        """Show applications from specific category with lazy loading"""
        if not self.apps_flowbox:
            return
        
        self.current_category = category
        
        # Limpiar apps actuales
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
            'librex': f"https://librex.terryiscool160.xyz/search.php?q={encoded_query}",
            'bing': f"https://www.bing.com/search?q={encoded_query}",
            'yahoo': f"https://search.yahoo.com/search?p={encoded_query}",
            'startpage': f"https://www.startpage.com/search?q={encoded_query}",
            'ecosia': f"https://www.ecosia.org/search?q={encoded_query}"
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
        """Handle application launch - Fix para carpetas forzadas y gtk-launch"""
        try:
            GLib.timeout_add(50, lambda: Gtk.main_quit())
            
            command = app_info.get('Exec', '')
            name = app_info.get('Name', 'Unknown')
            
            if not command:
                return
    
            # --- CORRECCIÓN DINÁMICA DE CARPETAS ---
            import re
            path_match = re.search(r'(/[^\s\']+)', command)
            if path_match:
                potential_path = os.path.expanduser(path_match.group(1))
                if os.path.isdir(potential_path):
                    print(f"🗂️ DEBUG: Detectada ruta en comando, abriendo con sistema: {potential_path}")
                    open_directory(potential_path)
                    return
            # ---------------------------------------
    
            # 🔧 FIX PARA GTK-LAUNCH
            if command.startswith('gtk-launch '):
                desktop_name = command.replace('gtk-launch ', '').strip()
                
                # Buscar el archivo .desktop en las rutas estándar
                desktop_paths = [
                    "/usr/share/applications/",
                    "/usr/local/share/applications/",
                    os.path.expanduser("~/.local/share/applications/")
                ]
                
                for base_path in desktop_paths:
                    desktop_file = os.path.join(base_path, desktop_name)
                    if not desktop_file.endswith('.desktop'):
                        desktop_file += '.desktop'
                    
                    if os.path.exists(desktop_file):
                        # Extraer el comando Exec= del archivo .desktop
                        try:
                            with open(desktop_file, 'r') as f:
                                for line in f:
                                    if line.startswith('Exec='):
                                        command = line.replace('Exec=', '').strip()
                                        # Limpiar parámetros %f, %F, %u, etc.
                                        command = re.sub(r'\s+%\w+', '', command)
                                        break
                        except Exception as e:
                            print(f"❌ Error leyendo {desktop_file}: {e}")
                        break
            
            # Limpiar el comando de parámetros .desktop
            command = re.sub(r'\s+%\w+', '', command).strip()
            
            print(f"▶️ Ejecutando comando: {command}")
            subprocess.Popen(command, 
                            shell=True,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            start_new_session=True)
            
        except Exception as e:
            print(f"❌ Error lanzando {name}: {e}")       
            
    def launch_application(self, app_info):
        """Función centralizada para lanzar cualquier aplicación"""
        try:
            GLib.timeout_add(50, lambda: Gtk.main_quit())
            
            command = app_info['Exec']
            print(f"DEBUG: Comando original: {command}")
            
            # Caso 1: Si el comando está vacío
            if not command or not command.strip():
                print(f"ERROR: Comando vacío para {app_info['Name']}")
                return
            
            # Limpiar parámetros de .desktop
            import re
            clean_command = re.sub(r'\s+%\w', '', command)
            clean_command = clean_command.strip()
            
            print(f"DEBUG: Comando limpio: {clean_command}")
            
            # Dividir el comando
            try:
                cmd_parts = shlex.split(clean_command)
            except ValueError:
                cmd_parts = clean_command.split()
            
            if not cmd_parts:
                print(f"ERROR: No se pudo dividir el comando")
                return
            
            print(f"DEBUG: Partes del comando: {cmd_parts}")
            
            # Verificar si es un comando especial (gtk-launch, xdg-open, etc)
            special_commands = ['gtk-launch', 'xdg-open', 'python', 'python3', 'sh', 'bash']
            
            # Si es un comando especial, mantenerlo completo
            if cmd_parts[0] in special_commands:
                print(f"DEBUG: Comando especial detectado: {cmd_parts[0]}")
                # No buscar en PATH, ejecutar directamente
                final_cmd = cmd_parts
            else:
                # Para comandos normales, verificar si existen
                executable = cmd_parts[0]
                
                if os.path.isabs(executable):
                    # Es ruta absoluta
                    if not os.path.exists(executable):
                        print(f"ERROR: Ejecutable no existe: {executable}")
                        return
                else:
                    # Buscar en PATH
                    found = False
                    for path_dir in os.environ.get('PATH', '').split(':'):
                        full_path = os.path.join(path_dir, executable)
                        if os.path.exists(full_path) and os.access(full_path, os.X_OK):
                            cmd_parts[0] = full_path
                            found = True
                            break
                    
                    if not found:
                        print(f"DEBUG: '{executable}' no encontrado en PATH, intentando igual")
                
                final_cmd = cmd_parts
            
            print(f"DEBUG: Comando final: {final_cmd}")
            
            # Ejecutar
            subprocess.Popen(final_cmd,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            start_new_session=True)
            
            print(f"✅ Aplicación lanzada: {app_info['Name']}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()                 
            
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
