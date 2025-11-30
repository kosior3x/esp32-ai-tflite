import pygame

class UI:
    def __init__(self, screen, agent, game):
        self.screen = screen
        self.agent = agent
        self.game = game
        self.font_small = pygame.font.Font(None, 45)
        self.font_medium = pygame.font.Font(None, 55)
        self.font_large = pygame.font.Font(None, 80)
        self.font_huge = pygame.font.Font(None, 95)

    def draw(self):
        self.screen.fill((0, 0, 0))
        if not self.agent:
            self.draw_menu()
        else:
            self.draw_game()
        pygame.display.flip()

    def draw_menu(self):
        y = 150
        title = self.font_huge.render("AI SURVIVAL", True, (255, 255, 0))
        self.screen.blit(title, (1025//2 - title.get_width()//2, y))
        y += 200
        subtitle = self.font_medium.render("180 Dni Przetrwania", True, (255, 255, 255))
        self.screen.blit(subtitle, (1025//2 - subtitle.get_width()//2, y))
        y += 100
        stats = [
            f"Liczba prób: {self.game.knowledge.attempts}",
            f"Najlepszy wynik: {self.game.knowledge.best_survival_days} dni",
            ""
        ]
        for stat in stats:
            text = self.font_medium.render(stat, True, (255, 255, 255))
            self.screen.blit(text, (1025//2 - text.get_width()//2, y))
            y += 80
        if self.game.knowledge.death_causes:
            text = self.font_medium.render("Top przyczyny śmierci:", True, (255, 255, 0))
            self.screen.blit(text, (1025//2 - text.get_width()//2, y))
            y += 80
            sorted_causes = sorted(self.game.knowledge.death_causes.items(), key=lambda x: x[1], reverse=True)[:4]
            for cause, count in sorted_causes:
                text = self.font_small.render(f"{cause}: {count}x", True, (255, 0, 0))
                self.screen.blit(text, (1025//2 - text.get_width()//2, y))
                y += 60
        button_y = 2200 - 300
        button = pygame.Rect(100, button_y, 1025 - 200, 180)
        pygame.draw.rect(self.screen, (0, 255, 0), button)
        pygame.draw.rect(self.screen, (255, 255, 255), button, 5)
        text = self.font_large.render("ROZPOCZNIJ GRĘ", True, (255, 255, 255))
        self.screen.blit(text, (1025//2 - text.get_width()//2, button_y + 50))

    def draw_game(self):
        map_height = 800
        ui_start_y = map_height + 10 + self.game.ui_scroll_y
        self.draw_map(0, 0, 1025, map_height)
        y = ui_start_y
        day_text = f"DZIEŃ {self.agent.current_day}/180"
        time_icon = "🌙" if self.agent.is_night else "☀️"
        header = self.font_medium.render(f"{day_text} {time_icon}", True, (255, 255, 0))
        self.screen.blit(header, (15, y))
        time_left = 90 * (1.0 - self.agent.day_progress)
        time_text = f"Pozostało: {time_left:.1f}s"
        time_render = self.font_medium.render(time_text, True, (255, 255, 255))
        self.screen.blit(time_render, (1025 // 2 - time_render.get_width() // 2, y))
        lvl_text = f"LVL {self.agent.level}"
        text = self.font_medium.render(lvl_text, True, (255, 255, 255))
        self.screen.blit(text, (1025 - text.get_width() - 15, y))
        y += 65
        bar_w = 1025 - 30
        pygame.draw.rect(self.screen, (128, 128, 128), (15, y, bar_w, 25))
        progress_w = int(self.agent.day_progress * bar_w)
        color = (0, 0, 139) if self.agent.is_night else (255, 255, 0)
        pygame.draw.rect(self.screen, color, (15, y, progress_w, 25))
        pygame.draw.rect(self.screen, (255, 255, 255), (15, y, bar_w, 25), 2)
        y += 40
        attr_text = f"STR:{self.agent.strength} DEX:{self.agent.dexterity} PER:{self.agent.perception} INT:{self.agent.intelligence} VIT:{self.agent.vitality}"
        text = self.font_small.render(attr_text, True, (255, 255, 255))
        self.screen.blit(text, (15, y))
        y += 50

        # EXP bar - added per request
        bar_h = 35
        bar_w = 1025 - 30
        # HP
        self.draw_bar_compact(15, y, bar_w, bar_h, self.agent.hp, self.agent.max_hp, (255, 0, 0), "HP")
        y += bar_h + 10
        # Hunger
        self.draw_bar_compact(15, y, bar_w, bar_h, self.agent.hunger, 100, (255, 165, 0), "Głód")
        y += bar_h + 10
        # Thirst
        self.draw_bar_compact(15, y, bar_w, bar_h, self.agent.thirst, 100, (0, 100, 255), "Woda")
        y += bar_h + 10
        # Warmth
        self.draw_bar_compact(15, y, bar_w, bar_h, self.agent.warmth, 100, (255, 255, 0), "Ciepło")
        y += bar_h + 10
        # Stamina
        self.draw_bar_compact(15, y, bar_w, bar_h, self.agent.stamina, self.agent.max_stamina, (0, 255, 0), "Energia")
        y += bar_h + 20
        # EXP bar (new)
        self.draw_bar_compact(15, y, bar_w, bar_h, self.agent.exp, self.agent.exp_to_next, (128, 0, 128), "EXP")
        y += bar_h + 20

        # Camp Storage
        storage_text = "Obóz: " + " ".join([f"{self.game.emoji(res)}:{amt}" for res, amt in self.agent.camp["storage"].items()])
        text = self.font_small.render(storage_text, True, (255, 255, 255))
        self.screen.blit(text, (15, y))
        y += 50

        inv_text = f"Inwentarz ({self.agent.get_total_inventory_size()}/{self.agent.current_carry_capacity}):"
        text = self.font_small.render(inv_text, True, (255, 255, 0))
        self.screen.blit(text, (15, y))
        y += 45
        inv_line = f"🪵:{self.agent.inventory['wood']} 🪨:{self.agent.inventory['stone']} 🍎:{self.agent.inventory['food']} 💧:{self.agent.inventory['water']} 🧵:{self.agent.inventory['fiber']} ⚙️:{self.agent.inventory['metal']}"
        text = self.font_small.render(inv_line, True, (255, 255, 255))
        self.screen.blit(text, (15, y))
        y += 50
        quota = self.agent.calculate_daily_quota(days_ahead=2)
        quota_text = f"Quota (2 Dni): 🍎 x{quota['food']} | 💧 x{quota['water']}"
        quota_render = self.font_small.render(quota_text, True, (144, 238, 144))
        self.screen.blit(quota_render, (15, y))
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
        text = self.font_small.render(equip_text[:50], True, (255, 255, 255))
        self.screen.blit(text, (15, y))
        y += 50
        camp_text = f"Obóz: Poziom {self.agent.camp['level']} | Struktury: {len(self.agent.camp['structures'])}"
        text = self.font_small.render(camp_text, True, (255, 165, 0))
        self.screen.blit(text, (15, y))
        y += 50

        # PRZEMYŚLENIA
        text = self.font_small.render("--- PRZEMYŚLENIA ---", True, (128, 0, 128))
        self.screen.blit(text, (15, y))
        y += 45
        if self.agent.thoughts:
            last_thought = self.agent.thoughts[-1]
            text = self.font_small.render(f"💭 {last_thought}"[:55], True, (144, 238, 144))
            self.screen.blit(text, (15, y))
            y += 40

        # LOG
        text = self.font_small.render("--- LOG ---", True, (255, 255, 0))
        self.screen.blit(text, (15, y))
        y += 45
        for entry in self.game.log[-self.game.max_log:]:
            text = self.font_small.render(entry[:55], True, (255, 255, 255))
            self.screen.blit(text, (15, y))
            y += 40

        # UMIEJĘTNOŚCI
        text = self.font_small.render("--- UMIEJĘTNOŚCI ---", True, (0, 100, 255))
        self.screen.blit(text, (15, y))
        y += 45
        if self.agent.learned_skills:
            skills_text = ", ".join([f"{skill.name} Lvl {skill.level}" for skill in self.agent.learned_skills.values()])
            text = self.font_small.render(skills_text, True, (144, 238, 144))
            self.screen.blit(text, (15, y))
        else:
            text = self.font_small.render("Brak umiejętności", True, (128, 128, 128))
            self.screen.blit(text, (15, y))
        y += 40

        # KARY OSTROŻNOŚCI
        if self.agent.caution_penalty_score > 0:
            text = self.font_small.render(f"⚠️ Kary ostrożności: {self.agent.caution_penalty_score}", True, (255, 0, 0))
            self.screen.blit(text, (15, y))
            y += 40

        button_y = 2200 - 150
        button_w = (1025 - 40) // 2
        pause_btn = pygame.Rect(15, button_y, button_w, 120)
        pause_color = (255, 165, 0) if self.game.paused else (255, 0, 0)
        pygame.draw.rect(self.screen, pause_color, pause_btn)
        pygame.draw.rect(self.screen, (255, 255, 255), pause_btn, 4)
        text = self.font_medium.render("PAUZA" if not self.game.paused else "WZNÓW", True, (255, 255, 255))
        self.screen.blit(text, (pause_btn.centerx - text.get_width()//2, button_y + 35))
        restart_btn = pygame.Rect(25 + button_w, button_y, button_w, 120)
        pygame.draw.rect(self.screen, (0, 255, 0) if not self.game.simulation_active else (128, 128, 128), restart_btn)
        pygame.draw.rect(self.screen, (255, 255, 255), restart_btn, 4)
        text = self.font_medium.render("NOWA", True, (255, 255, 255))
        self.screen.blit(text, (restart_btn.centerx - text.get_width()//2, button_y + 35))

    def draw_map(self, x, y, width, height):
        map_surface = pygame.Surface((width, height))
        map_surface.fill((0, 0, 0))
        if self.agent:
            tiles_per_screen_x = width // 35
            tiles_per_screen_y = height // 35
            self.game.camera_x = self.agent.x - tiles_per_screen_x // 2
            self.game.camera_y = self.agent.y - tiles_per_screen_y // 2
            self.game.camera_x = max(0, min(self.game.camera_x, self.game.world_map.width - tiles_per_screen_x))
            self.game.camera_y = max(0, min(self.game.camera_y, self.game.world_map.height - tiles_per_screen_y))
        camp_start_x = self.game.world_map.camp_x - 5 // 2
        camp_start_y = self.game.world_map.camp_y - 5 // 2
        for row in range(self.game.world_map.height):
            for col in range(self.game.world_map.width):
                screen_x = (col - self.game.camera_x) * 35
                screen_y = (row - self.game.camera_y) * 35
                if screen_x < -35 or screen_x > width or screen_y < -35 or screen_y > height:
                    continue
                tile_type = self.game.world_map.tiles[row][col]["type"]
                if tile_type == 0:
                    color = (34, 139, 34)
                elif tile_type == 1:
                    color = (0, 128, 0)
                elif tile_type == 2:
                    color = (128, 128, 128)
                elif tile_type == 3:
                    color = (144, 238, 144)
                elif tile_type == 4:
                    color = (0, 100, 255)
                elif tile_type == 5:
                    color = (210, 180, 140)
                elif tile_type == 6:
                    color = (64, 64, 64)
                elif tile_type == 7:
                    color = (101, 67, 33)
                else:
                    color = (0, 0, 0)
                pygame.draw.rect(self.screen, color, (screen_x, screen_y, 35, 35))
                # obrys bez alfa
                pygame.draw.rect(self.screen, (0, 0, 0), (screen_x, screen_y, 35, 35), 1)
        camp_screen_x = (camp_start_x - self.game.camera_x) * 35
        camp_screen_y = (camp_start_y - self.game.camera_y) * 35
        camp_rect = pygame.Rect(camp_screen_x, camp_screen_y, 5 * 35, 5 * 35)
        pygame.draw.rect(self.screen, (255, 255, 0), camp_rect, 3)
        if self.agent:
            for struct in self.agent.camp["structures"]:
                struct_world_x = camp_start_x + struct.x
                struct_world_y = camp_start_y + struct.y
                struct_screen_x = (struct_world_x - self.game.camera_x) * 35
                struct_screen_y = (struct_world_y - self.game.camera_y) * 35
                if -35 <= struct_screen_x < width and -35 <= struct_screen_y < height:
                    center_x = int(struct_screen_x + 35 // 2)
                    center_y = int(struct_screen_y + 35 // 2)
                    pygame.draw.circle(self.screen, struct.color, (center_x, center_y), 35 // 3)
                    pygame.draw.circle(self.screen, (255, 255, 255), (center_x, center_y), 35 // 3, 2)
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
                        icon_text = self.font_small.render(icon, True, (255, 255, 255))
                        self.screen.blit(icon_text, (center_x - icon_text.get_width()//2, center_y - icon_text.get_height()//2))
        for node in self.game.world_map.resource_nodes:
            screen_x = (node.x - self.game.camera_x) * 35
            screen_y = (node.y - self.game.camera_y) * 35
            if screen_x < -35 or screen_x > width or screen_y < -35 or screen_y > height:
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
                text = self.font_small.render(icon, True, (255, 255, 255))
                self.screen.blit(text, (screen_x + 35//2 - text.get_width()//2,
                                  screen_y + 35//2 - text.get_height()//2))
        if self.agent:
            agent_x = (self.agent.x - self.game.camera_x) * 35
            agent_y = (self.agent.y - self.game.camera_y) * 35
            if 0 <= agent_x < width and 0 <= agent_y < height:
                pygame.draw.circle(self.screen, (255, 255, 0),
                                 (int(agent_x + 35//2), int(agent_y + 35//2)),
                                 35//2 + 2, 2)
                pygame.draw.circle(self.screen, (255, 255, 255),
                                 (int(agent_x + 35//2), int(agent_y + 35//2)),
                                 35//3)
                lvl_text = self.font_small.render(f"L{self.agent.level}", True, (255, 255, 0))
                self.screen.blit(lvl_text, (agent_x + 35//2 - lvl_text.get_width()//2,
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
            text = self.font_small.render(f"{icon} {name}", True, (255, 255, 255))
            bg_rect = pygame.Rect(legend_x - 3, legend_y - 3, text.get_width() + 6, text.get_height() + 6)
            pygame.draw.rect(self.screen, (0, 0, 0), bg_rect)
            pygame.draw.rect(self.screen, (255, 255, 255), bg_rect, 1)
            self.screen.blit(text, (legend_x, legend_y))
            legend_x += text.get_width() + 15

    def draw_bar_compact(self, x, y, width, height, value, max_value, color, label):
        pygame.draw.rect(self.screen, (30, 30, 30), (x, y, width, height))
        fill_width = int((max(value, 0) / max_value) * width) if max_value > 0 else 0
        pygame.draw.rect(self.screen, color, (x, y, fill_width, height))
        pygame.draw.rect(self.screen, (255, 255, 255), (x, y, width, height), 2)
        text = self.font_small.render(f"{label}: {int(max(value, 0))}/{int(max_value)}", True, (255, 255, 255))
        self.screen.blit(text, (x + 5, y + 2))
