import json
import os
import random
from datetime import datetime

class QLearningSystem:
    def __init__(self, actions):
        self.q_table = {}
        self.actions = actions
        self.learning_rate = 0.1
        self.discount_factor = 0.9
        self.epsilon = 0.9 # Exploration rate
        self.epsilon_decay = 0.995
        self.epsilon_min = 0.05

    def get_state(self, agent, world_map):
        hunger_tier = int(agent.hunger / 25)
        thirst_tier = int(agent.thirst / 25)
        stamina_tier = int(agent.stamina / 25)
        time_of_day = "day" if not agent.is_night else "night"
        distance_from_camp = abs(agent.x - world_map.camp_x) + abs(agent.y - world_map.camp_y)
        distance_tier = int(distance_from_camp / 5)

        return (hunger_tier, thirst_tier, stamina_tier, time_of_day, distance_tier)

    def choose_action(self, state, agent):
        risk_adjusted_epsilon = self.epsilon * (1.0 - agent.knowledge.risk_tolerance)
        if random.random() < risk_adjusted_epsilon:
            return random.choice(self.actions) # Explore
        else:
            # Exploit
            q_values = self.q_table.get(state, {})
            if not q_values:
                return random.choice(self.actions)
            return max(q_values, key=q_values.get)

    def update_q_table(self, state, action, reward, next_state):
        old_value = self.q_table.get(state, {}).get(action, 0)

        next_max = 0
        if next_state in self.q_table:
            next_max = max(self.q_table[next_state].values())

        new_value = old_value + self.learning_rate * (reward + self.discount_factor * next_max - old_value)

        if state not in self.q_table:
            self.q_table[state] = {}
        self.q_table[state][action] = new_value
        self.decay_epsilon()

    def decay_epsilon(self):
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay

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

    def save_to_file(self, filename="survival_2.0b/ai_knowledge.json"):
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

    def load_from_file(self, filename="survival_2.0b/ai_knowledge.json"):
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
