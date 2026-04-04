"""
测试插件

功能说明：
1. 静态错误检测：为所有Mod添加一个静态错误标记
2. 动态错误检测：为所有已启用Mod添加一个动态错误标记
3. 自定义排序：将当前已启用Mod列表倒序排列
4. 右键菜单：新增禁用当前选中Mod的功能

遵循双插件体系规范：
- 功能插件之间不互斥（可同时启用多个）
- 功能插件与游戏插件不互斥（可混合启用）

使用SDK开发，无需主程序源码
"""

from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from yh_mods_manager_sdk import (
    FeaturePlugin,
    Mod,
    ModIssueStatus,
    GameMetadata,
)

if TYPE_CHECKING:
    from yh_mods_manager_sdk import ManagerCollectionProtocol


class TestPlugin(FeaturePlugin):
    """测试插件"""

    PLUGIN_ID = "test_plugin"
    PLUGIN_NAME = "Test Plugin"
    PLUGIN_VERSION = "1.0.0"
    PLUGIN_AUTHOR = "Trae"
    PLUGIN_DESCRIPTION = "测试插件功能：静态/动态错误检测、自定义排序、右键菜单"

    def __init__(self):
        super().__init__()
        self._mod_manager = None

    def on_initialize(self, manager_collection: "ManagerCollectionProtocol") -> Tuple[bool, str]:
        """初始化插件"""
        success, error = super().on_initialize(manager_collection)
        if not success:
            return success, error

        self._mod_manager = manager_collection.get_mod_manager()

        return True, ""

    def on_shutdown(self) -> None:
        """插件关闭时的清理工作"""
        self._mod_manager = None
        super().on_shutdown()

    def static_error_check(self, mods: List[Mod], game_metadata: GameMetadata) -> None:
        """静态错误检测：为所有Mod添加一个静态错误标记"""
        for mod in mods:
            mod.add_issue(ModIssueStatus.CUSTOM_STATIC_ERROR)

    def dynamic_error_check(self, mods: List[Mod], game_metadata: GameMetadata,
                            manager_collection: "ManagerCollectionProtocol") -> None:
        """动态错误检测：为所有已启用Mod添加一个动态错误标记"""
        enabled_ids = set()
        if self._mod_manager:
            for mod in self._mod_manager.get_enabled_mods():
                enabled_ids.add(mod.id)

        for mod in mods:
            if mod.id in enabled_ids:
                mod.add_issue(ModIssueStatus.CUSTOM_DYNAMIC_WARNING)

    def custom_topological_sort(self, mods: List[Mod],
                                manager_collection: "ManagerCollectionProtocol") -> list[Mod] | None:
        """自定义排序：将当前已启用Mod列表倒序排列"""
        if not self._mod_manager:
            return None

        enabled_mods = self._mod_manager.get_enabled_mods()
        if not enabled_mods:
            return None

        enabled_ids = {mod.id for mod in enabled_mods}

        enabled_list = [mod for mod in mods if mod.id in enabled_ids]
        disabled_list = [mod for mod in mods if mod.id not in enabled_ids]

        enabled_list.reverse()

        return enabled_list + disabled_list

    def get_context_menu_items(self, selected_mods: List[Mod],
                               manager_collection: "ManagerCollectionProtocol") -> List[Dict[str, Any]]:
        """拓展Mod列表右键菜单：新增禁用选中Mod的功能"""
        if not selected_mods:
            return []

        return [
            {
                "id": "test_plugin_disable_selected",
                "label": "禁用选中Mod（测试插件）",
                "action_id": "disable_selected_mods",
                "enabled": True,
                "separator_before": True
            }
        ]

    def on_mod_list_action(self, action_id: str, selected_mods: List[Mod],
                           manager_collection: "ManagerCollectionProtocol") -> Optional[Any]:
        """处理Mod列表动作"""
        if action_id == "disable_selected_mods":
            return self._disable_selected_mods(selected_mods)
        return None

    def _disable_selected_mods(self, selected_mods: List[Mod]) -> Dict[str, Any]:
        """禁用选中的Mod"""
        if not selected_mods:
            return {"success": False, "message": "没有选中的Mod"}

        if not self._mod_manager:
            return {"success": False, "message": "Mod管理器未初始化"}

        disabled_count = 0
        for mod in selected_mods:
            if self._mod_manager.is_mod_enabled(mod.id):
                self._mod_manager.disable_mod(mod.id)
                disabled_count += 1

        self.notify_mod_list_changed()

        return {
            "success": True,
            "message": f"已禁用 {disabled_count} 个Mod"
        }
