# NightOcean’s Mods Manager Plugins

[![License](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-green.svg)](https://www.python.org/)

Plugin development examples for NightOcean’s Mods Manager ([YHModsManager](https://github.com/IdealNightOcean/YHModsManager)).

This repository contains example plugins for NightOcean’s Mods Manager. Please visit the main repository for the main program and SDK.

> ⚠️ **Note**: This repository is not a centralized storage for plugins. It only showcases some example plugins for developers to reference and learn from.

## Table of Contents

- [Example Plugins List](#example-plugins-list)
  - [Game Plugin Examples](#game-plugin-examples)
  - [Feature Plugin Examples](#feature-plugin-examples)
- [Project Structure](#project-structure)
- [Development Guide](#development-guide)
- [Related Links](#related-links)

## Example Plugins List

### Game Plugin Examples

Game plugins are responsible for parsing specific game Mod metadata and managing Mod configurations.

| Game | Steam App ID | Features |
| --- | --- | --- |
| **Mount & Blade II: Bannerlord (Singleplayer)** | 261550 | Auto-detect game path, parse SubModule.xml metadata, separate singleplayer/multiplayer management |
| **RimWorld** | 294100 | Auto-detect game path, parse About.xml metadata, **Save Mod configuration import** |
| **Kenshi** | 233860 | Auto-detect game path, parse Mod metadata (basic functionality) |

### Feature Plugin Examples

Feature plugins extend program functionality, such as theme switching, error detection, etc.

| Plugin | Description |
| --- | --- |
| **Theme Switcher** | Quick switch between dark/light themes |
| **Error Test** | Test plugin functionality: static/dynamic error detection, custom sorting, context menu |

## Project Structure

```
YHModsManagerPlugins/
├── plugins/                      # Packaged plugins
│   ├── feature/                  # Feature plugins
│   └── game/                     # Game plugins
├── plugins_dev/                  # Plugin source code
│   ├── feature/                  # Feature plugin source code
│   │   ├── error_test/
│   │   └── theme_switcher/
│   └── game/                     # Game plugin source code
│       ├── AmazingCultivationSimulator/
│       ├── Bannerlord_Multiplayer/
│       ├── Bannerlord_Singleplayer/
│       ├── Kenshi/
│       └── Rimworld/
└── pack_plugins.py               # Plugin packaging script
```

## Development Guide

For detailed plugin development guide, please refer to [PLUGIN_DEVELOPMENT.md](./PLUGIN_DEVELOPMENT.md).

### Quick Start

1. Get the SDK from [main repository](https://github.com/IdealNightOcean/YHModsManager) and install:
   ```bash
   pip install yh_mods_manager_sdk-x.x.x-py3-none-any.whl
   ```
   > Note: `x.x.x` is the actual SDK version number

2. Create a new plugin in the `plugins_dev` directory

3. Run the packaging script:
   ```bash
   python pack_plugins.py
   ```

### Dependency Restrictions

> ⚠️ **Important**: The main program assumes users have no Python knowledge and cannot manually install dependencies. Therefore, plugins must work out-of-the-box.

Plugins can only use the following three types of libraries:

| Category | Description | Examples |
|------|------|------|
| **Python Standard Library** | Python built-in libraries, no installation required | `os`, `json`, `logging`, `typing`, `subprocess` |
| **SDK** | Development kit provided by this project | `yh_mods_manager_sdk` |
| **Libraries Packaged with Main Program** | Third-party libraries included in the main program EXE | `PyQt6`, `watchdog` |

**Do not use** any third-party libraries that require additional `pip install`, otherwise users will encounter errors at runtime.

#### If You Really Need Other Libraries

If a third-party library is **essential for plugin functionality and has strong generality**, you can apply to have it added to the main program's packaging list. How to apply:

1. Submit a request in the **main project** GitHub Issues
2. Explain the library's purpose, size, and necessity
3. After evaluation, it may be added to the main program packaging

The main program will control the packaging size and only accept truly necessary libraries.

## Related Links

- Main Project Repository: [YHModsManager](https://github.com/IdealNightOcean/YHModsManager)
- Issue Feedback: [GitHub Issues](https://github.com/IdealNightOcean/YHModsManagerPlugins/issues)
