import pygame
import json
from agent import Agent
from world import WorldMap, Pathfinder
from ai_system import AIKnowledge
from ui import UI

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((1025, 2200))
        pygame.display.set_caption("AI Survival - 180 Days (Final)")
        self.clock = pygame.time.Clock()
        self.font_small = pygame.font.Font(None, 45)
        self.font_medium = pygame.font.Font(None, 55)
        self.font_large = pygame.font.Font(None, 80)
        self.font_huge = pygame.font.Font(None, 95)

        self.knowledge = AIKnowledge()
        try:
            self.knowledge.load_from_file()
        except json.JSONDecodeError as e:
            print(f"Błąd wczytywania pliku wiedzy (JSONDecodeError): {e}. Rozpoczynam bez danych historycznych.")
            self.knowledge = AIKnowledge()

        self.agent = None
        self.world_map = None
        self.pathfinder = None
        self.running = True
        self.paused = False
        self.ui = None

        self.log = []
        self.max_log = 8

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
        self.pathfinder = Pathfinder(self.world_map)
        self.agent = Agent(self.knowledge, self.world_map, self.add_log, self.pathfinder)
        self.ui = UI(self.screen, self.agent, self)
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
            state = self.agent.q_learning.get_state(self.agent, self.world_map)
            action = self.agent.ai_decide_action(self.world_map)

            # The action from ai_decide_action can be a tuple
            action_for_q_table = action
            if isinstance(action, tuple):
                if action[0] == "move_to_camp":
                    action_for_q_table = "move_to_camp"
                else:
                    action_for_q_table = f"{action[0]}_{action[1]}"

            success, result, new_delay = self.agent.execute_action(action, self.world_map)

            reward = self.agent.reward_values.get(action_for_q_table, 0) if success else -10
            next_state = self.agent.q_learning.get_state(self.agent, self.world_map)
            self.agent.q_learning.update_q_table(state, action_for_q_table, reward, next_state)

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

    def run(self):
        while self.running:
            delta_time = self.clock.tick(60) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                if event.type == pygame.MOUSEWHEEL:
                    self.ui_scroll_y += event.y * 30
                    self.ui_scroll_y = min(0, self.ui_scroll_y)
                    self.ui_scroll_y = max(-(2200 - 800), self.ui_scroll_y)
                if event.type == pygame.MOUSEBUTTONDOWN:
                    mouse_pos = pygame.mouse.get_pos()
                    if not self.agent:
                        if mouse_pos[1] > 2200 - 300:
                            self.start_new_attempt()
                    else:
                        button_y = 2200 - 150
                        button_w = (1025 - 40) // 2
                        if 15 <= mouse_pos[0] <= 15 + button_w and button_y <= mouse_pos[1] <= button_y + 120:
                            self.paused = not self.paused
                        if 25 + button_w <= mouse_pos[0] <= 25 + button_w * 2 and button_y <= mouse_pos[1] <= button_y + 120:
                            if not self.simulation_active:
                                self.start_new_attempt()
            if self.simulation_active and not self.paused:
                self.simulate_tick(delta_time)
            if self.ui:
                self.ui.draw()
            else:
                # Draw a simple menu if ui is not initialized
                self.screen.fill((0,0,0))
                title = self.font_huge.render("AI SURVIVAL", True, (255, 255, 0))
                self.screen.blit(title, (1025//2 - title.get_width()//2, 150))
                button = pygame.Rect(100, 2200 - 300, 1025 - 200, 180)
                pygame.draw.rect(self.screen, (0, 255, 0), button)
                text = self.font_large.render("ROZPOCZNIJ GRĘ", True, (255, 255, 255))
                self.screen.blit(text, (1025//2 - text.get_width()//2, 2200 - 300 + 50))
                pygame.display.flip()

        self.knowledge.save_to_file()
        pygame.quit()

if __name__ == "__main__":
    game = Game()
    game.run()
