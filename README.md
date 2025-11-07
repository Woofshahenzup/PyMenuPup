# PyMenuPup

A modern, customizable start menu for JWM (Joe's Window Manager) and Puppy Linux, written in Python with GTK3.

![Python Version](https://img.shields.io/badge/python-3.6%2B-blue)
![License](https://img.shields.io/badge/license-GPL-green)
![Platform](https://img.shields.io/badge/platform-Linux-lightgrey)

---

## Description

PyMenuPup is a modern and highly customizable start menu designed specifically for lightweight distributions like Puppy Linux that use JWM as window manager. It is also compatible with Openbox and Tint2.

### Main Features

- Fully customizable: colors, fonts, sizes and positioning
- Multilingual: support for English and Spanish
- Quick search: find applications instantly
- Quick access: system folders with one click
- Web integration: direct browser search
- Profile picture: customizable (square or circular)
- Automatic detection: support for JWM, Openbox and Tint2
- Optimized performance: lazy loading of applications
- Customizable categories: hide the ones you don't need
- Keyboard navigation: arrow keys and Enter support
- System theme integration: use GTK theme colors

---

## Components

### 1. pymenu-globicons.py
Main menu that displays all system applications organized by categories.

**Functionalities:**
- Automatic reading of JWM's `.jwmrc` file
- Intelligent application categorization
- Real-time search
- Quick access to common folders
- Social network integration
- Desktop shortcut creation
- Keyboard support (arrow key navigation)
- Context menu (right-click on applications)

### 2. pymenu-config.py
Graphical configuration tool to customize the menu.

**Configurable options:**
- Window dimensions and position
- Colors and transparency
- Fonts and text sizes
- File paths and commands
- Visible/hidden categories
- GTK system theme integration

---
 

## Distribution Variants

PyMenuPup has different versions optimized for different Linux environments:

### Original Version (Puppy Linux)
The main version (`pymenu-globicons.py` and `pymenu-config.py`) is designed specifically for Puppy Linux, which:
- Runs the system as root user by default
- Does not require the use of `sudo` for system operations
- Has Puppy Linux specific paths and configurations

### Versions for Standard Linux Distributions

In the `distro-linux/` folder you will find versions adapted for other Linux distributions that use non-root users:

#### **Essora** (`distro-linux/Essora/`)
Modified version for standard Linux distributions (Debian, Ubuntu, Arch, Fedora, etc.) with the following changes:

- **Permission management**: Proper use of `sudo` for operations requiring elevated privileges
- **Adapted paths**: Configurations adjusted for standard user directory structures
- **System commands**: Adaptation of shutdown, reboot and lock commands for multi-user systems
- **Environment variables**: Correct handling of `$HOME` and `$USER` for non-root users

**When to use each version?**
- **Use the main version** if you are on Puppy Linux or derivatives
- **Use the Essora version** if you are on Debian, Ubuntu, Arch, Fedora, Mint or other standard distributions

---

## Dependencies

### System Requirements

```
Python 3 (>= 3.6)
python3-gi
gir1.2-gtk-3.0
gir1.2-gdk-3.0
gir1.2-gdkpixbuf-2.0
gir1.2-pango-1.0
gir1.2-gio-2.0
gir1.2-glib-2.0
xdg-utils
Nerd Fonts
```

### Installing Dependencies

#### On Puppy Linux:
```bash
# Puppy Package Manager (PPM) usually includes python3-gi
# Verify that you have it installed:
python3 --version
python3 -c "import gi; print('GTK3 OK')"
```

#### On Debian/Ubuntu:
```bash
sudo apt update
sudo apt install python3 python3-gi python3-gi-cairo gir1.2-gtk-3.0 xdg-utils
```

#### On Arch Linux:
```bash
sudo pacman -S python python-gobject gtk3 xdg-utils
```

#### On Fedora/RHEL:
```bash
sudo dnf install python3 python3-gobject gtk3 xdg-utils
```

---

## Installation

### Manual Installation

1. Clone the repository:
```bash
git clone https://github.com/your-username/PyMenuPup.git
cd PyMenuPup
```

2. Copy the scripts to the system:
```bash
sudo cp pymenu-globicons.py /usr/local/bin/
sudo cp pymenu-config.py /usr/local/bin/

# Give execution permissions
sudo chmod +x /usr/local/bin/pymenu-globicons.py
sudo chmod +x /usr/local/bin/pymenu-config.py
```

3. Create symbolic links (optional):
```bash
sudo ln -s /usr/local/bin/pymenu-globicons.py /usr/local/bin/pymenu
sudo ln -s /usr/local/bin/pymenu-config.py /usr/local/bin/pymenu-config
```

---

## Configuration

### First Run

When running PyMenuPup for the first time, a configuration file will be automatically created at:

```
~/.config/pymenu.json
```

### Configuring JWM

Edit your `~/.jwmrc` file and add:

```xml
<Program label="Menu" icon="applications-system">
    /usr/local/bin/pymenu-globicons.py
</Program>
```

Or to use with specific coordinates:

```xml
<Program label="Menu" icon="applications-system">
    /usr/local/bin/pymenu-globicons.py 100 100
</Program>
```

In PuppyLinux /root/.jwmrc:

```xml
<RootMenu label="Menu" labeled="false" height="24" onroot="3">
```
then /root/.jwmrc-tray

```xml
 <TrayButton label="[MENU]" popup="Open menú">exec:pymenu-globicons.py</TrayButton>
```

### Configuring with Tint2

If you use Tint2, edit `~/.config/tint2/tint2rc`:

```ini
# Launcher
launcher_item_app = /usr/local/bin/pymenu-globicons.py
```

---

## Usage

### Running the Menu

```bash
# Basic execution
pymenu-globicons.py

# With custom position (x, y)
pymenu-globicons.py 100 100

# With custom JWM file
pymenu-globicons.py /path/to/jwmrc
```

### Opening the Configurator

```bash
pymenu-config.py
```

Or from the main menu, click on the configuration icon.

### Keyboard Shortcuts

- **Esc**: Close the menu
- **Alt + Left Click**: Move the window
- **Middle Click (wheel)**: Close the menu
- **Arrow Keys**: Navigate through applications
- **Enter**: Launch selected application
- **Right Click on app**: Context menu

---

## File Structure

```
PyMenuPup/
├── pymenu-globicons.py      # Main menu
├── pymenu-config.py          # GTK configurator
├── README.md                 # This file
├── LICENSE                   # GPL License
└── screenshots/              # Screenshots (optional)
```

### User Configuration Files

```
~/.config/
├── pymenu.json              # Main configuration
└── tint2/
    └── tint2rc              # Tint2 config (if applicable)

~/
├── .jwmrc                   # JWM config
├── .jwmrc-tray             # JWM tray config
└── .face                    # Profile picture
```

---

## Advanced Customization

### Manually Editing Configuration

The `~/.config/pymenu.json` file has this structure:

```json
{
    "window": {
        "width": 700,
        "height": 850,
        "decorated_window": false,
        "hide_header": false,
        "hide_quick_access": false,
        "hide_social_networks": false,
        "hide_category_text": false,
        "halign": "center",
        "icon_size": 32,
        "category_icon_size": 16,
        "profile_pic_size": 128,
        "profile_pic_shape": "square"
    },
    "font": {
        "family": "Sans 12",
        "size_categories": 12000,
        "size_names": 10000,
        "size_header": 8000
    },
    "colors": {
        "use_gtk_theme": false,
        "background": "rgba(0, 0, 0, 0.7)",
        "border": "rgba(255, 255, 255, 0.1)",
        "text_normal": "#D8DEE9",
        "text_header_os": "#D8DEE9",
        "text_header_kernel": "#D0883A",
        "text_header_hostname": "#88C0D0",
        "hover_background": "rgba(255, 255, 255, 0.1)",
        "button_normal_background": "rgba(0,0,0,0.6)",
        "button_text": "#ECEFF4",
        "categories_background": "rgba(0,0,0,0.6)"
    },
    "paths": {
        "profile_pic": "/root/.face",
        "profile_manager": "/usr/local/bin/ProfileManager.py",
        "shutdown_cmd": "/usr/local/bin/apagado-avatar.py",
        "jwmrc_tray": "/root/.jwmrc-tray",
        "tint2rc": "/root/.config/tint2/tint2rc"
    },
    "tray": {
        "use_tint2": false
    },
    "categories": {
        "excluded": []
    }
}
```

### Adding Custom Icons

PyMenuPup searches for icons in these paths:
- `/usr/local/lib/X11/pixmaps`
- `/usr/share/pixmaps`
- `/usr/share/icons/hicolor/*/apps`
- `/usr/share/pixmaps/puppy`

Place your icons in any of these folders.

### Excluding Categories

Edit the configuration file to hide specific categories:

```json
"categories": {
    "excluded": ["Help", "Leave", "Rectify"]
}
```

---

## Troubleshooting

### Menu doesn't appear

```bash
# Verify that Python3 is installed
python3 --version

# Verify GTK dependencies
python3 -c "import gi; gi.require_version('Gtk', '3.0'); from gi.repository import Gtk; print('GTK OK')"
```

### Icons not showing

```bash
# Verify icon paths in your .jwmrc
grep IconPath ~/.jwmrc

# Reinstall icon package
# (in Puppy Linux it's usually included)
```

### Permission errors

```bash
# Make sure scripts are executable
chmod +x /usr/local/bin/pymenu-globicons.py
chmod +x /usr/local/bin/pymenu-config.py
```

### Menu closes immediately

```bash
# Run from terminal to see errors
python3 /usr/local/bin/pymenu-globicons.py
```

### Profile picture not loading

```bash
# Verify the profile picture exists
ls -la ~/.face

# Or check the configured path
grep profile_pic ~/.config/pymenu.json
```

---

## Contributing

Contributions are welcome! If you want to improve PyMenuPup:

1. Fork the repository
2. Create a branch for your feature (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## License

This project is licensed under the GPL v3 License. See the `LICENSE` file for more details.

---

## Author

Nilson Morales
- GitHub: [@woofshahenzup](https://github.com/Woofshahenzup)
- Forum: [Puppy Linux Forum](https://forum.puppylinux.com)

---

## Acknowledgments

- The Puppy Linux team for creating such a lightweight and efficient distribution
- Joe Wingbermuehle for JWM (Joe's Window Manager)
- The GTK and Python communities
- All project contributors

---

## Screenshots and Demo

### Screenshots
![Main Menu](screenshots/main-menu.png)
![Configuration Tool](screenshots/config-tool.png)

### Video Demo
[![PyMenuPup Demo - Full Walkthrough](https://img.youtube.com/vi/VIDEO_ID/maxresdefault.jpg)](https://www.youtube.com/watch?v=VIDEO_ID)
*Click to watch the full demo on YouTube*

---

## Useful Links

- [Puppy Linux Official](https://puppylinux.com)
- [JWM Documentation](http://joewing.net/projects/jwm/)
- [GTK3 Documentation](https://docs.gtk.org/gtk3/)
- [Python GObject Documentation](https://pygobject.readthedocs.io/)

---

**Do you like PyMenuPup? Give the repository a star!**
