from yh_mods_manager_sdk import GameDetectorBase, PluginConfig


class BannerlordDetector(GameDetectorBase):
    """Bannerlord游戏检测器

    配置驱动，自动支持平台差异化路径
    """

    def __init__(self, config: PluginConfig):
        self._config = config
        if config.game_info:
            self.STEAM_APP_ID = config.game_info.steam_app_id

    def _get_local_mods_folder(self) -> str:
        if self._config and self._config.path_validation:
            required = self._config.path_validation.get_required_paths()
            if "modules" in required:
                return required["modules"]
        return "Modules"
