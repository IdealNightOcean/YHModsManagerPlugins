import os
from typing import Optional

from yh_mods_manager_sdk import GameDetectorBase, PluginConfig, GamePaths


class RimWorldDetector(GameDetectorBase):
    """RimWorld游戏检测器

    配置驱动，自动支持平台差异化路径
    """

    def __init__(self, config: PluginConfig):
        self._config = config
        if config.game_info:
            self.STEAM_APP_ID = config.game_info.steam_app_id

    def _get_local_mods_folder(self) -> str:
        if self._config and self._config.path_validation:
            required = self._config.path_validation.get_required_paths()
            if "mods" in required:
                return required["mods"]
        return "Mods"

    def _validate_game_dir_path(self, path: str) -> bool:
        if super()._validate_game_dir_path(path):
            return True
        data_core = os.path.join(path, "Data", "Core")
        return os.path.exists(data_core)

    def detect_game_dir_paths(self) -> GamePaths:
        result = super().detect_game_dir_paths()

        save_dir_path = self._detect_save_directory(result.game_config_dir_path)

        return GamePaths(
            game_dir_path=result.game_dir_path,
            workshop_dir_path=result.workshop_dir_path,
            game_config_dir_path=result.game_config_dir_path,
            local_mod_dir_path=result.local_mod_dir_path,
            default_save_dir_path=save_dir_path
        )

    @staticmethod
    def _detect_save_directory(config_dir_path: Optional[str] = None) -> Optional[str]:
        if config_dir_path:
            parent_dir = os.path.dirname(config_dir_path)
            save_dir = os.path.join(parent_dir, "Saves")
            if os.path.exists(save_dir):
                return save_dir
        return None
