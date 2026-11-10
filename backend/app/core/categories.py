from enum import StrEnum


class ESOCategory(StrEnum):
    """Central ESO domain categories. Add new members here; labels derive from the value."""

    ITEM = "ITEM"
    GEAR_SET = "GEAR_SET"
    SKILL = "SKILL"
    BUILD = "BUILD"
    CHAMPION_POINTS = "CHAMPION_POINTS"
    CRAFTING = "CRAFTING"
    RECIPE = "RECIPE"
    PROVISIONING = "PROVISIONING"
    FISHING = "FISHING"
    DUNGEON = "DUNGEON"
    TRIAL = "TRIAL"
    BOSS = "BOSS"
    ZONE = "ZONE"
    LOCATION = "LOCATION"
    QUEST = "QUEST"
    ACHIEVEMENT = "ACHIEVEMENT"
    PVP = "PVP"
    CYRODIIL = "CYRODIIL"
    TRADING = "TRADING"
    ADDON = "ADDON"
    GAME_HELP = "GAME_HELP"

    @property
    def label(self) -> str:
        return _LABEL_OVERRIDES.get(self, self.value.replace("_", " ").title())


_LABEL_OVERRIDES = {ESOCategory.PVP: "PvP"}


class SourceType(StrEnum):
    OFFICIAL = "official"
    WIKI = "wiki"
    ADDON_REPOSITORY = "addon_repository"
    COMMUNITY = "community"
    MANUAL = "manual"
    INTERNAL = "internal"
