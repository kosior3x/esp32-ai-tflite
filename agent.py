# agent.py
import random
import json
import os
import math
from datetime import datetime
from crafting import CraftingSystem, Item
from world import CampStructure
from settings import (
    NIGHT_START,
    NIGHT_HP_DRAIN,
    MIN_ACTION_DELAY,
    IDLE_TIME_TO_REGEN,
    BASE_HUNGER_DRAIN_PER_DAY,
    BASE_THIRST_DRAIN_PER_DAY,
    SECONDS_PER_DAY,
    CAMP_SIZE,
    BROWN
)

class AIKnowledge:
    def __init__(self):
        self.attempts = 0
        self.best_survival_days = 0
        self.death_causes = {}
        self.successful_actions = {}
        self.learned_recipes = []
        self.death_days = []

    def record_death(self, day, cause):
        self.attempts += 1
        self.death_days.append(day)
        if day > self.best_survival_days:
            self.best_survival_days = day
        if cause not in self.death_causes:
            self.death_causes[cause] = 0
        self.death_causes[cause] += 1

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
            "death_days": self.death_days
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
            "metal": 0,
            "copper": 0
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
        while self.exp >= self.exp_to_next:
            self.level_up()
        self.knowledge.record_action(self.current_day, action_type, True, {"exp": total_exp})
        return total_exp

    def level_up(self):
        self.level += 1
        self.exp -= self.exp_to_next
        self.exp_to_next = int(self.exp_to_next * 1.15) + 15
        self.stat_points += 5
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

        # Check for walls
        for structure in self.camp["structures"]:
            if structure.type == "wall" and structure.x == new_x and structure.y == new_y:
                return False # Wall blocks movement

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
        actions = []

        # --- Potrzeby Podstawowe ---
        if self.inventory["food"] > 0:
            actions.append({"action": "eat", "priority": (100 - self.hunger) * 1.5})
        if self.inventory["water"] > 0:
            actions.append({"action": "drink", "priority": (100 - self.thirst) * 1.5})
        if self.in_camp:
            actions.append({"action": "rest", "priority": (self.max_hp - self.hp) + (self.max_stamina - self.stamina) / 2})

        # --- Walka ---
        for enemy in world_map.enemies:
            dist = abs(enemy.x - self.x) + abs(enemy.y - self.y)
            if dist <= 1:
                # Priorytet ataku rośnie, gdy agent ma więcej HP niż wróg
                hp_advantage = self.hp - enemy.hp
                actions.append({"action": ("attack", enemy), "priority": 100 + hp_advantage})

        # --- Zarządzanie Ekwipunkiem ---
        if self.get_total_inventory_size() >= self.current_carry_capacity -1:
            if not self.in_camp:
                actions.append({"action": ("move_to_camp", world_map.camp_x, world_map.camp_y), "priority": 80})
            else:
                actions.append({"action": "deposit", "priority": 85})

        # --- Zbieranie Zasobów ---
        quota = self.calculate_daily_quota(days_ahead=2)
        if self.inventory["food"] < quota["food"]:
             actions.append({"action": ("find_resource", "food"), "priority": 70})
        if self.inventory["water"] < quota["water"]:
             actions.append({"action": ("find_resource", "water"), "priority": 70})

        # --- Budowa i Crafting ---
        if self.in_camp:
            if not self.equipment["tool"] and self.inventory["wood"] >=3 and self.inventory["stone"] >= 2:
                actions.append({"action": "craft_stone_axe", "priority": 60})
            if len(self.camp["structures"]) < 3 and self.inventory["wood"] >= 10 and self.inventory["stone"] >= 3 and self.level >= 2:
                 actions.append({"action": "build_fire", "priority": 55})

        # --- Inne Akcje ---
        if self.day_progress > NIGHT_START and not self.in_camp:
             actions.append({"action": ("move_to_camp", world_map.camp_x, world_map.camp_y), "priority": 90})

        # Domyślna akcja - eksploracja
        actions.append({"action": "explore", "priority": 10})

        # Wybierz akcję o najwyższym priorytecie
        if not actions:
            return "explore"

        best_action = max(actions, key=lambda x: x["priority"])
        return best_action["action"]

    def execute_action(self, action, world_map):
        self.current_action = action
        self.idle_timer = 0
        action_duration = 1.0

        if isinstance(action, tuple):
            action_type = action[0]
            if action_type == "attack":
                target = action[1]
                killed = self.attack(target)
                if killed:
                    world_map.enemies.remove(target)
                return True, "Walka!", 0.5

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
                            exp = self.gain_exp(4, f"gather_{resource_type}")
                            return True, f"Zebrano {harvested} {resource_type} (+{exp} EXP)", action_duration

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
                return True, "Zjedzono jedzenie", action_duration
            return False, "Brak jedzenia", action_duration

        elif action == "drink":
            action_duration = max(0.5 - (self.dexterity * 0.01), MIN_ACTION_DELAY)
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
                    exp = self.gain_exp(7, "craft_stone_axe")
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
                                exp = self.gain_exp(10, f"build_{structure_type}")
                                return True, f"{msg} (+{exp} EXP)", action_duration
                            return False, msg, action_duration
                return False, "Brak miejsca w obozie", action_duration

        elif action == "explore":
            dx = random.randint(-1, 1)
            dy = random.randint(-1, 1)
            new_x = max(0, min(self.x + dx, world_map.width - 1))
            new_y = max(0, min(self.y + dy, world_map.height - 1))
            started = self.start_move(new_x, new_y, world_map)
            if not started:
                return False, "Nie można eksplorować - mało staminy", 0.1
            return True, "Eksploracja...", self.move_speed

        return False, "Nieznana akcja", 1.0

    def attack(self, target):
        damage = self.strength
        if self.equipment["weapon"]:
            damage += self.equipment["weapon"].stats_bonus.get("damage", 0)

        target.hp -= damage
        self.add_log(f"Zadano {damage} obrażeń wilkowi!")
        if target.hp <= 0:
            self.add_log("Wilk pokonany!")
            return True # Target is dead
        return False

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
        self.hunger -= BASE_HUNGER_DRAIN_PER_DAY * day_fraction
        self.thirst -= BASE_THIRST_DRAIN_PER_DAY * day_fraction

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

        has_fire = any(s.type == "fire" for s in self.camp["structures"])

        if self.is_night:
            if not self.in_camp:
                self.hp -= NIGHT_HP_DRAIN * delta_time
                self.warmth -= 0.1 * delta_time
            elif not has_fire: # In camp but no fire
                self.warmth -= 0.05 * delta_time


        if self.day_progress >= 1.0:
            self.end_day(world_map)

        self.check_death()

    def end_day(self, world_map):
        self.current_day += 1
        self.day_progress = 0.0
        self.is_night = False
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
