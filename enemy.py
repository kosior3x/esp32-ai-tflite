# enemy.py
import random
from settings import TILE_SIZE

class Enemy:
    def __init__(self, x, y, enemy_type="wolf"):
        self.x = x
        self.y = y
        self.type = enemy_type
        self.hp = 0
        self.max_hp = 0
        self.damage = 0
        self.speed = 0
        self.agro_radius = 5
        self.is_agro = False

        if self.type == "wolf":
            self.hp = 30
            self.max_hp = 30
            self.damage = 5
            self.speed = 0.8 # Szybszy od agenta

        self.move_cooldown = 0.0

    def update(self, delta_time, agent, world_map):
        # Aktualizacja logiki wroga
        self.move_cooldown = max(0, self.move_cooldown - delta_time)

        dist_to_agent = abs(self.x - agent.x) + abs(self.y - agent.y)

        if dist_to_agent <= self.agro_radius:
            self.is_agro = True

        if self.is_agro and self.move_cooldown <= 0:
            if dist_to_agent <= 1:
                # Attack
                agent.hp -= self.damage
                agent.add_log(f"Wilk atakuje! Tracisz {self.damage} HP.")
                self.move_cooldown = 1.0 # Cooldown after attack
            else:
                # Move
                self.move_towards_agent(agent, world_map)

    def move_towards_agent(self, agent, world_map):
        dx = agent.x - self.x
        dy = agent.y - self.y

        step_x = 0
        if dx > 0: step_x = 1
        elif dx < 0: step_x = -1

        step_y = 0
        if dy > 0: step_y = 1
        elif dy < 0: step_y = -1

        new_x = self.x + step_x
        new_y = self.y + step_y

        # Check for walls
        for structure in agent.camp["structures"]:
            if structure.type == "wall" and structure.x == new_x and structure.y == new_y:
                return # Wall blocks movement

        if 0 <= new_x < world_map.width and 0 <= new_y < world_map.height:
            self.x = new_x
            self.y = new_y
            self.move_cooldown = self.speed
