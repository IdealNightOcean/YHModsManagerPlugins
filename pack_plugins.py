"""
插件打包脚本
将 plugins_dev 中的插件打包到 plugins 目录
支持双插件体系：游戏插件和功能插件分别从不同目录加载和输出
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from yh_mods_manager_sdk import PluginPacker, verify_plugin, PLUGIN_MANIFEST
from yh_mods_manager_sdk.menu import PluginType


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = SCRIPT_DIR

PLUGINS_DEV_DIR_NAME = "plugins_dev"
PLUGINS_DIR_NAME = "plugins"

GAME_SUBDIR = "game"
FEATURE_SUBDIR = "feature"

PLUGINS_DEV_DIR = os.path.join(PROJECT_DIR, PLUGINS_DEV_DIR_NAME)
PLUGINS_DIR = os.path.join(PROJECT_DIR, PLUGINS_DIR_NAME)

GAME_PLUGINS_DEV_DIR = os.path.join(PLUGINS_DEV_DIR, GAME_SUBDIR)
FEATURE_PLUGINS_DEV_DIR = os.path.join(PLUGINS_DEV_DIR, FEATURE_SUBDIR)

GAME_PLUGINS_DIR = os.path.join(PLUGINS_DIR, GAME_SUBDIR)
FEATURE_PLUGINS_DIR = os.path.join(PLUGINS_DIR, FEATURE_SUBDIR)


def get_plugin_type(plugin_dir: str) -> PluginType:
    """从manifest.json获取插件类型"""
    config_file = os.path.join(plugin_dir, PLUGIN_MANIFEST)
    if os.path.exists(config_file):
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
            plugin_type_str = config_data.get("plugin_type")
            if plugin_type_str:
                return PluginType(plugin_type_str)
            return PluginType.GAME
    return PluginType.GAME


def pack_all_plugins():
    """打包所有插件"""
    os.makedirs(GAME_PLUGINS_DIR, exist_ok=True)
    os.makedirs(FEATURE_PLUGINS_DIR, exist_ok=True)

    packed_count = 0
    game_count = 0
    feature_count = 0

    if os.path.exists(GAME_PLUGINS_DEV_DIR):
        for plugin_name in os.listdir(GAME_PLUGINS_DEV_DIR):
            plugin_dir = os.path.join(GAME_PLUGINS_DEV_DIR, plugin_name)

            if not os.path.isdir(plugin_dir):
                continue

            config_file = os.path.join(plugin_dir, PLUGIN_MANIFEST)
            if not os.path.exists(config_file):
                print(f"跳过 {plugin_name}: 缺少 {PLUGIN_MANIFEST}")
                continue

            try:
                output_path = PluginPacker.pack(plugin_dir, PLUGINS_DIR, plugin_type=PluginType.GAME)
                if output_path:
                    print(f"打包成功 [游戏插件]: {output_path}")

                    result = verify_plugin(output_path)
                    if result["valid"]:
                        print(f"  - 插件ID: {result['plugin_id']}")
                        print(f"  - 版本: {result['plugin_version']}")
                        print(f"  - 文件数: {len(result['files'])}")
                    else:
                        print(f"  - 验证失败: {result['errors']}")

                    packed_count += 1
                    game_count += 1
            except Exception as e:
                print(f"打包失败 {plugin_name}: {e}")

    if os.path.exists(FEATURE_PLUGINS_DEV_DIR):
        for plugin_name in os.listdir(FEATURE_PLUGINS_DEV_DIR):
            plugin_dir = os.path.join(FEATURE_PLUGINS_DEV_DIR, plugin_name)

            if not os.path.isdir(plugin_dir):
                continue

            config_file = os.path.join(plugin_dir, PLUGIN_MANIFEST)
            if not os.path.exists(config_file):
                print(f"跳过 {plugin_name}: 缺少 {PLUGIN_MANIFEST}")
                continue

            try:
                output_path = PluginPacker.pack(plugin_dir, PLUGINS_DIR, plugin_type=PluginType.FEATURE)
                if output_path:
                    print(f"打包成功 [功能插件]: {output_path}")

                    result = verify_plugin(output_path)
                    if result["valid"]:
                        print(f"  - 插件ID: {result['plugin_id']}")
                        print(f"  - 版本: {result['plugin_version']}")
                        print(f"  - 文件数: {len(result['files'])}")
                    else:
                        print(f"  - 验证失败: {result['errors']}")

                    packed_count += 1
                    feature_count += 1
            except Exception as e:
                print(f"打包失败 {plugin_name}: {e}")

    print(f"\n完成! 共打包 {packed_count} 个插件")
    print(f"  - 游戏插件: {game_count}")
    print(f"  - 功能插件: {feature_count}")


def pack_single_plugin(p_name: str, p_type: PluginType = None):
    """打包单个插件
    
    Args:
        p_name: 插件名称
        p_type: 插件类型，如果为None则自动检测
    """
    plugin_dir = None
    detected_type = None

    if os.path.exists(os.path.join(GAME_PLUGINS_DEV_DIR, p_name)):
        plugin_dir = os.path.join(GAME_PLUGINS_DEV_DIR, p_name)
        detected_type = PluginType.GAME
    elif os.path.exists(os.path.join(FEATURE_PLUGINS_DEV_DIR, p_name)):
        plugin_dir = os.path.join(FEATURE_PLUGINS_DEV_DIR, p_name)
        detected_type = PluginType.FEATURE

    if not plugin_dir:
        print(f"插件目录不存在: {p_name}")
        return

    if p_type is None:
        p_type = detected_type or get_plugin_type(plugin_dir)

    try:
        output_path = PluginPacker.pack(plugin_dir, PLUGINS_DIR, plugin_type=p_type)
        if output_path:
            type_label = "游戏插件" if p_type == PluginType.GAME else "功能插件"
            print(f"打包成功 [{type_label}]: {output_path}")

            result = verify_plugin(output_path)
            if result["valid"]:
                print(f"插件ID: {result['plugin_id']}")
                print(f"版本: {result['plugin_version']}")
            else:
                print(f"验证失败: {result['errors']}")
    except Exception as e:
        print(f"打包失败: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        plugin_type = None
        if len(sys.argv) > 2:
            type_str = sys.argv[2]
            try:
                plugin_type = PluginType(type_str)
            except ValueError:
                print(f"无效的插件类型: {type_str}，可选值: game, feature")
                sys.exit(1)
        pack_single_plugin(sys.argv[1], plugin_type)
    else:
        pack_all_plugins()
