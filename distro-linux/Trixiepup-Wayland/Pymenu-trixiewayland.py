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

# Import the pango module using GObject Introspection
gi.require_version('Pango', '1.0')
from gi.repository import Pango

PROFILE_PIC = "/root/.face"
PROFILE_MANAGER = "/usr/local/bin/ProfileManager.py"
SHUTDOWN_CMD = "/usr/local/bin/apagado-avatar.py"
CONFIG_FILE = "/root/.config/pymenu.json"

class ConfigManager:
    """Manages reading and writing the application's JSON configuration."""
    def __init__(self, config_file=CONFIG_FILE):
        self.config_file = config_file
        self.config = self.load_config()

    def get_default_config(self):
        """Return the default configuration matching the current script's aesthetics."""
        return {
            "window": {
                "width": 700,
                "height": 850,
                "halign": "center",
                "icon_size": 32,
                "profile_pic_size": 128
            },
            "font": {
                "family": "sans-serif",
                "size_categories": 15000,
                "size_names": 10000,
                "size_header": 16000
            },
            "colors": {
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
                "profile_pic": "/root/.face",
                "profile_manager": "/usr/local/bin/ProfileManager.py",
                "shutdown_cmd": "/usr/local/bin/apagado-avatar.py"
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


class OpenboxMenuParser:
    """Parses an Openbox menu.xml file to extract applications."""
    def __init__(self, menu_file="/root/.config/labwc/menu.xml"):
        self.menu_file = menu_file
        self.applications = {}
        self.icon_paths = [
            "/usr/share/pixmaps",
            "/usr/share/icons/hicolor/48x48/apps",
            "/usr/share/icons/hicolor/32x32/apps",
            "/usr/share/icons/hicolor/64x64/apps",
            "/usr/local/lib/X11/pixmaps",
            "/usr/share/pixmaps/puppy",
            "/usr/share/pixmaps/puppy"
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
        """Dummy function for compatibility, Openbox doesn't have a tray in the same way."""
        return self.tray_config
        
    def parse_jwm_menu(self):
        """Parse the Openbox menu file and extract applications."""
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
                
                if not label and menu_id:
                    continue

                apps = self.extract_items_from_menu(menu)
                if apps:
                    applications[label] = apps
            
            # Handle root-level items like Help and Leave from the root-menu block
            root_menu = root.find('.//menu[@id="root-menu"]')
            if root_menu:
                for item in root_menu.findall('./item'):
                    label = item.get('label', '')
                    command = item.findtext('./action/command', '').strip()
                    icon = item.get('icon', '')
                    
                    if not label or not command:
                        continue
                    
                    app_info = {
                        'Name': label,
                        'Exec': command,
                        'Icon': icon,
                        'Comment': label,
                        'Terminal': 'terminal' in command.lower() or 'urxvt' in command.lower(),
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

    def extract_icon_paths(self, root):
        """Dummy function for compatibility. Openbox doesn't define paths this way."""
        return self.icon_paths

    def extract_items_from_menu(self, menu_element):
        """Extract application items from a menu element."""
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
        """Fallback applications if parsing fails."""
        return {
            'System': [
                {'Name': 'Terminal', 'Exec': 'lxterminal', 'Icon': 'terminal', 'Comment': 'Terminal emulator', 'Terminal': False, 'Categories': []},
                {'Name': 'File Manager', 'Exec': 'spacefm', 'Icon': 'spacefm', 'Comment': 'File manager', 'Terminal': False, 'Categories': []},
            ],
            'Internet': [
                {'Name': 'Firefox', 'Exec': 'firefox', 'Icon': 'firefox', 'Comment': 'Web browser', 'Terminal': False, 'Categories': []},
            ]
        }
        
class ArcMenuLauncher(Gtk.Window):
    def __init__(self, icon_size=None, jwm_file=None, x=None, y=None):
        super().__init__(title="ArcMenu Launcher")
        
        self.config_manager = ConfigManager()
        self.config = self.config_manager.config
        
        # Use icon_size from config, or fallback to default
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
        
        self.menu_file = Gio.File.new_for_path(self.parser.menu_file)
        self.file_monitor = self.jwm_file.monitor_file(Gio.FileMonitorFlags.NONE, None)
        self.file_monitor.connect("changed", self.on_jwm_file_changed)
        print(f"Now monitoring JWM file for changes: {jwm_file_path}")

    def apply_css(self):
        """Loads and applies CSS from the configuration."""
        colors = self.config['colors']
        
        css = f"""
        GtkWindow, GtkEventBox {{
            background-color: {colors['background']};
            border-radius: 0px;
            box-shadow: none;
            border: none;
        }}
    
        .menu-window {{
            background-color: {colors['background']};
            border-radius: 12px;
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
            padding: 5px;
            background-color: {colors['button_normal_background']};
            color: {colors['button_text']};
            border: none;
        }}
        
        listbox row.selected-category {{
            background-color: {colors['selected_background']};
            color: {colors['selected_text']};
        }}
    
        button:hover {{
            background-color: {colors['hover_background']};
        }}

        .app-box {{
            min-width: {self.icon_size + 30}px;
        }}
        """
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
                
    def calculate_menu_position(self):
        """Calculate menu position based on config and screen size"""
        display = Gdk.Display.get_default()
        monitor = display.get_primary_monitor()
        geometry = monitor.get_geometry()
        
        screen_width = geometry.width
        screen_height = geometry.height
        
        menu_width = self.config['window']['width']
        menu_height = self.config['window']['height']
        
        # New logic to read 'halign' from config
        menu_halign = self.config['window'].get('halign', None)
        
        if menu_halign == 'left':
            x = 10
        elif menu_halign == 'right':
            x = screen_width - menu_width - 10
        else: # Defaults to 'center' or existing JWM logic
            tray_halign = self.tray_config['halign']
            if tray_halign == 'left':
                x = 10
            elif tray_halign == 'right':
                x = screen_width - menu_width - 10
            else:
                x = (screen_width - menu_width) // 2
        
        tray_height = self.tray_config['height']
        tray_valign = self.tray_config['valign']
        
        if tray_valign == 'top':
            y = tray_height 
        elif tray_valign in ['bottom', 'buttom']:
            y = screen_height - tray_height - menu_height 
        else:
            y = (screen_height - menu_height) // 2
        
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
            print(f"Positioning menu at ({x}, {y}) based on tray config: {self.tray_config}")
    
        self.set_resizable(False)
        self.set_decorated(False)
        self.set_app_paintable(True)
        self.set_type_hint(Gdk.WindowTypeHint.DOCK)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.connect("key-press-event", self.on_key_press)
        self.connect("focus-out-event", self.on_focus_out)
        self.connect("button-press-event", self.on_button_press)
    
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
            
        return False
 
    def on_key_press(self, widget, event):
        """Close window with Escape key"""
        if event.keyval == Gdk.KEY_Escape:
            Gtk.main_quit()
            return True
        return False
    
    def on_focus_out(self, widget, event):
        """Close window when it loses focus"""
        Gtk.main_quit()
        return False
                    
    def create_interface(self):
        """Create the main interface"""
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        main_box.get_style_context().add_class('menu-window')
        self.add(main_box)
    
        header_box = self.create_header()
        main_box.pack_start(header_box, False, False, 0)
    
        main_box.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 0)
    
        content_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        main_box.pack_start(content_box, True, True, 0)
    
        content_box.pack_start(self.create_categories_sidebar(), False, False, 0)
        content_box.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, False, 0)
        content_box.pack_start(self.create_applications_area(), True, True, 0)
    
        main_box.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 0)
    
        bottom_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        bottom_box.set_margin_top(6)
        bottom_box.set_margin_bottom(6)
        bottom_box.set_margin_start(10)
        bottom_box.set_margin_end(10)
    
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search applications...")
        self.search_entry.connect("search-changed", self.on_search_changed)
        self.search_entry.set_size_request(200, 30)
        bottom_box.pack_start(self.search_entry, True, True, 0)
        
        # ---- Botón de apagado ----
        shutdown_button = Gtk.Button()
        shutdown_icon_label = Gtk.Label()
        shutdown_icon_label.set_markup('<span font="Terminess Nerd Font Propo 16">󰤁</span>')
        shutdown_button.add(shutdown_icon_label)
        shutdown_button.set_tooltip_text("Shutdown")  # Tooltip agregado
        shutdown_button.connect("clicked", self.on_shutdown_clicked)
        bottom_box.pack_end(shutdown_button, False, False, 0)
        
        # ---- Nuevo botón de navegador ----
        browser_button = Gtk.Button()
        browser_icon_label = Gtk.Label()
        browser_icon_label.set_markup('<span font="Terminess Nerd Font Propo 16">󰜏</span>')
        browser_button.add(browser_icon_label)
        browser_button.set_tooltip_text("Search in the web")  # Tooltip agregado
        browser_button.connect("clicked", self.on_browser_search_clicked)
        bottom_box.pack_end(browser_button, False, False, 0)
        
        # ---- Botón de configuración ----
        config_button = Gtk.Button()
        config_icon_label = Gtk.Label()
        config_icon_label.set_markup('<span font="Terminess Nerd Font Propo 16"></span>')  # O la polea: 
        config_button.add(config_icon_label)
        config_button.set_tooltip_text("Pymenu config")  # Tooltip agregado
        config_button.connect("clicked", self.on_config_clicked)
        bottom_box.pack_end(config_button, False, False, 0)
        
        main_box.pack_end(bottom_box, False, False, 0)
        
        self.show_all()
        self.search_entry.grab_focus()

        
    def create_header(self):
        """Create the top header with profile picture, OS, kernel, and hostname"""
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=115)
        header_box.set_margin_top(1)
        header_box.set_margin_bottom(1)
        header_box.set_margin_start(5)
        header_box.set_margin_end(5)
    
        profile_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        profile_box.set_valign(Gtk.Align.CENTER)
        
        profile_button = Gtk.Button()
        profile_button.set_relief(Gtk.ReliefStyle.NONE)
        
        self.profile_image = Gtk.Image()
        profile_button.add(self.profile_image)
        
        def load_profile_image():
            profile_pic_path = self.config['paths']['profile_pic']
            profile_pic_size = self.config['window'].get('profile_pic_size', 128)
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(profile_pic_path, profile_pic_size, profile_pic_size, True)
                self.profile_image.set_from_pixbuf(pixbuf)
            except Exception as e:
                print(f"Failed to load profile picture: {e}")
                self.profile_image.set_from_icon_name("avatar-default", Gtk.IconSize.DIALOG)
        
        load_profile_image()
        
        def on_profile_clicked(button):
            try:
                GLib.timeout_add(100, lambda: Gtk.main_quit())
                profile_manager_path = self.config['paths']['profile_manager']
                if os.path.exists(profile_manager_path):
                    subprocess.Popen([profile_manager_path],
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL)
                else:
                    subprocess.Popen(["python3", profile_manager_path], 
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL)
                print(f"Launching Profile Manager: {profile_manager_path}")
            except Exception as e:
                print(f"Error opening Profile Manager: {e}")
        
        profile_button.connect("clicked", on_profile_clicked)
        profile_box.pack_start(profile_button, False, False, 0)
        header_box.pack_start(profile_box, False, False, 0)
        
        system_info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        system_info_box.set_valign(Gtk.Align.CENTER)
        
        os_name, kernel = self.get_os_info()
        hostname = self.get_hostname()
        
        header_font_string = self.config['font']['family']
        header_font_description = Pango.FontDescription(header_font_string)
        
        os_label = Gtk.Label()
        os_label.set_markup(f'<span color="{self.config["colors"]["text_header_os"]}"><b>{os_name}</b></span>')
        os_label.override_font(header_font_description)
        os_label.set_halign(Gtk.Align.START)
        os_label.set_ellipsize(3)
        os_label.set_max_width_chars(30)
        system_info_box.pack_start(os_label, False, False, 0)
        
        kernel_label = Gtk.Label()
        kernel_label.set_markup(f'<span color="{self.config["colors"]["text_header_kernel"]}"> {kernel}</span>')
        kernel_label.override_font(header_font_description)
        kernel_label.set_halign(Gtk.Align.START)
        kernel_label.set_ellipsize(3)
        kernel_label.set_max_width_chars(30)
        system_info_box.pack_start(kernel_label, False, False, 0)

        hostname_label = Gtk.Label()
        hostname_label.set_markup(f'<span color="{self.config["colors"]["text_header_hostname"]}"> {hostname}</span>')
        hostname_label.override_font(header_font_description)
        hostname_label.set_halign(Gtk.Align.START)
        hostname_label.set_ellipsize(3)
        hostname_label.set_max_width_chars(30)
        system_info_box.pack_start(hostname_label, False, False, 0)
        
        header_box.pack_start(system_info_box, True, True, 0)
    
        profile_file = Gio.File.new_for_path(self.config['paths']['profile_pic'])
        monitor = profile_file.monitor_file(Gio.FileMonitorFlags.NONE, None)
        
        def on_file_changed(monitor, file, other_file, event_type):
            if event_type in (Gio.FileMonitorEvent.CHANGED, Gio.FileMonitorEvent.CREATED):
                GLib.idle_add(load_profile_image)
        
        monitor.connect("changed", on_file_changed)
        
        return header_box


    def create_categories_sidebar(self):
        """Create categories sidebar with improved hover functionality"""
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_size_request(175, -1)
        
        self.categories_listbox = Gtk.ListBox()
        self.categories_listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.categories_listbox.connect("row-activated", self.on_category_clicked)
    
        category_icons = {
            'Desktop': 'preferences-desktop',
            'System': 'applications-system',
            'Setup': 'preferences-system',
            'Utility': 'applications-utilities',
            'Filesystem': 'folder',
            'Graphic': 'applications-graphics',
            'Document': 'x-office-document',
            'Business': 'x-office-spreadsheet',
            'Personal': 'x-office-calendar',
            'Network': 'applications-internet',
            'Internet': 'applications-internet',
            'Multimedia': 'applications-multimedia',
            'Fun': 'applications-games',
            'Help': 'help-browser',
            'Leave': 'system-shutdown',
        }
    
        preferred_order = ['Desktop', 'System', 'Setup', 'Utility', 'Filesystem', 
                           'Graphic', 'Document', 'Business', 'Personal', 
                           'Network', 'Internet', 'Multimedia', 'Fun', 'Help', 'Leave']
    
        added_categories = set()
        for category in preferred_order:
            if category in self.applications and self.applications[category]:
                self.add_category_row(category, category_icons.get(category, 'applications-other'))
                added_categories.add(category)
    
        for category in sorted(self.applications.keys()):
            if category not in added_categories and self.applications[category]:
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
        
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)  # Reducido de 10
        box.set_property("margin-left", 8)    # Reducido de 10
        box.set_property("margin-right", 8)   # Reducido de 10
        box.set_property("margin-top", 3)     # Reducido de 8
        box.set_property("margin-bottom", 3)  # Reducido de 8
    
        icon = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.MENU)
        box.pack_start(icon, False, False, 0)
    
        label = Gtk.Label()
        font_description = Pango.FontDescription(self.config['font']['family'])
        font_description.set_size(self.config['font']['size_categories'])
        label.override_font(font_description)
        label.set_markup(f"<span foreground='{self.config['colors']['text_normal']}'>{category}</span>")
        label.set_halign(Gtk.Align.START)
        box.pack_start(label, True, True, 0)
    
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
        self.apps_flowbox.set_property("margin-left", 10)
        self.apps_flowbox.set_property("margin-right", 10)
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
        box.set_property("margin-left", 5)
        box.set_property("margin-right", 5)
        box.set_property("margin-top", 5)
        box.set_property("margin-bottom", 5)
        
        # Ícono de la aplicación
        icon = self.load_app_icon(app_info.get('Icon', 'application-x-executable'))
        box.pack_start(icon, False, False, 0)
        
        # Nombre de la aplicación
        name_label = Gtk.Label(label=app_info['Name'])
        
        # Estilo de fuente
        font_description = Pango.FontDescription(self.config['font']['family'])
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
        
        return button

    
    def load_app_icon(self, icon_name):
        """Carga el ícono de la aplicación con caché y un sistema robusto de fallbacks."""
        if not icon_name:
            icon_name = "application-x-executable"

        cache_key = f"{icon_name}_{self.icon_size}"
        if cache_key in self.icon_cache:
            return self.icon_cache[cache_key]

        icon_theme = Gtk.IconTheme.get_default()
        clean_name = os.path.splitext(os.path.basename(icon_name))[0]
        icon_candidates = [clean_name, clean_name.lower(), icon_name]

        for candidate in icon_candidates:
            try:
                if icon_theme.has_icon(candidate):
                    # Forzar el tamaño para que se redimensione
                    icon_info = icon_theme.lookup_icon(candidate, self.icon_size, Gtk.IconLookupFlags.FORCE_SIZE)
                    if icon_info:
                        pixbuf = icon_info.load_icon()
                        if pixbuf:
                            image = Gtk.Image.new_from_pixbuf(pixbuf)
                            self.icon_cache[cache_key] = image
                            return image
            except Exception:
                continue

        icon_path = self.find_icon_path(icon_name)
        if icon_path and os.path.exists(icon_path):
            try:
                if self.icon_size <= 32:
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(icon_path, self.icon_size, self.icon_size, True)
                    image = Gtk.Image.new_from_pixbuf(pixbuf)
                    self.icon_cache[cache_key] = image
                    return image
                else:
                    resized_icon = self.resize_icon_with_magick(icon_path)
                    if resized_icon:
                        try:
                            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(resized_icon, self.icon_size, self.icon_size, True)
                            image = Gtk.Image.new_from_pixbuf(pixbuf)
                            self.icon_cache[cache_key] = image
                            return image
                        finally:
                            try:
                                os.unlink(resized_icon)
                            except:
                                pass
            except Exception as e:
                pass

        try:
            image = Gtk.Image.new_from_icon_name("application-x-executable", Gtk.IconSize.BUTTON)
            self.icon_cache[cache_key] = image
            return image
        except:
            image = Gtk.Image()
            self.icon_cache[cache_key] = image
            return image
    
    def find_icon_path(self, icon_name):
        """Find icon in the defined icon paths"""
        if os.path.isabs(icon_name):
            return icon_name if os.path.exists(icon_name) else None
        
        extensions = ['.png', '.svg', '.xpm', '.ico', '.jpg', '.jpeg', '.gif', '']
        
        for path in self.parser.icon_paths:
            if not os.path.exists(path):
                continue
            
            for ext in extensions:
                full_path = os.path.join(path, icon_name + ext)
                if os.path.exists(full_path) and self.is_valid_image_file(full_path):
                    return full_path
            
            try:
                for filename in os.listdir(path):
                    if filename.startswith(icon_name):
                        full_path = os.path.join(path, filename)
                        if os.path.isfile(full_path) and self.is_valid_image_file(full_path):
                            return full_path
            except (OSError, PermissionError):
                continue
        
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

    def resize_icon_with_magick(self, icon_path):
        """Resize icon using ImageMagick if available"""
        try:
            result = subprocess.run(['which', 'magick'], capture_output=True, timeout=5)
            magick_cmd = 'magick' if result.returncode == 0 else 'convert'
            if magick_cmd == 'convert':
                result = subprocess.run(['which', 'convert'], capture_output=True, timeout=5)
                if result.returncode != 0:
                    return None
            
            temp_dir = '/tmp'
            temp_file = os.path.join(temp_dir, f"resized_icon_{os.getpid()}_{hash(icon_path)}_{self.icon_size}.png")
            if os.path.exists(temp_file):
                return temp_file
            
            _, ext = os.path.splitext(icon_path.lower())
            
            if ext == '.svg':
                cmd = [magick_cmd, '-background', 'none', icon_path, '-resize', f'{self.icon_size}x{self.icon_size}', '-flatten', temp_file]
            else:
                cmd = [magick_cmd, icon_path, '-resize', f'{self.icon_size}x{self.icon_size}', temp_file]
            
            result = subprocess.run(cmd, capture_output=True, timeout=15, env={**os.environ, 'MAGICK_CONFIGURE_PATH': ''})
            
            if os.path.exists(temp_file) and os.path.getsize(temp_file) > 0:
                return temp_file
            elif result.returncode != 0:
                stderr = result.stderr.decode()
                if not any(warn in stderr for warn in ['linearGradient', 'radialGradient', 'warning/color.c']):
                    print(f"ImageMagick failed for {icon_path}: {stderr}")
                
        except subprocess.TimeoutExpired:
            print(f"ImageMagick timeout for {icon_path}")
        except Exception as e:
            print(f"ImageMagick resize failed for {icon_path}: {e}")
        
        return None
    
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
        search_url = f"https://www.google.com/search?q={encoded_query}"
        
        try:
            print(f"Launching browser search for: '{search_query}'")
            # Use xdg-open to launch the default browser
            subprocess.Popen(["xdg-open", search_url], 
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
            # Close the menu after launching the browser
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

    def on_profile_clicked(self, button):
        """Open ProfileManager when profile thumbnail is clicked"""
        try:
            GLib.timeout_add(100, lambda: Gtk.main_quit())
            profile_manager_path = self.config['paths']['profile_manager']
            if os.path.exists(profile_manager_path):
                subprocess.Popen([profile_manager_path], 
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
            else:
                subprocess.Popen(["python3", profile_manager_path], 
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
            print(f"Launching Profile Manager: {profile_manager_path}")
        except Exception as e:
            print(f"Error opening Profile Manager: {e}")
            
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
        """Run shutdown command"""
        try:
            GLib.timeout_add(100, lambda: Gtk.main_quit())
            shutdown_cmd_path = self.config['paths']['shutdown_cmd']
            if os.path.exists(shutdown_cmd_path):
                subprocess.Popen([shutdown_cmd_path],
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
            else:
                subprocess.Popen(["python3", shutdown_cmd_path],
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
            print(f"Launching shutdown command: {shutdown_cmd_path}")
        except Exception as e:
            print(f"Failed to run shutdown command: {e}")
            
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
