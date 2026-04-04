"""
Kenshi游戏适配器
实现规范化插件接口

使用SDK开发，无需主程序源码

遵循规则P3：使用GamePaths聚合类管理路径，禁止离散路径参数
"""

import logging
import os
from typing import Optional, List, Tuple, Dict, Any

from .detector import KenshiDetector
from .mod_parser import KenshiModParser
from yh_mods_manager_sdk import (
    Mod,
    GameMetadata,
    ModMetadata,
    GameAdapter,
    PluginConfig,
    GamePaths,
    PlatformUtils,
    ManagerCollectionProtocol,
)

logger = logging.getLogger(__name__)


class KenshiAdapter(GameAdapter):
    """Kenshi游戏适配器
    
    实现规范化插件接口：
    - 强制要求：路径验证、游戏元数据、Mod元数据、生命周期处理
    - 可选功能：自动检测、静态错误检测
    
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

    def get_mod_parser(self, paths: GamePaths, i18n=None) -> KenshiModParser:
        game_version = self.detect_game_version(paths)
        updated_paths = paths.with_version(game_version) if game_version else paths
        return KenshiModParser(
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

    def create_detector(self) -> KenshiDetector:
        return KenshiDetector(self._config)

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

    def on_startup_complete(self, context: ManagerCollectionProtocol) -> None:
        pass

    @staticmethod
    def get_mod_order_file_path(manager_collection: "ManagerCollectionProtocol") -> Optional[str]:
        config_manager = manager_collection.get_config_manager()
        if not config_manager:
            return None
        game_dir_path = config_manager.get_game_dir_path()
        if game_dir_path:
            config_file_path = os.path.join(game_dir_path, "data", "mods.cfg")
            if os.path.exists(config_file_path):
                return config_file_path
        return None

    @staticmethod
    def write_mod_order(manager_collection: "ManagerCollectionProtocol") -> Tuple[bool, str]:
        config_manager = manager_collection.get_config_manager()
        if not config_manager:
            return False, "config_manager not available"

        game_dir_path = config_manager.get_game_dir_path()
        if not game_dir_path:
            return False, "game_dir_path not set"

        config_file_path = os.path.join(game_dir_path, "data", "mods.cfg")
        config_dir = os.path.dirname(config_file_path)
        if not config_dir or not os.path.exists(config_dir):
            return False, f"Config directory not found: {config_file_path}"

        mod_manager = manager_collection.get_mod_manager()
        if not mod_manager:
            return False, "mod_manager not available"

        enabled_mods = mod_manager.get_enabled_mods()

        try:
            lines = []
            for mod in enabled_mods:
                official_id = f"{mod.original_id}.mod"
                lines.append(official_id)

            with open(config_file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
                if lines:
                    f.write('\n')

            return True, ""
        except PermissionError as e:
            logger.error(f"Permission denied: {e}")
            return False, f"Permission denied: {config_file_path}: {str(e)}"
        except OSError as e:
            return False, f"Failed to write mods.cfg: {str(e)}"

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
            return False, "Kenshi executable not found"

        result = PlatformUtils.launch_executable(exe_path, working_dir=game_dir_path)
        return result.success, result.message

    def launch_game_steam(self, manager_collection: "ManagerCollectionProtocol") -> Tuple[bool, str]:
        success, error = self.write_mod_order(manager_collection)
        if not success:
            return False, f"Failed to write mod order: {error}"

        result = PlatformUtils.launch_steam_url(self.game_steam_app_id)
        return result.success, result.message
