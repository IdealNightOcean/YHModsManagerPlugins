"""
主题切换功能插件

功能说明：
- 添加「切换深色主题」菜单项到主程序工具菜单
- 点击可一键切换程序界面主题（浅色↔深色）
- 测试高亮功能：单选一个mod，让它同列表+2，不同列表系统位置的mod红色高亮

遵循双插件体系规范：
- 功能插件之间不互斥（可同时启用多个）
- 功能插件与游戏插件不互斥（可混合启用）

使用SDK开发，无需主程序源码
"""

from typing import List, Optional, Tuple, TYPE_CHECKING

from yh_mods_manager_sdk import (
    FeaturePlugin,
    PluginMenuItem,
    PluginEventType,
    PluginEvent,
    PluginResult,
    Mod,
    ListType,
)

if TYPE_CHECKING:
    from yh_mods_manager_sdk import ManagerCollectionProtocol


class ThemeSwitcherPlugin(FeaturePlugin):
    """主题切换功能插件"""

    PLUGIN_ID = "theme_switcher"
    PLUGIN_NAME = "Theme Switcher"
    PLUGIN_VERSION = "1.0.0"
    PLUGIN_AUTHOR = "Trae"
    PLUGIN_DESCRIPTION = "快速切换深色/浅色主题 + 高亮测试"

    DARK_THEME_ID = "dark"
    LIGHT_THEME_ID = "light"

    HIGHLIGHT_RULE_ID = "selection_relative_highlight"

    def __init__(self):
        super().__init__()
        self._theme_manager = None
        self._config_manager = None
        self._is_dark_mode = False
        self._mod_manager = None
        self._current_selection: Optional[str] = None
        self._current_list_type: Optional[ListType] = None
        self._current_index: int = -1

    def get_menu_items(self) -> List[PluginMenuItem]:
        """获取插件提供的菜单项"""
        return [
            PluginMenuItem(
                id="theme_switcher_toggle",
                label="切换主题",
                action_id="toggle_theme",
                shortcut="Ctrl+T",
                enabled=True,
                separator_before=True
            )
        ]

    @staticmethod
    def get_subscribed_events() -> List[PluginEventType]:
        """订阅选择变化事件"""
        return [PluginEventType.MOD_SELECTION_CHANGED]

    def on_initialize(self, manager_collection: "ManagerCollectionProtocol") -> Tuple[bool, str]:
        """初始化插件"""
        success, error = super().on_initialize(manager_collection)
        if not success:
            return success, error

        self._config_manager = manager_collection.get_config_manager()
        self._mod_manager = manager_collection.get_mod_manager()
        self._theme_manager = manager_collection.get_theme_manager()

        if self._theme_manager:
            current_theme = self._theme_manager.current_theme_id
            self._is_dark_mode = current_theme == self.DARK_THEME_ID

        return True, ""

    def on_shutdown(self) -> None:
        """插件关闭时的清理工作"""
        self.unregister_highlight_rule(self.HIGHLIGHT_RULE_ID)
        self._theme_manager = None
        self._config_manager = None
        self._mod_manager = None
        self._current_selection = None
        self._current_list_type = None
        self._current_index = -1
        super().on_shutdown()

    def on_menu_action(self, action_id: str, manager_collection: "ManagerCollectionProtocol") -> Optional[PluginResult]:
        """处理菜单动作"""
        if action_id == "toggle_theme":
            return self._toggle_theme()
        return None

    def on_event(self, event: PluginEvent) -> None:
        """处理事件"""
        if event.event_type == PluginEventType.MOD_SELECTION_CHANGED:
            self._on_selection_changed(event)

    def _on_selection_changed(self, event: PluginEvent) -> None:
        """处理选择变化事件"""
        selected_ids = event.get("selected_ids", set())
        primary_id = event.get("primary_id")
        list_type = event.get("list_type")
        is_multi = event.get("is_multi", False)

        if not selected_ids or is_multi or not primary_id:
            self._clear_highlight()
            return

        self._current_selection = primary_id
        self._current_list_type = list_type

        enabled_mods = self._mod_manager.get_enabled_mods()
        disabled_mods = sorted(
            self._mod_manager.get_disabled_mods(),
            key=lambda m: m.display_name.lower()
        )

        if list_type == ListType.ENABLED:
            mod_ids = [m.id for m in enabled_mods]
        else:
            mod_ids = [m.id for m in disabled_mods]

        try:
            self._current_index = mod_ids.index(primary_id)
        except ValueError:
            self._clear_highlight()
            return

        self._update_highlight(enabled_mods, disabled_mods)

    def _update_highlight(self, enabled_mods: List[Mod], disabled_mods: List[Mod]) -> None:
        """更新高亮规则"""
        self.unregister_highlight_rule(self.HIGHLIGHT_RULE_ID)

        if not self._mod_manager or self._current_index < 0:
            return

        target_same_list_idx = self._current_index + 2
        target_other_list_idx = self._current_index

        enabled_ids = [m.id for m in enabled_mods]
        disabled_ids = [m.id for m in disabled_mods]

        highlight_ids = set()

        if self._current_list_type == ListType.ENABLED:
            if target_same_list_idx < len(enabled_ids):
                highlight_ids.add(enabled_ids[target_same_list_idx])
            if target_other_list_idx < len(disabled_ids):
                highlight_ids.add(disabled_ids[target_other_list_idx])
        else:
            if target_same_list_idx < len(disabled_ids):
                highlight_ids.add(disabled_ids[target_same_list_idx])
            if target_other_list_idx < len(enabled_ids):
                highlight_ids.add(enabled_ids[target_other_list_idx])

        if not highlight_ids:
            return

        if not self._theme_manager:
            return

        def highlight_condition(mod: Mod) -> bool:
            return mod.id in highlight_ids

        highlight_bg = self._theme_manager.get_color('error_light')
        highlight_border = self._theme_manager.get_color('error')

        self.register_highlight_rule(
            rule_id=self.HIGHLIGHT_RULE_ID,
            condition=highlight_condition,
            background_color=highlight_bg,
            border_color=highlight_border,
            priority=10,
            description="选中Mod的相对位置高亮"
        )

        self.notify_highlight_changed()

    def _clear_highlight(self) -> None:
        """清除高亮"""
        self._current_selection = None
        self._current_list_type = None
        self._current_index = -1
        self.unregister_highlight_rule(self.HIGHLIGHT_RULE_ID)
        self.notify_highlight_changed()

    def _toggle_theme(self) -> PluginResult:
        """切换主题"""
        if not self._theme_manager:
            return PluginResult.error("主题管理器未初始化")

        available_themes = self._theme_manager.get_theme_list()

        target_theme = self.LIGHT_THEME_ID
        message = "已切换到浅色主题"

        if not self._is_dark_mode:
            if self.DARK_THEME_ID in available_themes:
                target_theme = self.DARK_THEME_ID
                message = "已切换到深色主题"
            else:
                return PluginResult.error("深色主题不可用")

        success = self._theme_manager.load_theme(target_theme)

        if success:
            self._is_dark_mode = (target_theme == self.DARK_THEME_ID)
            self._theme_manager.apply_theme_to_app()

            return PluginResult.ok(message)
        else:
            return PluginResult.error(f"切换主题失败: {target_theme}")

    def on_game_changed(self, game_id: str) -> None:
        """游戏切换时的回调"""
        self._clear_highlight()
