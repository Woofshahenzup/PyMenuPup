# PyMenuPup - Technical Documentation

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Core Components](#core-components)
3. [Menu Parsing System](#menu-parsing-system)
4. [Configuration System](#configuration-system)
5. [Icon Loading and Caching](#icon-loading-and-caching)
6. [UI Rendering](#ui-rendering)
7. [Window Manager Detection](#window-manager-detection)
8. [Event Handling](#event-handling)
9. [Performance Optimizations](#performance-optimizations)
10. [Internationalization](#internationalization)

---

## Architecture Overview

PyMenuPup is built using **GTK3** via **GObject Introspection (PyGObject)**. The application follows a modular architecture with three main layers:

```
┌─────────────────────────────────┐
│   User Interface Layer          │
│   (GTK3 Widgets)                │
├─────────────────────────────────┤
│   Business Logic Layer          │
│   (Parsing, Config, Navigation) │
├─────────────────────────────────┤
│   System Integration Layer      │
│   (JWM/Openbox, File Monitoring)│
└─────────────────────────────────┘
```

### Key Design Patterns

- **Singleton Pattern**: `ConfigManager` ensures one configuration instance
- **Observer Pattern**: File monitoring with `Gio.FileMonitor`
- **Lazy Loading**: Applications load in batches to prevent UI freezing
- **Cache Strategy**: Icon pixbufs are cached to improve performance

---

## Core Components

### 1. `JWMMenuParser`

This class is responsible for parsing menu files from either JWM or Openbox/labwc.

**Key Methods:**

```python
def parse_jwm_menu(self):
    """Parse JWM XML menu file and extract applications"""
    # Uses ElementTree to parse XML
    # Normalizes category names using CATEGORY_MAP
    # Returns dict: {'Category': [app_info, ...]}
```

**XML Structure Handled:**

```xml
<JWM>
  <Menu label="System">
    <Program label="Terminal" icon="terminal">
      lxterminal
    </Program>
  </Menu>
</JWM>
```

**Normalization Example:**

```python
CATEGORY_MAP = {
    'Escritorio': 'Desktop',
    'Sistema': 'System',
    # ... ensures consistent category naming
}
```

---

### 2. `ConfigManager`

Manages JSON configuration with automatic migration and validation.

**Configuration Structure:**

```json
{
  "window": {
    "width": 477,
    "height": 427,
    "icon_size": 32,
    "profile_pic_shape": "square"
  },
  "colors": {
    "use_gtk_theme": false,
    "background": "rgba(0, 0, 0, 0.7)"
  },
  "paths": {
    "profile_pic": "/root/.face",
    "jwmrc_tray": "/root/.jwmrc-tray"
  }
}
```

**Automatic Migration:**

```python
def load_config(self):
    # Merges user config with default config
    # Ensures all keys exist even after updates
    for key in default_config:
        if key not in config:
            config[key] = default_config[key]
```

---

## Menu Parsing System

### Dual Parser Support

PyMenuPup detects the window manager and chooses the appropriate parser:

```python
def detect_window_manager():
    """
    Reads /etc/windowmanager to detect WM
    Returns 'openbox' or 'jwm'
    """
    try:
        with open('/etc/windowmanager', 'r') as f:
            wm_content = f.read().strip().lower()
            if 'openbox-session' in wm_content:
                return 'openbox'
    except:
        pass
    return 'jwm'
```

### Icon Path Resolution

The parser builds a list of icon search paths:

```python
def extract_icon_paths(self, root):
    paths = []
    # Parse from JWM config
    for iconpath in root.findall('.//IconPath'):
        paths.append(iconpath.text.strip())
    
    # Add fallback paths
    default_paths = [
        "/usr/local/lib/X11/pixmaps",
        "/usr/share/pixmaps",
        "/usr/share/icons/hicolor/48x48/apps"
    ]
    
    return paths + default_paths
```

### Category Organization

Applications are organized with preferred ordering:

```python
preferred_order = [
    'Desktop', 'System', 'Setup', 'Utility', 
    'Filesystem', 'Graphic', 'Document', 'Business',
    'Personal', 'Network', 'Internet', 'Multimedia',
    'Fun', 'Help', 'Leave'
]
```

---

## Configuration System

### Dynamic CSS Generation

CSS is generated from JSON configuration:

```python
def apply_css(self):
    use_gtk_theme = self.config['colors'].get('use_gtk_theme', False)
    
    if use_gtk_theme:
        # Use system theme colors
        css = """
        .menu-window {
            background-color: @theme_bg_color;
        }
        """
    else:
        # Use custom colors from config
        colors = self.config['colors']
        css = f"""
        .menu-window {{
            background-color: {colors['background']};
            border: 1px solid {colors['border']};
        }}
        """
```

### Window Positioning

Smart positioning based on tray configuration:

```python
def calculate_menu_position(self):
    tray_height = self.tray_config.get('height', 0)
    tray_valign = self.tray_config.get('valign', 'center')
    
    if tray_valign == 'top':
        y = tray_height
    elif tray_valign == 'bottom':
        y = screen_height - tray_height - menu_height
    else:
        y = (screen_height - menu_height) // 2
    
    return x, y
```

---

## Icon Loading and Caching

### Three-Tier Icon Loading

```python
def load_app_icon(self, icon_name):
    cache_key = f"{icon_name}_{self.icon_size}"
    
    # 1. Check cache
    if cache_key in self.icon_cache:
        return Gtk.Image.new_from_pixbuf(self.icon_cache[cache_key])
    
    # 2. Try icon theme
    try:
        pixbuf = Gtk.IconTheme.get_default().load_icon(
            icon_name, self.icon_size, Gtk.IconLookupFlags.FORCE_SIZE
        )
    except:
        pixbuf = None
    
    # 3. Try file path
    if pixbuf is None:
        icon_path = self.find_icon_path(icon_name)
        if icon_path:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                icon_path, self.icon_size, self.icon_size, True
            )
    
    # 4. Fallback icon
    if pixbuf is None:
        pixbuf = Gtk.IconTheme.get_default().load_icon(
            "application-x-executable", self.icon_size
        )
    
    # Cache and return
    self.icon_cache[cache_key] = pixbuf
    return Gtk.Image.new_from_pixbuf(pixbuf)
```

### Circular Profile Picture Mask

Using Cairo to create circular masks:

```python
def apply_circular_mask(pixbuf):
    size = min(pixbuf.get_width(), pixbuf.get_height())
    
    # Create mask surface
    mask_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    mask_cr = cairo.Context(mask_surface)
    
    # Draw white circle
    center = size / 2.0
    radius = size / 2.0
    mask_cr.arc(center, center, radius, 0, 2 * math.pi)
    mask_cr.set_source_rgba(1, 1, 1, 1)
    mask_cr.fill()
    
    # Apply mask with DEST_IN operator
    final_cr.set_operator(cairo.OPERATOR_DEST_IN)
    final_cr.paint()
    
    return Gdk.pixbuf_get_from_surface(final_surface, 0, 0, size, size)
```

---

## UI Rendering

### Lazy Loading Strategy

Applications load in batches to prevent UI freezing:

```python
def load_applications_batch(self, apps_data, start_index, batch_size=10):
    count = 0
    
    for category, apps in apps_data:
        for i, app in enumerate(apps[start_index:], start_index):
            if count >= batch_size:
                # Schedule next batch
                GLib.idle_add(
                    self.load_applications_batch, 
                    [(category, apps)], 
                    i
                )
                return False
            
            button = self.create_app_button(app)
            self.apps_flowbox.add(button)
            count += 1
    
    self.apps_flowbox.show_all()
    return False
```

### Category Selection States

Three selection states are maintained:

```python
self.selected_category      # Permanently selected (by click)
self.hovered_category       # Temporarily hovered
self.current_category       # Currently displayed
```

**State Machine:**

```
User hovers → Preview (150ms delay)
User clicks  → Permanent selection
Mouse leaves → Restore to selected (150ms delay)
```

---

## Window Manager Detection

### Automatic WM Detection

```python
def detect_window_manager():
    try:
        with open('/etc/windowmanager', 'r') as f:
            content = f.read().strip().lower()
            if 'openbox' in content:
                return 'openbox'
    except:
        pass
    return 'jwm'
```

### Tray Configuration Parsing

**For Tint2:**

```python
def parse_tray_config(self):
    # Read tint2rc
    if 'panel_size' in line:
        tray_info['height'] = int(parts[1])
    
    if 'panel_position' in line:
        tray_info['valign'] = pos_parts[0]  # top/bottom
        tray_info['halign'] = pos_parts[1]  # left/center/right
```

**For JWM:**

```python
# Parse XML <Tray> element
tray_element = root.find('.//Tray')
tray_info['height'] = int(tray_element.get('height', '30'))
tray_info['valign'] = tray_element.get('valign', 'bottom')
```

---

## Event Handling

### Focus Management

```python
def on_focus_out(self, widget, event):
    """Close menu when it loses focus"""
    if not self.is_resizing and not self.context_menu_active:
        Gtk.main_quit()
    return False
```

### Keyboard Navigation

```python
def on_apps_key_press(self, widget, event):
    keyval = event.keyval
    
    if keyval == Gdk.KEY_Down:
        self.navigate_apps(keyval)
    elif keyval == Gdk.KEY_Return:
        self.launch_selected_app()
    elif keyval == Gdk.KEY_Escape:
        Gtk.main_quit()
```

### File Monitoring

```python
# Monitor JWM config for changes
self.file_monitor = self.jwm_file.monitor_file(
    Gio.FileMonitorFlags.NONE, None
)
self.file_monitor.connect("changed", self.on_jwm_file_changed)

def on_jwm_file_changed(self, monitor, file, other_file, event_type):
    if event_type == Gio.FileMonitorEvent.CHANGES_DONE_HINT:
        # Reload applications
        self.applications = self.parser.parse_jwm_menu()
        self.recreate_interface()
```

---

## Performance Optimizations

### 1. Icon Caching

```python
self.icon_cache = {}  # Format: {"{name}_{size}": GdkPixbuf}
```

**Benefit:** Prevents reloading the same icon multiple times.

### 2. Batch Rendering

Applications render in batches of 10 to keep UI responsive:

```python
GLib.idle_add(self.load_applications_batch, apps_data, 0)
```

### 3. Delayed Focus Grab

```python
GLib.timeout_add(100, self.delayed_focus_grab)
```

Prevents placeholder text from disappearing immediately.

### 4. Smart Search

Only recreates widgets that match search:

```python
def on_search_changed(self, search_entry):
    search_text = search_entry.get_text().lower()
    
    if not search_text:
        self.show_category_applications(self.current_category)
        return
    
    # Only show matching apps
    for app in apps:
        if search_text in app['Name'].lower():
            button = self.create_app_button(app)
            self.apps_flowbox.add(button)
```

---

## Internationalization

### Translation System

```python
LANG = {
    'en': {
        'Search applications...': 'Search applications...',
        'Shutdown': 'Shutdown'
    },
    'es': {
        'Search applications...': 'Buscar aplicaciones...',
        'Shutdown': 'Apagar'
    }
}

def get_translation_texts():
    sys_locale = locale.getlocale()
    lang_code = sys_locale[0].split('_')[0]
    return LANG.get(lang_code, LANG['en'])

TR = get_translation_texts()
```

### Category Name Normalization

```python
CATEGORY_MAP = {
    'Escritorio': 'Desktop',
    'Sistema': 'System',
    # Ensures categories work in any language
}
```

### Localized Directory Access

```python
quick_access_items = [
    ('󰉍', 'DownloadsDir'),  # Translates to 'Downloads' or 'Descargas'
    ('󰈙', 'DocumentsDir'),  # Translates to 'Documents' or 'Documentos'
]

translated_dir_name = TR[dir_key]
path = f"~/{translated_dir_name}"
```

---

## Desktop Shortcut Creation

### .desktop File Generation

```python
def create_desktop_shortcut(self, app_info):
    # Validate command
    exec_cmd = app_info.get('Exec', '')
    parts = shlex.split(exec_cmd)
    
    # Remove desktop entry field codes
    cleaned_parts = [
        p for p in parts 
        if not any(p.startswith(x) for x in ['%f','%F','%u','%U'])
    ]
    
    # Find icon path
    icon_path = self.find_icon_path(app_info.get('Icon', ''))
    
    # Create .desktop file
    desktop_content = f"""[Desktop Entry]
Type=Application
Name={app_info['Name']}
Exec={' '.join(cleaned_parts)}
Icon={icon_path}
Terminal={'true' if app_info.get('Terminal') else 'false'}
"""
    
    # Write and make executable
    with open(desktop_file, 'w') as f:
        f.write(desktop_content)
    os.chmod(desktop_file, 0o755)
```

---

## Best Practices for Contributors

### 1. Adding New Categories

```python
# Update these three locations:

# 1. Translation dictionary
LANG = {
    'en': {'NewCategory': 'New Category'},
    'es': {'NewCategory': 'Nueva Categoría'}
}

# 2. Category map
CATEGORY_MAP = {
    'Nueva Categoría': 'NewCategory'
}

# 3. Preferred order
preferred_order = ['Desktop', ..., 'NewCategory']
```

### 2. Adding Configuration Options

```python
# 1. Add to default config
def get_default_config(self):
    return {
        "new_section": {
            "new_option": "default_value"
        }
    }

# 2. Access in code
value = self.config['new_section']['new_option']

# 3. Config is automatically saved on window resize
```

### 3. Icon Resolution

Always use `find_icon_path()` for custom icons:

```python
icon_path = self.find_icon_path("my_icon")
if icon_path:
    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(
        icon_path, size, size, True
    )
```

---

## Debugging Tips

### Enable Verbose Output

```python
# Add at module level
DEBUG = True

# Use throughout code
if DEBUG:
    print(f"Loading icon: {icon_name}")
```

### Test Menu Parsing

```python
parser = JWMMenuParser("/path/to/jwmrc")
apps = parser.parse_jwm_menu()
print(json.dumps(apps, indent=2))
```

### Monitor File Changes

```bash
# Watch for config changes
watch -n 1 cat ~/.config/pymenu.json

# Monitor JWM file
inotifywait -m ~/.jwmrc
```

---

## Future Improvements

### Planned Features

1. **Plugin System**: Allow custom extensions
2. **Theme Presets**: Predefined color schemes
3. **Application Categories Editor**: GUI for managing categories
4. **Favorites System**: Pin frequently used apps
5. **Search History**: Remember recent searches
6. **Multi-monitor Support**: Per-monitor positioning

### Performance Enhancements

1. **Icon Pre-caching**: Load common icons at startup
2. **Virtual Scrolling**: Render only visible items
3. **WebP Icon Support**: Smaller file sizes
4. **Async File Operations**: Non-blocking I/O

---

## Contributing Guidelines

When contributing code, ensure:

1. **Type Safety**: Use type hints where possible
2. **Error Handling**: Always use try-except for I/O operations
3. **Documentation**: Document complex functions
4. **Translation**: Add new strings to both language dictionaries
5. **Testing**: Test on both JWM and Openbox environments

---

## License

This documentation is part of PyMenuPup and is licensed under GPL v3.

For questions or contributions, visit: https://github.com/Woofshahenzup/PyMenuPup
