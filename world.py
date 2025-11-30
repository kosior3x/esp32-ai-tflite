# world.py
import random
from settings import MAP_WIDTH, MAP_HEIGHT, CAMP_SIZE
from enemy import Enemy
from perlin_noise import PerlinNoise

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
        self.tiles = [[{"type": 0, "biome": "forest"} for _ in range(self.width)] for _ in range(self.height)]
        self.resource_nodes = []
        self.enemies = []
        self.camp_x = self.width // 2
        self.camp_y = self.height // 2
        self.generate_map()
        self.spawn_enemies()

    def generate_map(self):
        noise = PerlinNoise(octaves=3, seed=random.randint(1, 100))
        scale = 15.0

        for y in range(self.height):
            for x in range(self.width):
                n = noise([x / scale, y / scale])
                if n > 0.25:
                    self.tiles[y][x]["biome"] = "mountain"
                    self.tiles[y][x]["type"] = 6 # Dark Gray for mountain
                else:
                    self.tiles[y][x]["biome"] = "forest"
                    self.tiles[y][x]["type"] = 1 # Dark Green for forest

        camp_start_x = self.camp_x - CAMP_SIZE // 2
        camp_start_y = self.camp_y - CAMP_SIZE // 2

        for cy in range(CAMP_SIZE):
            for cx in range(CAMP_SIZE):
                actual_x = camp_start_x + cx
                actual_y = camp_start_y + cy
                if 0 <= actual_x < self.width and 0 <= actual_y < self.height:
                    self.tiles[actual_y][actual_x]["type"] = 7
                    self.tiles[actual_y][actual_x]["biome"] = "camp"

        def place_resource(res_type, count, max_amount, respawn, biome, tile_id):
            attempts = 0
            placed = 0
            while placed < count and attempts < 200:
                x = random.randint(0, self.width - 1)
                y = random.randint(0, self.height - 1)
                if self.tiles[y][x]["biome"] == biome and self.get_resource_at(x, y) is None and not self.is_in_camp(x,y):
                    self.resource_nodes.append(ResourceNode(res_type, max_amount, x, y, respawn_days=respawn))
                    self.tiles[y][x]["type"] = tile_id
                    placed += 1
                attempts += 1

        # Resources based on biome
        place_resource("wood", 10, 50, 3, "forest", 1)
        place_resource("food", 6, 30, 2, "forest", 3)
        place_resource("fiber", 6, 35, 3, "forest", 5)
        place_resource("stone", 8, 40, 4, "mountain", 2)
        place_resource("metal", 4, 20, 5, "mountain", 6)
        place_resource("copper", 5, 25, 4, "mountain", 6)
        place_resource("water", 1, 100, 1, "forest", 4)

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

    def spawn_enemies(self, num_enemies=5):
        for _ in range(num_enemies):
            while True:
                x = random.randint(0, self.width - 1)
                y = random.randint(0, self.height - 1)
                if not self.is_in_camp(x, y):
                    self.enemies.append(Enemy(x, y))
                    break
