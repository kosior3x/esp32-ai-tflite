# survival_completed_final.py
# Final version with:
# - EXP progress bar in UI
# - Auto-stop movement when stamina is critically low (<=2) and prevent starting movement when stamina < 5.
# - Agent will wait and regenerate until stamina >= 5 to allow starting movement again.
# - Based on user's requested fixes and previous iterative updates.
import pygame
import random
import json
import math
import os
from datetime import datetime


class Skill:
    def __init__(self, name, skill_type, description, max_level=5, effects=None):
        self.name = name
        self.type = skill_type
        self.description = description
        self.level = 0
        self.max_level = max_level
        self.effects = effects or {}

    def upgrade(self):
        if self.level < self.max_level:
            self.level += 1
            return True
        return False

    def get_effect(self, effect_name):
        if self.level == 0:
            return 0
        base_value = self.effects.get(effect_name, 0)
        return base_value * self.level


class SkillTree:
    def __init__(self):
        self.skills = {
            "survival": {
                "forager": Skill("Zbieracz", "passive", "+20% zebranych zasobów, +10% szansa na jedzenie", effects={"gathering_bonus": 0.2, "food_chance": 0.1}),
                "hunter": Skill("Łowca", "passive", "+30% bonusu do jedzenia, +15% jakości mięsa", effects={"food_bonus": 0.3, "meat_quality": 0.15}),
                "water_finder": Skill("Wykrywacz Wody", "passive", "-15% utrata pragnienia, +20% efektywność wody", effects={"thirst_reduction": 0.15, "water_efficiency": 0.2}),
                "survivalist": Skill("Survivalista", "passive", "-15% utrata głodu i pragnienia", effects={"hunger_reduction": 0.15, "thirst_reduction": 0.15}),
            },
            "combat": {
                "warrior": Skill("Wojownik", "passive", "+25% obrażeń, +15% obrony", effects={"damage_bonus": 0.25, "defense_bonus": 0.15}),
                "scout": Skill("Zwiadowca", "passive", "+1 zasięg widzenia, +10% szybkość ruchu", effects={"vision_range": 1, "move_speed_bonus": 0.1}),
            },
            "crafting": {
                "builder": Skill("Budowniczy", "passive", "+20% szybkość budowy, +25% wytrzymałość struktur", effects={"build_speed": 0.2, "structure_hp": 0.25}),
                "craftsman": Skill("Rzemieślnik", "passive", "+30% wytrzymałość narzędzi, -15% zużycie materiałów", effects={"tool_durability": 0.3, "material_efficiency": 0.15}),
                "engineer": Skill("Inżynier", "passive", "Odblokowuje zaawansowane struktury, +20% bonus do blueprintów", effects={"advanced_structures": 1, "blueprint_bonus": 0.2}),
            },
            "intelligence": {
                "scholar": Skill("Uczony", "passive", "+20% EXP, +15% szybkość uczenia", effects={"exp_bonus": 0.2, "learning_speed": 0.15}),
                "strategist": Skill("Strateg", "passive", "+20% efektywność AI, +25% zarządzanie zasobami", effects={"ai_efficiency": 0.2, "resource_management": 0.25}),
                "medic": Skill("Medyk", "passive", "+30% regeneracja HP, +10 Max HP", effects={"hp_regen": 0.3, "max_hp_bonus": 10}),
            },
            "exploration": {
                "explorer": Skill("Odkrywca", "passive", "+25% bonus za odkrywanie, +1 odkrywany zasięg", effects={"exploration_bonus": 0.25, "discover_range": 1}),
                "navigator": Skill("Nawigator", "passive", "Nigdy się nie zgubi, +30% szybkość powrotu", effects={"no_lost": 1, "return_speed": 0.3}),
                "athlete": Skill("Atleta", "passive", "+20 Max Stamina, -20% zużycie staminy", effects={"max_stamina_bonus": 20, "stamina_reduction": 0.2}),
            }
        }

    def get_skill(self, category, skill_name):
        return self.skills.get(category, {}).get(skill_name)


class QLearningSystem:
    def __init__(self):
        self.rewards = {
            "gather_food": 5, "gather_water": 5, "gather_wood": 3, "gather_stone": 3, "gather_fiber": 3, "gather_metal": 4,
            "build_shelter": 15, "build_fire": 18, "build_workbench": 20, "build_storage": 22, "build_wall": 25,
            "craft_stone_axe": 12, "craft_iron_axe": 18,
            "survive_day": 10, "survive_night_in_camp": 25, "survive_week": 100,
            "explore_new_tile": 8, "discover_resource_node": 15,
            "deposit_resources": 5, "fill_storage_quota": 20,
            "night_outside_camp": -40, "death_hunger": -150, "death_thirst": -150, "death_cold": -120, "death_hp": -100,
            "inventory_full_waste": -8, "too_cautious": -15
        }
        self.total_reward = 0
        self.daily_rewards = {}
        self.action_rewards = {}

    def add_reward(self, agent, action, reward, day):
        self.total_reward += reward
        if reward < -10:
            agent.think(f"😞 To był błąd... ({reward} Q)")
        if day not in self.daily_rewards:
            self.daily_rewards[day] = 0
        self.daily_rewards[day] += reward

        if action not in self.action_rewards:
            self.action_rewards[action] = []
        self.action_rewards[action].append(reward)

    def get_reward_for_action(self, action):
        return self.rewards.get(action, 0)

    def get_daily_summary(self, day):
        reward = self.daily_rewards.get(day, 0)
        if reward > 50:
            return f"🌟 Świetny dzień! +{reward} Q"
        elif 20 <= reward <= 50:
            return f"✅ Dobry dzień! +{reward} Q"
        elif 0 <= reward < 20:
            return f"📊 Dzień: +{reward} Q"
        else:
            return f"⚠️ Słaby dzień: {reward} Q"

    def get_best_actions(self):
        avg_rewards = {}
        for action, rewards in self.action_rewards.items():
            avg_rewards[action] = sum(rewards) / len(rewards)

        sorted_actions = sorted(avg_rewards.items(), key=lambda item: item[1], reverse=True)
        return sorted_actions[:5]

pygame.init()

SCREEN_WIDTH = 1025
SCREEN_HEIGHT = 2200
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("AI Survival - 180 Days (Final)")

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
BLUE = (0, 100, 255)
YELLOW = (255, 255, 0)
BROWN = (139, 69, 19)
GRAY = (128, 128, 128)
DARK_GREEN = (0, 128, 0)
ORANGE = (255, 165, 0)
PURPLE = (128, 0, 128)
DARK_BLUE = (0, 0, 139)
LIGHT_GREEN = (144, 238, 144)
DARK_GRAY = (64, 64, 64)

clock = pygame.time.Clock()
FPS = 60

SECONDS_PER_DAY = 90
NIGHT_START = 0.6
NIGHT_HP_DRAIN = 0.02
MIN_ACTION_DELAY = 0.3
IDLE_TIME_TO_REGEN = 1.0

BASE_HUNGER_DRAIN_PER_DAY = 20.0
BASE_THIRST_DRAIN_PER_DAY = 25.0

MAP_WIDTH = 20
MAP_HEIGHT = 20
TILE_SIZE = 35

CAMP_SIZE = 5

class CampStructure:
    def __init__(self, name, structure_type, x, y, color, durability=100):
        self.name = name
        self.type = structure_type
        self.x = x
        self.y = y
        self.color = color
        self.durability = durability
        self.max_durability = durability
        self.level = 1
        self.built = True

    def repair(self, amount):
        self.durability = min(self.durability + amount, self.max_durability)

class ResourceNode:
    def __init__(self, resource_type, amount, x, y, respawn_days=3):
        self.type = resource_type
        self.max_amount = amount
        self.current_amount = amount
        self.respawn_days = respawn_days
        self.days_since_harvested = 0
        self.depleted = False
        self.x = x
        self.y = y

    def harvest(self, requested_amount):
        """Redukuje current_amount o requested_amount i zwraca faktycznie wydobyte."""
        if self.current_amount <= 0:
            self.depleted = True
            return 0

        actual = min(requested_amount, self.current_amount)
        self.current_amount -= actual
        if self.current_amount <= 0:
            self.depleted = True
            self.days_since_harvested = 0
        return actual

    def update_day(self):
        if self.depleted:
            self.days_since_harvested += 1
            if self.days_since_harvested >= self.respawn_days:
                self.current_amount = self.max_amount
                self.depleted = False
                self.days_since_harvested = 0

