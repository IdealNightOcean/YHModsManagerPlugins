import logging
import os
from typing import List, Dict, Optional
from xml.etree import ElementTree as ET

from yh_mods_manager_sdk import ModParserBase, Mod, ModType, ModIDUtils, ModIssueStatus

logger = logging.getLogger(__name__)


class RimWorldModParser(ModParserBase):
    """RimWorld Mod解析器

    遵循规则P3：使用GamePaths聚合类管理路径
    """

    def scan_all_mods(self) -> List[Mod]:
        mods: List[Mod] = []
        mod_id_map: Dict[str, Mod] = {}

        if self.game_dir_path:
            data_path = os.path.join(self.game_dir_path, self.GAME_CORE_FOLDER)
            if os.path.exists(data_path):
                self._scan_data_directory(mods, mod_id_map, data_path)

        if self.local_mod_dir_path and os.path.exists(self.local_mod_dir_path):
            self._scan_directory(mods, mod_id_map, self.local_mod_dir_path, mod_type=ModType.LOCAL)

        if self.workshop_dir_path and os.path.exists(self.workshop_dir_path):
            self._scan_workshop_directory(mods, mod_id_map, self.workshop_dir_path)

        return mods

    def _scan_data_directory(self, mods: List[Mod], mod_id_map: Dict[str, Mod], data_path: str):
        try:
            for item in os.listdir(data_path):
                mod_path = os.path.join(data_path, item)
                if os.path.isdir(mod_path):
                    mod = self._parse_mod(mod_path, mod_type=ModType.CORE)
                    if mod:
                        mod.name = item
                        self._add_mod(mods, mod_id_map, mod)
        except PermissionError as e:
            logger.warning(f"Permission denied accessing data directory {data_path}: {e}")

    def _parse_mod(self, mod_path: str, mod_type: ModType = ModType.LOCAL, workshop_id: Optional[str] = None) -> \
            Optional[Mod]:
        about_path = os.path.join(mod_path, "About", self.MOD_METADATA_FILE)

        if not os.path.exists(about_path):
            alt_path = os.path.join(mod_path, "about", "about.xml")
            if os.path.exists(alt_path):
                about_path = alt_path
            else:
                return None

        try:
            tree = ET.parse(about_path)
            root = tree.getroot()

            original_id = RimWorldModParser._get_xml_value(root, "packageId", os.path.basename(mod_path))
            mod_name = RimWorldModParser._get_xml_value(root, "name", original_id)
            version = RimWorldModParser._get_xml_value(root, "modVersion", "")

            authors = self._parse_authors(root)
            supported_versions = self._parse_supported_versions(root)

            mod_type = self._determine_mod_type(original_id, mod_type)
            mod_id = ModIDUtils.generate_mod_id(original_id, mod_type)

            depended_modules = RimWorldModParser._parse_module_list(root, "modDependencies", "packageId")
            load_before = RimWorldModParser._parse_module_list(root, "loadBefore")
            load_after = RimWorldModParser._parse_module_list(root, "loadAfter")
            incompatible_modules = RimWorldModParser._parse_module_list(root, "incompatibleWith")

            force_load_before = RimWorldModParser._parse_module_list(root, "forceLoadBefore")
            force_load_after = RimWorldModParser._parse_module_list(root, "forceLoadAfter")

            load_before = list(set(load_before + force_load_before))
            load_after = list(set(load_after + force_load_after))

            description = RimWorldModParser._get_xml_value(root, "description", "")

            preview_image_path = os.path.join(mod_path, "About", "Preview.png")
            preview_image = preview_image_path if os.path.exists(preview_image_path) else None

            mod = Mod(
                id=mod_id,
                original_id=original_id,
                name=mod_name,
                version=version or "1.0.0",
                supported_versions=supported_versions,
                authors=authors,
                path=mod_path,
                mod_type=mod_type,
                workshop_id=workshop_id,
                preview_image=preview_image,
                description=description if description else None,
                depended_modules=depended_modules,
                load_before=load_before,
                load_after=load_after,
                incompatible_modules=incompatible_modules
            )

            if supported_versions and self.game_version:
                if not self._is_version_compatible(supported_versions):
                    mod.add_issue(ModIssueStatus.VERSION_MISMATCH)
                    mod.set_issue_details(ModIssueStatus.VERSION_MISMATCH,
                                          [self.tr("supported_versions", ', '.join(supported_versions))])

            return mod

        except ET.ParseError as e:
            logger.error(f"XML parse error: {mod_path} - {str(e)}")
            return RimWorldModParser._create_error_mod(mod_path, mod_type, workshop_id, f"XML parse error: {str(e)}")
        except Exception as e:
            logger.error(f"Parse error: {mod_path} - {str(e)}")
            return RimWorldModParser._create_error_mod(mod_path, mod_type, workshop_id, f"Parse error: {str(e)}")

    @staticmethod
    def _parse_authors(root: ET.Element) -> List[str]:
        authors = []
        authors_elem = root.find("./authors")
        if authors_elem is not None:
            authors = [li.text.strip() for li in authors_elem.findall("./li") if li.text and li.text.strip()]

        if not authors:
            author_single = RimWorldModParser._get_xml_value(root, "author", "")
            if author_single:
                authors = [a.strip() for a in author_single.split(",") if a.strip()]

        if not authors:
            authors = ["Unknown"]
        else:
            authors = sorted(authors, key=str.lower)

        return authors

    @staticmethod
    def _parse_supported_versions(root: ET.Element) -> List[str]:
        supported_versions = []
        supported_versions_elem = root.find("./supportedVersions")
        if supported_versions_elem is not None:
            for li in supported_versions_elem.findall("./li"):
                if li.text:
                    supported_versions.append(li.text.strip())
        return sorted(supported_versions, key=RimWorldModParser._version_sort_key)

    @staticmethod
    def _parse_module_list(root: ET.Element, parent_tag: str, child_tag: str = None) -> List[str]:
        result = []
        parent_elem = root.find(f"./{parent_tag}")
        if parent_elem is not None:
            for li in parent_elem.findall("./li"):
                if child_tag:
                    child_elem = li.find(child_tag)
                    if child_elem is not None and child_elem.text:
                        result.append(child_elem.text.strip())
                elif li.text:
                    result.append(li.text.strip())
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

    def _is_version_compatible(self, supported_versions: List[str]) -> bool:
        if not supported_versions or not self.game_version:
            return True
        game_parts = self.game_version.split('.')
        game_major_minor = f"{game_parts[0]}.{game_parts[1]}" if len(game_parts) >= 2 else game_parts[0]
        for mod_version in supported_versions:
            mod_parts = mod_version.strip().split('.')
            mod_major_minor = f"{mod_parts[0]}.{mod_parts[1]}" if len(mod_parts) >= 2 else mod_parts[0]
            if mod_major_minor == game_major_minor:
                return True
        return False

    @staticmethod
    def _get_xml_value(root: ET.Element, tag_name: str, default: str = "") -> str:
        elem = root.find(f"./{tag_name}")
        if elem is not None and elem.text:
            return elem.text.strip()
        return default

    @staticmethod
    def _version_sort_key(version: str):
        parts = version.split('.')
        result = []
        for part in parts:
            try:
                result.append(int(part))
            except ValueError:
                result.append(0)
        return tuple(result)
