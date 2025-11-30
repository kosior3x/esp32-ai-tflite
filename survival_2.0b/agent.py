import random
import math
from datetime import datetime
from ai_system import QLearningSystem
from world import CampStructure, CraftingSystem

NIGHT_START = 0.6

class DevelopmentPath:
    def __init__(self, name, description, bonuses):
        self.name = name
        self.description = description
        self.bonuses = bonuses

    def get_bonus(self, bonus_name):
        return self.bonuses.get(bonus_name, 0)


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


class Agent:
    def __init__(self, knowledge, world_map, add_log_func, pathfinder):
        self.pathfinder = pathfinder
        self.path = []
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
        self.action_frequency = {}

        self.development_paths = {
            "Combat": DevelopmentPath("Combat", "Focus on fighting and defense.", {"damage_bonus": 0.15, "defense_bonus": 0.1}),
            "Survival": DevelopmentPath("Survival", "Focus on resource gathering and crafting.", {"gathering_bonus": 0.2, "crafting_speed": 0.15}),
            "Nomad": DevelopmentPath("Nomad", "Focus on exploration and movement.", {"move_speed_bonus": 0.1, "stamina_reduction": 0.15})
        }
        self.chosen_path = None
        self.daily_profile = None

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
        if self.chosen_path:
            self.move_speed *= (1.0 - self.chosen_path.get_bonus("move_speed_bonus"))
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
        self.actions = ["eat", "drink", "rest", "deposit", "craft_stone_axe", "build_fire", "explore",
                        "find_resource_wood", "find_resource_stone", "find_resource_food",
                        "find_resource_water", "find_resource_fiber"]
        self.reward_values = {
            "gather_food": 5, "gather_water": 5, "gather_wood": 3, "gather_stone": 3, "gather_fiber": 3, "gather_metal": 4,
            "build_shelter": 15, "build_fire": 18, "build_workbench": 20, "build_storage": 22, "build_wall": 25,
            "craft_stone_axe": 12, "craft_iron_axe": 18,
            "survive_day": 10, "survive_night_in_camp": 25, "survive_week": 100,
            "explore_new_tile": 8, "discover_resource_node": 15,
            "deposit_resources": 5, "fill_storage_quota": 20,
            "night_outside_camp": -40, "death_hunger": -150, "death_thirst": -150, "death_cold": -120, "death_hp": -100,
            "inventory_full_waste": -8, "too_cautious": -15
        }
        self.q_learning = QLearningSystem(self.actions)

    def _update_action_frequency(self):
        # "Forget" old actions by reducing their frequency count
        for action in list(self.action_frequency.keys()):
            self.action_frequency[action] -= 0.2
            if self.action_frequency[action] <= 0:
                del self.action_frequency[action]

    def init_camp_structures(self):
        self.camp["structures"].append(
            CampStructure("Schronienie", "shelter", 2, 2, "BROWN", 100)
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

        # Dynamic EXP cost based on action frequency
        frequency_penalty = self.action_frequency.get(action_type, 0)
        exp_multiplier = max(0.1, 1.0 - (frequency_penalty * 0.1)) # Diminishing returns

        # Apply development path bonus
        if self.chosen_path and "gather" in action_type:
            exp_multiplier += self.chosen_path.get_bonus("gathering_bonus")

        total_exp = int(amount * day_bonus * int_bonus * exp_multiplier)
        self.exp += total_exp
        if self.exp < 0:
            self.exp = 0
        while self.exp >= self.exp_to_next:
            self.level_up()

        # Record this action for frequency tracking
        self.action_frequency[action_type] = self.action_frequency.get(action_type, 0) + 1

        self.knowledge.record_action(self.current_day, action_type, True, {"exp": total_exp})
        return total_exp

    def _select_daily_profile(self):
        # Tactical Profile Selection
        if self.hp < 30 or self.hunger < 20 or self.thirst < 20:
            self.daily_profile = "Emergency Day"
            return

        death_history = [d['cause'] for d in self.knowledge.death_analysis[-3:]]
        if len(death_history) >= 2 and len(set(death_history)) == 1:
            # If last 2 deaths have the same cause, be defensive
            self.daily_profile = "Defensive Day"
            return

        if sum(self.camp["storage"].values()) < 20:
            self.daily_profile = "Aggressive Day"
        elif any(s.durability < s.max_durability * 0.5 for s in self.camp["structures"]):
            self.daily_profile = "Maintenance Day"
        elif not self.in_camp:
            self.daily_profile = "Emergency Day" # Focus on returning to camp
        else:
            self.daily_profile = "Aggressive Day"

    def _choose_development_path(self):
        if self.level >= 5 and not self.chosen_path:
            action_counts = {"Combat": 0, "Survival": 0, "Nomad": 0}
            for action, freq in self.action_frequency.items():
                if "gather" in action or "craft" in action or "build" in action:
                    action_counts["Survival"] += freq
                elif "explore" in action or "move" in action:
                    action_counts["Nomad"] += freq
                else: # Generic combat/other
                    action_counts["Combat"] += freq

            chosen_path_name = max(action_counts, key=action_counts.get)
            self.chosen_path = self.development_paths[chosen_path_name]
            self.add_log(f"Wybrano ścieżkę rozwoju: {self.chosen_path.name}!")

    def level_up(self):
        self.level += 1
        self.exp -= self.exp_to_next
        self.exp_to_next = int(self.exp_to_next * 1.12) + 10
        self.stat_points += 5
        self._choose_development_path()
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
        # Adaptive progression based on death history
        death_history = [d['cause'] for d in self.knowledge.death_analysis[-3:]] # Last 3 deaths

        while self.stat_points > 0:
            priorities = {
                "strength": 1, "dexterity": 1, "perception": 1,
                "intelligence": 1, "vitality": 1
            }

            for cause in death_history:
                if cause in ["hunger", "thirst"]:
                    priorities["perception"] += 3
                    priorities["vitality"] += 2
                elif cause == "hp_depletion":
                    priorities["strength"] += 2
                    priorities["dexterity"] += 2
                    priorities["vitality"] += 3
                elif cause == "cold":
                    priorities["vitality"] += 3
                    priorities["intelligence"] += 2

            # Weighted random choice
            choices = []
            for stat, weight in priorities.items():
                choices.extend([stat] * weight)

            if not choices:
                choices = ["strength", "dexterity", "perception", "intelligence", "vitality"]

            stat = random.choice(choices)
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
        if self.stamina < 5:
            self.path = []
            return False

        start_node = (self.x, self.y)
        end_node = (target_x, target_y)

        if start_node == end_node:
            return False

        self.path = self.pathfinder.find_path(start_node, end_node)
        if not self.path:
            # No path found, maybe try a random move to get unstuck
            self.move_target = (self.x + random.randint(-1, 1), self.y + random.randint(-1, 1))
            return True

        return True

    def _do_move_step_towards_target(self, world_map):
        """Follows the A* path or moves towards move_target if no path."""
        if not self.path and not self.move_target:
            return False

        if self.path:
            if self.stamina < 5:
                self.path = []
                return False

            next_pos = self.path.pop(0)
            self.x, self.y = next_pos
        elif self.move_target:
            # Fallback for when no path is found
            target_x, target_y = self.move_target
            dx = target_x - self.x
            dy = target_y - self.y

            if dx == 0 and dy == 0:
                self.move_target = None
                return True

            step_x = 1 if dx > 0 else -1 if dx < 0 else 0
            step_y = 1 if dy > 0 else -1 if dy < 0 else 0

            self.x += step_x
            self.y += step_y

            if self.x == target_x and self.y == target_y:
                self.move_target = None


        self.position_history.append((self.x, self.y))
        if len(self.position_history) > 10:
            self.position_history.pop(0)
        self.update_discovered_tiles(self.x, self.y)
        self.move_cooldown = self.move_speed
        stamina_cost = 2
        if self.chosen_path:
            stamina_cost *= (1.0 - self.chosen_path.get_bonus("stamina_reduction"))
        self.stamina = max(0, self.stamina - stamina_cost)
        self.idle_timer = 0
        self.in_camp = world_map.is_in_camp(self.x, self.y)

        return True

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

    def simulate_action(self, action):
        """Predicts the agent's state after a hypothetical action."""
        sim_stats = {
            "hp": self.hp, "hunger": self.hunger, "thirst": self.thirst,
            "stamina": self.stamina, "warmth": self.warmth
        }

        # Simplified simulation of action effects
        if action == "eat":
            sim_stats["hunger"] = min(self.hunger + 35, 100)
        elif action == "drink":
            sim_stats["thirst"] = min(self.thirst + 45, 100)
        elif action == "rest" and self.in_camp:
            sim_stats["hp"] = min(self.hp + self.vitality * 5, self.max_hp)
            sim_stats["stamina"] = min(self.stamina + self.vitality * 10, self.max_stamina)
        elif isinstance(action, tuple) and action[0] == "find_resource":
            # Assume it takes time and effort
            sim_stats["stamina"] -= 15
        elif action == "explore":
            sim_stats["stamina"] -= 20

        # Generic stat drain for time passing
        sim_stats["hunger"] -= 2
        sim_stats["thirst"] -= 3

        return sim_stats


    def ai_decide_action(self, world_map):
        if self.pending_skill_choice:
            self.auto_choose_skill()
            # Return a default safe action while choosing skill
            return "rest"

        # Loop detection
        if len(self.action_history) > 10:
            last_10 = self.action_history[-10:]
            if len(set(last_10)) <= 2: # Repetitive loop
                state = self.q_learning.get_state(self, world_map)
                for action in set(last_10):
                    self.q_learning.update_q_table(state, action, -20, state) # Penalize
                return "explore" # Break the loop

        # Emergency overrides for Q-learning decisions
        if self.hunger < 15 and self.inventory["food"] > 0:
            return "eat"
        if self.thirst < 15 and self.inventory["water"] > 0:
            return "drink"
        if self.hp < self.max_hp * 0.2 and self.in_camp:
            return "rest"
        if self.day_progress > NIGHT_START and not self.in_camp:
             return ("move_to_camp", world_map.camp_x, world_map.camp_y)

        # Prioritize actions based on daily profile
        if self.daily_profile == "Emergency Day":
            if self.in_camp:
                return "rest"
            else:
                return ("move_to_camp", world_map.camp_x, world_map.camp_y)
        elif self.daily_profile == "Defensive Day":
            if self.in_camp:
                return "rest" # Prioritize regeneration
            else:
                return ("move_to_camp", world_map.camp_x, world_map.camp_y)
        elif self.daily_profile == "Maintenance Day":
            if self.in_camp:
                if self.equipment["tool"] and self.equipment["tool"].durability < 30:
                    return "repair_tool"

                for structure in self.camp["structures"]:
                    if structure.durability < structure.max_durability * 0.7:
                        return "repair_structure"

                if self.inventory["wood"] > 10 and self.inventory["stone"] > 5:
                    return "build_fire"
            return ("find_resource", "wood")

        state = self.q_learning.get_state(self, world_map)

        # Get top 3 actions from Q-table
        q_values = self.q_learning.q_table.get(state, {})
        if q_values:
            sorted_actions = sorted(q_values.keys(), key=lambda a: q_values[a], reverse=True)[:3]

            best_action = None
            best_score = -float('inf')

            for action in sorted_actions:
                sim_stats = self.simulate_action(action)
                # Simple scoring: prioritize survival stats
                score = sim_stats["hunger"] + sim_stats["thirst"] + sim_stats["hp"] - (100 - sim_stats["stamina"])
                if score > best_score:
                    best_score = score
                    best_action = action

            action = best_action if best_action else self.q_learning.choose_action(state, self)
        else:
            action = self.q_learning.choose_action(state, self)


        # Prevent invalid actions
        if action == "eat" and self.inventory["food"] == 0:
            action = "find_resource_food"
        if action == "drink" and self.inventory["water"] == 0:
            action = "find_resource_water"

        if action.startswith("find_resource"):
            resource_type = action.split("_")[-1]
            return ("find_resource", resource_type)

        return action

    def execute_action(self, action, world_map):
        if action == "repair_structure":
            damaged_structure = None
            for s in self.camp["structures"]:
                if s.durability < s.max_durability:
                    damaged_structure = s
                    break

            if damaged_structure and self.in_camp:
                repair_cost = {"wood": 2, "stone": 1} # Example cost
                can_repair = all(self.inventory.get(res, 0) >= cost for res, cost in repair_cost.items())
                if can_repair:
                    for res, cost in repair_cost.items():
                        self.inventory[res] -= cost
                    damaged_structure.repair(50) # Repair by 50 points
                    return True, f"Naprawiono {damaged_structure.name}", 2.0
                else:
                    return False, "Brak surowców do naprawy struktury", 1.0
            return False, "Brak uszkodzonych struktur", 1.0

        if action == "repair_tool":
            tool = self.equipment.get("tool")
            if tool and self.in_camp:
                repair_cost = {"wood": 1, "stone": 1}
                can_repair = all(self.inventory.get(res, 0) >= cost for res, cost in repair_cost.items())
                if can_repair:
                    for res, cost in repair_cost.items():
                        self.inventory[res] -= cost
                    tool.durability = tool.max_durability
                    return True, f"Naprawiono {tool.name}", 1.5
                else:
                    return False, "Brak surowców do naprawy", 1.0
            return False, "Nie można naprawić", 1.0

        self.action_history.append(action)
        if len(self.action_history) > 20:
            self.action_history.pop(0)

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
                        action_duration = max(base_time * correction, 0.3)

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
            action_duration = max(0.5 - (self.dexterity * 0.01), 0.3)
            if self.inventory["food"] > 0:
                self.inventory["food"] -= 1
                self.hunger = min(self.hunger + 35, 100)
                return True, "Zjedzono jedzenie", action_duration
            return False, "Brak jedzenia", action_duration

        elif action == "drink":
            action_duration = max(0.5 - (self.dexterity * 0.01), 0.3)
            if self.inventory["water"] > 0:
                self.inventory["water"] -= 1
                self.thirst = min(self.thirst + 45, 100)
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
                return True, f"Odpoczynek (+{vitality_regen} HP/Stamina)", action_duration
            return False, "Nie w obozie", action_duration

        elif action == "deposit":
            action_duration = max(0.5 - (self.strength * 0.01), 0.3)
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
                return True, f"Zdeponowano {deposited} przedmiotów", action_duration
            return False, "Nie w obozie", action_duration

        elif action.startswith("craft_"):
            recipe_name = action.split("craft_")[1]
            if recipe_name == "stone_axe":
                recipe = self.crafting.recipes["stone_axe"]
                action_duration = max(2.0 - (self.intelligence * 0.1), 0.3)
                can_craft, reason = recipe.can_craft(self, self.inventory)
                if can_craft:
                    for res, amt in recipe.requirements.items():
                        self.inventory[res] -= amt
                    self.equipment["tool"] = recipe.result
                    exp = self.gain_exp(15, "craft_stone_axe")
                    return True, f"Skraftowano Topór (+{exp} EXP)", action_duration
                return False, reason, action_duration
            return False, "Nieznany przepis", action_duration

        elif action.startswith("build_"):
            structure_type = action.split("build_")[1]
            if structure_type in self.crafting.structure_recipes:
                action_duration = max(3.0 - (self.strength * 0.15), 0.3)
                if not self.in_camp:
                    return False, "Nie w obozie", action_duration
                for cy in range(5):
                    for cx in range(5):
                        occupied = False
                        for struct in self.camp["structures"]:
                            if struct.x == cx and struct.y == cy:
                                occupied = True
                                break
                        if not occupied:
                            success, msg = self.build_structure(structure_type, cx, cy)
                            if success:
                                exp = self.gain_exp(25, f"build_{structure_type}")
                                return True, f"{msg} (+{exp} EXP)", action_duration
                            return False, msg, action_duration
                return False, "Brak miejsca w obozie", action_duration

        elif action == "explore":
            dx = random.randint(-1, 1)
            dy = random.randint(-1, 1)
            new_x = max(0, min(self.x + dx, 20 - 1))
            new_y = max(0, min(self.y + dy, 20 - 1))
            is_new_tile = (new_x, new_y) not in self.discovered_tiles
            started = self.start_move(new_x, new_y, world_map)
            if not started:
                return False, "Nie można eksplorować - mało staminy", 0.1
            return True, "Eksploracja...", self.move_speed

        return False, "Nieznana akcja", 1.0

    def update(self, delta_time, world_map):
        # reduce cooldown
        self.move_cooldown = max(0, self.move_cooldown - delta_time)

        # AUTO-ODPOCZYNEK PRZY NISKIEJ STAMINIE
        # Jeśli stamina spadła do <=2 -> natychmiast przerwij ruch, aby umożliwić regenerację.
        if self.stamina <= 2 and self.move_target is not None:
            self.move_target = None
            self.add_log("Krytyczna stamina — przerwanie ruchu. Odpoczynek...")

        # jeśli ustawiony cel i cooldown==0 -> wykonaj krok
        if self.move_target and self.move_cooldown <= 0:
            self._do_move_step_towards_target(world_map)

        day_fraction = delta_time / 90
        hunger_drain = 20.0
        thirst_drain = 25.0

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
        if self.idle_timer >= 1.0:
            if not self.is_night:
                base_stamina_regen = 2.0
                stamina_regen_rate = (base_stamina_regen + (self.vitality * 0.5)) * delta_time
                camp_bonus = 1.5 if self.in_camp else 1.0
                self.stamina = min(self.stamina + stamina_regen_rate * camp_bonus, self.max_stamina)
                self.hp = min(self.hp + (self.vitality * 0.05 * delta_time), self.max_hp)

        # clamp stamina to valid range
        self.stamina = max(0, min(self.stamina, self.max_stamina))

        self.day_progress += delta_time / 90
        self.is_night = self.day_progress >= 0.6

        if self.is_night and not self.in_camp:
            self.hp -= 0.02 * delta_time
            self.warmth -= 0.1 * delta_time

        if self.day_progress >= 1.0:
            self.end_day(world_map)

        self.check_dangerous_situation()
        self.check_death()

    def end_day(self, world_map):
        self._select_daily_profile()
        self.current_day += 1
        self.day_progress = 0.0
        self.is_night = False
        self.reflect_on_day()
        self.days_without_exploration += 1
        if self.in_camp:
            self.consecutive_camp_days += 1
        else:
            self.consecutive_camp_days = 0

        self._update_action_frequency()
        self.check_caution_penalties()

        # Nightly resource consumption
        if self.in_camp:
            food_consumed = 1
            water_consumed = 1
            wood_consumed = sum(s.maintenance_cost for s in self.camp["structures"])

            self.camp["storage"]["food"] = self.camp["storage"].get("food", 0) - food_consumed
            self.camp["storage"]["water"] = self.camp["storage"].get("water", 0) - water_consumed
            self.camp["storage"]["wood"] = self.camp["storage"].get("wood", 0) - wood_consumed

            if self.camp["storage"]["food"] < 0:
                self.hunger -= abs(self.camp["storage"]["food"] * 10)
                self.camp["storage"]["food"] = 0
            if self.camp["storage"]["water"] < 0:
                self.thirst -= abs(self.camp["storage"]["water"] * 10)
                self.camp["storage"]["water"] = 0
            if self.camp["storage"]["wood"] < 0:
                self.warmth -= abs(self.camp["storage"]["wood"] * 5)
                self.camp["storage"]["wood"] = 0

        if not self.in_camp:
            self.gain_exp(-150, "night_out_penalty")
            self.add_log("Otrzymano karę EXP za noc poza obozem.")
        if self.in_camp:
            camp_exp = 60 + (self.camp["level"] * 10)
            camp_exp = int(camp_exp * (1 + self.current_day * 0.08))
            self.gain_exp(camp_exp, "survive_day")
            self.add_log(f"Zakończono Dzień {self.current_day}. (+{camp_exp} EXP)")
        world_map.update_day()
        self.check_death()

    def check_death(self):
        if self.hunger <= 0:
            self.alive = False
            self.death_cause = "hunger"
        elif self.thirst <= 0:
            self.alive = False
            self.death_cause = "thirst"
        elif self.warmth <= 0:
            self.alive = False
            self.death_cause = "cold"
        elif self.hp <= 0:
            self.alive = False
            self.death_cause = "hp_depletion"
