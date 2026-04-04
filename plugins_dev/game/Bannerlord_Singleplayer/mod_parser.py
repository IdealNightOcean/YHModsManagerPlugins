import logging
import os
from typing import Optional, List
from xml.etree import ElementTree as ET

from yh_mods_manager_sdk import ModParserBase, PluginConfig, GamePaths, ModType, Mod, ModIDUtils, ModIssueStatus

logger = logging.getLogger(__name__)


class BannerlordModParser(ModParserBase):
    """Bannerlord Mod解析器

    遵循规则P3：使用GamePaths聚合类管理路径
    """
    Multiplayer = False

    def __init__(self, config: PluginConfig, paths: GamePaths, i18n=None):
        super().__init__(config, paths, i18n)
        mod_parser_config = config.mod_parser
        self.GAME_CORE_FOLDER = mod_parser_config.game_core_folder if mod_parser_config else "Modules"
        self.LOCAL_MODS_FOLDER = mod_parser_config.local_mods_folder if mod_parser_config else "Modules"
        self.CORE_MOD_ID = mod_parser_config.game_core_id if mod_parser_config else "Native"
        self.DLC_MOD_IDS = set(mod_parser_config.game_dlc_ids) if mod_parser_config else set()

        if config.custom_data:
            self.Multiplayer = config.custom_data.get("multiplayer", False)

    def _determine_mod_type(self, mod_id: str, original_type: ModType) -> ModType:
        if original_type == ModType.WORKSHOP:
            return ModType.WORKSHOP
        if mod_id == self.CORE_MOD_ID:
            return ModType.CORE
        elif mod_id in self.DLC_MOD_IDS:
            return ModType.DLC
        return ModType.LOCAL

    def _parse_mod(self, mod_path: str, mod_type: ModType = ModType.LOCAL,
                   workshop_id: Optional[str] = None) -> Optional[Mod]:
        submodule_path = os.path.join(mod_path, self.MOD_METADATA_FILE)

        if not os.path.exists(submodule_path):
            alt_path = os.path.join(mod_path, "submodule.xml")
            if os.path.exists(alt_path):
                submodule_path = alt_path
            else:
                return None

        try:
            tree = ET.parse(submodule_path)
            root = tree.getroot()

            original_id = BannerlordModParser._get_xml_value(root, "Id", os.path.basename(mod_path))

            if not BannerlordModParser._is_mod_need_parse(root, original_id, self.Multiplayer):
                return None

            mod_name = BannerlordModParser._get_xml_value(root, "Name", original_id)
            version = BannerlordModParser._get_xml_value(root, "Version", "1.0.0")

            if version and not version.startswith("v") and not version.startswith("V"):
                version = f"v{version}"

            mod_type = self._determine_mod_type(original_id, mod_type)
            mod_id = ModIDUtils.generate_mod_id(original_id, mod_type)

            depended_modules = BannerlordModParser._parse_module_list(root, "DependedModules")
            load_before = BannerlordModParser._parse_module_list(root, "ModulesToLoadAfterThis")
            load_after = BannerlordModParser._parse_module_list(root, "ModulesToLoadBeforeThis")
            incompatible_modules = BannerlordModParser._parse_module_list(root, "IncompatibleModules")

            author = BannerlordModParser._get_xml_value(root, "Author", "Unknown")
            authors = [author] if author else ["Unknown"]
            game_version = BannerlordModParser._get_xml_value(root, "GameVersion", "")
            supported_versions = [game_version] if game_version else []

            mod = Mod(
                id=mod_id,
                original_id=original_id,
                name=mod_name,
                version=version,
                supported_versions=supported_versions,
                authors=authors,
                path=mod_path,
                mod_type=mod_type,
                workshop_id=workshop_id,
                depended_modules=depended_modules,
                load_before=load_before,
                load_after=load_after,
                incompatible_modules=incompatible_modules
            )

            if game_version and not self._is_version_compatible(game_version):
                mod.add_issue(ModIssueStatus.VERSION_MISMATCH)
                mod.set_issue_details(ModIssueStatus.VERSION_MISMATCH, [f"Game version: {game_version}"])

            return mod

        except ET.ParseError as e:
            logger.error(f"XML parse error: {mod_path} - {str(e)}")
            return BannerlordModParser._create_error_mod(mod_path, mod_type, workshop_id, f"XML parse error: {str(e)}")
        except Exception as e:
            logger.error(f"Parse error: {mod_path} - {str(e)}")
            return BannerlordModParser._create_error_mod(mod_path, mod_type, workshop_id, f"Parse error: {str(e)}")

    @staticmethod
    def _is_mod_need_parse(root: ET.Element, mod_id: str, multiplayer: bool) -> bool:
        if mod_id == "Native":
            return True

        mod_category = BannerlordModParser._get_xml_value(root, "ModuleCategory")
        if mod_category:
            if mod_category == "Singleplayer":
                return not multiplayer
            elif mod_category == "Multiplayer":
                return multiplayer

        single_player_module = BannerlordModParser._get_xml_value(root, "SingleplayerModule", "true")
        if not multiplayer and single_player_module.lower() != "true":
            return False
        multi_player_module = BannerlordModParser._get_xml_value(root, "MultiplayerModule", "false")
        if multiplayer and multi_player_module.lower() != "true":
            return False
        return True

    @staticmethod
    def _parse_module_list(root: ET.Element, parent_tag: str) -> List[str]:
        result = []
        for module in root.findall(f".//{parent_tag}/*"):
            dep_id = module.get("Id") or module.get("id") or module.text
            if dep_id:
                result.append(dep_id.strip())
        return result

    @staticmethod
    def _create_error_mod(mod_path: str, mod_type: ModType,
                          workshop_id: Optional[str], error_msg: str) -> Mod:
        original_id = os.path.basename(mod_path)
        mod_id = ModIDUtils.generate_mod_id(original_id, mod_type)
        mod = Mod(
            id=mod_id,
            original_id=original_id,
            name=original_id,
            path=mod_path,
            mod_type=mod_type,
            workshop_id=workshop_id
        )
        mod.add_issue(ModIssueStatus.INCOMPLETE)
        mod.set_issue_details(ModIssueStatus.INCOMPLETE, [error_msg])
        return mod

    def _is_version_compatible(self, mod_game_version: str) -> bool:
        if not mod_game_version or not self.game_version:
            return True
        mod_game_version = mod_game_version.strip()
        supported_parts = self.game_version.split('.')
        mod_parts = mod_game_version.split('.')
        if len(mod_parts) >= 2 and len(supported_parts) >= 2:
            if mod_parts[0] == supported_parts[0] and mod_parts[1] == supported_parts[1]:
                return True
        return False

    @staticmethod
    def _get_xml_value(root: ET.Element, tag_name: str, default: str = "") -> str:
        elem = root.find(f".//{tag_name}")
        if elem is not None:
            value = elem.get("value")
            if value:
                return value
            if elem.text:
                return elem.text.strip()

        attr_value = root.get(tag_name.lower()) or root.get(tag_name)
        if attr_value:
            return attr_value

        return default
