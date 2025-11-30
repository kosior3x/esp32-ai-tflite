import random
import heapq

class Pathfinder:
    def __init__(self, world_map):
        self.world_map = world_map

    def find_path(self, start, end):
        # A* algorithm
        open_set = []
        heapq.heappush(open_set, (0, start))
        came_from = {}
        g_score = {start: 0}
        f_score = {start: self.heuristic(start, end)}

        while open_set:
            current = heapq.heappop(open_set)[1]

            if current == end:
                return self.reconstruct_path(came_from, current)

            for neighbor, cost in self.get_neighbors(current):
                tentative_g_score = g_score[current] + cost
                if tentative_g_score < g_score.get(neighbor, float('inf')):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = tentative_g_score + self.heuristic(neighbor, end)
                    if neighbor not in [i[1] for i in open_set]:
                        heapq.heappush(open_set, (f_score[neighbor], neighbor))
        return None

    def heuristic(self, a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def get_neighbors(self, node):
        neighbors = []
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            x, y = node[0] + dx, node[1] + dy
            if 0 <= x < self.world_map.width and 0 <= y < self.world_map.height:
                risk = self.world_map.tiles[y][x]["risk"]
                cost = 1 + risk * 10 # Base cost of 1, plus risk penalty
                neighbors.append(((x, y), cost))
        return neighbors

    def reconstruct_path(self, came_from, current):
        path = []
        while current in came_from:
            path.append(current)
            current = came_from[current]
        return path[::-1]


class CampStructure:
    def __init__(self, name, structure_type, x, y, color, durability=100, maintenance_cost=1):
        self.name = name
        self.type = structure_type
        self.maintenance_cost = maintenance_cost
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
        self.width = 20
        self.height = 20
        self.tiles = [[{"type": 0, "risk": 0.1} for _ in range(self.width)] for _ in range(self.height)]
        self.resource_nodes = []
        self.camp_x = self.width // 2
        self.camp_y = self.height // 2
        self.generate_map()

    def generate_map(self):
        camp_start_x = self.camp_x - 5 // 2
        camp_start_y = self.camp_y - 5 // 2

        for cy in range(5):
            for cx in range(5):
                actual_x = camp_start_x + cx
                actual_y = camp_start_y + cy
                if 0 <= actual_x < self.width and 0 <= actual_y < self.height:
                    self.tiles[actual_y][actual_x]["type"] = 7
                    self.tiles[actual_y][actual_x]["risk"] = 0 # Camp is safe

        def place_resource(res_type, count, max_amount, respawn, tile_id, risk):
            attempts = 0
            while len([n for n in self.resource_nodes if n.type == res_type]) < count and attempts < 200:
                x = random.randint(0, self.width - 1)
                y = random.randint(0, self.height - 1)
                if self.tiles[y][x]["type"] != 7 and self.get_resource_at(x, y) is None:
                    self.resource_nodes.append(ResourceNode(res_type, max_amount, x, y, respawn_days=respawn))
                    self.tiles[y][x]["type"] = tile_id
                    self.tiles[y][x]["type"] = tile_id
                    self.tiles[y][x]["risk"] = risk
                attempts += 1

        place_resource("wood", 10, 50, 3, 1, 0.2)
        place_resource("stone", 8, 40, 4, 2, 0.3)
        place_resource("food", 6, 30, 2, 3, 0.1)
        place_resource("water", 1, 100, 1, 4, 0.05)
        place_resource("fiber", 6, 35, 3, 5, 0.1)
        place_resource("metal", 4, 20, 5, 6, 0.5)

    def get_resource_at(self, x, y):
        for node in self.resource_nodes:
            if node.x == x and node.y == y and not node.depleted:
                return node
        return None

    def is_in_camp(self, x, y):
        camp_start_x = self.camp_x - 5 // 2
        camp_start_y = self.camp_y - 5 // 2
        return (camp_start_x <= x < camp_start_x + 5 and
                camp_start_y <= y < camp_start_y + 5)

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
                "color": "BROWN",
                "level_req": 1
            },
            "fire": {
                "name": "Ognisko",
                "requirements": {"wood": 10, "stone": 3},
                "color": "ORANGE",
                "level_req": 2
            },
            "workbench": {
                "name": "Stół Roboczy",
                "requirements": {"wood": 12, "stone": 8},
                "color": "GRAY",
                "level_req": 3
            },
            "storage": {
                "name": "Magazyn",
                "requirements": {"wood": 20, "stone": 10},
                "color": "BROWN",
                "level_req": 4
            },
            "wall": {
                "name": "Mur Obronny",
                "requirements": {"stone": 15, "wood": 5},
                "color": "DARK_GRAY",
                "level_req": 5
            }
        }
