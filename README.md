# YHModsManager Plugins

[![License](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-green.svg)](https://www.python.org/)

夜海多用模组管理工具 ([YHModsManager](https://github.com/IdealNightOcean/YHModsManager)) 的插件开发示例。

本仓库包含 夜海多用模组管理工具 的示例插件，主程序和 SDK 请前往主仓库获取。

> ⚠️ **注意**：本仓库并非插件的集中存储仓库，仅是部分示例插件的展示，供开发者参考学习。

## 目录

- [示例插件列表](#示例插件列表)
  - [游戏插件示例](#游戏插件示例)
  - [功能插件示例](#功能插件示例)
- [项目结构](#项目结构)
- [开发指南](#开发指南)
- [相关链接](#相关链接)

## 示例插件列表

### 游戏插件示例

游戏插件负责解析特定游戏的 Mod 元数据、管理 Mod 配置。

| 游戏 | Steam App ID | 功能特性 |
| --- | --- | --- |
| **骑马与砍杀II：霸主 (单机)**<br>Mount & Blade II: Bannerlord | 261550 | 自动检测游戏路径、解析 SubModule.xml 元数据、单机/联机分离管理 |
| **环世界**<br>RimWorld | 294100 | 自动检测游戏路径、解析 About.xml 元数据、**存档 Mod 配置导入** |
| **剑士**<br>Kenshi | 233860 | 自动检测游戏路径、解析 Mod 元数据（基础功能） |

### 功能插件示例

功能插件扩展程序功能，如主题切换、错误检测等。

| 插件 | 说明 |
| --- | --- |
| **Theme Switcher** | 快速切换深色/浅色主题 |
| **Error Test** | 测试插件功能：静态/动态错误检测、自定义排序、右键菜单 |

## 项目结构

```
YHModsManagerPlugins/
├── plugins/                      # 打包后的插件
│   ├── feature/                  # 功能插件
│   └── game/                     # 游戏插件
├── plugins_dev/                  # 插件源码
│   ├── feature/                  # 功能插件源码
│   │   ├── error_test/
│   │   └── theme_switcher/
│   └── game/                     # 游戏插件源码
│       ├── AmazingCultivationSimulator/
│       ├── Bannerlord_Multiplayer/
│       ├── Bannerlord_Singleplayer/
│       ├── Kenshi/
│       └── Rimworld/
└── pack_plugins.py               # 插件打包脚本
```

## 开发指南

详细的插件开发指南请参阅 [PLUGIN_DEVELOPMENT.md](./PLUGIN_DEVELOPMENT.md)。

### 快速开始

1. 从 [YHModsManager 主仓库](https://github.com/IdealNightOcean/YHModsManager) 获取 SDK 并安装：
   ```bash
   pip install yh_mods_manager_sdk-x.x.x-py3-none-any.whl
   ```
   > 注意：`x.x.x` 为实际 SDK 版本号

2. 在 `plugins_dev` 目录下创建新插件

3. 运行打包脚本：
   ```bash
   python pack_plugins.py
   ```

## 相关链接

- 主项目仓库：[YHModsManager](https://github.com/IdealNightOcean/YHModsManager)
- 问题反馈：[GitHub Issues](https://github.com/IdealNightOcean/YHModsManagerPlugins/issues)
