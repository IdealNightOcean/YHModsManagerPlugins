"""
RimWorld游戏适配器
实现规范化插件接口

使用SDK开发，无需主程序源码

遵循规则P3：使用GamePaths聚合类管理路径，禁止离散路径参数
"""

import logging
import os
import xml.etree.ElementTree as ET
from typing import Optional, List, Tuple, Dict, Any
from xml.sax import make_parser, handler, SAXException

from .detector import RimWorldDetector
from .mod_parser import RimWorldModParser
from yh_mods_manager_sdk import (
    Mod,
    ModType,
    ModIssueStatus,
    GameMetadata,
    ModMetadata,
    GameAdapter,
    PluginConfig,
    GamePaths,
    SaveParseResult,
    SaveParserCapability,
    ModProfile,
    PlatformUtils,
    ManagerCollectionProtocol,
)

logger = logging.getLogger(__name__)


class RimWorldAdapter(GameAdapter):
    """RimWorld游戏适配器
    
    实现规范化插件接口：
    - 强制要求：路径验证、游戏元数据、Mod元数据、生命周期处理
    - 可选功能：自动检测、静态错误检测、自定义菜单、Mod顺序总结
    
    遵循规则P3：使用GamePaths聚合类管理路径
    """

    def __init__(self, config: Optional[PluginConfig] = None):
        super().__init__(config)

    def _get_required_paths(self) -> Dict[str, str]:
        if self._config and self._config.path_validation:
            return self._config.path_validation.get_required_paths()
        return {}

    def _get_executable_paths(self) -> List[str]:
        if self._config and self._config.path_validation:
            return self._config.path_validation.get_executable_paths()
        return []

    @property
    def _version_file(self) -> str:
        if self._config and self._config.path_validation:
            return self._config.path_validation.version_file
        return ""

    def get_mod_parser(self, paths: GamePaths, i18n=None) -> RimWorldModParser:
        game_version = self.detect_game_version(paths)
        updated_paths = paths.with_version(game_version) if game_version else paths
        return RimWorldModParser(
            config=self._config,
            paths=updated_paths,
            i18n=i18n
        )

    def detect_game_version(self, paths: GamePaths) -> str:
        if not self._version_file or not paths.game_dir_path:
            return ""
        version_file = os.path.join(paths.game_dir_path, self._version_file)
        if os.path.exists(version_file):
            try:
                with open(version_file, 'r', encoding='utf-8') as f:
                    version = f.read().strip()
                    if version:
                        return version
            except Exception as e:
                logger.warning(f"Failed to read version file {version_file}: {e}")
        return ""

    def create_detector(self) -> RimWorldDetector:
        return RimWorldDetector(self._config)

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
                if not self._check_version_compatibility(mod.supported_versions, game_version):
                    mod.add_issue(ModIssueStatus.VERSION_MISMATCH)

    @staticmethod
    def _check_version_compatibility(supported_versions: List[str], game_version: str) -> bool:
        if not supported_versions or not game_version:
            return True

        game_parts = game_version.split('.')
        game_major_minor = f"{game_parts[0]}.{game_parts[1]}" if len(game_parts) >= 2 else game_parts[0]
        for supported in supported_versions:
            supported_parts = supported.split('.')
            supported_major_minor = f"{supported_parts[0]}.{supported_parts[1]}" if len(supported_parts) >= 2 else \
                supported_parts[0]
            if supported_major_minor == game_major_minor:
                return True

        return False

    @staticmethod
    def get_mod_order_file_path(manager_collection: "ManagerCollectionProtocol") -> Optional[str]:
        config_manager = manager_collection.get_config_manager()
        if not config_manager:
            return None
        config_dir_path = config_manager.get_config_dir_path()
        if config_dir_path and os.path.exists(config_dir_path):
            config_file_path = os.path.join(config_dir_path, "ModsConfig.xml")
            if os.path.exists(config_file_path):
                return config_file_path
        return None

    @staticmethod
    def read_mod_order(manager_collection: "ManagerCollectionProtocol") -> Tuple[List[str], str]:
        return [], "not_implemented"

    @staticmethod
    def _convert_mod_id_to_official(mod: Mod) -> str:
        original_id_lower = mod.original_id.lower()
        if mod.mod_type == ModType.WORKSHOP:
            return f"{original_id_lower}_steam"
        else:
            return original_id_lower

    def write_mod_order(self, manager_collection: "ManagerCollectionProtocol") -> Tuple[bool, str]:
        config_manager = manager_collection.get_config_manager()
        if not config_manager:
            return False, "config_manager not available"

        config_dir_path = config_manager.get_config_dir_path()
        if not config_dir_path:
            return False, "game_config_dir_path not set"

        config_file_path = config_dir_path
        if os.path.isdir(config_dir_path):
            config_file_path = os.path.join(config_dir_path, "ModsConfig.xml")

        config_dir = os.path.dirname(config_file_path)
        if not config_dir or not os.path.exists(config_dir):
            return False, f"Config directory not found: {config_file_path}"

        mod_manager = manager_collection.get_mod_manager()
        if not mod_manager:
            return False, "mod_manager not available"

        enabled_mods = mod_manager.get_enabled_mods()
        game_version = mod_manager.game_version

        try:
            root = ET.Element("ModsConfigData")

            version_elem = ET.SubElement(root, "version")
            version_elem.text = game_version if game_version else "1"

            active_mods_elem = ET.SubElement(root, "activeMods")
            known_mods_elem = ET.SubElement(root, "knownExpansions")

            for mod in enabled_mods:
                if not mod:
                    continue

                official_id = self._convert_mod_id_to_official(mod)
                li = ET.SubElement(active_mods_elem, "li")
                li.text = official_id

                if mod.mod_type == ModType.CORE or mod.mod_type == ModType.DLC:
                    li = ET.SubElement(known_mods_elem, "li")
                    li.text = official_id

            tree = ET.ElementTree(root)
            ET.indent(tree, space="  ")
            tree.write(config_file_path, encoding="utf-8", xml_declaration=True)

            return True, ""
        except PermissionError as e:
            logger.error(f"Permission denied: {e}")
            return False, f"Permission denied: {config_file_path}: {str(e)}"
        except OSError as e:
            return False, f"Failed to write ModsConfig.xml: {str(e)}"

    def get_launch_executable(self, paths: GamePaths) -> Optional[str]:
        for exe_name in self._get_executable_paths():
            exe_path = os.path.join(paths.game_dir_path, exe_name)
            if os.path.exists(exe_path):
                return exe_path
        return None

    def launch_game_native(self, manager_collection: "ManagerCollectionProtocol") -> Tuple[bool, str]:
        config_manager = manager_collection.get_config_manager()
        if not config_manager:
            return False, "config_manager not available"

        game_dir_path = config_manager.get_game_dir_path()
        if not game_dir_path:
            return False, "Game directory not configured"

        exe_path = None
        for exe_name in self._get_executable_paths():
            candidate = os.path.join(game_dir_path, exe_name)
            if os.path.exists(candidate):
                exe_path = candidate
                break

        if not exe_path:
            return False, "RimWorld executable not found"

        result = PlatformUtils.launch_executable(exe_path, working_dir=game_dir_path)
        return result.success, result.message

    def launch_game_steam(self, manager_collection: "ManagerCollectionProtocol") -> Tuple[bool, str]:
        result = PlatformUtils.launch_steam_url(self.game_steam_app_id)
        return result.success, result.message

    def get_save_parser_capabilities(self) -> List[SaveParserCapability]:
        return [
            SaveParserCapability(
                supported_extensions=[".rws"],
                supported_versions=[],
                description="RimWorld Save File (.rws)",
                priority=0
            )
        ]

    def parse_save_file(self, file_path: str, manager_collection: "ManagerCollectionProtocol" = None,
                        **kwargs) -> SaveParseResult:
        if not os.path.exists(file_path):
            return SaveParseResult.error(f"Save file not found: {file_path}")

        try:
            mod_ids, game_version = self._parse_save_file_sax(file_path)

            if not mod_ids:
                return SaveParseResult.error("No mods found in save file")

            converted_ids = self._convert_save_mod_ids(mod_ids, manager_collection)

            return SaveParseResult(
                success=True,
                mod_order=converted_ids,
                game_version=game_version,
                raw_data={"original_ids": mod_ids}
            )
        except SAXException as e:
            logger.error(f"SAX parse error: {file_path} - {e}")
            return SaveParseResult.error(f"Failed to parse save file: {str(e)}")
        except Exception as e:
            logger.error(f"Parse error: {file_path} - {e}")
            return SaveParseResult.error(f"Failed to parse save file: {str(e)}")

    @staticmethod
    def _parse_save_file_sax(file_path: str) -> Tuple[List[str], str]:
        sax_parser = _RimWorldSaveSAXParser()

        parser = make_parser()
        parser.setContentHandler(sax_parser)
        parser.setFeature(handler.feature_namespaces, False)

        with open(file_path, 'r', encoding='utf-8') as f:
            parser.parse(f)

        return sax_parser.mod_ids, sax_parser.game_version

    @staticmethod
    def _convert_save_mod_ids(original_ids: List[str], manager_collection: "ManagerCollectionProtocol") -> List[str]:
        if not manager_collection:
            return original_ids

        mod_manager = manager_collection.get_mod_manager()
        if not mod_manager:
            return original_ids

        id_comparer = mod_manager.id_comparer
        if not id_comparer:
            return original_ids

        converted_ids = []
        steam_suffix = "_steam"

        for original_id in original_ids:
            prefer_steam = original_id.lower().endswith(steam_suffix)
            clean_id = original_id[:-len(steam_suffix)] if prefer_steam else original_id

            resolved_id = id_comparer.resolve_original_id(clean_id, prefer_steam=prefer_steam)
            converted_ids.append(resolved_id if resolved_id else original_id)

        return converted_ids

    @staticmethod
    def create_save_import_profile(parse_result: SaveParseResult,
                                   manager_collection: "ManagerCollectionProtocol"):
        profile = ModProfile(
            mod_order=parse_result.mod_order,
            game_version=parse_result.game_version
        )

        return profile


