# PyMenuPup - Documentación Técnica

**[English](TECHNICAL.md) | Español**

## Tabla de Contenidos
1. [Resumen de Arquitectura](#resumen-de-arquitectura)
2. [Componentes Principales](#componentes-principales)
3. [Sistema de Análisis de Menús](#sistema-de-análisis-de-menús)
4. [Sistema de Configuración](#sistema-de-configuración)
5. [Carga y Caché de Iconos](#carga-y-caché-de-iconos)
6. [Renderizado de UI](#renderizado-de-ui)
7. [Detección del Gestor de Ventanas](#detección-del-gestor-de-ventanas)
8. [Manejo de Eventos](#manejo-de-eventos)
9. [Optimizaciones de Rendimiento](#optimizaciones-de-rendimiento)
10. [Internacionalización](#internacionalización)

---

## Resumen de Arquitectura

PyMenuPup está construido usando **GTK3** a través de **GObject Introspection (PyGObject)**. La aplicación sigue una arquitectura modular con tres capas principales:

```
┌─────────────────────────────────┐
│   Capa de Interfaz de Usuario  │
│   (Widgets GTK3)                │
├─────────────────────────────────┤
│   Capa de Lógica de Negocio    │
│   (Análisis, Config, Navegación)│
├─────────────────────────────────┤
│   Capa de Integración de Sistema│
│   (JWM/Openbox, Monitoreo)      │
└─────────────────────────────────┘
```

### Patrones de Diseño Clave

- **Patrón Singleton**: `ConfigManager` asegura una instancia de configuración
- **Patrón Observer**: Monitoreo de archivos con `Gio.FileMonitor`
- **Carga Perezosa**: Las aplicaciones se cargan en lotes para prevenir congelamiento de la UI
- **Estrategia de Caché**: Los pixbufs de iconos se almacenan en caché para mejorar el rendimiento

---

## Componentes Principales

### 1. `JWMMenuParser`

Esta clase es responsable de analizar archivos de menú de JWM u Openbox/labwc.

**Métodos Clave:**

```python
def parse_jwm_menu(self):
    """Analiza el archivo de menú XML de JWM y extrae las aplicaciones"""
    # Usa ElementTree para analizar XML
    # Normaliza nombres de categorías usando CATEGORY_MAP
    # Retorna dict: {'Categoría': [info_app, ...]}
```

**Estructura XML Manejada:**

```xml
<JWM>
  <Menu label="Sistema">
    <Program label="Terminal" icon="terminal">
      lxterminal
    </Program>
  </Menu>
</JWM>
```

**Ejemplo de Normalización:**

```python
CATEGORY_MAP = {
    'Escritorio': 'Desktop',
    'Sistema': 'System',
    # ... asegura nombres de categoría consistentes
}
```

---

### 2. `ConfigManager`

Gestiona la configuración JSON con migración y validación automática.

**Estructura de Configuración:**

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

**Migración Automática:**

```python
def load_config(self):
    # Fusiona la config del usuario con la config por defecto
    # Asegura que todas las claves existan incluso después de actualizaciones
    for key in default_config:
        if key not in config:
            config[key] = default_config[key]
```

---

## Sistema de Análisis de Menús

### Soporte Dual de Parser

PyMenuPup detecta el gestor de ventanas y elige el parser apropiado:

```python
def detect_window_manager():
    """
    Lee /etc/windowmanager para detectar WM
    Retorna 'openbox' o 'jwm'
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

### Resolución de Rutas de Iconos

El parser construye una lista de rutas de búsqueda de iconos:

```python
def extract_icon_paths(self, root):
    paths = []
    # Analiza desde la config de JWM
    for iconpath in root.findall('.//IconPath'):
        paths.append(iconpath.text.strip())
    
    # Agrega rutas de respaldo
    default_paths = [
        "/usr/local/lib/X11/pixmaps",
        "/usr/share/pixmaps",
        "/usr/share/icons/hicolor/48x48/apps"
    ]
    
    return paths + default_paths
```

### Organización de Categorías

Las aplicaciones se organizan con un orden preferido:

```python
preferred_order = [
    'Desktop', 'System', 'Setup', 'Utility', 
    'Filesystem', 'Graphic', 'Document', 'Business',
    'Personal', 'Network', 'Internet', 'Multimedia',
    'Fun', 'Help', 'Leave'
]
```

---

## Sistema de Configuración

### Generación Dinámica de CSS

El CSS se genera desde la configuración JSON:

```python
def apply_css(self):
    use_gtk_theme = self.config['colors'].get('use_gtk_theme', False)
    
    if use_gtk_theme:
        # Usa colores del tema del sistema
        css = """
        .menu-window {
            background-color: @theme_bg_color;
        }
        """
    else:
        # Usa colores personalizados de la config
        colors = self.config['colors']
        css = f"""
        .menu-window {{
            background-color: {colors['background']};
            border: 1px solid {colors['border']};
        }}
        """
```

### Posicionamiento de Ventana

Posicionamiento inteligente basado en la configuración de la bandeja:

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

## Carga y Caché de Iconos

### Carga de Iconos en Tres Niveles

```python
def load_app_icon(self, icon_name):
    cache_key = f"{icon_name}_{self.icon_size}"
    
    # 1. Verificar caché
    if cache_key in self.icon_cache:
        return Gtk.Image.new_from_pixbuf(self.icon_cache[cache_key])
    
    # 2. Intentar tema de iconos
    try:
        pixbuf = Gtk.IconTheme.get_default().load_icon(
            icon_name, self.icon_size, Gtk.IconLookupFlags.FORCE_SIZE
        )
    except:
        pixbuf = None
    
    # 3. Intentar ruta de archivo
    if pixbuf is None:
        icon_path = self.find_icon_path(icon_name)
        if icon_path:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                icon_path, self.icon_size, self.icon_size, True
            )
    
    # 4. Icono de respaldo
    if pixbuf is None:
        pixbuf = Gtk.IconTheme.get_default().load_icon(
            "application-x-executable", self.icon_size
        )
    
    # Almacenar en caché y retornar
    self.icon_cache[cache_key] = pixbuf
    return Gtk.Image.new_from_pixbuf(pixbuf)
```

### Máscara Circular para Foto de Perfil

Usando Cairo para crear máscaras circulares:

```python
def apply_circular_mask(pixbuf):
    size = min(pixbuf.get_width(), pixbuf.get_height())
    
    # Crear superficie de máscara
    mask_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    mask_cr = cairo.Context(mask_surface)
    
    # Dibujar círculo blanco
    center = size / 2.0
    radius = size / 2.0
    mask_cr.arc(center, center, radius, 0, 2 * math.pi)
    mask_cr.set_source_rgba(1, 1, 1, 1)
    mask_cr.fill()
    
    # Aplicar máscara con operador DEST_IN
    final_cr.set_operator(cairo.OPERATOR_DEST_IN)
    final_cr.paint()
    
    return Gdk.pixbuf_get_from_surface(final_surface, 0, 0, size, size)
```

---

## Renderizado de UI

### Estrategia de Carga Perezosa

Las aplicaciones se cargan en lotes para prevenir congelamiento de la UI:

```python
def load_applications_batch(self, apps_data, start_index, batch_size=10):
    count = 0
    
    for category, apps in apps_data:
        for i, app in enumerate(apps[start_index:], start_index):
            if count >= batch_size:
                # Programar siguiente lote
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

### Estados de Selección de Categoría

Se mantienen tres estados de selección:

```python
self.selected_category      # Permanentemente seleccionada (por clic)
self.hovered_category       # Temporalmente sobre ella
self.current_category       # Actualmente mostrada
```

**Máquina de Estados:**

```
Usuario sobre → Vista previa (retraso de 150ms)
Usuario clic  → Selección permanente
Ratón sale    → Restaurar a seleccionada (retraso de 150ms)
```

---

## Detección del Gestor de Ventanas

### Detección Automática de WM

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

### Análisis de Configuración de Bandeja

**Para Tint2:**

```python
def parse_tray_config(self):
    # Leer tint2rc
    if 'panel_size' in line:
        tray_info['height'] = int(parts[1])
    
    if 'panel_position' in line:
        tray_info['valign'] = pos_parts[0]  # top/bottom
        tray_info['halign'] = pos_parts[1]  # left/center/right
```

**Para JWM:**

```python
# Analizar elemento XML <Tray>
tray_element = root.find('.//Tray')
tray_info['height'] = int(tray_element.get('height', '30'))
tray_info['valign'] = tray_element.get('valign', 'bottom')
```

---

## Manejo de Eventos

### Gestión de Foco

```python
def on_focus_out(self, widget, event):
    """Cerrar menú cuando pierde el foco"""
    if not self.is_resizing and not self.context_menu_active:
        Gtk.main_quit()
    return False
```

### Navegación con Teclado

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

### Monitoreo de Archivos

```python
# Monitorear config de JWM para cambios
self.file_monitor = self.jwm_file.monitor_file(
    Gio.FileMonitorFlags.NONE, None
)
self.file_monitor.connect("changed", self.on_jwm_file_changed)

def on_jwm_file_changed(self, monitor, file, other_file, event_type):
    if event_type == Gio.FileMonitorEvent.CHANGES_DONE_HINT:
        # Recargar aplicaciones
        self.applications = self.parser.parse_jwm_menu()
        self.recreate_interface()
```

---

## Optimizaciones de Rendimiento

### 1. Caché de Iconos

```python
self.icon_cache = {}  # Formato: {"{nombre}_{tamaño}": GdkPixbuf}
```

**Beneficio:** Previene recargar el mismo icono múltiples veces.

### 2. Renderizado por Lotes

Las aplicaciones se renderizan en lotes de 10 para mantener la UI responsiva:

```python
GLib.idle_add(self.load_applications_batch, apps_data, 0)
```

### 3. Captura de Foco Retardada

```python
GLib.timeout_add(100, self.delayed_focus_grab)
```

Previene que el texto placeholder desaparezca inmediatamente.

### 4. Búsqueda Inteligente

Solo recrea widgets que coinciden con la búsqueda:

```python
def on_search_changed(self, search_entry):
    search_text = search_entry.get_text().lower()
    
    if not search_text:
        self.show_category_applications(self.current_category)
        return
    
    # Solo mostrar apps coincidentes
    for app in apps:
        if search_text in app['Name'].lower():
            button = self.create_app_button(app)
            self.apps_flowbox.add(button)
```

---

## Internacionalización

### Sistema de Traducción

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

### Normalización de Nombres de Categoría

```python
CATEGORY_MAP = {
    'Escritorio': 'Desktop',
    'Sistema': 'System',
    # Asegura que las categorías funcionen en cualquier idioma
}
```

### Acceso Localizado a Directorios

```python
quick_access_items = [
    ('󰉍', 'DownloadsDir'),  # Se traduce a 'Downloads' o 'Descargas'
    ('󰈙', 'DocumentsDir'),  # Se traduce a 'Documents' o 'Documentos'
]

translated_dir_name = TR[dir_key]
path = f"~/{translated_dir_name}"
```

---

## Creación de Accesos Directos en el Escritorio

### Generación de Archivo .desktop

```python
def create_desktop_shortcut(self, app_info):
    # Validar comando
    exec_cmd = app_info.get('Exec', '')
    parts = shlex.split(exec_cmd)
    
    # Remover códigos de campo de entrada de escritorio
    cleaned_parts = [
        p for p in parts 
        if not any(p.startswith(x) for x in ['%f','%F','%u','%U'])
    ]
    
    # Encontrar ruta de icono
    icon_path = self.find_icon_path(app_info.get('Icon', ''))
    
    # Crear archivo .desktop
    desktop_content = f"""[Desktop Entry]
Type=Application
Name={app_info['Name']}
Exec={' '.join(cleaned_parts)}
Icon={icon_path}
Terminal={'true' if app_info.get('Terminal') else 'false'}
"""
    
    # Escribir y hacer ejecutable
    with open(desktop_file, 'w') as f:
        f.write(desktop_content)
    os.chmod(desktop_file, 0o755)
```

---

## Mejores Prácticas para Contribuidores

### 1. Agregando Nuevas Categorías

```python
# Actualizar estas tres ubicaciones:

# 1. Diccionario de traducción
LANG = {
    'en': {'NewCategory': 'New Category'},
    'es': {'NewCategory': 'Nueva Categoría'}
}

# 2. Mapa de categorías
CATEGORY_MAP = {
    'Nueva Categoría': 'NewCategory'
}

# 3. Orden preferido
preferred_order = ['Desktop', ..., 'NewCategory']
```

### 2. Agregando Opciones de Configuración

```python
# 1. Agregar a config por defecto
def get_default_config(self):
    return {
        "new_section": {
            "new_option": "default_value"
        }
    }

# 2. Acceder en el código
value = self.config['new_section']['new_option']

# 3. La config se guarda automáticamente al redimensionar ventana
```

### 3. Resolución de Iconos

Siempre usa `find_icon_path()` para iconos personalizados:

```python
icon_path = self.find_icon_path("mi_icono")
if icon_path:
    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(
        icon_path, size, size, True
    )
```

---

## Consejos de Depuración

### Habilitar Salida Detallada

```python
# Agregar a nivel de módulo
DEBUG = True

# Usar a lo largo del código
if DEBUG:
    print(f"Cargando icono: {icon_name}")
```

### Probar Análisis de Menú

```python
parser = JWMMenuParser("/ruta/a/jwmrc")
apps = parser.parse_jwm_menu()
print(json.dumps(apps, indent=2))
```

### Monitorear Cambios de Archivos

```bash
# Ver cambios en la config
watch -n 1 cat ~/.config/pymenu.json

# Monitorear archivo JWM
inotifywait -m ~/.jwmrc
```

---

## Mejoras Futuras

### Características Planeadas

1. **Sistema de Plugins**: Permitir extensiones personalizadas
2. **Presets de Temas**: Esquemas de color predefinidos
3. **Editor de Categorías de Aplicaciones**: GUI para gestionar categorías
4. **Sistema de Favoritos**: Anclar apps usadas frecuentemente
5. **Historial de Búsqueda**: Recordar búsquedas recientes
6. **Soporte Multi-monitor**: Posicionamiento por monitor

### Mejoras de Rendimiento

1. **Pre-caché de Iconos**: Cargar iconos comunes al inicio
2. **Scroll Virtual**: Renderizar solo elementos visibles
3. **Soporte de Iconos WebP**: Tamaños de archivo más pequeños
4. **Operaciones de Archivo Asíncronas**: E/S no bloqueante

---

## Guías de Contribución

Al contribuir código, asegúrate de:

1. **Seguridad de Tipos**: Usa type hints donde sea posible
2. **Manejo de Errores**: Siempre usa try-except para operaciones de E/S
3. **Documentación**: Documenta funciones complejas
4. **Traducción**: Agrega nuevas cadenas a ambos diccionarios de idioma
5. **Pruebas**: Prueba en entornos JWM y Openbox

---

## Licencia

Esta documentación es parte de PyMenuPup y está licenciada bajo GPL v3.

Para preguntas o contribuciones, visita: https://github.com/Woofshahenzup/PyMenuPup