class WorldMap:
    def __init__(self):
        self.width = MAP_WIDTH
        self.height = MAP_HEIGHT
        self.tiles = [[0 for _ in range(self.width)] for _ in range(self.height)]
        self.resource_nodes = []
        self.camp_x = self.width // 2
        self.camp_y = self.height // 2
        self.generate_map()

    def generate_map(self):
        camp_start_x = self.camp_x - CAMP_SIZE // 2
        camp_start_y = self.camp_y - CAMP_SIZE // 2

        for cy in range(CAMP_SIZE):
            for cx in range(CAMP_SIZE):
                actual_x = camp_start_x + cx
                actual_y = camp_start_y + cy
                if 0 <= actual_x < self.width and 0 <= actual_y < self.height:
                    self.tiles[actual_y][actual_x] = 7

        def place_resource(res_type, count, max_amount, respawn, tile_id):
            attempts = 0
            while len([n for n in self.resource_nodes if n.type == res_type]) < count and attempts < 200:
                x = random.randint(0, self.width - 1)
                y = random.randint(0, self.height - 1)
                if self.tiles[y][x] != 7 and self.get_resource_at(x, y) is None:
                    self.resource_nodes.append(ResourceNode(res_type, max_amount, x, y, respawn_days=respawn))
                    self.tiles[y][x] = tile_id
                attempts += 1

        place_resource("wood", 10, 50, 3, 1)
        place_resource("stone", 8, 40, 4, 2)
        place_resource("food", 6, 30, 2, 3)
        place_resource("water", 1, 100, 1, 4)
        place_resource("fiber", 6, 35, 3, 5)
        place_resource("metal", 4, 20, 5, 6)

    def get_resource_at(self, x, y):
        for node in self.resource_nodes:
            if node.x == x and node.y == y and not node.depleted:
                return node
        return None

    def is_in_camp(self, x, y):
        camp_start_x = self.camp_x - CAMP_SIZE // 2
        camp_start_y = self.camp_y - CAMP_SIZE // 2
        return (camp_start_x <= x < camp_start_x + CAMP_SIZE and
                camp_start_y <= y < camp_start_y + CAMP_SIZE)

    def update_day(self):
        for resource in self.resource_nodes:
            resource.update_day()

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

