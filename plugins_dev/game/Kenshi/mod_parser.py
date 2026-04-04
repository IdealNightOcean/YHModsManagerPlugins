import logging
import os
from typing import Optional, List
from xml.etree import ElementTree as ET

from yh_mods_manager_sdk import ModParserBase, PluginConfig, GamePaths, ModType, Mod, ModIDUtils, ModIssueStatus

logger = logging.getLogger(__name__)


class KenshiModParser(ModParserBase):
    """Kenshi Mod解析器

    遵循规则P3：使用GamePaths聚合类管理路径
    """

    def __init__(self, config: PluginConfig, paths: GamePaths, i18n=None):
        super().__init__(config, paths, i18n)
        path_validation = config.path_validation
        self.LOCAL_MODS_FOLDER = path_validation.get_required_paths().get("mods", "") if path_validation else ""

    def _parse_mod(self, mod_path: str, mod_type: ModType = ModType.LOCAL,
                   workshop_id: Optional[str] = None) -> Optional[Mod]:
        original_id = self._find_mod_file(mod_path)
        if not original_id:
            return None

        info_path = self._find_info_file(mod_path, original_id)
        if not info_path:
            return None

        try:
            tree = ET.parse(info_path)
            root = tree.getroot()

            mod_name = KenshiModParser._get_xml_value(root, "title", original_id)
            official_tags = KenshiModParser._parse_official_tags(root)

            mod_id = ModIDUtils.generate_mod_id(original_id, mod_type)

            mod = Mod(
                id=mod_id,
                original_id=original_id,
                name=mod_name,
                path=mod_path,
                mod_type=mod_type,
                workshop_id=workshop_id,
                official_tags=official_tags,
            )

            return mod

        except ET.ParseError as e:
            logger.error(f"XML parse error: {mod_path} - {str(e)}")
            return KenshiModParser._create_error_mod(mod_path, mod_type, workshop_id, f"XML parse error: {str(e)}")
        except Exception as e:
            logger.error(f"Parse error: {mod_path} - {str(e)}")
            return KenshiModParser._create_error_mod(mod_path, mod_type, workshop_id, f"Parse error: {str(e)}")

    @staticmethod
    def _find_mod_file(mod_path: str) -> Optional[str]:
        try:
            for item in os.listdir(mod_path):
                if item.lower().endswith(".mod"):
                    return item[:-4]
        except (PermissionError, OSError) as e:
            logger.warning(f"Failed to list directory {mod_path}: {e}")
        return None

    @staticmethod
    def _find_info_file(mod_path: str, original_id: str) -> Optional[str]:
        info_path = os.path.join(mod_path, f"_{original_id}.info")
        if os.path.exists(info_path):
            return info_path

        try:
            for item in os.listdir(mod_path):
                if item.lower().endswith(".info"):
                    return os.path.join(mod_path, item)
        except (PermissionError, OSError) as e:
            logger.warning(f"Failed to list directory {mod_path}: {e}")

        return None

    @staticmethod
    def _parse_official_tags(root: ET.Element) -> List[str]:
        tags = []
        tags_elem = root.find("./tags")
        if tags_elem is not None:
            for string_elem in tags_elem.findall("./string"):
                if string_elem.text and string_elem.text.strip():
                    tags.append(string_elem.text.strip())
        return tags

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

    @staticmethod
    def _get_xml_value(root: ET.Element, tag_name: str, default: str = "") -> str:
        elem = root.find(f"./{tag_name}")
        if elem is not None and elem.text:
            return elem.text.strip()
        return default
