#!/usr/bin/env python3
"""
Sistema de traducción universal para aplicaciones Python/GTK
Archivo: /usr/local/bin/pymenupuplang.py
Funciona en Puppy Linux (root) y distribuciones normales.
"""

import os
import locale

class TranslationManager:
    """Gestor de traducciones universal basado en archivos .lang"""
    
    # Rutas genéricas para búsqueda de traducciones
    LOCALE_PATHS = [
        os.path.expanduser("~/.config/locale"),
        "/usr/local/share/locale",
        "/usr/share/locale",
    ]
    
    # Diccionario vacío - cada app debe proveer sus propias traducciones
    # o usar archivos .lang en las rutas especificadas
    
    def __init__(self, locale_paths=None, app_name=None):
        """
        Inicializa el gestor de traducciones.
        
        Args:
            locale_paths: Lista de rutas personalizadas (opcional)
            app_name: Nombre de la aplicación para búsqueda automática
        """
        try:
            self.locale_paths = self._resolve_locale_paths(locale_paths, app_name)
            self.translations = {}  # Diccionario vacío
            self.current_lang = self._detect_system_language()
            self._load_translations()
            self.category_map = self._build_category_map()
            
            # Debug opcional
            if os.environ.get('PYMENUPUP_DEBUG'):
                self._print_debug_info(app_name)
                
        except Exception as e:
            print(f"⚠️  TranslationManager init failed: {e}")
            self.locale_paths = []
            self.translations = {}
            self.current_lang = 'en'
            self.category_map = {}
    
    def _print_debug_info(self, app_name):
        """Muestra información de debug"""
        print(f"🔍 TranslationManager debug:")
        print(f"   App: {app_name or 'none'}")
        print(f"   Language: {self.current_lang}")
        print(f"   Paths searched: {self.locale_paths}")
        print(f"   Translations loaded: {len(self.translations)}")
        for path in self.locale_paths:
            if os.path.exists(path):
                for file in os.listdir(path):
                    if file.endswith('.lang'):
                        print(f"   ✅ Found: {os.path.join(path, file)}")
    
    def _resolve_locale_paths(self, locale_paths=None, app_name=None):
        """Resuelve rutas de traducción para cualquier distribución"""
        paths = []
        
        # 1. Rutas personalizadas explícitas
        if locale_paths:
            for p in locale_paths:
                expanded = os.path.expanduser(p)
                if expanded not in paths:
                    paths.append(expanded)
        
        # 2. Rutas específicas de la app
        if app_name:
            # Detectar directorio home actual
            current_home = os.path.expanduser("~")
            
            # Rutas para usuario actual
            user_paths = [
                f"{current_home}/.config/{app_name}/locale",
                f"{current_home}/.local/share/locale/{app_name}",
            ]
            
            # Si es root en Puppy Linux, también buscar en posibles usuarios normales
            if current_home == "/root":
                # Buscar en /home para distribuciones normales
                if os.path.exists("/home"):
                    for user in os.listdir("/home"):
                        if user != "root":
                            user_paths.extend([
                                f"/home/{user}/.config/{app_name}/locale",
                                f"/home/{user}/.local/share/locale/{app_name}",
                            ])
                            break  # Solo el primer usuario no-root
            
            # Rutas del sistema
            system_paths = [
                f"/usr/local/share/locale/{app_name}",
                f"/usr/share/locale/{app_name}",
                f"/opt/{app_name}/locale",
            ]
            
            # Combinar todas las rutas
            all_paths = user_paths + system_paths
            
            for p in all_paths:
                if p not in paths:
                    paths.append(p)
        
        # 3. Rutas genéricas del sistema
        for p in self.LOCALE_PATHS:
            if p not in paths:
                paths.append(p)
        
        return paths
        
    
    def _build_category_map(self):
        """
        Construye un mapa de categorías traducidas a sus nombres estándar en inglés.
        Esto permite que el sistema reconozca categorías del JWM en cualquier idioma.
        """
        # Categorías estándar que necesitan mapeo
        standard_categories = [
            'Desktop', 'System', 'Setup', 'Utility', 'Filesystem',
            'Graphic', 'Document', 'Business', 'Personal', 'Network',
            'Internet', 'Multimedia', 'Fun', 'Help', 'Rectify', 
            'Shutdown', 'Leave'
        ]
        
        category_map = {}
        
        # Agregar mapeo de inglés a inglés (identidad)
        for cat in standard_categories:
            category_map[cat] = cat
        
        # Buscar traducciones en todos los archivos .lang disponibles
        for locale_path in self.locale_paths:
            if not os.path.exists(locale_path):
                continue
            
            try:
                for filename in os.listdir(locale_path):
                    if not filename.endswith('.lang'):
                        continue
                    
                    filepath = os.path.join(locale_path, filename)
                    file_translations = self._parse_lang_file(filepath)
                    
                    # Para cada categoría estándar, agregar su traducción al mapa
                    for standard_cat in standard_categories:
                        translated_cat = file_translations.get(standard_cat)
                        if translated_cat and translated_cat != standard_cat:
                            category_map[translated_cat] = standard_cat
            except Exception as e:
                print(f"⚠️  Error construyendo category_map desde {locale_path}: {e}")
        
        print(f"✓ Category map construido con {len(category_map)} entradas")
        return category_map
    
    def get_category_map(self):
        """Retorna el mapa de categorías traducidas"""
        return self.category_map
    
    def _detect_system_language(self):
        """Detecta el idioma del sistema"""
        try:
            sys_locale = locale.getlocale()
            if sys_locale[0]:
                # Obtiene código completo (ej: es_MX -> es-MX)
                lang_code = sys_locale[0].replace('_', '-')
                return lang_code
        except:
            pass
        return 'en'
    
    def _find_lang_file(self, lang_code):
        """Busca el archivo .lang en las rutas configuradas"""
        # Primero intenta con el código completo (ej: es-MX.lang)
        for base_path in self.locale_paths:
            full_path = os.path.join(base_path, f"{lang_code}.lang")
            if os.path.exists(full_path):
                return full_path
        
        # Si no encuentra, intenta solo con el idioma base (ej: es.lang)
        if '-' in lang_code:
            base_lang = lang_code.split('-')[0]
            for base_path in self.locale_paths:  # Cambia esto también
                full_path = os.path.join(base_path, f"{base_lang}.lang")
                if os.path.exists(full_path):
                    return full_path
        
        return None
    
    def _parse_lang_file(self, filepath):
        """
        Lee un archivo .lang y retorna un diccionario
        Formato: clave = valor
        Soporta comentarios con # y líneas vacías
        """
        translations = {}
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    
                    # Ignorar líneas vacías y comentarios
                    if not line or line.startswith('#'):
                        continue
                    
                    # Buscar el separador =
                    if '=' not in line:
                        print(f"⚠️  Línea {line_num} ignorada (sin '='): {line}")
                        continue
                    
                    # Separar clave y valor
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    if key and value:
                        translations[key] = value
                    
        except Exception as e:
            print(f"⚠️  Error leyendo archivo de traducción {filepath}: {e}")
        
        return translations
    
    def _load_translations(self):
        """Carga las traducciones para el idioma actual"""
        lang_file = self._find_lang_file(self.current_lang)
        
        if lang_file:
            print(f"✓ Cargando traducciones desde: {lang_file}")
            loaded_translations = self._parse_lang_file(lang_file)
            # Actualiza solo las claves que existen en el archivo
            self.translations.update(loaded_translations)
        else:
            # Si no encuentra archivo, intenta solo con el idioma base
            base_lang = self.current_lang.split('-')[0] if '-' in self.current_lang else self.current_lang
            if base_lang != 'en':
                print(f"⚠️  No se encontró archivo de traducción para '{self.current_lang}'")
                print(f"   Buscado en: {', '.join(self.locale_paths)}")
                print(f"   Usando traducciones por defecto (inglés)")
    
    def get(self, key, default=None):
        """Obtiene una traducción por clave"""
        return self.translations.get(key, default or key)
    
    def __getitem__(self, key):
        """Permite usar TR['clave'] como antes"""
        return self.get(key)


# Para testing
if __name__ == "__main__":
    TR = TranslationManager()
    print(f"Idioma detectado: {TR.current_lang}")
    print(f"Ejemplo: {TR['PyMenuPup Configurator']}")