class AIKnowledge:
    def __init__(self):
        self.attempts = 0
        self.best_survival_days = 0
        self.death_causes = {}
        self.successful_actions = {}
        self.learned_recipes = []
        self.death_days = []

        self.death_analysis = []
        self.action_history = {}
        self.milestone_achievements = {}
        self.resource_patterns = {}
        self.building_patterns = {}
        self.risk_tolerance = 0.5
        self.caution_deaths = 0

    def record_death(self, day, cause):
        self.attempts += 1
        self.death_days.append(day)
        if day > self.best_survival_days:
            self.best_survival_days = day
        if cause not in self.death_causes:
            self.death_causes[cause] = 0
        self.death_causes[cause] += 1

    def analyze_death(self, agent):
        analysis = {
            "day": agent.current_day,
            "cause": agent.death_cause,
            "final_stats": {
                "hp": agent.hp,
                "hunger": agent.hunger,
                "thirst": agent.thirst,
                "stamina": agent.stamina
            },
            "inventory": agent.inventory,
            "storage": agent.camp["storage"],
            "structures": len(agent.camp["structures"]),
            "level": agent.level,
            "skills": [s.name for s in agent.learned_skills.values()],
            "errors": [],
            "recommendations": []
        }

        # Identify errors
        if agent.death_cause == "hunger" and agent.inventory["food"] == 0 and agent.camp["storage"].get("food", 0) == 0:
            analysis["errors"].append("Zbyt mało zapasów")
            analysis["recommendations"].append("🍎 Priorytet: zbierać jedzenie codziennie")
            analysis["recommendations"].append("📦 Cel: min. 10 jednostek jedzenia w magazynie")
            self.risk_tolerance -= 0.05
        elif agent.death_cause == "thirst" and agent.inventory["water"] == 0 and agent.camp["storage"].get("water", 0) == 0:
            analysis["errors"].append("Brak źródła wody")
            analysis["recommendations"].append("💧 Znajdź i eksploatuj źródło wody")
            self.risk_tolerance -= 0.05
        if len(agent.camp["structures"]) < 2 and agent.death_cause == "cold":
            analysis["errors"].append("Za mało struktur")
            analysis["recommendations"].append("🔥 Zbudować ognisko do dnia 5")
            self.risk_tolerance -= 0.05

        if agent.death_cause == "hp_depletion" and not agent.in_camp and agent.is_night:
            analysis["errors"].append("Spędzanie nocy na zewnątrz")
            analysis["recommendations"].append("⛺ Wracaj do obozu przed nocą")

        if agent.current_day < 15 and len(agent.discovered_tiles) < 30:
            analysis["errors"].append("Zbyt mało eksploracji")
            analysis["recommendations"].append("🗺️ Eksplorować aktywniej!")
            self.risk_tolerance += 0.1

        total_resources = sum(agent.camp["storage"].values())
        if total_resources > 100 and len(agent.camp["structures"]) < 3:
            analysis["errors"].append("Gromadzenie bez budowania")
            analysis["recommendations"].append("🏗️ Inwestuj zasoby w rozwój obozu")
            self.risk_tolerance += 0.1

        self.risk_tolerance = max(0.0, min(1.0, self.risk_tolerance))

        if agent.caution_penalty_score > 5:
            self.caution_deaths += 1
            analysis["errors"].append("Zbyt ostrożne działanie")
            analysis["recommendations"].append("⚠️ Zwiększ tolerancję na ryzyko")
            self.risk_tolerance += 0.1

        self.death_analysis.append(analysis)

    def record_action(self, day, action, success, details=None):
        if success:
            if day not in self.successful_actions:
                self.successful_actions[day] = []
            self.successful_actions[day].append({"action": action, "details": details})

    def get_strategy_for_day(self, day):
        if day <= 3:
            return ["build_camp", "gather_basic", "craft_tools"]
        elif day <= 15:
            return ["upgrade_camp", "explore", "craft_better"]
        elif day <= 30:
            return ["craft_weapons", "stockpile", "optimize"]
        else:
            return ["maintain", "endgame", "survive"]

    def save_to_file(self, filename="ai_knowledge.json"):
        data = {
            "timestamp": datetime.now().isoformat(),
            "attempts": self.attempts,
            "best_survival_days": self.best_survival_days,
            "death_causes": self.death_causes,
            "successful_actions": self.successful_actions,
            "learned_recipes": self.learned_recipes,
            "death_days": self.death_days,
            "death_analysis": self.death_analysis,
            "action_history": self.action_history,
            "milestone_achievements": self.milestone_achievements,
            "resource_patterns": self.resource_patterns,
            "building_patterns": self.building_patterns,
            "risk_tolerance": self.risk_tolerance,
            "caution_deaths": self.caution_deaths
        }
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Błąd zapisu: {e}")
            return False

    def load_from_file(self, filename="ai_knowledge.json"):
        try:
            if os.path.exists(filename):
                with open(filename, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.attempts = data.get("attempts", 0)
                self.best_survival_days = data.get("best_survival_days", 0)
                self.death_causes = data.get("death_causes", {})
                self.successful_actions = data.get("successful_actions", {})
                self.learned_recipes = data.get("learned_recipes", [])
                self.death_days = data.get("death_days", [])
                self.death_analysis = data.get("death_analysis", [])
                self.action_history = data.get("action_history", {})
                self.milestone_achievements = data.get("milestone_achievements", {})
                self.resource_patterns = data.get("resource_patterns", {})
                self.building_patterns = data.get("building_patterns", {})
                self.risk_tolerance = data.get("risk_tolerance", 0.5)
                self.caution_deaths = data.get("caution_deaths", 0)
                return True
        except Exception as e:
            print(f"Błąd wczytywania: {e}")
        return False

class Agent:
    def __init__(self, knowledge, world_map, add_log_func):
        self.strength = 5
        self.dexterity = 5
        self.perception = 5
        self.intelligence = 5
        self.vitality = 5

        self.add_log = add_log_func

        self.level = 1
        self.exp = 0
        self.exp_to_next = 100
        self.stat_points = 0

        self.skill_tree = SkillTree()
        self.learned_skills = {}
        self.skill_points = 0
        self.pending_skill_choice = False

        self.hp = self.vitality * 20
        self.max_hp = self.vitality * 20
        self.hunger = 100
        self.thirst = 100
        self.warmth = 100
        self.stamina = 100
        self.max_stamina = 100 + (self.vitality * 5)

        self.x = world_map.camp_x
        self.y = world_map.camp_y
        self.move_cooldown = 0.0
        self.move_speed = 0.5
        self.idle_timer = 0.0

        self.base_carry_capacity = 10
        self.current_carry_capacity = self.base_carry_capacity + self.strength

        self.inventory = {
            "wood": 0,
            "stone": 0,
            "food": 0,
            "water": 0,
            "fiber": 0,
            "metal": 0
        }

        self.equipment = {
            "weapon": None,
            "tool": None,
            "armor": None,
            "backpack": None
        }

        self.camp = {
            "level": 1,
            "storage": {},
            "structures": []
        }

        self.init_camp_structures()

        self.knowledge = knowledge
        self.crafting = CraftingSystem()
        self.current_day = 0
        self.day_progress = 0.0
        self.is_night = False
        self.in_camp = True
        self.alive = True
        self.death_cause = None
        self.current_action = None

        # Movement target: if not None agent moves towards it in update()
        self.move_target = None

        self.thoughts = []
        self.action_history = []
        self.memory_context = {}
        self.position_history = []

        self.caution_penalty_score = 0
        self.days_without_exploration = 0
        self.days_without_building = 0
        self.excessive_gathering_count = 0
        self.consecutive_camp_days = 0

        self.discovered_tiles = set()
        self.q_learning = QLearningSystem()

    def init_camp_structures(self):
        self.camp["structures"].append(
            CampStructure("Schronienie", "shelter", 2, 2, BROWN, 100)
        )

    def build_structure(self, structure_type, camp_x, camp_y):
        recipe = self.crafting.structure_recipes.get(structure_type)
        if not recipe:
            return False, "Nieznana struktura"
        if self.level < recipe["level_req"]:
            return False, f"Wymaga poziomu {recipe['level_req']}"
        for res, amt in recipe["requirements"].items():
            if self.inventory.get(res, 0) < amt:
                return False, f"Brak {res}"
        for struct in self.camp["structures"]:
            if struct.x == camp_x and struct.y == camp_y:
                return False, "Pole zajęte"
        for res, amt in recipe["requirements"].items():
            self.inventory[res] -= amt
        new_struct = CampStructure(
            recipe["name"],
            structure_type,
            camp_x,
            camp_y,
            recipe["color"],
            100
        )
        self.camp["structures"].append(new_struct)
        self.camp["level"] += 1
        return True, f"Zbudowano {recipe['name']}"

    def calculate_carry_capacity(self):
        capacity = self.base_carry_capacity + self.strength
        if self.equipment["backpack"]:
            capacity += self.equipment["backpack"].stats_bonus.get("carry_capacity", 0)
        self.current_carry_capacity = capacity
        return capacity

    def get_total_inventory_size(self):
        return sum(self.inventory.values())

    def can_carry_more(self, amount=1):
        return self.get_total_inventory_size() + amount <= self.current_carry_capacity

    def gain_exp(self, amount, action_type):
        day_bonus = 1.0 + (self.current_day * 0.08)
        int_bonus = 1.0 + (self.intelligence * 0.02)
        total_exp = int(amount * day_bonus * int_bonus)
        self.exp += total_exp
        if self.exp < 0:
            self.exp = 0
        while self.exp >= self.exp_to_next:
            self.level_up()
        self.knowledge.record_action(self.current_day, action_type, True, {"exp": total_exp})
        return total_exp

    def level_up(self):
        self.level += 1
        self.exp -= self.exp_to_next
        self.exp_to_next = int(self.exp_to_next * 1.12) + 10
        self.stat_points += 5
        if self.level % 6 == 0:
            self.skill_points += 1
            self.pending_skill_choice = True
            self.add_log(f"Otrzymano 1 punkt umiejętności!")
        self.auto_distribute_stats()
        self.max_stamina = 100 + (self.vitality * 5)
        self.max_hp = self.vitality * 20
        self.hp = min(self.hp, self.max_hp)
        self.add_log(f"AWANS! Poziom {self.level}! Otrzymano 5 pkt atrybutów.")

    def auto_distribute_stats(self):
        while self.stat_points > 0:
            priorities = []
            if self.knowledge.death_causes.get("hunger", 0) > 2 or self.knowledge.death_causes.get("thirst", 0) > 2:
                priorities.append("perception")
                priorities.append("vitality")
            if self.knowledge.death_causes.get("combat", 0) > 1:
                priorities.extend(["strength", "dexterity"])
            if self.knowledge.death_causes.get("cold", 0) > 1:
                priorities.append("vitality")
            if not priorities:
                priorities = ["strength", "dexterity", "perception", "intelligence", "vitality"]
            stat = random.choice(priorities)
            setattr(self, stat, getattr(self, stat) + 1)
            self.stat_points -= 1
        self.calculate_carry_capacity()

    def think(self, thought):
        self.thoughts.append(thought)
        if len(self.thoughts) > 5:
            self.thoughts.pop(0)

    def reflect_on_day(self):
        if self.current_day == 1:
            self.think("📅 Pierwszy dzień. Muszę znaleźć wodę i jedzenie.")
        elif self.current_day == 5:
            if len(self.camp["structures"]) < 2:
                self.think("Trzeba rozbudować obóz.")
            else:
                self.think("Obóz wygląda dobrze.")
        elif self.current_day == 10:
            if self.level < 3:
                self.think("Mój poziom jest niski. Muszę zdobywać więcej EXP.")
        elif self.current_day > self.knowledge.best_survival_days:
            self.think("🎉 NOWY REKORD!")

    def think_about_action(self, action):
        if "gather" in action:
            self.think(f"🍎 Potrzebuję jedzenia. Idę zbierać.")
        elif "rest" in action:
            self.think("😴 Jestem wykończony. Czas na odpoczynek.")
        elif "build" in action:
            self.think("🏗️ Buduję ognisko. Rozwój obozu to klucz.")

    def check_dangerous_situation(self):
        if self.hunger < 15:
            self.think("🚨 KRYTYCZNY GŁÓD! Natychmiastowe działanie!")
        if self.thirst < 15:
            self.think("💀 Woda TERAZ! To kwestia życia lub śmierci!")
        if self.is_night and not self.in_camp:
            self.think("⚠️ Ostatnim razem spędziłem noc na zewnątrz i... nie przeżyłem.")

    def apply_skill_effects(self):
        # Reset bonuses to base values before applying skill effects
        self.max_hp = self.vitality * 20
        self.max_stamina = 100 + (self.vitality * 5)

        for skill in self.learned_skills.values():
            self.max_hp += skill.get_effect("max_hp_bonus")
            self.max_stamina += skill.get_effect("max_stamina_bonus")
            # Other passive effects can be applied directly in the relevant methods
            # For example, hunger/thirst reduction would be applied in the update method

    def update_discovered_tiles(self, x, y):
        if (x, y) not in self.discovered_tiles:
            self.discovered_tiles.add((x, y))
            self.days_without_exploration = 0

    def check_caution_penalties(self):
        # Kara #1: Brak eksploracji
        if self.days_without_exploration >= 3 and self.current_day < 30:
            self.hp -= 5
            self.stamina -= 10
            self.caution_penalty_score += 1
            self.think("😰 Stagnacja! Muszę coś odkrywać!")

        # Kara #2: Gromadzenie bez budowania
        total_resources = sum(self.camp["storage"].values())
        if total_resources > 80 and len(self.camp["structures"]) < 4 and self.current_day < 20:
            self.hunger -= 10
            self.thirst -= 10
            self.caution_penalty_score += 1
            self.think("🤔 Zbyt dużo gromadzę, a za mało buduję!")

        # Kara #3: Zbyt długo w obozie
        if self.consecutive_camp_days >= 4 and self.current_day > 5:
            self.hp -= 8
            self.caution_penalty_score += 1
            self.think("⚠️ Siedzenie w obozie mnie zabije! Muszę działać!")

        # Kara #4: Zbyt wolny rozwój
        if self.level < (self.current_day / 3) and self.current_day >= 10:
            self.max_hp -= 10
            self.caution_penalty_score += 1
            self.think(f"📊 Powinienem być poziom {self.current_day // 3}, a jestem {self.level}!")

        # Kara #5: Mało odkrytych pól
        if len(self.discovered_tiles) < (self.current_day * 3) and self.current_day >= 5:
            self.stamina -= 15
            self.caution_penalty_score += 1
            self.think(f"🗺️ Odkryłem tylko {len(self.discovered_tiles)} pól! Za mało!")

    def auto_choose_skill(self):
        if self.skill_points > 0:
            # Prioritize based on death causes
            priorities = []
            if self.knowledge.death_causes.get("hunger", 0) > 2 or self.knowledge.death_causes.get("thirst", 0) > 2:
                priorities.append("survival")
            if self.knowledge.death_causes.get("hp_depletion", 0) > 1:
                priorities.append("combat")
            if self.knowledge.death_causes.get("cold", 0) > 1:
                priorities.append("crafting")

            if not priorities:
                priorities = ["survival", "crafting", "exploration", "intelligence", "combat"]

            category = random.choice(priorities)
            skill_name = random.choice(list(self.skill_tree.skills[category].keys()))
            skill = self.skill_tree.get_skill(category, skill_name)

            if skill.upgrade():
                self.learned_skills[skill.name] = skill
                self.skill_points -= 1
                self.pending_skill_choice = False
                self.add_log(f"Wybrano umiejętność: {skill.name} Lvl {skill.level}")
                self.apply_skill_effects()

    def start_move(self, target_x, target_y, world_map):
        # If agent's stamina is below threshold, do not start movement.
        if self.stamina < 5:
            # ensure no target is set so agent can idle & regenerate
            self.move_target = None
            # Log a short message (if logging function is available)
            try:
                self.add_log("Stamina zbyt niska, odpoczynek przed ruchem.")
            except Exception:
                pass
            return False

        # if already at target, nothing to do
        if self.x == target_x and self.y == target_y:
            self.move_target = None
            return False
        # set the target; update() will handle stepwise movement
        self.move_target = (target_x, target_y)
        return True

    def _do_move_step_towards_target(self, world_map):
        """Wykonuje krok ruchu (gdy move_cooldown <= 0) w kierunku move_target."""
        if not self.move_target:
            return False

        target_x, target_y = self.move_target
        dx = target_x - self.x
        dy = target_y - self.y

        if dx == 0 and dy == 0:
            self.move_target = None
            return True

        step_x = 0
        if dx > 0:
            step_x = 1
        elif dx < 0:
            step_x = -1
        step_y = 0
        if dy > 0:
            step_y = 1
        elif dy < 0:
            step_y = -1

        new_x = self.x + step_x
        new_y = self.y + step_y

        if 0 <= new_x < world_map.width and 0 <= new_y < world_map.height:
            # Prevent movement if stamina below minimum required for movement
            if self.stamina < 5:
                # cancel target to allow regeneration
                self.move_target = None
                try:
                    self.add_log("Przerwanie ruchu — za mało staminy, odpoczynek.")
                except Exception:
                    pass
                return False

            self.x = new_x
            self.y = new_y
            self.position_history.append((self.x, self.y))
            if len(self.position_history) > 10:
                self.position_history.pop(0)
            self.update_discovered_tiles(self.x, self.y)
            self.move_cooldown = self.move_speed
            self.stamina = max(0, self.stamina - 2)
            self.idle_timer = 0
            self.in_camp = world_map.is_in_camp(self.x, self.y)
            # jeśli dotarliśmy
            if self.x == target_x and self.y == target_y:
                self.move_target = None
            return True

        # nie udało się poruszyć (krawędź mapy)
        self.move_target = None
        return False

    def calculate_daily_quota(self, days_ahead=2):
        base_food_units = 1 * days_ahead
        base_water_units = 1 * days_ahead
        level_bonus_percent = (self.level - 1) * 0.05
        required_food = math.ceil(base_food_units * (1.0 + level_bonus_percent))
        required_water = math.ceil(base_water_units * (1.0 + level_bonus_percent))
        return {
            "food": required_food,
            "water": required_water
        }

    def ai_decide_action(self, world_map):
        if len(self.position_history) > 6 and len(set(self.position_history[-6:])) <= 2:
            self.think("Utknąłem w pętli, eksploruję losowo.")
            return "explore"
        if self.pending_skill_choice:
            self.auto_choose_skill()

        # Priority based on last death cause
        if self.knowledge.death_analysis:
            last_death = self.knowledge.death_analysis[-1]
            if last_death['cause'] == 'hunger' and self.inventory['food'] < 10:
                self.think("Muszę unikać śmierci z głodu. Priorytet: jedzenie!")
                return ("find_resource", "food")
            if last_death['cause'] == 'thirst' and self.inventory['water'] < 10:
                self.think("Ostatnio zginąłem z pragnienia. Priorytet: woda!")
                return ("find_resource", "water")

        if self.hunger < 20 and self.inventory["food"] > 0:
            return "eat"
        if self.thirst < 20 and self.inventory["water"] > 0:
            return "drink"
        if self.stamina < self.max_stamina * 0.2 and self.in_camp:
            return "rest"
        if self.hp < self.max_hp * 0.4 and self.in_camp:
            return "rest"

        if self.get_total_inventory_size() >= self.current_carry_capacity - 1:
            if not self.in_camp:
                self.add_log("Inwentarz pełny. Powrót do obozu!")
                return ("move_to_camp", world_map.camp_x, world_map.camp_y)
            else:
                self.add_log("Deponowanie zasobów.")
                return "deposit"

        quota = self.calculate_daily_quota(days_ahead=2)
        current_food_units = self.inventory["food"]
        current_water_units = self.inventory["water"]

        if current_food_units < quota["food"]:
            return ("find_resource", "food")
        if current_water_units < quota["water"]:
            return ("find_resource", "water")

        if self.day_progress > NIGHT_START and not self.in_camp:
            self.add_log("Nadchodzi noc. Wracam do obozu.")
            return ("move_to_camp", world_map.camp_x, world_map.camp_y)

        if self.current_day <= 3:
            if self.inventory["wood"] < 15 and self.can_carry_more():
                return ("find_resource", "wood")
            if self.inventory["stone"] < 5 and self.can_carry_more():
                return ("find_resource", "stone")
            if self.in_camp and self.inventory["wood"] >= 3 and self.inventory["stone"] >= 2 and not self.equipment["tool"]:
                return "craft_stone_axe"
        elif self.current_day <= 10:
            if self.in_camp and len(self.camp["structures"]) < 3:
                if self.level >= 2 and self.inventory["wood"] >= 10 and self.inventory["stone"] >= 3:
                    return "build_fire"
            if self.inventory["fiber"] < 10 and self.can_carry_more():
                 return ("find_resource", "fiber")

        if self.inventory["wood"] < 30 and self.can_carry_more():
            return ("find_resource", "wood")
        if self.inventory["stone"] < 30 and self.can_carry_more():
            return ("find_resource", "stone")

        # Default action based on risk tolerance
        if self.knowledge.risk_tolerance > 0.65:
            return "explore"
        else:
            # Fallback to gathering basic resources if low risk tolerance
            if self.inventory["wood"] < 50:
                return ("find_resource", "wood")
            else:
                return "explore"

    def execute_action(self, action, world_map):
        self.current_action = action
        self.idle_timer = 0
        action_duration = 1.0

        if isinstance(action, str):
            self.think_about_action(action)
        elif isinstance(action, tuple):
            self.think_about_action(action[0])

        if isinstance(action, tuple):
            action_type = action[0]
            if action_type == "move_to_camp":
                target_x, target_y = action[1], action[2]
                started = self.start_move(target_x, target_y, world_map)
                # Jeżeli nie wystartowano bo już na miejscu -> daj małą opóźnienie
                if not started:
                    return False, "Już w obozie lub brak staminy", 0.1
                return True, "Powrót do obozu...", self.move_speed

            elif action_type == "find_resource":
                resource_type = action[1]
                closest = None
                closest_dist = 9999
                for node in world_map.resource_nodes:
                    if node.type == resource_type and not node.depleted:
                        dist = abs(node.x - self.x) + abs(node.y - self.y)
                        if dist < closest_dist:
                            closest = node
                            closest_dist = dist

                if closest:
                    if self.x == closest.x and self.y == closest.y:
                        # Jesteśmy na węźle -> zbieramy, ale bierzemy pod uwagę przestrzeń w ekwipunku
                        if self.get_total_inventory_size() >= self.current_carry_capacity:
                            self.add_log(f"Inwentarz pełny, nie mogę zebrać {resource_type}.")
                            return False, "Ekwipunek pełny. Wymagane deponowanie.", 0.1

                        base_time = 1.5
                        correction = 1.0 - (self.strength * 0.05)
                        action_duration = max(base_time * correction, MIN_ACTION_DELAY)

                        tool_efficiency = 1.0
                        if self.equipment["tool"]:
                            tool_efficiency = self.equipment["tool"].stats_bonus.get("harvest_speed", 1.0)
                            if self.equipment["tool"].broken:
                                self.add_log(f"Narzędzie {self.equipment['tool'].name} zepsute!")
                                return False, "Zepsute narzędzie.", action_duration

                        # Wylicz losową ilość możliwą do zebrania i ogranicz ją pojemnością
                        predicted = min(int(random.randint(1, 3) * tool_efficiency), closest.current_amount)
                        available_space = self.current_carry_capacity - self.get_total_inventory_size()
                        actual = min(predicted, available_space)

                        if actual <= 0:
                            self.add_log(f"Brak miejsca na {resource_type}.")
                            return False, "Brak miejsca w ekwipunku.", 0.1

                        # Pobierz actual z węzła
                        harvested = closest.harvest(actual)
                        if harvested > 0:
                            if self.equipment["tool"]:
                                self.equipment["tool"].use()
                            self.inventory[resource_type] += harvested
                            self.stamina = max(0, self.stamina - 5)
                            exp = self.gain_exp(8, f"gather_{resource_type}")
                            reward = self.q_learning.get_reward_for_action(f"gather_{resource_type}") + harvested * 0.5
                            self.q_learning.add_reward(self, f"gather_{resource_type}", reward, self.current_day)
                            if reward > 15:
                                self.think(f"🌟 Świetna akcja! (+{reward} Q)")
                            return True, f"Zebrano {harvested} {resource_type} (+exp EXP)", action_duration

                        return False, "Surowiec wyczerpany.", action_duration
                    else:
                        # ruszamy do węzła: ustaw cel (kontynuowany automatycznie w update)
                        started = self.start_move(closest.x, closest.y, world_map)
                        if not started:
                            return False, "Błąd startu ruchu lub brak staminy.", 0.1
                        return True, f"Szukanie {resource_type}...", self.move_speed

                return False, f"Brak {resource_type}", 1.0

        if action == "eat":
            action_duration = max(0.5 - (self.dexterity * 0.01), MIN_ACTION_DELAY)
            if self.inventory["food"] > 0:
                self.inventory["food"] -= 1
                self.hunger = min(self.hunger + 35, 100)
                reward = self.q_learning.get_reward_for_action("eat")
                self.q_learning.add_reward(self, "eat", reward, self.current_day)
                return True, "Zjedzono jedzenie", action_duration
            return False, "Brak jedzenia", action_duration

        elif action == "drink":
            action_duration = max(0.5 - (self.dexterity * 0.01), MIN_ACTION_DELAY)
            if self.inventory["water"] > 0:
                self.inventory["water"] -= 1
                self.thirst = min(self.thirst + 45, 100)
                reward = self.q_learning.get_reward_for_action("drink")
                self.q_learning.add_reward(self, "drink", reward, self.current_day)
                return True, "Wypito wodę", action_duration
            return False, "Brak wody", action_duration

        elif action == "rest":
            action_duration = 0.5
            if self.in_camp:
                vitality_regen = self.vitality * 5
                self.hp = min(self.hp + vitality_regen, self.max_hp)
                self.stamina = min(self.stamina + (vitality_regen * 2), self.max_stamina)
                self.hunger = min(self.hunger + 5, 100)
                self.thirst = min(self.thirst + 5, 100)
                self.warmth = min(self.warmth + 10, 100)
                reward = self.q_learning.get_reward_for_action("rest")
                self.q_learning.add_reward(self, "rest", reward, self.current_day)
                return True, f"Odpoczynek (+{vitality_regen} HP/Stamina)", action_duration
            return False, "Nie w obozie", action_duration

        elif action == "deposit":
            action_duration = max(0.5 - (self.strength * 0.01), MIN_ACTION_DELAY)
            if self.in_camp:
                deposited = sum(self.inventory.values())
                if deposited == 0:
                    return False, "Ekwipunek pusty, brak depozytu.", 0.1
                for res in list(self.inventory.keys()):
                    if res in self.camp["storage"]:
                        self.camp["storage"][res] += self.inventory[res]
                    else:
                        self.camp["storage"][res] = self.inventory[res]
                    self.inventory[res] = 0
                reward = self.q_learning.get_reward_for_action("deposit_resources")
                self.q_learning.add_reward(self, "deposit_resources", reward, self.current_day)
                return True, f"Zdeponowano {deposited} przedmiotów", action_duration
            return False, "Nie w obozie", action_duration

        elif action.startswith("craft_"):
            recipe_name = action.split("craft_")[1]
            if recipe_name == "stone_axe":
                recipe = self.crafting.recipes["stone_axe"]
                action_duration = max(2.0 - (self.intelligence * 0.1), MIN_ACTION_DELAY)
                can_craft, reason = recipe.can_craft(self, self.inventory)
                if can_craft:
                    for res, amt in recipe.requirements.items():
                        self.inventory[res] -= amt
                    item = Item("Kamienny Topór", "tool", 50, {"harvest_speed": 1.5})
                    self.equipment["tool"] = item
                    exp = self.gain_exp(15, "craft_stone_axe")
                    reward = self.q_learning.get_reward_for_action("craft_stone_axe")
                    self.q_learning.add_reward(self, "craft_stone_axe", reward, self.current_day)
                    if reward > 15:
                        self.think(f"🌟 Świetna akcja! (+{reward} Q)")
                    return True, f"Skraftowano Topór (+{exp} EXP)", action_duration
                return False, reason, action_duration
            return False, "Nieznany przepis", action_duration

        elif action.startswith("build_"):
            structure_type = action.split("build_")[1]
            if structure_type in self.crafting.structure_recipes:
                action_duration = max(3.0 - (self.strength * 0.15), MIN_ACTION_DELAY)
                if not self.in_camp:
                    return False, "Nie w obozie", action_duration
                for cy in range(CAMP_SIZE):
                    for cx in range(CAMP_SIZE):
                        occupied = False
                        for struct in self.camp["structures"]:
                            if struct.x == cx and struct.y == cy:
                                occupied = True
                                break
                        if not occupied:
                            success, msg = self.build_structure(structure_type, cx, cy)
                            if success:
                                exp = self.gain_exp(25, f"build_{structure_type}")
                                reward = self.q_learning.get_reward_for_action(f"build_{structure_type}")
                                self.q_learning.add_reward(self, f"build_{structure_type}", reward, self.current_day)
                                if reward > 15:
                                    self.think(f"🌟 Świetna akcja! (+{reward} Q)")
                                return True, f"{msg} (+{exp} EXP)", action_duration
                            return False, msg, action_duration
                return False, "Brak miejsca w obozie", action_duration

        elif action == "explore":
            dx = random.randint(-1, 1)
            dy = random.randint(-1, 1)
            new_x = max(0, min(self.x + dx, world_map.width - 1))
            new_y = max(0, min(self.y + dy, world_map.height - 1))
            is_new_tile = (new_x, new_y) not in self.discovered_tiles
            started = self.start_move(new_x, new_y, world_map)
            if not started:
                return False, "Nie można eksplorować - mało staminy", 0.1
            if is_new_tile:
                reward = self.q_learning.get_reward_for_action("explore_new_tile")
                self.q_learning.add_reward(self, "explore_new_tile", reward, self.current_day)
                if reward > 15:
                    self.think(f"🌟 Świetna akcja! (+{reward} Q)")
            return True, "Eksploracja...", self.move_speed

        return False, "Nieznana akcja", 1.0

    def update(self, delta_time, world_map):
        # reduce cooldown
        self.move_cooldown = max(0, self.move_cooldown - delta_time)

        # AUTO-ODPOCZYNEK PRZY NISKIEJ STAMINIE
        # Jeśli stamina spadła do <=2 -> natychmiast przerwij ruch, aby umożliwić regenerację.
        if self.stamina <= 2 and self.move_target is not None:
            self.move_target = None
            try:
                self.add_log("Krytyczna stamina — przerwanie ruchu. Odpoczynek...")
            except Exception:
                pass

        # jeśli ustawiony cel i cooldown==0 -> wykonaj krok
        if self.move_target and self.move_cooldown <= 0:
            self._do_move_step_towards_target(world_map)

        day_fraction = delta_time / SECONDS_PER_DAY
        hunger_drain = BASE_HUNGER_DRAIN_PER_DAY
        thirst_drain = BASE_THIRST_DRAIN_PER_DAY

        if "Survivalista" in self.learned_skills:
            hunger_drain *= (1 - self.learned_skills["Survivalista"].get_effect("hunger_reduction"))
            thirst_drain *= (1 - self.learned_skills["Survivalista"].get_effect("thirst_reduction"))

        self.hunger -= hunger_drain * day_fraction
        self.thirst -= thirst_drain * day_fraction

        if self.move_cooldown <= 0 and not self.move_target:
            self.idle_timer += delta_time
        else:
            self.idle_timer = 0

        # jeśli agent stoi bezczynnie przez wymagany czas i jest dzień -> regeneracja stamina
        if self.idle_timer >= IDLE_TIME_TO_REGEN:
            if not self.is_night:
                base_stamina_regen = 2.0
                stamina_regen_rate = (base_stamina_regen + (self.vitality * 0.5)) * delta_time
                camp_bonus = 1.5 if self.in_camp else 1.0
                self.stamina = min(self.stamina + stamina_regen_rate * camp_bonus, self.max_stamina)
                self.hp = min(self.hp + (self.vitality * 0.05 * delta_time), self.max_hp)

        # clamp stamina to valid range
        self.stamina = max(0, min(self.stamina, self.max_stamina))

        self.day_progress += delta_time / SECONDS_PER_DAY
        self.is_night = self.day_progress >= NIGHT_START

        if self.is_night and not self.in_camp:
            self.hp -= NIGHT_HP_DRAIN * delta_time
            self.warmth -= 0.1 * delta_time

        if self.day_progress >= 1.0:
            self.end_day(world_map)

        self.check_dangerous_situation()
        self.check_death()

    def end_day(self, world_map):
        self.current_day += 1
        self.day_progress = 0.0
        self.is_night = False
        self.reflect_on_day()
        self.days_without_exploration += 1
        if self.in_camp:
            self.consecutive_camp_days += 1
        else:
            self.consecutive_camp_days = 0

        self.check_caution_penalties()

        if not self.in_camp:
            self.gain_exp(-150, "night_out_penalty")
            self.add_log("Otrzymano karę EXP za noc poza obozem.")
        if self.in_camp:
            camp_exp = 60 + (self.camp["level"] * 10)
            camp_exp = int(camp_exp * (1 + self.current_day * 0.08))
            self.gain_exp(camp_exp, "survive_day")
            reward = self.q_learning.get_reward_for_action("survive_night_in_camp")
            self.q_learning.add_reward(self, "survive_night_in_camp", reward, self.current_day)
            self.add_log(f"Zakończono Dzień {self.current_day}. (+{camp_exp} EXP)")
        world_map.update_day()
        self.check_death()

    def check_death(self):
        if self.hunger <= 0:
            self.alive = False
            self.death_cause = "hunger"
            reward = self.q_learning.get_reward_for_action("death_hunger")
            self.q_learning.add_reward(self, "death_hunger", reward, self.current_day)
        elif self.thirst <= 0:
            self.alive = False
            self.death_cause = "thirst"
            reward = self.q_learning.get_reward_for_action("death_thirst")
            self.q_learning.add_reward(self, "death_thirst", reward, self.current_day)
        elif self.warmth <= 0:
            self.alive = False
            self.death_cause = "cold"
            reward = self.q_learning.get_reward_for_action("death_cold")
            self.q_learning.add_reward(self, "death_cold", reward, self.current_day)
        elif self.hp <= 0:
            self.alive = False
            self.death_cause = "hp_depletion"
            reward = self.q_learning.get_reward_for_action("death_hp")
            self.q_learning.add_reward(self, "death_hp", reward, self.current_day)

class Game:
    def __init__(self):
        self.knowledge = AIKnowledge()
        try:
            self.knowledge.load_from_file()
        except json.JSONDecodeError as e:
            print(f"Błąd wczytywania pliku wiedzy (JSONDecodeError): {e}. Rozpoczynam bez danych historycznych.")
            self.knowledge = AIKnowledge()

        self.agent = None
        self.world_map = None
        self.running = True
        self.paused = False

        self.log = []
        self.max_log = 8

        self.font_small = pygame.font.Font(None, 45)
        self.font_medium = pygame.font.Font(None, 55)
        self.font_large = pygame.font.Font(None, 80)
        self.font_huge = pygame.font.Font(None, 95)

        self.simulation_active = False
        self.action_cooldown = 0
        self.action_delay = 1.0

        self.camera_x = 0
        self.camera_y = 0
        self.ui_scroll_y = 0

    def emoji(self, resource_name):
        emojis = {
            "wood": "🪵", "stone": "🪨", "food": "🍎",
            "water": "💧", "fiber": "🧵", "metal": "⚙️"
        }
        return emojis.get(resource_name, "❓")

    def load_consciousness(self):
        self.add_log(f"🧠 To moja próba #{self.knowledge.attempts + 1}")
        self.add_log(f"📈 Rekord do pobicia: {self.knowledge.best_survival_days} dni")
        if self.knowledge.death_analysis:
            last_death = self.knowledge.death_analysis[-1]
            self.add_log(f"💀 Pamiętam... ostatnim razem zginąłem w dniu {last_death['day']}")
            self.add_log(f"📍 Przyczyna: {last_death['cause']}")
            if last_death['recommendations']:
                self.add_log("💡 Tym razem zrobię to lepiej:")
                for rec in last_death['recommendations']:
                    self.add_log(f"   • {rec}")
        if self.knowledge.risk_tolerance > 0.7:
            self.add_log("⚠️ Poprzednio byłem zbyt ostrożny. Czas na działanie!")
        elif self.knowledge.risk_tolerance < 0.3:
            self.add_log("⚠️ Poprzednio byłem zbyt lekkomyślny. Teraz będę ostrożniejszy.")


    def start_new_attempt(self):
        self.world_map = WorldMap()
        self.agent = Agent(self.knowledge, self.world_map, self.add_log)
        self.log = []
        self.load_consciousness()
        self.simulation_active = True
        self.action_cooldown = 0

    def add_log(self, message):
        self.log.append(message)
        if len(self.log) > self.max_log:
            self.log.pop(0)

    def simulate_tick(self, delta_time):
        if not self.agent or not self.agent.alive:
            return

        self.agent.update(delta_time, self.world_map)

        self.action_cooldown -= delta_time
        if self.action_cooldown <= 0 and self.agent.stamina > 5 and self.agent.alive:
            action = self.agent.ai_decide_action(self.world_map)
            success, result, new_delay = self.agent.execute_action(action, self.world_map)

            if success and "Powrót" not in result and "Szukanie" not in result and "Eksploracja" not in result:
                self.add_log(f"[D{self.agent.current_day+1}] {result}")

            # zabezpieczenie: jeśli new_delay None lub <=0 ustaw minimalne opóźnienie
            if new_delay is None or new_delay <= 0:
                new_delay = 0.1
            self.action_cooldown = new_delay

        if not self.agent.alive:
            self.end_attempt()
        elif self.agent.current_day >= 180:
            self.add_log("PRZEŻYTO 180 DNI!")
            self.simulation_active = False
            self.knowledge.save_to_file()

    def end_attempt(self):
        if self.agent:
            self.knowledge.record_death(self.agent.current_day, self.agent.death_cause)
            self.knowledge.analyze_death(self.agent)
            self.knowledge.save_to_file()
            self.add_log(f"💀 Przyczyna: {self.agent.death_cause}")
            self.add_log(f"Przeżyto: {self.agent.current_day}/180 dni")
        self.simulation_active = False

    def draw(self):
        screen.fill(BLACK)
        if not self.agent:
            self.draw_menu()
        else:
            self.draw_game()
        pygame.display.flip()

    def draw_menu(self):
        y = 150
        title = self.font_huge.render("AI SURVIVAL", True, YELLOW)
        screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, y))
        y += 200
        subtitle = self.font_medium.render("180 Dni Przetrwania", True, WHITE)
        screen.blit(subtitle, (SCREEN_WIDTH//2 - subtitle.get_width()//2, y))
        y += 100
        stats = [
            f"Liczba prób: {self.knowledge.attempts}",
            f"Najlepszy wynik: {self.knowledge.best_survival_days} dni",
            ""
        ]
        for stat in stats:
            text = self.font_medium.render(stat, True, WHITE)
            screen.blit(text, (SCREEN_WIDTH//2 - text.get_width()//2, y))
            y += 80
        if self.knowledge.death_causes:
            text = self.font_medium.render("Top przyczyny śmierci:", True, YELLOW)
            screen.blit(text, (SCREEN_WIDTH//2 - text.get_width()//2, y))
            y += 80
            sorted_causes = sorted(self.knowledge.death_causes.items(), key=lambda x: x[1], reverse=True)[:4]
            for cause, count in sorted_causes:
                text = self.font_small.render(f"{cause}: {count}x", True, RED)
                screen.blit(text, (SCREEN_WIDTH//2 - text.get_width()//2, y))
                y += 60
        button_y = SCREEN_HEIGHT - 300
        button = pygame.Rect(100, button_y, SCREEN_WIDTH - 200, 180)
        pygame.draw.rect(screen, GREEN, button)
        pygame.draw.rect(screen, WHITE, button, 5)
        text = self.font_large.render("ROZPOCZNIJ GRĘ", True, WHITE)
        screen.blit(text, (SCREEN_WIDTH//2 - text.get_width()//2, button_y + 50))

    def draw_game(self):
        map_height = 800
        ui_start_y = map_height + 10 + self.ui_scroll_y
        self.draw_map(0, 0, SCREEN_WIDTH, map_height)
        y = ui_start_y
        day_text = f"DZIEŃ {self.agent.current_day}/180"
        time_icon = "🌙" if self.agent.is_night else "☀️"
        header = self.font_medium.render(f"{day_text} {time_icon}", True, YELLOW)
        screen.blit(header, (15, y))
        time_left = SECONDS_PER_DAY * (1.0 - self.agent.day_progress)
        time_text = f"Pozostało: {time_left:.1f}s"
        time_render = self.font_medium.render(time_text, True, WHITE)
        screen.blit(time_render, (SCREEN_WIDTH // 2 - time_render.get_width() // 2, y))
        lvl_text = f"LVL {self.agent.level}"
        text = self.font_medium.render(lvl_text, True, WHITE)
        screen.blit(text, (SCREEN_WIDTH - text.get_width() - 15, y))
        y += 65
        bar_w = SCREEN_WIDTH - 30
        pygame.draw.rect(screen, GRAY, (15, y, bar_w, 25))
        progress_w = int(self.agent.day_progress * bar_w)
        color = DARK_BLUE if self.agent.is_night else YELLOW
        pygame.draw.rect(screen, color, (15, y, progress_w, 25))
        pygame.draw.rect(screen, WHITE, (15, y, bar_w, 25), 2)
        y += 40
        attr_text = f"STR:{self.agent.strength} DEX:{self.agent.dexterity} PER:{self.agent.perception} INT:{self.agent.intelligence} VIT:{self.agent.vitality}"
        text = self.font_small.render(attr_text, True, WHITE)
        screen.blit(text, (15, y))
        y += 50

        # EXP bar - added per request
        bar_h = 35
        bar_w = SCREEN_WIDTH - 30
        # HP
        self.draw_bar_compact(15, y, bar_w, bar_h, self.agent.hp, self.agent.max_hp, RED, "HP")
        y += bar_h + 10
        # Hunger
        self.draw_bar_compact(15, y, bar_w, bar_h, self.agent.hunger, 100, ORANGE, "Głód")
        y += bar_h + 10
        # Thirst
        self.draw_bar_compact(15, y, bar_w, bar_h, self.agent.thirst, 100, BLUE, "Woda")
        y += bar_h + 10
        # Warmth
        self.draw_bar_compact(15, y, bar_w, bar_h, self.agent.warmth, 100, YELLOW, "Ciepło")
        y += bar_h + 10
        # Stamina
        self.draw_bar_compact(15, y, bar_w, bar_h, self.agent.stamina, self.agent.max_stamina, GREEN, "Energia")
        y += bar_h + 20
        # EXP bar (new)
        self.draw_bar_compact(15, y, bar_w, bar_h, self.agent.exp, self.agent.exp_to_next, PURPLE, "EXP")
        y += bar_h + 20

        # Camp Storage
        storage_text = "Obóz: " + " ".join([f"{self.emoji(res)}:{amt}" for res, amt in self.agent.camp["storage"].items()])
        text = self.font_small.render(storage_text, True, WHITE)
        screen.blit(text, (15, y))
        y += 50

        inv_text = f"Inwentarz ({self.agent.get_total_inventory_size()}/{self.agent.current_carry_capacity}):"
        text = self.font_small.render(inv_text, True, YELLOW)
        screen.blit(text, (15, y))
        y += 45
        inv_line = f"🪵:{self.agent.inventory['wood']} 🪨:{self.agent.inventory['stone']} 🍎:{self.agent.inventory['food']} 💧:{self.agent.inventory['water']} 🧵:{self.agent.inventory['fiber']} ⚙️:{self.agent.inventory['metal']}"
        text = self.font_small.render(inv_line, True, WHITE)
        screen.blit(text, (15, y))
        y += 50
        quota = self.agent.calculate_daily_quota(days_ahead=2)
        quota_text = f"Quota (2 Dni): 🍎 x{quota['food']} | 💧 x{quota['water']}"
        quota_render = self.font_small.render(quota_text, True, LIGHT_GREEN)
        screen.blit(quota_render, (15, y))
        y += 50
        equip_text = "Ekwipunek: "
        equipped_items = []
        for slot, item in self.agent.equipment.items():
            if item:
                dur_text = "" if slot == "backpack" else f"({item.durability})"
                equipped_items.append(f"{item.name}{dur_text}")
        if equipped_items:
            equip_text += ", ".join(equipped_items)
        else:
            equip_text += "Brak"
        text = self.font_small.render(equip_text[:50], True, WHITE)
        screen.blit(text, (15, y))
        y += 50
        camp_text = f"Obóz: Poziom {self.agent.camp['level']} | Struktury: {len(self.agent.camp['structures'])}"
        text = self.font_small.render(camp_text, True, ORANGE)
        screen.blit(text, (15, y))
        y += 50

        # PRZEMYŚLENIA
        text = self.font_small.render("--- PRZEMYŚLENIA ---", True, PURPLE)
        screen.blit(text, (15, y))
        y += 45
        if self.agent.thoughts:
            last_thought = self.agent.thoughts[-1]
            text = self.font_small.render(f"💭 {last_thought}"[:55], True, LIGHT_GREEN)
            screen.blit(text, (15, y))
            y += 40

        # LOG
        text = self.font_small.render("--- LOG ---", True, YELLOW)
        screen.blit(text, (15, y))
        y += 45
        for entry in self.log[-self.max_log:]:
            text = self.font_small.render(entry[:55], True, WHITE)
            screen.blit(text, (15, y))
            y += 40

        # NAGRODY
        text = self.font_small.render("--- NAGRODY ---", True, YELLOW)
        screen.blit(text, (15, y))
        y += 45
        summary = self.agent.q_learning.get_daily_summary(self.agent.current_day)
        text = self.font_small.render(summary, True, WHITE)
        screen.blit(text, (15, y))
        y += 40
        total_q = f"Suma Q: {self.agent.q_learning.total_reward}"
        text = self.font_small.render(total_q, True, ORANGE)
        screen.blit(text, (15, y))
        y += 40

        # UMIEJĘTNOŚCI
        text = self.font_small.render("--- UMIEJĘTNOŚCI ---", True, BLUE)
        screen.blit(text, (15, y))
        y += 45
        if self.agent.learned_skills:
            skills_text = ", ".join([f"{skill.name} Lvl {skill.level}" for skill in self.agent.learned_skills.values()])
            text = self.font_small.render(skills_text, True, LIGHT_GREEN)
            screen.blit(text, (15, y))
        else:
            text = self.font_small.render("Brak umiejętności", True, GRAY)
            screen.blit(text, (15, y))
        y += 40

        # KARY OSTROŻNOŚCI
        if self.agent.caution_penalty_score > 0:
            text = self.font_small.render(f"⚠️ Kary ostrożności: {self.agent.caution_penalty_score}", True, RED)
            screen.blit(text, (15, y))
            y += 40

        button_y = SCREEN_HEIGHT - 150
        button_w = (SCREEN_WIDTH - 40) // 2
        pause_btn = pygame.Rect(15, button_y, button_w, 120)
        pause_color = ORANGE if self.paused else RED
        pygame.draw.rect(screen, pause_color, pause_btn)
        pygame.draw.rect(screen, WHITE, pause_btn, 4)
        text = self.font_medium.render("PAUZA" if not self.paused else "WZNÓW", True, WHITE)
        screen.blit(text, (pause_btn.centerx - text.get_width()//2, button_y + 35))
        restart_btn = pygame.Rect(25 + button_w, button_y, button_w, 120)
        pygame.draw.rect(screen, GREEN if not self.simulation_active else GRAY, restart_btn)
        pygame.draw.rect(screen, WHITE, restart_btn, 4)
        text = self.font_medium.render("NOWA", True, WHITE)
        screen.blit(text, (restart_btn.centerx - text.get_width()//2, button_y + 35))

    def draw_map(self, x, y, width, height):
        map_surface = pygame.Surface((width, height))
        map_surface.fill(BLACK)
        if self.agent:
            tiles_per_screen_x = width // TILE_SIZE
            tiles_per_screen_y = height // TILE_SIZE
            self.camera_x = self.agent.x - tiles_per_screen_x // 2
            self.camera_y = self.agent.y - tiles_per_screen_y // 2
            self.camera_x = max(0, min(self.camera_x, self.world_map.width - tiles_per_screen_x))
            self.camera_y = max(0, min(self.camera_y, self.world_map.height - tiles_per_screen_y))
        camp_start_x = self.world_map.camp_x - CAMP_SIZE // 2
        camp_start_y = self.world_map.camp_y - CAMP_SIZE // 2
        for row in range(self.world_map.height):
            for col in range(self.world_map.width):
                screen_x = (col - self.camera_x) * TILE_SIZE
                screen_y = (row - self.camera_y) * TILE_SIZE
                if screen_x < -TILE_SIZE or screen_x > width or screen_y < -TILE_SIZE or screen_y > height:
                    continue
                tile_type = self.world_map.tiles[row][col]
                if tile_type == 0:
                    color = (34, 139, 34)
                elif tile_type == 1:
                    color = DARK_GREEN
                elif tile_type == 2:
                    color = GRAY
                elif tile_type == 3:
                    color = LIGHT_GREEN
                elif tile_type == 4:
                    color = BLUE
                elif tile_type == 5:
                    color = (210, 180, 140)
                elif tile_type == 6:
                    color = DARK_GRAY
                elif tile_type == 7:
                    color = (101, 67, 33)
                else:
                    color = BLACK
                pygame.draw.rect(screen, color, (screen_x, screen_y, TILE_SIZE, TILE_SIZE))
                # obrys bez alfa
                pygame.draw.rect(screen, (0, 0, 0), (screen_x, screen_y, TILE_SIZE, TILE_SIZE), 1)
        camp_screen_x = (camp_start_x - self.camera_x) * TILE_SIZE
        camp_screen_y = (camp_start_y - self.camera_y) * TILE_SIZE
        camp_rect = pygame.Rect(camp_screen_x, camp_screen_y, CAMP_SIZE * TILE_SIZE, CAMP_SIZE * TILE_SIZE)
        pygame.draw.rect(screen, YELLOW, camp_rect, 3)
        if self.agent:
            for struct in self.agent.camp["structures"]:
                struct_world_x = camp_start_x + struct.x
                struct_world_y = camp_start_y + struct.y
                struct_screen_x = (struct_world_x - self.camera_x) * TILE_SIZE
                struct_screen_y = (struct_world_y - self.camera_y) * TILE_SIZE
                if -TILE_SIZE <= struct_screen_x < width and -TILE_SIZE <= struct_screen_y < height:
                    center_x = int(struct_screen_x + TILE_SIZE // 2)
                    center_y = int(struct_screen_y + TILE_SIZE // 2)
                    pygame.draw.circle(screen, struct.color, (center_x, center_y), TILE_SIZE // 3)
                    pygame.draw.circle(screen, WHITE, (center_x, center_y), TILE_SIZE // 3, 2)
                    icon = ""
                    if struct.type == "shelter":
                        icon = "🏠"
                    elif struct.type == "fire":
                        icon = "🔥"
                    elif struct.type == "workbench":
                        icon = "🔨"
                    elif struct.type == "storage":
                        icon = "📦"
                    elif struct.type == "wall":
                        icon = "🧱"
                    if icon:
                        icon_text = self.font_small.render(icon, True, WHITE)
                        screen.blit(icon_text, (center_x - icon_text.get_width()//2, center_y - icon_text.get_height()//2))
        for node in self.world_map.resource_nodes:
            screen_x = (node.x - self.camera_x) * TILE_SIZE
            screen_y = (node.y - self.camera_y) * TILE_SIZE
            if screen_x < -TILE_SIZE or screen_x > width or screen_y < -TILE_SIZE or screen_y > height:
                continue
            if not node.depleted:
                icon = ""
                if node.type == "wood":
                    icon = "🌲"
                elif node.type == "stone":
                    icon = "🪨"
                elif node.type == "food":
                    icon = "🍎"
                elif node.type == "water":
                    icon = "💧"
                elif node.type == "fiber":
                    icon = "🌾"
                elif node.type == "metal":
                    icon = "⚙️"
                text = self.font_small.render(icon, True, WHITE)
                screen.blit(text, (screen_x + TILE_SIZE//2 - text.get_width()//2,
                                  screen_y + TILE_SIZE//2 - text.get_height()//2))
        if self.agent:
            agent_x = (self.agent.x - self.camera_x) * TILE_SIZE
            agent_y = (self.agent.y - self.camera_y) * TILE_SIZE
            if 0 <= agent_x < width and 0 <= agent_y < height:
                pygame.draw.circle(screen, YELLOW,
                                 (int(agent_x + TILE_SIZE//2), int(agent_y + TILE_SIZE//2)),
                                 TILE_SIZE//2 + 2, 2)
                pygame.draw.circle(screen, WHITE,
                                 (int(agent_x + TILE_SIZE//2), int(agent_y + TILE_SIZE//2)),
                                 TILE_SIZE//3)
                lvl_text = self.font_small.render(f"L{self.agent.level}", True, YELLOW)
                screen.blit(lvl_text, (agent_x + TILE_SIZE//2 - lvl_text.get_width()//2,
                                      agent_y - 18))
        legend_y = 10
        legend_items = [
            ("🌲", "Drewno"),
            ("🪨", "Kamień"),
            ("🍎", "Jedzenie"),
            ("💧", "Woda"),
            ("🏕️", "Obóz")
        ]
        legend_x = 10
        for icon, name in legend_items:
            text = self.font_small.render(f"{icon} {name}", True, WHITE)
            bg_rect = pygame.Rect(legend_x - 3, legend_y - 3, text.get_width() + 6, text.get_height() + 6)
            pygame.draw.rect(screen, BLACK, bg_rect)
            pygame.draw.rect(screen, WHITE, bg_rect, 1)
            screen.blit(text, (legend_x, legend_y))
            legend_x += text.get_width() + 15

    def draw_bar_compact(self, x, y, width, height, value, max_value, color, label):
        pygame.draw.rect(screen, (30, 30, 30), (x, y, width, height))
        fill_width = int((max(value, 0) / max_value) * width) if max_value > 0 else 0
        pygame.draw.rect(screen, color, (x, y, fill_width, height))
        pygame.draw.rect(screen, WHITE, (x, y, width, height), 2)
        text = self.font_small.render(f"{label}: {int(max(value, 0))}/{int(max_value)}", True, WHITE)
        screen.blit(text, (x + 5, y + 2))

    def run(self):
        while self.running:
            delta_time = clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                if event.type == pygame.MOUSEWHEEL:
                    self.ui_scroll_y += event.y * 30
                    self.ui_scroll_y = min(0, self.ui_scroll_y)
                    self.ui_scroll_y = max(-(SCREEN_HEIGHT - 800), self.ui_scroll_y)
                if event.type == pygame.MOUSEBUTTONDOWN:
                    mouse_pos = pygame.mouse.get_pos()
                    if not self.agent:
                        if mouse_pos[1] > SCREEN_HEIGHT - 300:
                            self.start_new_attempt()
                    else:
                        button_y = SCREEN_HEIGHT - 150
                        button_w = (SCREEN_WIDTH - 40) // 2
                        if 15 <= mouse_pos[0] <= 15 + button_w and button_y <= mouse_pos[1] <= button_y + 120:
                            self.paused = not self.paused
                        if 25 + button_w <= mouse_pos[0] <= 25 + button_w * 2 and button_y <= mouse_pos[1] <= button_y + 120:
                            if not self.simulation_active:
                                self.start_new_attempt()
            if self.simulation_active and not self.paused:
                self.simulate_tick(delta_time)
            self.draw()
        self.knowledge.save_to_file()
        pygame.quit()

if __name__ == "__main__":
    game = Game()
    game.run()
