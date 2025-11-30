# ui.py
import pygame
from settings import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    BLACK,
    WHITE,
    GREEN,
    RED,
    BLUE,
    YELLOW,
    GRAY,
    DARK_GREEN,
    ORANGE,
    PURPLE,
    DARK_BLUE,
    LIGHT_GREEN,
    DARK_GRAY,
    SECONDS_PER_DAY,
    TILE_SIZE,
    CAMP_SIZE
)

class UI:
    def __init__(self, screen):
        self.screen = screen
        self.font_small = pygame.font.Font(None, 45)
        self.font_medium = pygame.font.Font(None, 55)
        self.font_large = pygame.font.Font(None, 80)
        self.font_huge = pygame.font.Font(None, 95)
        self.camera_x = 0
        self.camera_y = 0

    def draw_menu(self, knowledge):
        y = 150
        title = self.font_huge.render("AI SURVIVAL", True, YELLOW)
        self.screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, y))
        y += 200
        subtitle = self.font_medium.render("180 Dni Przetrwania", True, WHITE)
        self.screen.blit(subtitle, (SCREEN_WIDTH//2 - subtitle.get_width()//2, y))
        y += 100
        stats = [
            f"Liczba prób: {knowledge.attempts}",
            f"Najlepszy wynik: {knowledge.best_survival_days} dni",
            ""
        ]
        for stat in stats:
            text = self.font_medium.render(stat, True, WHITE)
            self.screen.blit(text, (SCREEN_WIDTH//2 - text.get_width()//2, y))
            y += 80
        if knowledge.death_causes:
            text = self.font_medium.render("Top przyczyny śmierci:", True, YELLOW)
            self.screen.blit(text, (SCREEN_WIDTH//2 - text.get_width()//2, y))
            y += 80
            sorted_causes = sorted(knowledge.death_causes.items(), key=lambda x: x[1], reverse=True)[:4]
            for cause, count in sorted_causes:
                text = self.font_small.render(f"{cause}: {count}x", True, RED)
                self.screen.blit(text, (SCREEN_WIDTH//2 - text.get_width()//2, y))
                y += 60
        button_y = SCREEN_HEIGHT - 300
        button = pygame.Rect(100, button_y, SCREEN_WIDTH - 200, 180)
        pygame.draw.rect(self.screen, GREEN, button)
        pygame.draw.rect(self.screen, WHITE, button, 5)
        text = self.font_large.render("ROZPOCZNIJ GRĘ", True, WHITE)
        self.screen.blit(text, (SCREEN_WIDTH//2 - text.get_width()//2, button_y + 50))

    def draw_game(self, agent, world_map, log, paused, simulation_active):
        map_height = 800
        ui_start_y = map_height + 10
        self.draw_map(agent, world_map, 0, 0, SCREEN_WIDTH, map_height)
        y = ui_start_y
        day_text = f"DZIEŃ {agent.current_day}/180"
        time_icon = "🌙" if agent.is_night else "☀️"
        header = self.font_medium.render(f"{day_text} {time_icon}", True, YELLOW)
        self.screen.blit(header, (15, y))
        time_left = SECONDS_PER_DAY * (1.0 - agent.day_progress)
        time_text = f"Pozostało: {time_left:.1f}s"
        time_render = self.font_medium.render(time_text, True, WHITE)
        self.screen.blit(time_render, (SCREEN_WIDTH // 2 - time_render.get_width() // 2, y))
        lvl_text = f"LVL {agent.level}"
        text = self.font_medium.render(lvl_text, True, WHITE)
        self.screen.blit(text, (SCREEN_WIDTH - text.get_width() - 15, y))
        y += 65
        bar_w = SCREEN_WIDTH - 30
        pygame.draw.rect(self.screen, GRAY, (15, y, bar_w, 25))
        progress_w = int(agent.day_progress * bar_w)
        color = DARK_BLUE if agent.is_night else YELLOW
        pygame.draw.rect(self.screen, color, (15, y, progress_w, 25))
        pygame.draw.rect(self.screen, WHITE, (15, y, bar_w, 25), 2)
        y += 40
        attr_text = f"STR:{agent.strength} DEX:{agent.dexterity} PER:{agent.perception} INT:{agent.intelligence} VIT:{agent.vitality}"
        text = self.font_small.render(attr_text, True, WHITE)
        self.screen.blit(text, (15, y))
        y += 50

        bar_h = 35
        bar_w = SCREEN_WIDTH - 30
        self.draw_bar_compact(15, y, bar_w, bar_h, agent.hp, agent.max_hp, RED, "HP")
        y += bar_h + 10
        self.draw_bar_compact(15, y, bar_w, bar_h, agent.hunger, 100, ORANGE, "Głód")
        y += bar_h + 10
        self.draw_bar_compact(15, y, bar_w, bar_h, agent.thirst, 100, BLUE, "Woda")
        y += bar_h + 10
        self.draw_bar_compact(15, y, bar_w, bar_h, agent.warmth, 100, YELLOW, "Ciepło")
        y += bar_h + 10
        self.draw_bar_compact(15, y, bar_w, bar_h, agent.stamina, agent.max_stamina, GREEN, "Energia")
        y += bar_h + 20
        self.draw_bar_compact(15, y, bar_w, bar_h, agent.exp, agent.exp_to_next, PURPLE, "EXP")
        y += bar_h + 20

        inv_text = f"Inwentarz ({agent.get_total_inventory_size()}/{agent.current_carry_capacity}):"
        text = self.font_small.render(inv_text, True, YELLOW)
        self.screen.blit(text, (15, y))
        y += 45
        inv_line = f"🪵:{agent.inventory['wood']} 🪨:{agent.inventory['stone']} 🍎:{agent.inventory['food']} 💧:{agent.inventory['water']} 🧵:{agent.inventory['fiber']} ⚙️:{agent.inventory['metal']} 🥉:{agent.inventory['copper']}"
        text = self.font_small.render(inv_line, True, WHITE)
        self.screen.blit(text, (15, y))
        y += 50
        quota = agent.calculate_daily_quota(days_ahead=2)
        quota_text = f"Quota (2 Dni): 🍎 x{quota['food']} | 💧 x{quota['water']}"
        quota_render = self.font_small.render(quota_text, True, LIGHT_GREEN)
        self.screen.blit(quota_render, (15, y))
        y += 50
        equip_text = "Ekwipunek: "
        equipped_items = []
        for slot, item in agent.equipment.items():
            if item:
                dur_text = "" if slot == "backpack" else f"({item.durability})"
                equipped_items.append(f"{item.name}{dur_text}")
        if equipped_items:
            equip_text += ", ".join(equipped_items)
        else:
            equip_text += "Brak"
        text = self.font_small.render(equip_text[:50], True, WHITE)
        self.screen.blit(text, (15, y))
        y += 50
        camp_text = f"Obóz: Poziom {agent.camp['level']} | Struktury: {len(agent.camp['structures'])}"
        text = self.font_small.render(camp_text, True, ORANGE)
        self.screen.blit(text, (15, y))
        y += 50
        text = self.font_small.render("--- LOG ---", True, YELLOW)
        self.screen.blit(text, (15, y))
        y += 45
        for entry in log:
            text = self.font_small.render(entry[:55], True, WHITE)
            self.screen.blit(text, (15, y))
            y += 40
        button_y = SCREEN_HEIGHT - 150
        button_w = (SCREEN_WIDTH - 40) // 2
        pause_btn = pygame.Rect(15, button_y, button_w, 120)
        pause_color = ORANGE if paused else RED
        pygame.draw.rect(self.screen, pause_color, pause_btn)
        pygame.draw.rect(self.screen, WHITE, pause_btn, 4)
        text = self.font_medium.render("PAUZA" if not paused else "WZNÓW", True, WHITE)
        self.screen.blit(text, (pause_btn.centerx - text.get_width()//2, button_y + 35))
        restart_btn = pygame.Rect(25 + button_w, button_y, button_w, 120)
        pygame.draw.rect(self.screen, GREEN if not simulation_active else GRAY, restart_btn)
        pygame.draw.rect(self.screen, WHITE, restart_btn, 4)
        text = self.font_medium.render("NOWA", True, WHITE)
        self.screen.blit(text, (restart_btn.centerx - text.get_width()//2, button_y + 35))

    def draw_map(self, agent, world_map, x, y, width, height):
        map_surface = pygame.Surface((width, height))
        map_surface.fill(BLACK)
        if agent:
            tiles_per_screen_x = width // TILE_SIZE
            tiles_per_screen_y = height // TILE_SIZE
            self.camera_x = agent.x - tiles_per_screen_x // 2
            self.camera_y = agent.y - tiles_per_screen_y // 2
            self.camera_x = max(0, min(self.camera_x, world_map.width - tiles_per_screen_x))
            self.camera_y = max(0, min(self.camera_y, world_map.height - tiles_per_screen_y))
        camp_start_x = world_map.camp_x - CAMP_SIZE // 2
        camp_start_y = world_map.camp_y - CAMP_SIZE // 2
        for row in range(world_map.height):
            for col in range(world_map.width):
                screen_x = (col - self.camera_x) * TILE_SIZE
                screen_y = (row - self.camera_y) * TILE_SIZE
                if screen_x < -TILE_SIZE or screen_x > width or screen_y < -TILE_SIZE or screen_y > height:
                    continue
                tile_type = world_map.tiles[row][col]["type"]
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
                pygame.draw.rect(self.screen, color, (screen_x, screen_y, TILE_SIZE, TILE_SIZE))
                pygame.draw.rect(self.screen, (0, 0, 0), (screen_x, screen_y, TILE_SIZE, TILE_SIZE), 1)
        camp_screen_x = (camp_start_x - self.camera_x) * TILE_SIZE
        camp_screen_y = (camp_start_y - self.camera_y) * TILE_SIZE
        camp_rect = pygame.Rect(camp_screen_x, camp_screen_y, CAMP_SIZE * TILE_SIZE, CAMP_SIZE * TILE_SIZE)
        pygame.draw.rect(self.screen, YELLOW, camp_rect, 3)
        if agent:
            for struct in agent.camp["structures"]:
                struct_world_x = camp_start_x + struct.x
                struct_world_y = camp_start_y + struct.y
                struct_screen_x = (struct_world_x - self.camera_x) * TILE_SIZE
                struct_screen_y = (struct_world_y - self.camera_y) * TILE_SIZE
                if -TILE_SIZE <= struct_screen_x < width and -TILE_SIZE <= struct_screen_y < height:
                    center_x = int(struct_screen_x + TILE_SIZE // 2)
                    center_y = int(struct_screen_y + TILE_SIZE // 2)
                    pygame.draw.circle(self.screen, struct.color, (center_x, center_y), TILE_SIZE // 3)
                    pygame.draw.circle(self.screen, WHITE, (center_x, center_y), TILE_SIZE // 3, 2)
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
                        self.screen.blit(icon_text, (center_x - icon_text.get_width()//2, center_y - icon_text.get_height()//2))
        for node in world_map.resource_nodes:
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
                self.screen.blit(text, (screen_x + TILE_SIZE//2 - text.get_width()//2,
                                  screen_y + TILE_SIZE//2 - text.get_height()//2))
        if agent:
            # Draw enemies
            for enemy in world_map.enemies:
                enemy_x = (enemy.x - self.camera_x) * TILE_SIZE
                enemy_y = (enemy.y - self.camera_y) * TILE_SIZE
                if 0 <= enemy_x < width and 0 <= enemy_y < height:
                    pygame.draw.circle(self.screen, RED,
                                     (int(enemy_x + TILE_SIZE//2), int(enemy_y + TILE_SIZE//2)),
                                     TILE_SIZE//3)

            agent_x = (agent.x - self.camera_x) * TILE_SIZE
            agent_y = (agent.y - self.camera_y) * TILE_SIZE
            if 0 <= agent_x < width and 0 <= agent_y < height:
                pygame.draw.circle(self.screen, YELLOW,
                                 (int(agent_x + TILE_SIZE//2), int(agent_y + TILE_SIZE//2)),
                                 TILE_SIZE//2 + 2, 2)
                pygame.draw.circle(self.screen, WHITE,
                                 (int(agent_x + TILE_SIZE//2), int(agent_y + TILE_SIZE//2)),
                                 TILE_SIZE//3)
                lvl_text = self.font_small.render(f"L{agent.level}", True, YELLOW)
                self.screen.blit(lvl_text, (agent_x + TILE_SIZE//2 - lvl_text.get_width()//2,
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
            pygame.draw.rect(self.screen, BLACK, bg_rect)
            pygame.draw.rect(self.screen, WHITE, bg_rect, 1)
            self.screen.blit(text, (legend_x, legend_y))
            legend_x += text.get_width() + 15

    def draw_bar_compact(self, x, y, width, height, value, max_value, color, label):
        pygame.draw.rect(self.screen, (30, 30, 30), (x, y, width, height))
        fill_width = int((max(value, 0) / max_value) * width) if max_value > 0 else 0
        pygame.draw.rect(self.screen, color, (x, y, fill_width, height))
        pygame.draw.rect(self.screen, WHITE, (x, y, width, height), 2)
        text = self.font_small.render(f"{label}: {int(max(value, 0))}/{int(max_value)}", True, WHITE)
        self.screen.blit(text, (x + 5, y + 2))
