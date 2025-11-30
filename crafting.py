# crafting.py
from settings import BROWN, ORANGE, GRAY, DARK_GRAY

class Item:
    def __init__(self, name, item_type, durability, stats_bonus=None):
        self.name = name
        self.type = item_type
        self.max_durability = durability
        self.durability = durability
        self.stats_bonus = stats_bonus or {}
        self.broken = False

    def use(self):
        if self.type != "backpack":
            self.durability -= 1
            if self.durability <= 0:
                self.broken = True
                return False
        return True

class CraftingRecipe:
    def __init__(self, name, requirements, result, level_req=1, str_req=0, dex_req=0):
        self.name = name
        self.requirements = requirements
        self.result = result
        self.level_req = level_req
        self.str_req = str_req
        self.dex_req = dex_req

    def can_craft(self, agent, inventory):
        if agent.level < self.level_req:
            return False, "Za niski poziom"
        if agent.strength < self.str_req:
            return False, f"Wymaga Siły: {self.str_req}"
        if agent.dexterity < self.dex_req:
            return False, f"Wymaga Zręczności: {self.dex_req}"

        for resource, amount in self.requirements.items():
            if inventory.get(resource, 0) < amount:
                return False, f"Brak {resource}"

        return True, "OK"

class CraftingSystem:
    def __init__(self):
        self.recipes = {
            "stone_axe": CraftingRecipe(
                "Kamienny Topór",
                {"wood": 3, "stone": 2},
                Item("Kamienny Topór", "tool", 50, {"harvest_speed": 1.5}),
                level_req=1, str_req=3
            ),
            "iron_axe": CraftingRecipe(
                "Żelazny Topór",
                {"wood": 2, "metal": 3},
                Item("Żelazny Topór", "tool", 100, {"harvest_speed": 2.0}),
                level_req=5, str_req=6
            ),
            "wooden_spear": CraftingRecipe(
                "Drewniana Włócznia",
                {"wood": 5, "fiber": 2},
                Item("Drewniana Włócznia", "weapon", 40, {"damage": 5}),
                level_req=1, str_req=3, dex_req=3
            ),
            "fiber_clothes": CraftingRecipe(
                "Ubranie z Włókna",
                {"fiber": 10},
                Item("Ubranie z Włókna", "armor", 60, {"warmth": 10, "defense": 2}),
                level_req=2
            ),
            "basic_backpack": CraftingRecipe(
                "Podstawowy Plecak",
                {"fiber": 8, "wood": 2},
                Item("Podstawowy Plecak", "backpack", 999, {"carry_capacity": 5}),
                level_req=6
            ),
            "copper_pickaxe": CraftingRecipe(
                "Miedziany Kilof",
                {"wood": 3, "copper": 4},
                Item("Miedziany Kilof", "tool", 80, {"harvest_speed": 2.5}),
                level_req=4, str_req=5
            )
        }

        self.structure_recipes = {
            "shelter": {
                "name": "Schronienie",
                "requirements": {"wood": 15, "fiber": 5},
                "color": BROWN,
                "level_req": 1
            },
            "fire": {
                "name": "Ognisko",
                "requirements": {"wood": 10, "stone": 3},
                "color": ORANGE,
                "level_req": 2
            },
            "workbench": {
                "name": "Stół Roboczy",
                "requirements": {"wood": 12, "stone": 8},
                "color": GRAY,
                "level_req": 3
            },
            "storage": {
                "name": "Magazyn",
                "requirements": {"wood": 20, "stone": 10},
                "color": BROWN,
                "level_req": 4
            },
            "wall": {
                "name": "Mur Obronny",
                "requirements": {"stone": 15, "wood": 5},
                "color": DARK_GRAY,
                "level_req": 5
            }
        }
