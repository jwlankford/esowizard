from enum import StrEnum

from pydantic import BaseModel, Field


class Category(StrEnum):
    ITEMS = "Items"
    GEAR_SETS = "Gear Sets"
    SKILLS = "Skills"
    BUILDS = "Builds"
    CHAMPION_POINTS = "Champion Points"
    CRAFTING = "Crafting"
    RECIPES = "Recipes"
    PROVISIONING = "Provisioning"
    FISHING = "Fishing"
    DUNGEONS = "Dungeons"
    TRIALS = "Trials"
    BOSSES = "Bosses"
    ZONES = "Zones"
    LOCATIONS = "Locations"
    QUESTS = "Quests"
    ACHIEVEMENTS = "Achievements"
    PVP = "PvP"
    CYRODIIL = "Cyrodiil"
    TRADING = "Trading"
    ADDONS = "Addons"
    GAME_HELP = "Game Help"


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    category: Category | None = None
    limit: int = Field(default=10, ge=1, le=50)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    category: Category | None = None


class Source(BaseModel):
    title: str
    source_name: str
    source_url: str
    chunk_number: int
    content: str


class SearchResponse(BaseModel):
    results: list[Source]


class AskResponse(BaseModel):
    answer: str
    sources: list[Source]
