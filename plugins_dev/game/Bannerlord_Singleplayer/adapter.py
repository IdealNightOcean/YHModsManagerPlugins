"""
Bannerlord游戏适配器
实现规范化插件接口

使用SDK开发，无需主程序源码

遵循规则P3：使用GamePaths聚合类管理路径，禁止离散路径参数
"""

import logging
import os
import xml.etree.ElementTree as ET
from typing import Optional, List, Tuple, Dict, Any

from .detector import BannerlordDetector
from .mod_parser import BannerlordModParser
from yh_mods_manager_sdk import (
    Mod,
    ModIssueStatus,
    GameMetadata,
    ModMetadata,
    GameAdapter,
    PluginConfig,
    GamePaths,
    PlatformUtils,
    ManagerCollectionProtocol,
)

logger = logging.getLogger(__name__)


class BannerlordAdapter(GameAdapter):
    """Bannerlord游戏适配器
    
    遵循插件系统需求文档规范：
    - 插件负责：独立加载、解析游戏/Mod元数据，输出给主程序
    - 插件不管理、不长时间缓存任何元数据
    - 主程序负责：接收、存储、管理、分发元数据
    
    实现规范化插件接口：
    - 强制要求：路径验证、游戏元数据、Mod元数据、生命周期处理
    - 可选功能：自动检测、静态错误检测、自定义菜单、Mod顺序总结
    
    遵循规则P3：使用GamePaths聚合类管理路径
    """
    MULTIPLAYER = False

    def __init__(self, config: Optional[PluginConfig] = None):
        super().__init__(config)
        custom_data = self._config.custom_data if self._config else {}
        if custom_data:
            self.MULTIPLAYER = custom_data.get("multiplayer", False)

    def _get_required_paths(self) -> Dict[str, str]:
        if self._config and self._config.path_validation:
            return self._config.path_validation.get_required_paths()
        return {}

    def _get_executable_paths(self) -> List[str]:
        if self._config and self._config.path_validation:
            return self._config.path_validation.get_executable_paths()
        return []

    def get_mod_parser(self, paths: GamePaths, i18n=None) -> BannerlordModParser:
        game_version = self.detect_game_version(paths)
        updated_paths = paths.with_version(game_version) if game_version else paths
        return BannerlordModParser(
            config=self._config,
            paths=updated_paths,
            i18n=i18n
        )

    def detect_game_version(self, paths: GamePaths) -> str:
        if not paths.game_dir_path:
            return ""
        native_submodule = os.path.join(paths.game_dir_path, "Modules", "Native", "SubModule.xml")
        if os.path.exists(native_submodule):
            try:
                tree = ET.parse(native_submodule)
                root = tree.getroot()
                return self._get_xml_value(root, "Version", "")
            except Exception as e:
                logger.debug(f"Failed to read native submodule version: {e}")
        return ""

    def create_detector(self) -> BannerlordDetector:
        return BannerlordDetector(self._config)

    def validate_required_paths(self, paths: GamePaths) -> Tuple[bool, List[str]]:
        errors = []

        if not paths.game_dir_path:
            errors.append("Game directory path is required")
            return False, errors

        if not os.path.exists(paths.game_dir_path):
            errors.append(f"Game directory not found: {paths.game_dir_path}")
            return False, errors

        for name, rel_path in self._get_required_paths().items():
            full_path = os.path.join(paths.game_dir_path, rel_path)
            if not os.path.exists(full_path):
                errors.append(f"Required path missing: {name} ({rel_path})")

        return len(errors) == 0, errors

    def load_game_metadata(self, paths: GamePaths) -> GameMetadata:
        metadata = super().load_game_metadata(paths)

        game_version = self.detect_game_version(paths)
        if game_version:
            metadata.game_version = game_version

        if paths.game_dir_path:
            metadata.custom_data["engine_version"] = self._detect_engine_version(paths.game_dir_path)

        return metadata

    def load_mod_metadata(self, mod: Mod) -> ModMetadata:
        metadata = super().load_mod_metadata(mod)

        metadata.load_before = mod.load_before
        metadata.load_after = mod.load_after
        metadata.incompatible_with = mod.incompatible_modules

        return metadata

    def on_pre_initialize(self, context: Dict[str, Any]) -> Tuple[bool, str]:
        paths_data = context.get("paths")
        if not paths_data:
            game_dir_path = context.get("game_dir_path", "")
            if not game_dir_path:
                return True, ""
            paths = GamePaths(game_dir_path=game_dir_path)
        else:
            paths = paths_data

        valid, errors = self.validate_required_paths(paths)
        if not valid:
            return False, "; ".join(errors)

        return True, ""

    def on_initialize(self, context: ManagerCollectionProtocol) -> Tuple[bool, str]:
        return super().on_initialize(context)

    def on_startup_complete(self, context: Dict[str, Any]) -> None:
        pass

    def static_error_check(self, mods: List[Mod], game_metadata: GameMetadata) -> None:
        game_version = game_metadata.game_version

        for mod in mods:
            if mod.supported_versions and game_version:
                for supported in mod.supported_versions:
                    if not self._check_version_compatibility(supported, game_version):
                        mod.add_issue(ModIssueStatus.VERSION_MISMATCH)
                        break

    @staticmethod
    def _check_version_compatibility(mod_version: str, game_version: str) -> bool:
        if not mod_version or not game_version:
            return True

        mod_parts = mod_version.split('.')
        game_parts = game_version.split('.')

        if len(mod_parts) >= 2 and len(game_parts) >= 2:
            return mod_parts[0] == game_parts[0] and mod_parts[1] == game_parts[1]

        return True

    def _detect_engine_version(self, game_dir_path: str) -> str:
        engine_config = os.path.join(game_dir_path, "engine_config.xml")
        if os.path.exists(engine_config):
            try:
                tree = ET.parse(engine_config)
                root = tree.getroot()
                return self._get_xml_value(root, "Version", "")
            except Exception as e:
                logger.debug(f"Failed to read engine config: {e}")
        return ""

    @staticmethod
    def _get_xml_value(root: ET.Element, tag_name: str, default: str = "") -> str:
        elem = root.find(f".//{tag_name}")
        if elem is not None:
            value = elem.get("value")
            if value:
                return value
            if elem.text:
                return elem.text.strip()
        return default

    @staticmethod
    def get_mod_order_file_path(manager_collection: "ManagerCollectionProtocol") -> Optional[str]:
        config_manager = manager_collection.get_config_manager()
        if not config_manager:
            return None

        config_dir_path = config_manager.get_config_dir_path()
        if config_dir_path and os.path.exists(config_dir_path):
            launcher_data_path = os.path.join(config_dir_path, "LauncherData.xml")
            if os.path.exists(launcher_data_path):
                return launcher_data_path

        return None

    def read_mod_order(self, manager_collection: "ManagerCollectionProtocol") -> Tuple[List[str], str]:
        launcher_data_path = self.get_mod_order_file_path(manager_collection)
        if not launcher_data_path:
            return [], "LauncherData.xml not found"

        try:
            tree = ET.parse(launcher_data_path)
            root = tree.getroot()

            mod_order = []
            data_tag = "MultiplayerData" if self.MULTIPLAYER else "SingleplayerData"
            data_elem = root.find(f".//{data_tag}")

            if data_elem is not None:
                for user_mod_data in data_elem.findall(".//UserModData"):
                    mod_id_elem = user_mod_data.find("Id")
                    is_selected_elem = user_mod_data.find("IsSelected")

                    if mod_id_elem is not None and mod_id_elem.text:
                        is_selected = is_selected_elem is not None and is_selected_elem.text.lower() == "true"
                        if is_selected:
                            mod_order.append(mod_id_elem.text)

            return mod_order, ""
        except ET.ParseError as e:
            return [], f"Failed to parse LauncherData.xml: {str(e)}"
        except OSError as e:
            return [], f"Failed to read LauncherData.xml: {str(e)}"

    def write_mod_order(self, manager_collection: "ManagerCollectionProtocol") -> Tuple[bool, str]:
        config_manager = manager_collection.get_config_manager()
        if not config_manager:
            return False, "config_manager not available"

        mod_manager = manager_collection.get_mod_manager()
        if not mod_manager:
            return False, "mod_manager not available"

        config_dir_path = config_manager.get_config_dir_path()
        if not config_dir_path:
            return False, "config_dir_path not available"

        launcher_data_path = os.path.join(config_dir_path, "LauncherData.xml")

        enabled_mods = mod_manager.get_enabled_mods()
        disabled_mods = mod_manager.get_disabled_mods()

        root = None
        if os.path.exists(launcher_data_path):
            try:
                tree = ET.parse(launcher_data_path)
                root = tree.getroot()
            except ET.ParseError as e:
                logger.warning(f"Failed to parse existing LauncherData.xml: {e}")
                root = None

        if root is None:
            root = ET.Element("UserData")
            root.set("xmlns:xsd", "http://www.w3.org/2001/XMLSchema")
            root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")

        game_type_elem = root.find("GameType")
        if game_type_elem is None:
            game_type_elem = ET.SubElement(root, "GameType")
        game_type_elem.text = "Multiplayer" if self.MULTIPLAYER else "Singleplayer"

        if self.MULTIPLAYER:
            self._update_mod_datas(root, "MultiplayerData", enabled_mods, disabled_mods)
            singleplayer_elem = root.find("SingleplayerData")
            if singleplayer_elem is None:
                singleplayer_elem = ET.SubElement(root, "SingleplayerData")
                ET.SubElement(singleplayer_elem, "ModDatas")
        else:
            self._update_mod_datas(root, "SingleplayerData", enabled_mods, disabled_mods)
            multiplayer_elem = root.find("MultiplayerData")
            if multiplayer_elem is None:
                multiplayer_elem = ET.SubElement(root, "MultiplayerData")
                ET.SubElement(multiplayer_elem, "ModDatas")

        if root.find("DLLCheckData") is None:
            dll_check_data = ET.SubElement(root, "DLLCheckData")
            ET.SubElement(dll_check_data, "DLLData")

        try:
            tree = ET.ElementTree(root)
            ET.indent(tree, space="  ")
            tree.write(launcher_data_path, encoding="utf-8", xml_declaration=True)
            return True, ""
        except PermissionError as e:
            logger.error(f"Permission denied: {e}")
            return False, f"Permission denied: {launcher_data_path}: {str(e)}"
        except OSError as e:
            return False, f"Failed to write LauncherData.xml: {str(e)}"

    @staticmethod
    def _update_mod_datas(root: ET.Element, data_tag: str,
                          enabled_mods: List[Mod], disabled_mods: List[Mod]) -> None:
        data_elem = root.find(data_tag)
        if data_elem is None:
            data_elem = ET.SubElement(root, data_tag)

        mod_datas_elem = data_elem.find("ModDatas")
        if mod_datas_elem is None:
            mod_datas_elem = ET.SubElement(data_elem, "ModDatas")
        else:
            for mod_data in list(mod_datas_elem):
                mod_datas_elem.remove(mod_data)

        all_mods = list(enabled_mods) + list(disabled_mods)

        for mod in all_mods:
            mod_data = ET.SubElement(mod_datas_elem, "UserModData")

            id_elem = ET.SubElement(mod_data, "Id")
            id_elem.text = mod.original_id

            is_selected = mod in enabled_mods
            is_selected_elem = ET.SubElement(mod_data, "IsSelected")
            is_selected_elem.text = str(is_selected).lower()

            order_elem = ET.SubElement(mod_data, "Order")
            order_elem.text = str(enabled_mods.index(mod) if mod in enabled_mods else -1)

    def launch_game_native(self, manager_collection: "ManagerCollectionProtocol") -> Tuple[bool, str]:
        success, error = self.write_mod_order(manager_collection)
        if not success:
            return False, f"Failed to write mod order: {error}"

        config_manager = manager_collection.get_config_manager()
        if not config_manager:
            return False, "config_manager not available"

        game_dir_path = config_manager.get_game_dir_path()
        if not game_dir_path:
            return False, "Game directory not configured"

        exe_path = None
        for exec_name in self._get_executable_paths():
            candidate = os.path.join(game_dir_path, exec_name)
            if os.path.exists(candidate):
                exe_path = candidate
                break

        if not exe_path:
            return False, "Bannerlord executable not found"

        result = PlatformUtils.launch_executable(exe_path, working_dir=os.path.dirname(exe_path))
        return result.success, result.message

    def launch_game_steam(self, manager_collection: "ManagerCollectionProtocol") -> Tuple[bool, str]:
        success, error = self.write_mod_order(manager_collection)
        if not success:
            return False, f"Failed to write mod order: {error}"

        result = PlatformUtils.launch_steam_url(self.game_steam_app_id)
        return result.success, result.message