class _RimWorldSaveSAXParser(handler.ContentHandler):
    """RimWorld存档SAX解析器
    
    高效解析大型存档文件，只提取mod顺序信息
    """

    def __init__(self):
        super().__init__()
        self.mod_ids: List[str] = []
        self.game_version: str = ""
        self._in_meta: bool = False
        self._in_mod_ids: bool = False
        self._in_mod_ids_readonly: bool = False
        self._in_game_version: bool = False
        self._current_text: str = ""
        self._meta_depth: int = 0
        self._found_mods: bool = False

    def startElement(self, name: str, attrs: dict):
        name_lower = name.lower()

        if name_lower == "meta":
            self._in_meta = True
            self._meta_depth = 1
        elif self._in_meta:
            if name_lower == "modids":
                self._in_mod_ids = True
            elif name_lower == "modidsreadonly":
                self._in_mod_ids_readonly = True
            elif name_lower == "gameversion":
                self._in_game_version = True
            elif name_lower == "li":
                self._current_text = ""

    def endElement(self, name: str):
        name_lower = name.lower()

        if name_lower == "meta":
            self._in_meta = False
        elif name_lower == "modids":
            self._in_mod_ids = False
            self._found_mods = True
        elif name_lower == "modidsreadonly":
            self._in_mod_ids_readonly = False
            self._found_mods = True
        elif name_lower == "gameversion":
            self._in_game_version = False
        elif name_lower == "li":
            text = self._current_text.strip()
            if text:
                if self._in_mod_ids or self._in_mod_ids_readonly:
                    self.mod_ids.append(text)
                elif self._in_game_version:
                    self.game_version = text
            self._current_text = ""

    def characters(self, content: str):
        if self._in_mod_ids or self._in_mod_ids_readonly or self._in_game_version:
            self._current_text += content

    def endDocument(self):
        pass
