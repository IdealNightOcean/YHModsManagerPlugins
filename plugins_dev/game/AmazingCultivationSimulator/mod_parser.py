import json
import logging
import os
from typing import Optional

from yh_mods_manager_sdk import ModParserBase, PluginConfig, GamePaths, I18nProtocol, ModType, Mod, ModIDUtils, ModIssueStatus

logger = logging.getLogger(__name__)


class ACSModParser(ModParserBase):
    """了不起的修仙模拟器Mod解析器

    遵循规则P3：使用GamePaths聚合类管理路径
    """

    def __init__(self, config: PluginConfig, paths: GamePaths,
                 i18n: Optional["I18nProtocol"] = None):
        super().__init__(config, paths, i18n)
        mod_parser_config = config.mod_parser

        self.LOCAL_MODS_FOLDER = mod_parser_config.local_mods_folder if mod_parser_config else "Mods"

    def _parse_mod(self, mod_path: str, mod_type: ModType = ModType.LOCAL,
                   workshop_id: Optional[str] = None) -> Optional[Mod]:
        info_path = os.path.join(mod_path, self.MOD_METADATA_FILE)

        if not os.path.exists(info_path):
            return None

        try:
            with open(info_path, 'r', encoding='utf-8-sig') as f:
                content = f.read()

            info_data = json.loads(content)
            original_id = info_data.get("Name", os.path.basename(mod_path))
            mod_name = info_data.get("DisplayName", original_id)
            game_version = info_data.get("GameVersion", "")
            version = str(info_data.get("Version", "1.0.0"))
            author = info_data.get("Author", "Unknown")
            description = info_data.get("Desc", "")

            supported_versions = [str(game_version)] if game_version else []

            mod_id = ModIDUtils.generate_mod_id(original_id, mod_type)

            preview_image_path = os.path.join(mod_path, "Preview.png")
            preview_image = preview_image_path if os.path.exists(preview_image_path) else None

            mod = Mod(
                id=mod_id,
                original_id=original_id,
                name=mod_name,
                version=version,
                supported_versions=supported_versions,
                authors=[author] if author else ["Unknown"],
                path=mod_path,
                mod_type=mod_type,
                workshop_id=workshop_id,
                preview_image=preview_image,
                description=description if description else None,
            )

            return mod

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {mod_path} - {str(e)}")
            return ACSModParser._create_error_mod(mod_path, mod_type, workshop_id, f"JSON parse error: {str(e)}")
        except Exception as e:
            logger.error(f"Parse error: {mod_path} - {str(e)}")
            return ACSModParser._create_error_mod(mod_path, mod_type, workshop_id, f"Parse error: {str(e)}")

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
