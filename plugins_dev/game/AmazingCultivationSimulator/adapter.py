"""
了不起的修仙模拟器游戏适配器
实现规范化插件接口

使用SDK开发，无需主程序源码
"""

import logging
import os
from typing import Optional, List, Tuple, Dict, Any

from .detector import ACSDetector
from .mod_parser import ACSModParser
from yh_mods_manager_sdk import (
    Mod,
    GameMetadata,
    ModMetadata,
    GameAdapter,
    PluginConfig,
    GamePaths,
    I18nProtocol,
    PlatformUtils,
    ManagerCollectionProtocol
)

logger = logging.getLogger(__name__)


class ACSAdapter(GameAdapter):
    """了不起的修仙模拟器游戏适配器
    
    实现规范化插件接口：
    - 强制要求：路径验证、游戏元数据、Mod元数据、生命周期处理
    - 可选功能：自动检测
    
    遵循规则P3：使用GamePaths聚合类管理路径
    """

    def __init__(self, config: Optional[PluginConfig] = None):
        super().__init__(config)
        self._init_path_config()

    def _init_path_config(self):
        pass

    def _get_required_paths(self) -> Dict[str, str]:
        if self._config and self._config.path_validation:
            return self._config.path_validation.get_required_paths()
        return {}

    def _get_executable_paths(self) -> List[str]:
        if self._config and self._config.path_validation:
            return self._config.path_validation.get_executable_paths()
        return []

    def get_mod_parser(self, paths: GamePaths,
                       i18n: Optional["I18nProtocol"] = None) -> ACSModParser:
        return ACSModParser(
            config=self._config,
            paths=paths,
            i18n=i18n
        )

    def detect_game_version(self, paths: GamePaths) -> str:
        return ""

    def create_detector(self) -> ACSDetector:
        return ACSDetector(self._config)

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
        return super().load_game_metadata(paths)

    def load_mod_metadata(self, mod: Mod) -> ModMetadata:
        metadata = super().load_mod_metadata(mod)

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

    def get_launch_executable(self, game_dir_path: str) -> Optional[str]:
        for exe_name in self._get_executable_paths():
            exe_path = os.path.join(game_dir_path, exe_name)
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

        exe_path = self.get_launch_executable(game_dir_path)
        if not exe_path or not os.path.exists(exe_path):
            return False, "ACS executable not found"

        result = PlatformUtils.launch_executable(exe_path, working_dir=game_dir_path)
        return result.success, result.message

    def launch_game_steam(self, manager_collection: "ManagerCollectionProtocol") -> Tuple[bool, str]:
        result = PlatformUtils.launch_steam_url(self.game_steam_app_id)
        return result.success, result.message
